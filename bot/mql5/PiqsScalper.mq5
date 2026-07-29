//+------------------------------------------------------------------+
//|  PiqsScalper.mq5 - Expert Advisor Utama                           |
//|  XAUUSD M15 RSI Scalping Bot                                     |
//|  Version: 1.0.0                                                   |
//+------------------------------------------------------------------+
//|  ARSITEKTUR MODULAR:                                             |
//|    Config.mqh        → Konstanta & konfigurasi                   |
//|    RSITrigger.mqh   → Logika sinyal RSI                          |
//|    MoneyManagement.mqh → Kalkulasi lot & risk                    |
//|    APIClient.mqh    → Komunikasi HTTP ke server                  |
//|                                                                  |
//|  ROLLBACK GUIDE:                                                 |
//|    Jika error setelah modifikasi, replace file modul terkait     |
//|    saja (misal: RSITrigger.mqh) tanpa perlu ubah EA utama       |
//+------------------------------------------------------------------+

#property copyright   "PiqsBot Trade"
#property version      "1.0.0"
#property description  "XAUUSD M15 RSI Scalper - Modular EA"
#property strict

//+------------------------------------------------------------------+
//|  INCLUDES - Panggil SEMUA modul di sini                           |
//+------------------------------------------------------------------+
#include <Include/RSITrigger.mqh>
#include <Include/MoneyManagement.mqh>
#include <Include/APIClient.mqh>

//+------------------------------------------------------------------+
//|  INPUT PARAMETERS - Bisa diedit dari Strategy Tester / EA        |
//+------------------------------------------------------------------+
// --- RSI Settings ---
input group "=== RSI Configuration ==="
input int      InpRSIPeriod     = 14;           // RSI Period
input double   InpRSIExtreme    = 15.0;         // Extreme Level (Buy/Sell trigger)
input double   InpRSIWarning    = 30.0;         // Warning Level (Lower)
input double   InpRSISellWarn   = 70.0;         // Warning Level (Upper)
input double   InpRSISellExt    = 85.0;         // Extreme Level (Upper)

// --- Money Management ---
input group "=== Money Management ==="
input double   InpLotSize       = 0.10;         // Fixed Lot Size
input double   InpRiskPercent   = 2.0;          // Risk Per Trade (%)
input double   InpMaxLot        = 1.0;          // Maximum Lot
input int      InpMaxDaily     = 10;           // Max Daily Trades
input int      InpMaxSpread     = 30;           // Max Spread (points)

// --- Trade Settings ---
input group "=== Trade Levels ==="
input int      InpStopLoss      = 150;          // Stop Loss (points)
input int      InpTakeProfit    = 100;          // Take Profit (points)
input ulong    InpMagic         = 20240728;     // Magic Number

// --- Session ---
input group "=== Trading Hours ==="
input int      InpSessionStart  = 9;            // Session Start Hour
input int      InpSessionEnd    = 21;          // Session End Hour

// --- API Settings ---
input group "=== Web Logging ==="
input string   InpAPIUrl        = "https://your-server.com/backend/log_trade.php"; // API URL
input string   InpAPIKey        = "pk_live_piqs_xauusd_2024"; // API Secret Key
input bool     InpEnableLog     = true;         // Enable Web Logging

//+------------------------------------------------------------------+
//|  GLOBAL VARIABLES                                                |
//+------------------------------------------------------------------+

// Objek modul (dideklarasikan sekali, digunakan ulang)
static CRSITrigger       g_rsi;             // Modul RSI
static CMoneyManager     g_mm;              // Modul Money Management

// State tracking
static bool              g_initialized      = false;
static datetime           g_lastTradeTime    = 0;
static int               g_consecutiveLoss   = 0;
static bool              g_pauseMode         = false;

// Counter untuk display
static int               g_tickCounter       = 0;
static datetime          g_lastBarTime       = 0;

