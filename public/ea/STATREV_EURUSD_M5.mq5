//+------------------------------------------------------------------+
//|                                             STATREV_EURUSD_M5.mq5 |
//|          Single-asset statistical mean-reversion EA — EURUSD M5   |
//|                                                                   |
//|  RESEARCH STATUS: NOT VALIDATED FOR LIVE TRADING.                 |
//|  10.7 years of HistData M5 (2016-01 → 2026-09), 600-config grid,  |
//|  IS/VAL/OOS split, walk-forward, Monte Carlo, three cost regimes. |
//|  Least-bad net IS expectancy after 2.5 pip round-turn: -0.12R.    |
//|  OOS 2024–2025: -0.18R. Walk-forward aggregate: -0.17R.           |
//|  Zero of 600 in-sample configs cleared E>0 after costs.           |
//|                                                                   |
//|  This EA exists so the test is reproducible on a broker.          |
//|  Defaults match the least-bad researched set, not a claimed edge. |
//|  Demo/paper only. Do not fund a live account from this study.     |
//|                                                                   |
//|  Signal: closed M5 bar only. Fill at market after the bar close.  |
//|  One net EURUSD position. Hard broker SL/TP. 1% equity risk.      |
//|  No martingale, grid, averaging, or recovery.                     |
//+------------------------------------------------------------------+
#property copyright "STATREV research desk"
#property version   "1.00"
#property strict
#property description "EURUSD M5 statistical mean-reversion. NOT VALIDATED for live trading."

#include <Trade/Trade.mqh>
#include <Trade/PositionInfo.mqh>
#include <Trade/SymbolInfo.mqh>
#include <Trade/AccountInfo.mqh>

enum ENUM_STATREV_MODE
  {
   MODE_RESEARCH = 0,  // Match the historical engine as closely as possible
   MODE_DEMO     = 1   // Extra operational brakes for paper trading
  };

enum ENUM_PRICE_MODE
  {
   PRICE_TYPICAL_STAT = 0,
   PRICE_CLOSE_STAT   = 1,
   PRICE_RESIDUAL     = 2
  };

enum ENUM_CONFIRM_MODE
  {
   CONFIRM_IMMEDIATE  = 0,  // |Z| >= threshold
   CONFIRM_REVERSAL   = 1,  // previous bar extreme, current retraces toward 0
   CONFIRM_PERSIST    = 2,  // N consecutive bars beyond threshold
   CONFIRM_REENTRY    = 3   // was beyond, now back inside the band
  };

enum ENUM_SL_MODE
  {
   SL_FIXED_PIPS = 0,
   SL_ATR_MULT   = 1
  };

enum ENUM_NEWS_EXISTING
  {
   NEWS_LEAVE_OPEN = 0,
   NEWS_CLOSE_BEFORE = 1,
   NEWS_REDUCE_RISK  = 2
  };

//--- identity
input group "=== Identity ==="
input long               InpMagic            = 260928;
input ENUM_STATREV_MODE  InpMode             = MODE_DEMO;
input string             InpComment          = "STATREV";

//--- core signal (least-bad researched defaults)
input group "=== Signal (closed M5 bar) ==="
input ENUM_PRICE_MODE    InpPriceMode        = PRICE_TYPICAL_STAT;
input int                InpLookback         = 75;
input double             InpZEntry           = 3.0;
input ENUM_CONFIRM_MODE  InpConfirm          = CONFIRM_IMMEDIATE;
input int                InpPersistBars      = 3;
input int                InpResidualEMA      = 50;

//--- exits
input group "=== Stops / targets / time ==="
input ENUM_SL_MODE       InpSLMode           = SL_FIXED_PIPS;
input double             InpSLPips           = 15.0;
input double             InpATRMult          = 1.5;
input int                InpATRPeriod        = 14;
input double             InpTPRR             = 2.0;     // TP = RR × SL
input int                InpMaxHoldBars      = 48;
input int                InpCooldownBars     = 6;
input double             InpZExit            = 0.0;     // 0 = disabled
input double             InpMinSLPips        = 8.0;

//--- risk
input group "=== Risk (do not optimize for return) ==="
input double             InpRiskPercent      = 1.0;     // of CURRENT equity
input bool               InpOnePosition      = true;
input double             InpMaxSpreadPips    = 2.0;
input double             InpMaxCostToSL      = 0.40;    // spread/SL
input ulong              InpDeviationPoints  = 20;
input double             InpDailyLossPct     = 3.0;
input double             InpMaxDrawdownPct   = 20.0;
input int                InpMaxTradesDay     = 8;
input int                InpMaxConsecutiveLosses = 5;
input int                InpPauseAfterLossesMinutes = 120;

