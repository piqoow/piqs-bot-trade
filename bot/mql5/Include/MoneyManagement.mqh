//+------------------------------------------------------------------+
//|  MoneyManagement.mqh - Lot Sizing & Risk Control Module           |
//|                                                                  |
//|  Modul ini menangani SEMUA kalkulasi lot dan risk management      |
//|                                                                  |
//|  Fitur:                                                          |
//|    - Fixed Lot (dari Config.mqh)                                |
//|    - Risk-Based Lot (hitung dari SL dan balance)                 |
//|    - Daily trade counter                                         |
//|    - Max lot protection                                          |
//|    - Daily loss limit                                            |
//+------------------------------------------------------------------+

#ifndef MONEY_MANAGEMENT_MQH
#define MONEY_MANAGEMENT_MQH

#include "Config.mqh"

//+------------------------------------------------------------------+
//|  ENUM: Mode Lot Calculation                                      |
//+------------------------------------------------------------------+
enum ENUM_LOT_MODE
{
   LOT_MODE_FIXED      = 0,   // Lot tetap (LOT_SIZE dari Config)
   LOT_MODE_RISK_BASED = 1,   // Hitung dari risk % dan SL
   LOT_MODE_MINIMUM    = 2    // Lot minimum broker
};

//+------------------------------------------------------------------+
//|  STRUCT: Trade Risk Info                                         |
//+------------------------------------------------------------------+
struct RiskInfo
{
   double   lotSize;          // Lot yang akan digunakan
   double   riskAmount;       // Amount dalam mata uang deposit
   double   riskPercent;      // Risk dalam %
   double   stopLossPts;      // SL dalam poin
   double   takeProfitPts;    // TP dalam poin
   double   potentialProfit;  // Potensi profit
   double   potentialLoss;    // Potensi loss
   bool     isValid;          // Apakah kalkulasi valid
};

//+------------------------------------------------------------------+
//|  CLASS: CMoneyManager                                            |
//+------------------------------------------------------------------+
class CMoneyManager
{
private:
   ENUM_LOT_MODE       m_lotMode;       // Mode kalkulasi lot
   double              m_dailyTrades;   // Counter transaksi hari ini
   datetime            m_lastResetDate; // Tanggal reset counter terakhir
   double              m_dailyLoss;     // Total loss hari ini
   double              m_initialBalance;// Balance saat awal hari

   //+----------------------------------------------------------+
   //| Reset counter harian jika tanggal berubah                 |
   //+----------------------------------------------------------+
   void CheckDailyReset()
   {
      MqlDateTime dt;
      TimeCurrent(dt);

      string todayKey = IntegerToString(dt.year) + "-" +
                        IntegerToString(dt.mon)  + "-" +
                        IntegerToString(dt.day);

      MqlDateTime lastDt;
      TimeToStruct(m_lastResetDate, lastDt);

      string lastKey = IntegerToString(lastDt.year) + "-" +
                       IntegerToString(lastDt.mon)  + "-" +
                       IntegerToString(lastDt.day);

      if(todayKey != lastKey)
      {
         // Reset harian
         m_dailyTrades    = 0;
         m_dailyLoss      = 0;
         m_initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
         m_lastResetDate  = TimeCurrent();

         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "Daily counter RESET | Balance: ",
                  DoubleToString(m_initialBalance, 2));
      }
   }