//+------------------------------------------------------------------+
//|  EXPERT INITIALIZATION                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("===========================================");
   Print("  PiqsScalper EA v1.0.0 - INITIALIZING");
   Print("  Symbol: ", SYMBOL_NAME);
   Print("  Timeframe: M15");
   Print("  RSI Period: ", RSI_PERIOD);
   Print("  Lot: ", DoubleToString(LOT_SIZE, 2));
   Print("  SL: ", STOP_LOSS_PTS, " pts | TP: ", TAKE_PROFIT_PTS, " pts");
   Print("===========================================");

   // Cek symbol
   if(!SymbolSelect(SYMBOL_NAME, true))
   {
      Print("ERROR: Symbol ", SYMBOL_NAME, " tidak tersedia!");
      return(INIT_PARAMETERS_INCORRECT);
   }

   // Inisialisasi modul RSI
   g_rsi = CRSITrigger(SYMBOL_NAME, TIMEFRAME_WORK);
   if(!g_rsi.Initialize())
   {
      Print("ERROR: Gagal inisialisasi RSI!");
      return(INIT_FAILED);
   }

   // Inisialisasi money manager
   g_mm = CMoneyManager(LOT_MODE_FIXED);
   g_mm.SetLotMode(LOT_MODE_FIXED);

   // Cek konektivitas server API
   if(InpEnableLog)
   {
      bool apiOk = g_apiClient.PingServer();
      if(!apiOk)
         Print("WARNING: API server tidak reachable - logging disable");
   }

   // Beri waktu indikator RSI untuk mengisi data
   Sleep(500);

   g_initialized = true;
   Print("PiqsScalper READY - Monitoring ", SYMBOL_NAME);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//|  EXPERT DEINIT                                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Bersihkan handle indikator
   g_rsi.~CRSITrigger();

   string reasonText = "";
   switch(reason)
   {
      case REASON_PROGRAM:      reasonText = "EA dihentikan oleh user"; break;
      case REASON_REMOVE:       reasonText = "EA dihapus dari chart"; break;
      case REASON_RECOMPILE:    reasonText = "EA dikompilasi ulang"; break;
      case REASON_CHARTCHANGE:  reasonText = "Chart/symbol berubah"; break;
      case REASON_CHARTCLOSE:    reasonText = "Chart ditutup"; break;
      case REASON_PARAMETERS:   reasonText = "Parameter diubah"; break;
      case REASON_ACCOUNT:       reasonText = "Account berubah"; break;
      default:                   reasonText = "Unknown"; break;
   }

   Print("===========================================");
   Print("  PiqsScalper DEINIT | Reason: ", reasonText);
   Print("  API Success: ", g_apiClient.GetSuccessCount(),
         " | Failed: ", g_apiClient.GetFailCount());
   Print("===========================================");
}

//+------------------------------------------------------------------+
//|  EXPERT TICK - Dijalankan setiap tick/price update               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Cegah eksekusi jika belum initialization
   if(!g_initialized)
      return;

   // Cek apakah sudah dalam satu candle baru
   datetime currentBar = iTime(SYMBOL_NAME, TIMEFRAME_WORK, 0);
   if(currentBar == g_lastBarTime)
      return; // Masih candle yang sama, skip
   g_lastBarTime = currentBar;

   //+----------------------------------------------------+
   //|  CEK TRADING HOURS                                  |
   //+----------------------------------------------------+
   if(!IsWithinTradingHours())
   {
      // Di luar jam trading - close semua posisi
      ManageOpenPositions();
      return;
   }

   //+----------------------------------------------------+
   //|  CEK PAUSE MODE (kalau daily loss limit tercapai)  |
   //+----------------------------------------------------+
   if(g_pauseMode)
   {
      // Cek apakah sudah masuk jam baru (reset pause)
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      if(dt.hour == InpSessionStart)
         g_pauseMode = false;

      return;
   }

   //+----------------------------------------------------+
   //|  CEK MANAGE POSISI TERBUKA                         |
   //|  - Trailing Stop                                  |
   //|  - Break Even                                     |
   //|  - Close jika sinyal balik                        |
   //+----------------------------------------------------+
   ManageOpenPositions();

   //+----------------------------------------------------+
   //|  CEK SINYAL BARU                                  |
   //|  - Cek RSI untuk buy/sell signal                  |
   //|  - Jika ada sinyal + tidak ada posisi → eksekusi  |
   //+----------------------------------------------------+
   CheckAndExecuteSignal();
}

//+------------------------------------------------------------------+
//|  CEK JAM TRADING                                                 |
//+------------------------------------------------------------------+
bool IsWithinTradingHours()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int currentHour = dt.hour;

   return(currentHour >= InpSessionStart && currentHour <= InpSessionEnd);
}