//--- regime filters (off by default — none survived validation)
input group "=== Regime filters (optional; none cleared VAL E>0) ==="
input bool               InpUseADX           = false;
input ENUM_TIMEFRAMES    InpADXTF            = PERIOD_H1;
input int                InpADXPeriod        = 14;
input double             InpADXMax           = 22.0;
input bool               InpUseSlope         = false;
input ENUM_TIMEFRAMES    InpSlopeTF          = PERIOD_H1;
input int                InpSlopeEMA         = 20;
input int                InpSlopeBars        = 4;
input double             InpSlopeMax         = 1.2;
input bool               InpUseVolRatio      = false;
input int                InpVolATRPeriod     = 14;
input int                InpVolATRSma        = 100;
input double             InpVolRatioMax      = 1.8;
input bool               InpUseER            = false;
input int                InpERPeriod         = 20;
input double             InpERMax            = 0.40;

//--- session (HistData study used US Eastern wall clock)
input group "=== Session / clock ==="
input bool               InpBlockRollover    = true;
input int                InpRolloverStartHour= 16;
input int                InpRolloverStartMin = 45;
input int                InpRolloverEndHour  = 17;
input int                InpRolloverEndMin   = 15;
input bool               InpBlockFridayLate  = true;
input int                InpFridayCutoffHour = 16;
input bool               InpUseSessionWindow = false;
input int                InpSessionStartHour = 3;
input int                InpSessionEndHour   = 17;

//--- news
input group "=== News (live calendar; CSV fallback for tester) ==="
input bool               InpUseNewsFilter    = false;
input int                InpNewsPreMinutes   = 30;
input int                InpNewsPostMinutes  = 30;
input bool               InpNewsHighOnly     = true;
input ENUM_NEWS_EXISTING InpNewsExisting     = NEWS_LEAVE_OPEN;
input string             InpNewsCSV          = "STATREV_news.csv"; // MQL5/Files
input int                InpNewsCacheSeconds = 1800;

//--- logging / panel
input group "=== Logging ==="
input bool               InpLogSignals       = true;
input bool               InpShowPanel        = true;

CTrade         g_trade;
CPositionInfo  g_pos;
CSymbolInfo    g_sym;
CAccountInfo   g_acct;

int g_hADX = INVALID_HANDLE;
int g_hSlopeMA = INVALID_HANDLE;
int g_hSlopeATR = INVALID_HANDLE;
int g_hATR = INVALID_HANDLE;
int g_hVolATR = INVALID_HANDLE;

datetime g_lastBarTime      = 0;
datetime g_lastExitTime     = 0;
datetime g_cooldownUntilBar = 0;
datetime g_pauseUntil       = 0;
datetime g_dayStamp         = 0;
double   g_dayStartEquity   = 0;
double   g_peakEquity       = 0;
int      g_tradesToday      = 0;
int      g_consecLosses     = 0;
bool     g_killed           = false;
string   g_killReason       = "";
string   g_lastReject       = "";
string   g_newsStatus       = "news off";
datetime g_nextNews         = 0;
datetime g_newsCacheTime    = 0;

struct NewsEvent
  {
   datetime t;
   string   ccy;
   string   impact;
   string   title;
  };
NewsEvent g_news[];
int       g_newsCount = 0;

#define PANEL_PREFIX "STATREV_"