public:
   //+----------------------------------------------------------+
   //| Konstruktor                                               |
   //+----------------------------------------------------------+
   CMoneyManager(ENUM_LOT_MODE mode = LOT_MODE_FIXED)
   {
      m_lotMode      = mode;
      m_dailyTrades  = 0;
      m_dailyLoss    = 0;
      m_lastResetDate = 0;
      m_initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   //+----------------------------------------------------------+
   //| Hitung lot berdasarkan mode yang dipilih                  |
   //+----------------------------------------------------------+
   double CalculateLot(double stopLossPts, string symbol = SYMBOL_NAME)
   {
      double lot = 0;

      switch(m_lotMode)
      {
         case LOT_MODE_FIXED:
            lot = LOT_SIZE;
            break;

         case LOT_MODE_RISK_BASED:
            lot = CalculateRiskBasedLot(stopLossPts, symbol);
            break;

         case LOT_MODE_MINIMUM:
            lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
            break;
      }

      // Apply max lot protection
      lot = MathMin(lot, MAX_LOT);

      // Bulatkan ke step lot broker
      double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      if(step > 0)
         lot = MathFloor(lot / step) * step;

      // Minimum lot
      double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      if(lot < minLot)
         lot = minLot;

      if(ENABLE_DEBUG_LOG)
         Print(DEBUG_LOG_PREFIX, "Lot calculated: ", DoubleToString(lot, 2),
               " | Mode: ", EnumToString(m_lotMode));

      return(lot);
   }

   //+----------------------------------------------------------+
   //| Kalkulasi Risk-Based Lot                                   |
   //| Lot = (Balance × Risk%) / (SL_Points × Point_Value)       |
   //+----------------------------------------------------------+
   double CalculateRiskBasedLot(double slPoints, string symbol)
   {
      double balance     = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskAmount  = balance * (RISK_PERCENT / 100.0);

      // Dapatkan harga tick dan point
      double tickValue   = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double point       = SymbolInfoDouble(symbol, SYMBOL_POINT);

      // Hitung nilai per poin untuk 1 lot
      // Gold menggunakan mode: 1 lot = 100 oz, tick = 0.01
      double pointValue   = (tickValue / tickSize) * point;

      // Lot = Risk Amount / (SL Points × Point Value)
      double lot = 0;
      if(pointValue > 0 && slPoints > 0)
         lot = riskAmount / (slPoints * pointValue);

      if(ENABLE_DEBUG_LOG)
      {
         Print(DEBUG_LOG_PREFIX, "Risk Calc | Balance: ", DoubleToString(balance, 2),
               " | Risk: ", DoubleToString(riskAmount, 2),
               " | SL: ", slPoints,
               " | PointVal: ", DoubleToString(pointValue, 5),
               " | Lot: ", DoubleToString(lot, 2));
      }

      return(lot);
   }

   //+----------------------------------------------------------+
   //| Hitung info risk lengkap untuk satu trade                  |
   //+----------------------------------------------------------+
   RiskInfo CalculateRiskInfo(double lotSize, double slPoints,
                              double tpPoints, string symbol)
   {
      RiskInfo info;
      info.lotSize    = lotSize;
      info.riskPercent = RISK_PERCENT;
      info.stopLossPts = slPoints;
      info.takeProfitPts = tpPoints;

      double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double point     = SymbolInfoDouble(symbol, SYMBOL_POINT);

      double pointValue = (tickValue / tickSize) * point;

      info.riskAmount    = lotSize * slPoints * pointValue;
      info.potentialLoss = info.riskAmount;
      info.potentialProfit = lotSize * tpPoints * pointValue;

      info.isValid = (lotSize > 0 && slPoints > 0);

      return(info);
   }

   //+----------------------------------------------------------+
   //| CEK: Apakah boleh buka trade baru?                         |
   //+----------------------------------------------------------+
   bool CanOpenTrade()
   {
      CheckDailyReset();

      // Cek batas transaksi harian
      if(m_dailyTrades >= MAX_DAILY_TRADES)
      {
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "Batas harian tercapai: ",
                  (int)m_dailyTrades, "/", MAX_DAILY_TRADES);
         return(false);
      }

      // Cek margin level
      double marginLevel = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
      if(marginLevel > 0 && marginLevel < 150)
      {
         Print(ERROR_LOG_PREFIX, "Margin level terlalu rendah: ",
               DoubleToString(marginLevel, 2));
         return(false);
      }

      // Cek apakah ada posisi terbuka yang blocking
      if(PositionCount() >= 2)
      {
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "Posisi maksimum sudah terbuka");
         return(false);
      }

      return(true);
   }

   //+----------------------------------------------------------+
   //| Catat transaksi setelah close                              |
   //+----------------------------------------------------------+
   void RecordTrade(double profit)
   {
      m_dailyTrades++;

      if(profit < 0)
         m_dailyLoss += MathAbs(profit);

      if(ENABLE_DEBUG_LOG)
      {
         Print(DEBUG_LOG_PREFIX, "Trade recorded | #",
               (int)m_dailyTrades,
               " | Profit: ", DoubleToString(profit, 2),
               " | Daily Loss: ", DoubleToString(m_dailyLoss, 2));
      }

      // Opsional: Stop trading jika daily loss > 5%
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double maxDailyLoss = balance * 0.05;
      if(m_dailyLoss > maxDailyLoss)
      {
         Print(ERROR_LOG_PREFIX, "⚠️  DAILY LOSS LIMIT TERCAPAI: ",
               DoubleToString(m_dailyLoss, 2),
               " (Max: ", DoubleToString(maxDailyLoss, 2), ")");
         Print(ERROR_LOG_PREFIX, "EA akan PAUSE sampai besok");
      }
   }

   //+----------------------------------------------------------+
   //| Getter & Status                                            |
   //+----------------------------------------------------------+
   int   GetDailyTradeCount()  { CheckDailyReset(); return((int)m_dailyTrades); }
   double GetDailyLoss()        { CheckDailyReset(); return(m_dailyLoss); }
   void  SetLotMode(ENUM_LOT_MODE mode) { m_lotMode = mode; }
   ENUM_LOT_MODE GetLotMode() { return(m_lotMode); }

   //+----------------------------------------------------------+
   //| Hitung jumlah posisi terbuka untuk symbol ini              |
   //+----------------------------------------------------------+
   int PositionCount()
   {
      int count = 0;
      int total = PositionsTotal();
      for(int i = 0; i < total; i++)
      {
         if(PositionGetSymbol(i) == SYMBOL_NAME &&
            PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
            count++;
      }
      return(count);
   }

   //+----------------------------------------------------------+
   //| Cek apakah ada posisi terbuka untuk symbol ini             |
   //+----------------------------------------------------------+
   bool HasOpenPosition()
   {
      return(PositionCount() > 0);
   }
};

#endif // MONEY_MANAGEMENT_MQH