//+------------------------------------------------------------------+
//|  MANAJEMEN POSISI TERBUKA                                       |
//|  - Trailing Stop sederhana                                       |
//|  - Break Even                                                    |
//|  - Close jika RSI memberikan sinyal berlawanan                  |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   // Iterate semua posisi dengan magic number ini
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != SYMBOL_NAME)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != MAGIC_NUMBER)
         continue;

      ulong ticket    = PositionGetInteger(POSITION_TICKET);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      double volume    = PositionGetDouble(POSITION_VOLUME);
      double profit    = PositionGetDouble(POSITION_PROFIT);
      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double ask       = SymbolInfoDouble(SYMBOL_NAME, SYMBOL_ASK);
      double bid       = SymbolInfoDouble(SYMBOL_NAME, SYMBOL_BID);

      double point     = SymbolInfoDouble(SYMBOL_NAME, SYMBOL_POINT);
      double trailingPts = 50; // 5 pip trailing

      //+---------------------------------------------+
      //|  TRAILING STOP                                |
      //+---------------------------------------------+
      if(type == POSITION_TYPE_BUY)
      {
         double newSL = bid - trailingPts * point;
         // Pindah SL jika profit sudah cukup besar dan SL belum di level tersebut
         if(profit > trailingPts * point * volume && newSL > sl)
         {
            if(sl == 0)
               newSL = openPrice; // Set BE dulu
            else
               newSL = MathMax(sl, bid - trailingPts * point);

            TradeResultHandler(ticket, ORDER_TYPE_SELL, volume, newSL, tp, "TrailingStop");
         }
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double newSL = ask + trailingPts * point;
         if(profit > trailingPts * point * volume && newSL < sl)
         {
            if(sl == 0)
               newSL = openPrice; // Set BE dulu
            else
               newSL = MathMin(sl, ask + trailingPts * point);

            TradeResultHandler(ticket, ORDER_TYPE_BUY, volume, newSL, tp, "TrailingStop");
         }
      }

      //+---------------------------------------------+
      //|  CLOSE JIKA SINYAL BERLAWANAN                |
      //+---------------------------------------------+
      bool closeSignal = false;
      string closeReason = "";

      RSI_Signal sig = g_rsi.AnalyzeSignal();

      if(type == POSITION_TYPE_BUY && sig.zone == RSI_ZONE_EXTREME_SELL)
      {
         closeSignal = true;
         closeReason = "RSI Extreme Sell";
      }
      else if(type == POSITION_TYPE_SELL && sig.zone == RSI_ZONE_EXTREME_BUY)
      {
         closeSignal = true;
         closeReason = "RSI Extreme Buy";
      }

      if(closeSignal)
      {
         TradeResultHandler(ticket,
                           type == POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY,
                           volume, 0, 0, closeReason);
      }
   }
}

//+------------------------------------------------------------------+
//|  CEK DAN EKSEKUSI SINYAL                                         |
//+------------------------------------------------------------------+
void CheckAndExecuteSignal()
{
   // Cegah double trade di candle yang sama
   datetime currentBar = iTime(SYMBOL_NAME, TIMEFRAME_WORK, 0);
   if(currentBar == g_lastTradeTime)
      return;

   //+---------------------------------------------+
   //|  CEK SYARAT UMUM                             |
   //+---------------------------------------------+
   if(!g_mm.CanOpenTrade())
      return;

   if(g_mm.HasOpenPosition())
   {
      if(ENABLE_DEBUG_LOG)
         Print(DEBUG_LOG_PREFIX, "Posisi sudah terbuka, skip signal");
      return;
   }

   //+---------------------------------------------+
   //|  CEK BUY SIGNAL                              |
   //+---------------------------------------------+
   if(g_rsi.IsBuySignal())
   {
      ExecuteTrade(ORDER_TYPE_BUY);
      g_lastTradeTime = currentBar;
      return;
   }

   //+---------------------------------------------+
   //|  CEK SELL SIGNAL                             |
   //+---------------------------------------------+
   if(g_rsi.IsSellSignal())
   {
      ExecuteTrade(ORDER_TYPE_SELL);
      g_lastTradeTime = currentBar;
      return;
   }
}