//+------------------------------------------------------------------+
int OnInit()
  {
   if(_Period != PERIOD_M5)
      Print("STATREV warning: researched on EURUSD M5. Current TF is ", EnumToString(_Period));
   if(StringFind(_Symbol, "EURUSD") < 0)
      Print("STATREV warning: researched on EURUSD only. Symbol is ", _Symbol);

   g_sym.Name(_Symbol);
   g_sym.Refresh();
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints((int)InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.LogLevel(LOG_LEVEL_ERRORS);

   g_peakEquity     = g_acct.Equity();
   g_dayStartEquity = g_acct.Equity();
   g_dayStamp       = DayStamp(TimeCurrent());

   if(InpMode == MODE_DEMO)
      Print("STATREV DEMO mode. Operational brakes ON. NOT a live-trading recommendation.");
   else
      Print("STATREV RESEARCH mode. Defaults reproduce the least-bad historical set. Hypothesis was NOT validated after costs.");

   g_hATR     = iATR(_Symbol, PERIOD_M5, InpATRPeriod);
   g_hVolATR  = iATR(_Symbol, PERIOD_M5, InpVolATRPeriod);
   g_hADX     = iADX(_Symbol, InpADXTF, InpADXPeriod);
   g_hSlopeMA = iMA(_Symbol, InpSlopeTF, InpSlopeEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hSlopeATR= iATR(_Symbol, InpSlopeTF, InpATRPeriod);
   EventSetTimer(60);
   if(InpUseNewsFilter)
      RefreshNews(true);

   if(InpShowPanel)
      BuildPanel();

   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(g_hADX != INVALID_HANDLE) IndicatorRelease(g_hADX);
   if(g_hSlopeMA != INVALID_HANDLE) IndicatorRelease(g_hSlopeMA);
   if(g_hSlopeATR != INVALID_HANDLE) IndicatorRelease(g_hSlopeATR);
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hVolATR != INVALID_HANDLE) IndicatorRelease(g_hVolATR);
   ObjectsDeleteAll(0, PANEL_PREFIX);
  }

void OnTick()
  {
   g_sym.RefreshRates();
   g_sym.Refresh();
   UpdateDayAndKill();
   ManageOpenPosition();
   if(InpShowPanel)
      UpdatePanel();

   if(!IsNewM5Bar())
      return;

   if(g_killed)
      return;

   EvaluateEntryOnClosedBar();
  }

void OnTimer()
  {
   if(InpUseNewsFilter)
      RefreshNews(false);
  }

//+------------------------------------------------------------------+
//| New-bar detection (closed bar = index 1)                         |
//+------------------------------------------------------------------+
bool IsNewM5Bar()
  {
   datetime t[];
   if(CopyTime(_Symbol, PERIOD_M5, 0, 2, t) < 2)
      return false;
   if(t[1] != g_lastBarTime)
     {
      g_lastBarTime = t[1];
      return true;
     }
   return false;
  }

datetime DayStamp(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   return StructToTime(dt);
  }

void UpdateDayAndKill()
  {
   datetime ds = DayStamp(TimeCurrent());
   if(ds != g_dayStamp)
     {
      g_dayStamp = ds;
      g_dayStartEquity = g_acct.Equity();
      g_tradesToday = 0;
     }
   double eq = g_acct.Equity();
   if(eq > g_peakEquity)
      g_peakEquity = eq;

   if(InpMode == MODE_DEMO || InpDailyLossPct > 0)
     {
      double dayLoss = (g_dayStartEquity - eq) / MathMax(g_dayStartEquity, 1.0) * 100.0;
      if(InpDailyLossPct > 0 && dayLoss >= InpDailyLossPct)
        {
         g_killed = true;
         g_killReason = StringFormat("daily loss %.2f%% >= %.2f%%", dayLoss, InpDailyLossPct);
        }
     }
   if(InpMaxDrawdownPct > 0 && g_peakEquity > 0)
     {
      double dd = (g_peakEquity - eq) / g_peakEquity * 100.0;
      if(dd >= InpMaxDrawdownPct)
        {
         g_killed = true;
         g_killReason = StringFormat("drawdown %.2f%% >= %.2f%% kill switch", dd, InpMaxDrawdownPct);
        }
     }
  }

bool HasOurPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; --i)
     {
      if(g_pos.SelectByIndex(i) && g_pos.Symbol() == _Symbol && g_pos.Magic() == InpMagic)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Position management: time stop, z-exit, news close               |
//+------------------------------------------------------------------+
void ManageOpenPosition()
  {
   if(!HasOurPosition())
      return;
   if(!SelectOurPosition())
      return;

   datetime entry = (datetime)g_pos.Time();
   int held = iBarShift(_Symbol, PERIOD_M5, entry, true);
   if(held < 0)
      held = 0;

   if(InpMaxHoldBars > 0 && held >= InpMaxHoldBars)
     {
      CloseOur("time stop, held bars=" + IntegerToString(held));
      return;
     }

   if(InpZExit > 0)
     {
      double z = CurrentZ(1);
      if(MathIsValidNumber(z) && MathAbs(z) <= InpZExit)
        {
         CloseOur(StringFormat("z-exit |z|=%.3f", z));
         return;
        }
     }

   if(InpUseNewsFilter && InpNewsExisting == NEWS_CLOSE_BEFORE && InNewsWindow())
      CloseOur("news blackout close");
  }

bool SelectOurPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; --i)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         return g_pos.SelectByTicket(ticket);
        }
     }
   return false;
  }

void CloseOur(const string why)
  {
   if(!SelectOurPosition())
      return;
   double pnl = g_pos.Profit() + g_pos.Swap() + g_pos.Commission();
   ulong ticket = g_pos.Ticket();
   if(!g_trade.PositionClose(ticket))
     {
      Print("STATREV close failed ", why, " ret=", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
      return;
     }
   g_lastExitTime = TimeCurrent();
   g_cooldownUntilBar = iTime(_Symbol, PERIOD_M5, 0) + InpCooldownBars * PeriodSeconds(PERIOD_M5);
   if(pnl < 0)
     {
      g_consecLosses++;
      if(InpMaxConsecutiveLosses > 0 && g_consecLosses >= InpMaxConsecutiveLosses)
         g_pauseUntil = TimeCurrent() + InpPauseAfterLossesMinutes * 60;
     }
   else
      g_consecLosses = 0;
   Print("STATREV closed #", ticket, " ", why, " pnl=", DoubleToString(pnl, 2));
  }

//+------------------------------------------------------------------+
//| Signal on last CLOSED bar (index 1). Enter now (bar 0 open~now). |
//+------------------------------------------------------------------+
void EvaluateEntryOnClosedBar()
  {
   g_lastReject = "";
   if(InpOnePosition && HasOurPosition())
     { g_lastReject = "already in position"; return; }
   if(TimeCurrent() < g_pauseUntil)
     { g_lastReject = "consecutive-loss pause"; return; }
   if(InpCooldownBars > 0 && TimeCurrent() < g_cooldownUntilBar)
     { g_lastReject = "cooldown"; return; }
   if(InpMaxTradesDay > 0 && g_tradesToday >= InpMaxTradesDay)
     { g_lastReject = "max trades/day"; return; }
   if(!SessionAllowed())
     { g_lastReject = "session/rollover block"; return; }
   if(InpUseNewsFilter && InNewsWindow())
     { g_lastReject = "news blackout"; return; }

   double spreadPips = SpreadPips();
   if(InpMaxSpreadPips > 0 && spreadPips > InpMaxSpreadPips)
     {
      g_lastReject = StringFormat("spread %.2f > max %.2f", spreadPips, InpMaxSpreadPips);
      return;
     }

   if(!RegimeAllowed())
      return;

   double z1 = CurrentZ(1);
   double z2 = CurrentZ(2);
   if(!MathIsValidNumber(z1))
     { g_lastReject = "z undefined"; return; }

   int sig = SignalFromZ(z1, z2);
   if(sig == 0)
     { g_lastReject = StringFormat("no signal z=%.3f", z1); return; }

   double slDist = StopDistance();
   if(slDist <= 0)
     { g_lastReject = "invalid SL distance"; return; }
   double slPips = slDist / PipSize();
   if(slPips < InpMinSLPips)
     { g_lastReject = StringFormat("SL %.2f pips < min", slPips); return; }
   if(spreadPips / slPips > InpMaxCostToSL)
     { g_lastReject = StringFormat("spread/SL %.2f > %.2f", spreadPips / slPips, InpMaxCostToSL); return; }

   double lot = LotsForRisk(slDist);
   if(lot <= 0)
     { g_lastReject = "lot=0"; return; }

   double price = (sig > 0) ? g_sym.Ask() : g_sym.Bid();
   double sl, tp;
   if(sig > 0)
     {
      sl = price - slDist;
      tp = price + InpTPRR * slDist;
     }
   else
     {
      sl = price + slDist;
      tp = price - InpTPRR * slDist;
     }
   sl = NormalizePrice(sl);
   tp = NormalizePrice(tp);
   price = NormalizePrice(price);

   double stops = g_sym.StopsLevel() * g_sym.Point();
   if(stops > 0 && (MathAbs(price - sl) < stops || MathAbs(price - tp) < stops))
     { g_lastReject = "stops level"; return; }

   bool ok;
   if(sig > 0)
      ok = g_trade.Buy(lot, _Symbol, 0, sl, tp, InpComment);
   else
      ok = g_trade.Sell(lot, _Symbol, 0, sl, tp, InpComment);

   if(!ok)
     {
      g_lastReject = StringFormat("order fail %u %s", g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      Print("STATREV ", g_lastReject, " z=", DoubleToString(z1, 3),
            " lot=", DoubleToString(lot, 2), " sl=", DoubleToString(sl, _Digits),
            " tp=", DoubleToString(tp, _Digits), " spread=", DoubleToString(spreadPips, 2));
      return;
     }
   g_tradesToday++;
   if(InpLogSignals)
      PrintFormat("STATREV ENTRY %s z=%.3f lot=%.2f sl=%.5f tp=%.5f slPips=%.2f spread=%.2f equity=%.2f",
                  (sig > 0 ? "LONG" : "SHORT"), z1, lot, sl, tp, slPips, spreadPips, g_acct.Equity());
  }

int SignalFromZ(const double z1, const double z2)
  {
   int persistL = 0, persistS = 0;
   if(InpConfirm == CONFIRM_PERSIST)
     {
      for(int i = 1; i <= InpPersistBars; ++i)
        {
         double zi = CurrentZ(i);
         if(!MathIsValidNumber(zi))
            return 0;
         if(zi <= -InpZEntry) persistL++;
         else if(zi >= InpZEntry) persistS++;
        }
     }

   switch(InpConfirm)
     {
      case CONFIRM_IMMEDIATE:
         if(z1 <= -InpZEntry) return 1;
         if(z1 >=  InpZEntry) return -1;
         return 0;
      case CONFIRM_REVERSAL:
         if(!MathIsValidNumber(z2)) return 0;
         if(z2 <= -InpZEntry && z1 > z2 && z1 < 0.0) return 1;
         if(z2 >=  InpZEntry && z1 < z2 && z1 > 0.0) return -1;
         return 0;
      case CONFIRM_PERSIST:
         if(persistL >= InpPersistBars) return 1;
         if(persistS >= InpPersistBars) return -1;
         return 0;
      case CONFIRM_REENTRY:
         if(!MathIsValidNumber(z2)) return 0;
         if(z2 <= -InpZEntry && z1 > -InpZEntry && z1 < 0.0) return 1;
         if(z2 >=  InpZEntry && z1 <  InpZEntry && z1 > 0.0) return -1;
         return 0;
     }
   return 0;
  }

//+------------------------------------------------------------------+
//| Z-score on closed bars. Sample std (n-1), matches the Python engine.
//+------------------------------------------------------------------+
double CurrentZ(const int shift)
  {
   int need = InpLookback + InpResidualEMA + 5;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M5, shift, need, rates) < InpLookback)
      return EMPTY_VALUE;

   double px[];
   ArrayResize(px, InpLookback);
   if(InpPriceMode == PRICE_RESIDUAL)
     {
      int n = InpLookback + InpResidualEMA;
      double c[];
      ArrayResize(c, n);
      for(int i = 0; i < n; ++i)
         c[i] = rates[i].close;
      double alpha = 2.0 / (InpResidualEMA + 1.0);
      double e = c[n - 1];
      for(int i = n - 2; i >= 0; --i)
         e = alpha * c[i] + (1.0 - alpha) * e;
      // rebuild residual of last lookback using a running EMA from oldest
      double ema = rates[InpLookback + InpResidualEMA - 1].close;
      for(int i = InpLookback + InpResidualEMA - 2; i >= 0; --i)
        {
         ema = alpha * rates[i].close + (1.0 - alpha) * ema;
         if(i < InpLookback)
            px[i] = rates[i].close - ema;
        }
     }
   else
     {
      for(int i = 0; i < InpLookback; ++i)
        {
         if(InpPriceMode == PRICE_CLOSE_STAT)
            px[i] = rates[i].close;
         else
            px[i] = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
        }
     }

   double mean = 0.0;
   for(int i = 0; i < InpLookback; ++i)
      mean += px[i];
   mean /= InpLookback;
   double var = 0.0;
   for(int i = 0; i < InpLookback; ++i)
     {
      double d = px[i] - mean;
      var += d * d;
     }
   var /= (InpLookback - 1); // sample
   if(var <= 0.0)
      return EMPTY_VALUE;
   return (px[0] - mean) / MathSqrt(var);
  }