//+------------------------------------------------------------------+
//|  EKSEKUSI TRADE                                                   |
//|  Fungsi utama untuk membuka posisi                                |
//+------------------------------------------------------------------+
void ExecuteTrade(ENUM_ORDER_TYPE orderType)
{
   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   ZeroMemory(request);
   ZeroMemory(result);

   // Hitung lot
   double lot = g_mm.CalculateLot(STOP_LOSS_PTS);

   // Harga
   double ask = SymbolInfoDouble(SYMBOL_NAME, SYMBOL_ASK);
   double bid = SymbolInfoDouble(SYMBOL_NAME, SYMBOL_BID);
   double price = (orderType == ORDER_TYPE_BUY) ? ask : bid;

   // SL dan TP
   double slPrice = 0;
   double tpPrice = 0;

   if(orderType == ORDER_TYPE_BUY)
   {
      slPrice = NormalizeDouble(bid - STOP_LOSS_PTS * SymbolInfoDouble(SYMBOL_NAME, SYMBOL_POINT), _Digits);
      tpPrice = NormalizeDouble(ask + TAKE_PROFIT_PTS * SymbolInfoDouble(SYMBOL_NAME, SYMBOL_POINT), _Digits);
   }
   else
   {
      slPrice = NormalizeDouble(ask + STOP_LOSS_PTS * SymbolInfoDouble(SYMBOL_NAME, SYMBOL_POINT), _Digits);
      tpPrice = NormalizeDouble(bid - TAKE_PROFIT_PTS * SymbolInfoDouble(SYMBOL_NAME, SYMBOL_POINT), _Digits);
   }

   //+---------------------------------------------+
   //|  BUILD REQUEST                               |
   //+---------------------------------------------+
   request.action        = TRADE_ACTION_DEAL;
   request.symbol        = SYMBOL_NAME;
   request.volume        = lot;
   request.type          = orderType;
   request.price         = price;
   request.sl            = slPrice;
   request.tp            = tpPrice;
   request.deviation      = 10;
   request.magic          = MAGIC_NUMBER;
   request.comment        = EXPERT_COMMENT;
   request.type_filling   = ORDER_FILLING_FOK;

   // Kirim order
   if(!OrderSend(request, result))
   {
      Print(ERROR_LOG_PREFIX, "OrderSend GAGAL | Error: ", result.retcode,
            " | RetcodeString: ", result.comment);
      return;
   }

   if(result.retcode != TRADE_RETCODE_DONE)
   {
      Print(ERROR_LOG_PREFIX, "Order REJECTED | Retcode: ", result.retcode,
            " | ", result.comment);
      return;
   }

   ulong ticket = result.order;

   Print("===========================================");
   Print("  ORDER TERSEDIA | Ticket: #", ticket);
   Print("  Type: ", orderType == ORDER_TYPE_BUY ? "BUY" : "SELL");
   Print("  Price: ", DoubleToString(price, _Digits));
   Print("  Lot: ", DoubleToString(lot, 2));
   Print("  SL: ", DoubleToString(slPrice, _Digits));
   Print("  TP: ", DoubleToString(tpPrice, _Digits));
   Print("  RSI: ", DoubleToString(g_rsi.GetLastRSI(), 2));
   Print("===========================================");

   // Catat transaksi
   g_mm.RecordTrade(0); // Profit 0 karena posisi masih terbuka
}

//+------------------------------------------------------------------+
//|  TRADE RESULT HANDLER - Untuk modifikasi & close posisi           |
//+------------------------------------------------------------------+
bool TradeResultHandler(ulong ticket, ENUM_ORDER_TYPE orderType,
                        double lot, double sl, double tp, string reason)
{
   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   ZeroMemory(request);
   ZeroMemory(result);

   request.action    = TRADE_ACTION_SLTP;
   request.order     = ticket;
   request.sl        = sl;
   request.tp        = tp;
   request.volume    = lot;
   request.deviation = 10;

   bool ret = OrderSend(request, result);

   if(ret && result.retcode == TRADE_RETCODE_DONE)
   {
      if(ENABLE_DEBUG_LOG)
         Print(DEBUG_LOG_PREFIX, "Modifikasi order #", ticket,
               " | Reason: ", reason,
               " | New SL: ", DoubleToString(sl, _Digits),
               " | New TP: ", DoubleToString(tp, _Digits));
   }
   else
   {
      Print(ERROR_LOG_PREFIX, "Modifikasi gagal #", ticket,
            " | Error: ", result.retcode);
   }

   return(ret);
}