double PipSize()
  {
   int digits = (int)g_sym.Digits();
   double pt = g_sym.Point();
   if(digits == 3 || digits == 5)
      return pt * 10.0;
   return pt;
  }

double SpreadPips()
  {
   return (g_sym.Ask() - g_sym.Bid()) / PipSize();
  }

double StopDistance()
  {
   if(InpSLMode == SL_ATR_MULT)
     {
      if(g_hATR == INVALID_HANDLE)
         return 0;
      double atr[];
      ArraySetAsSeries(atr, true);
      if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1)
         return 0;
      return atr[0] * InpATRMult;
     }
   return InpSLPips * PipSize();
  }

double LotsForRisk(const double slDist)
  {
   double equity = g_acct.Equity();
   double riskMoney = equity * InpRiskPercent / 100.0;
   double tickSize  = g_sym.TickSize();
   double tickValue = g_sym.TickValue();
   if(tickSize <= 0 || tickValue <= 0 || slDist <= 0)
      return 0;
   double ticks = slDist / tickSize;
   double lots  = riskMoney / (ticks * tickValue);
   double vmin  = g_sym.LotsMin();
   double vmax  = g_sym.LotsMax();
   double step  = g_sym.LotsStep();
   if(step <= 0)
      step = vmin;
   lots = MathFloor(lots / step) * step;
   if(lots < vmin)
      return 0;
   if(lots > vmax)
      lots = vmax;
   double margin = 0;
   ENUM_ORDER_TYPE ot = ORDER_TYPE_BUY;
   if(!OrderCalcMargin(ot, _Symbol, lots, g_sym.Ask(), margin))
      return lots;
   if(margin > g_acct.FreeMargin() * 0.9)
     {
      lots = MathFloor((lots * (g_acct.FreeMargin() * 0.9 / margin)) / step) * step;
      if(lots < vmin)
         return 0;
     }
   int volDigits = 2;
   if(step >= 1.0) volDigits = 0;
   else if(step >= 0.1) volDigits = 1;
   else if(step >= 0.01) volDigits = 2;
   else volDigits = 3;
   return NormalizeDouble(lots, volDigits);
  }

double NormalizePrice(double p)
  {
   return NormalizeDouble(p, (int)g_sym.Digits());
  }

//+------------------------------------------------------------------+
bool SessionAllowed()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int hm = dt.hour * 60 + dt.min;
   if(InpBlockRollover)
     {
      int a = InpRolloverStartHour * 60 + InpRolloverStartMin;
      int b = InpRolloverEndHour * 60 + InpRolloverEndMin;
      if(a <= b)
        {
         if(hm >= a && hm < b)
            return false;
        }
      else if(hm >= a || hm < b)
         return false;
     }
   if(InpBlockFridayLate && dt.day_of_week == 5 && dt.hour >= InpFridayCutoffHour)
      return false;
   if(InpUseSessionWindow)
     {
      int a = InpSessionStartHour * 60;
      int b = InpSessionEndHour * 60;
      if(a <= b)
        {
         if(!(hm >= a && hm < b))
            return false;
        }
      else if(!(hm >= a || hm < b))
         return false;
     }
   return true;
  }

bool RegimeAllowed()
  {
   if(InpUseADX)
     {
      if(g_hADX == INVALID_HANDLE)
        { g_lastReject = "ADX handle"; return false; }
      double buf[];
      ArraySetAsSeries(buf, true);
      if(CopyBuffer(g_hADX, 0, 1, 1, buf) < 1 || !MathIsValidNumber(buf[0]))
        { g_lastReject = "ADX n/a"; return false; }
      if(buf[0] >= InpADXMax)
        { g_lastReject = StringFormat("ADX %.1f >= %.1f", buf[0], InpADXMax); return false; }
     }
   if(InpUseSlope)
     {
      if(g_hSlopeMA == INVALID_HANDLE || g_hSlopeATR == INVALID_HANDLE)
        { g_lastReject = "slope handle"; return false; }
      double e[], a[];
      ArraySetAsSeries(e, true);
      ArraySetAsSeries(a, true);
      if(CopyBuffer(g_hSlopeMA, 0, 1, InpSlopeBars + 1, e) < InpSlopeBars + 1)
        { g_lastReject = "slope n/a"; return false; }
      if(CopyBuffer(g_hSlopeATR, 0, 1, 1, a) < 1 || a[0] <= 0)
        { g_lastReject = "slope ATR n/a"; return false; }
      double sn = MathAbs(e[0] - e[InpSlopeBars]) / a[0];
      if(sn >= InpSlopeMax)
        { g_lastReject = StringFormat("|slope|/ATR %.2f >= %.2f", sn, InpSlopeMax); return false; }
     }
   if(InpUseVolRatio)
     {
      if(g_hVolATR == INVALID_HANDLE)
        { g_lastReject = "vol handle"; return false; }
      double a[];
      ArraySetAsSeries(a, true);
      if(CopyBuffer(g_hVolATR, 0, 1, InpVolATRSma, a) < InpVolATRSma)
        { g_lastReject = "vol n/a"; return false; }
      double sma = 0;
      for(int i = 0; i < InpVolATRSma; ++i)
         sma += a[i];
      sma /= InpVolATRSma;
      if(sma <= 0)
         return false;
      double vr = a[0] / sma;
      if(vr >= InpVolRatioMax)
        { g_lastReject = StringFormat("vol ratio %.2f >= %.2f", vr, InpVolRatioMax); return false; }
     }
   if(InpUseER)
     {
      double er = EfficiencyRatio(InpERPeriod);
      if(!MathIsValidNumber(er))
        { g_lastReject = "ER n/a"; return false; }
      if(er >= InpERMax)
        { g_lastReject = StringFormat("ER %.2f >= %.2f", er, InpERMax); return false; }
     }
   return true;
  }