//+------------------------------------------------------------------+
//|  ON TRADE TRANSACTION - Mendeteksi posisi tertutup               |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest&     request,
                        const MqlTradeResult&      result)
{
   // Hanya proses DEAL (eksekusi)
   if(trans.type != TRADE_TRANSACTION_DEAL)
      return;

   // Ambil data dari transaction
   ulong   dealTicket   = trans.deal;
   long    dealType    = trans.deal_type;
   long    magic       = trans.magic;
   string  symbol      = trans.symbol;
   double  volume      = trans.volume;
   double  price       = trans.price;
   double  profit      = trans.profit;
   long    entryType   = trans.entry;
   datetime time       = trans.time;

   // Skip jika bukan trade kita
   if(magic != MAGIC_NUMBER)
      return;

   //+---------------------------------------------+
   //|  KIRIM DATA KE WEB SERVER                    |
   //+---------------------------------------------+
   if(InpEnableLog)
   {
      TradeLogData logData;
      ZeroMemory(logData);

      logData.ticket      = dealTicket;
      logData.lot         = volume;
      logData.priceClose  = price;
      logData.profit      = profit;
      logData.symbol      = symbol;
      logData.timeClose   = time;
      logData.magic       = magic;
      logData.rsiValue    = g_rsi.GetLastRSI();
      logData.slPoints    = STOP_LOSS_PTS;
      logData.tpPoints    = TAKE_PROFIT_PTS;
      logData.ipAddress   = GetVPSIPAddress();

      // Tentukan tipe trade (BUY/SELL)
      if(dealType == DEAL_TYPE_BUY || dealType == DEAL_TYPE_BUY_LIMIT ||
         dealType == DEAL_TYPE_BUY_STOP)
         logData.tradeType = "BUY";
      else if(dealType == DEAL_TYPE_SELL || dealType == DEAL_TYPE_SELL_LIMIT ||
              dealType == DEAL_TYPE_SELL_STOP)
         logData.tradeType = "SELL";
      else
         logData.tradeType = "UNKNOWN";

      // Entry type: IN (membuka) atau OUT (menutup)
      if(entryType == DEAL_ENTRY_IN)
      {
         logData.priceOpen = price;
         logData.timeOpen  = time;
      }
      else
      {
         // Posisi ditutup - ambil harga open dari history
         HistorySelect(time - 86400, time + 86400);
         for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
         {
            ulong hTicket = HistoryDealGetTicket(i);
            if(HistoryDealGetInteger(hTicket, DEAL_TICKET) == dealTicket)
            {
               logData.priceOpen  = HistoryDealGetDouble(hTicket, DEAL_PRICE_OPEN);
               logData.timeOpen   = (datetime)HistoryDealGetInteger(hTicket, DEAL_TIME);
               break;
            }
         }
      }

      // KIRIM ASYNC - EA TETAP JALAN, tidak nunggu server reply
      ENUM_API_STATUS status = g_apiClient.SendTradeLog(logData);

      Print("===========================================");
      Print("  DEAL CLOSED | Ticket: #", dealTicket);
      Print("  Type: ", logData.tradeType, " | Volume: ", DoubleToString(volume, 2));
      Print("  Price Open: ", DoubleToString(logData.priceOpen, _Digits),
            " | Close: ", DoubleToString(price, _Digits));
      Print("  Profit: ", DoubleToString(profit, 2));
      Print("  API Status: ", EnumToString(status));
      Print("  IP: ", logData.ipAddress);
      Print("===========================================");

      // Update konsekuensi loss
      if(profit < 0)
      {
         g_consecutiveLoss++;
         g_mm.RecordTrade(profit);
      }
      else
      {
         g_consecutiveLoss = 0;
         g_mm.RecordTrade(profit);
      }

      // Pause jika 3x loss berturut-turut
      if(g_consecutiveLoss >= 3)
      {
         Print("WARNING: 3x consecutive loss - PAUSE mode aktif");
         g_pauseMode = true;
      }
   }
}

//+------------------------------------------------------------------+
//|  AMBIL IP ADDRESS VPS / LOKAL                                     |
//+------------------------------------------------------------------+
string GetVPSIPAddress()
{
   // Metode 1: Request ke ipify.org (gratis, no auth)
   char   result[];
   string headers = "";
   string response;

   int respCode = WebRequest(
      "GET",
      "https://api.ipify.org",
      headers,
      3000,
      "",
      result,
      headers
   );

   if(respCode == 200 && ArraySize(result) > 0)
   {
      response = CharArrayToString(result);
      if(StringLen(response) > 0)
         return(response);
   }

   // Fallback jika tidak dapat IP
   return("127.0.0.1");
}

//+------------------------------------------------------------------+
//|  EXPERT ADVISOR COMMENT (ditampilkan di chart)                  |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam,
                  const double &dparam, const string &sparam)
{
   Comment("");
}

//+------------------------------------------------------------------+
//|  EXPERT TRAILER & INFO                                           |
//+------------------------------------------------------------------+
string GetExpertInfo()
{
   string info = "";
   info += "PiqsScalper v1.0.0\n";
   info += "========================\n";
   info += "Symbol    : " + SYMBOL_NAME + "\n";
   info += "Timeframe : M15\n";
   info += "RSI       : " + DoubleToString(g_rsi.GetLastRSI(), 2) + "\n";
   info += "Daily Trades: " + (string)g_mm.GetDailyTradeCount() + "/" + (string)MAX_DAILY_TRADES + "\n";
   info += "Daily Loss  : " + DoubleToString(g_mm.GetDailyLoss(), 2) + "\n";
   info += "API Success : " + (string)g_apiClient.GetSuccessCount() + "\n";
   info += "API Failed  : " + (string)g_apiClient.GetFailCount() + "\n";
   if(g_pauseMode) info += "STATUS    : PAUSED\n";
   return(info);
}