double EfficiencyRatio(const int period)
  {
   double c[];
   ArraySetAsSeries(c, true);
   if(CopyClose(_Symbol, PERIOD_M5, 1, period + 1, c) < period + 1)
      return EMPTY_VALUE;
   double dir = MathAbs(c[0] - c[period]);
   double vol = 0;
   for(int i = 0; i < period; ++i)
      vol += MathAbs(c[i] - c[i + 1]);
   if(vol <= 0)
      return 0;
   return dir / vol;
  }

//+------------------------------------------------------------------+
//| News: MT5 calendar + CSV fallback                                |
//+------------------------------------------------------------------+
void RefreshNews(const bool force)
  {
   if(!force && (TimeCurrent() - g_newsCacheTime) < InpNewsCacheSeconds)
      return;
   g_newsCacheTime = TimeCurrent();
   g_newsCount = 0;
   ArrayResize(g_news, 0);

   datetime from = TimeCurrent() - 2 * 86400;
   datetime to   = TimeCurrent() + 7 * 86400;
   bool gotCal = LoadCalendarNews(from, to);
   if(!gotCal)
      LoadCsvNews();

   g_newsStatus = StringFormat("%d events cached", g_newsCount);
   g_nextNews = 0;
   datetime now = TimeCurrent();
   for(int i = 0; i < g_newsCount; ++i)
     {
      if(g_news[i].t > now)
        {
         g_nextNews = g_news[i].t;
         break;
        }
     }
  }

bool LoadCalendarNews(datetime from, datetime to)
  {
#ifdef __MQL5__
   MqlCalendarValue values[];
   // Country codes: US, EU (ECB/Eurozone). Filter high impact.
   string countries[2];
   countries[0] = "US";
   countries[1] = "EU";
   int total = 0;
   for(int c = 0; c < 2; ++c)
     {
      MqlCalendarValue tmp[];
      ResetLastError();
      int n = CalendarValueHistory(tmp, from, to, countries[c]);
      if(n <= 0)
         continue;
      int old = g_newsCount;
      ArrayResize(g_news, old + n);
      for(int i = 0; i < n; ++i)
        {
         MqlCalendarEvent ev;
         if(!CalendarEventById(tmp[i].event_id, ev))
            continue;
         if(InpNewsHighOnly && ev.importance < CALENDAR_IMPORTANCE_HIGH)
            continue;
         g_news[g_newsCount].t = tmp[i].time;
         g_news[g_newsCount].ccy = ev.currency;
         g_news[g_newsCount].impact = EnumToString(ev.importance);
         g_news[g_newsCount].title = ev.name;
         g_newsCount++;
        }
      total += n;
     }
   if(g_newsCount > 1)
      SortNews();
   return g_newsCount > 0;
#else
   return false;
#endif
  }

void LoadCsvNews()
  {
   int fh = FileOpen(InpNewsCSV, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(fh == INVALID_HANDLE)
     {
      g_newsStatus = "calendar empty; CSV not found (" + InpNewsCSV + ")";
      return;
     }
   while(!FileIsEnding(fh))
     {
      string tstr = FileReadString(fh);
      string ccy  = FileReadString(fh);
      string imp  = FileReadString(fh);
      string title= FileReadString(fh);
      if(tstr == "" || tstr[0] == '#')
         continue;
      datetime t = StringToTime(tstr);
      if(t <= 0)
         continue;
      if(InpNewsHighOnly && StringFind(imp, "high") < 0 && StringFind(imp, "HIGH") < 0)
         continue;
      ArrayResize(g_news, g_newsCount + 1);
      g_news[g_newsCount].t = t;
      g_news[g_newsCount].ccy = ccy;
      g_news[g_newsCount].impact = imp;
      g_news[g_newsCount].title = title;
      g_newsCount++;
     }
   FileClose(fh);
   SortNews();
   g_newsStatus = StringFormat("CSV %d events", g_newsCount);
  }

void SortNews()
  {
   for(int i = 0; i < g_newsCount; ++i)
      for(int j = i + 1; j < g_newsCount; ++j)
         if(g_news[j].t < g_news[i].t)
           {
            NewsEvent tmp = g_news[i];
            g_news[i] = g_news[j];
            g_news[j] = tmp;
           }
  }

bool InNewsWindow()
  {
   RefreshNews(false);
   datetime now = TimeCurrent();
   int pre = InpNewsPreMinutes * 60;
   int post= InpNewsPostMinutes * 60;
   for(int i = 0; i < g_newsCount; ++i)
     {
      datetime t = g_news[i].t;
      if(now >= t - pre && now <= t + post)
        {
         g_newsStatus = StringFormat("BLOCK %s %s", TimeToString(t, TIME_DATE|TIME_MINUTES), g_news[i].title);
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Chart panel                                                      |
//+------------------------------------------------------------------+
void BuildPanel()
  {
   ObjectsDeleteAll(0, PANEL_PREFIX);
   CreateLabel("title", 12, 18, "STATREV  EURUSD M5   NOT VALIDATED", 11, true);
   for(int i = 1; i <= 14; ++i)
      CreateLabel("r" + IntegerToString(i), 12, 18 + i * 16, "-", 9, false);
  }

void CreateLabel(const string id, int x, int y, const string text, int sz, bool bold)
  {
   string name = PANEL_PREFIX + id;
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clrGainsboro);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, sz);
      ObjectSetString(0, name, OBJPROP_FONT, bold ? "Arial Bold" : "Consolas");
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
  }

void SetRow(const int i, const string text)
  {
   ObjectSetString(0, PANEL_PREFIX + "r" + IntegerToString(i), OBJPROP_TEXT, text);
  }

void UpdatePanel()
  {
   double z = CurrentZ(1);
   double sp = SpreadPips();
   double sl = StopDistance() / PipSize();
   double eq = g_acct.Equity();
   double dd = (g_peakEquity > 0) ? (g_peakEquity - eq) / g_peakEquity * 100.0 : 0;
   double day = (g_dayStartEquity > 0) ? (eq - g_dayStartEquity) / g_dayStartEquity * 100.0 : 0;
   string mode = (InpMode == MODE_DEMO ? "DEMO" : "RESEARCH");
   SetRow(1, StringFormat("mode %s   magic %I64d   killed %s", mode, InpMagic, g_killed ? "YES" : "no"));
   SetRow(2, StringFormat("z=%.3f  entry |z|>=%.2f  lookback %d  confirm %d", z, InpZEntry, InpLookback, InpConfirm));
   SetRow(3, StringFormat("SL %.1f pips  TP %.1fx  hold<=%d  cooldown %d", sl, InpTPRR, InpMaxHoldBars, InpCooldownBars));
   SetRow(4, StringFormat("spread %.2f pips  max %.2f  cost/SL %.2f", sp, InpMaxSpreadPips, (sl > 0 ? sp / sl : 0)));
   SetRow(5, StringFormat("equity %.2f  risk %.2f%%  day P/L %.2f%%  DD %.2f%%", eq, InpRiskPercent, day, dd));
   SetRow(6, StringFormat("trades today %d/%d  consec losses %d  pos %s",
                          g_tradesToday, InpMaxTradesDay, g_consecLosses, HasOurPosition() ? "OPEN" : "flat"));
   SetRow(7, "ADX " + (InpUseADX ? "ON" : "off") +
            "  slope " + (InpUseSlope ? "ON" : "off") +
            "  vol " + (InpUseVolRatio ? "ON" : "off") +
            "  ER " + (InpUseER ? "ON" : "off"));
   SetRow(8, "news " + g_newsStatus);
   if(g_nextNews > 0)
      SetRow(9, "next event " + TimeToString(g_nextNews, TIME_DATE|TIME_MINUTES));
   else
      SetRow(9, "next event  n/a");
   SetRow(10, "session " + (SessionAllowed() ? "open" : "BLOCKED") +
              "   " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   SetRow(11, "last reject: " + (g_lastReject == "" ? "-" : g_lastReject));
   SetRow(12, g_killed ? ("KILL " + g_killReason) : "hypothesis NOT validated after costs — demo/paper only");
   SetRow(13, "lot preview " + DoubleToString(LotsForRisk(StopDistance()), 2));
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD && trans.deal > 0)
     {
      if(HistoryDealSelect(trans.deal))
        {
         long magic = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
         if(magic != InpMagic)
            return;
         ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
         if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_INOUT)
           {
            double pnl = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) +
                         HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
                         HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
            if(pnl < 0)
              {
               g_consecLosses++;
               if(InpMaxConsecutiveLosses > 0 && g_consecLosses >= InpMaxConsecutiveLosses)
                  g_pauseUntil = TimeCurrent() + InpPauseAfterLossesMinutes * 60;
              }
            else
               g_consecLosses = 0;
            g_lastExitTime = TimeCurrent();
            g_cooldownUntilBar = TimeCurrent() + InpCooldownBars * PeriodSeconds(PERIOD_M5);
           }
        }
     }
  }
//+------------------------------------------------------------------+
