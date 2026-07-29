//+------------------------------------------------------------------+
//|  RSITrigger.mqh - RSI Multi-Tiered Logic Module                  |
//|                                                                  |
//|  Modul ini menangani SEMUA logika pemicu sinyal trading          |
//|  berdasarkan RSI dengan 3 zona: Kritis, Warning, Netral          |
//|                                                                  |
//|  Arsitektur modular:                                             |
//|    - Pisahkan dari EA utama untuk rollback mudah                 |
//|    - Jika RSI logic error → replace file ini saja                |
//+------------------------------------------------------------------+

#ifndef RSI_TRIGGER_MQH
#define RSI_TRIGGER_MQH

#include "Config.mqh"

//+------------------------------------------------------------------+
//|  ENUM: Zona Sinyal RSI                                           |
//+------------------------------------------------------------------+
enum ENUM_RSI_SIGNAL_ZONE
{
   RSI_ZONE_UNKNOWN      = 0,   // Belum ada sinyal
   RSI_ZONE_EXTREME_BUY  = 1,   // ⬇ Kritis bawah   (RSI < 15)
   RSI_ZONE_WARNING_BUY  = 2,   // ⬇ Warning bawah  (RSI < 30)
   RSI_ZONE_NEUTRAL      = 3,   // — Netral         (RSI 30-70)
   RSI_ZONE_WARNING_SELL = 4,   // ⬆ Warning atas   (RSI > 70)
   RSI_ZONE_EXTREME_SELL = 5    // ⬆ Kritis atas    (RSI > 85)
};

//+------------------------------------------------------------------+
//|  STRUCT: Sinyal RSI                                              |
//+------------------------------------------------------------------+
struct RSI_Signal
{
   ENUM_RSI_SIGNAL_ZONE  zone;        // Zona sinyal saat ini
   double                rsiValue;     // Nilai RSI candle saat ini
   double                rsiPrev;      // Nilai RSI candle sebelumnya
   bool                  isConfirmed;  // Sinyal terkonfirmasi (candle close)
   datetime              signalTime;   // Waktu sinyal terbentuk
   string                symbol;       // Simbol
   ENUM_TIMEFRAMES       timeframe;   // Timeframe
};

//+------------------------------------------------------------------+
//|  CLASS: CRSITrigger                                              |
//+------------------------------------------------------------------+
class CRSITrigger
{
private:
   string                m_symbol;       // Simbol yang di-trading
   ENUM_TIMEFRAMES       m_tf;          // Timeframe
   int                   m_rsiHandle;   // Handle indikator RSI
   RSI_Signal            m_lastSignal;  // Sinyal terakhir
   datetime              m_lastCandle;  // Candle terakhir yang sudah diproses

   //+----------------------------------------------------------+
   //| Hitung level spread sekarang                              |
   //+----------------------------------------------------------+
   double GetCurrentSpread()
   {
      if(m_symbol == "")
         return(0);
      return(MathMax(SymbolInfoInteger(m_symbol, SYMBOL_SPREAD), 0));
   }

public:
   //+----------------------------------------------------------+
   //| Konstruktor                                               |
   //+----------------------------------------------------------+
   CRSITrigger(string symbol = SYMBOL_NAME, ENUM_TIMEFRAMES tf = TIMEFRAME_WORK)
   {
      m_symbol      = symbol;
      m_tf          = tf;
      m_rsiHandle   = INVALID_HANDLE;
      m_lastSignal.zone       = RSI_ZONE_UNKNOWN;
      m_lastSignal.isConfirmed = false;
      m_lastSignal.signalTime  = 0;
      m_lastSignal.symbol      = symbol;
      m_lastSignal.timeframe   = tf;
      m_lastCandle = 0;
   }

   //+----------------------------------------------------------+
   //| Destruktor - bersihkan handle                             |
   //+----------------------------------------------------------+
   ~CRSITrigger()
   {
      if(m_rsiHandle != INVALID_HANDLE)
      {
         IndicatorRelease(m_rsiHandle);
         m_rsiHandle = INVALID_HANDLE;
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "RSI Handle released for ", m_symbol);
      }
   }

   //+----------------------------------------------------------+
   //| Inisialisasi indikator RSI                                 |
   //| Return: true jika berhasil, false jika gagal               |
   //+----------------------------------------------------------+
   bool Initialize()
   {
      // Buat handle RSI
      m_rsiHandle = iRSI(m_symbol, m_tf, RSI_PERIOD, PRICE_CLOSE);

      if(m_rsiHandle == INVALID_HANDLE)
      {
         Print(ERROR_LOG_PREFIX, "Gagal membuat RSI handle untuk ", m_symbol);
         Print(ERROR_LOG_PREFIX, "Error: ", GetLastError());
         return(false);
      }

      // Tunggu data RSI tersedia
      ArraySetAsSeries(m_rsiBuffer, true);
      int attempts = 0;
      while(CopyBuffer(m_rsiHandle, 0, 0, 3, m_rsiBuffer) < 3)
      {
         Sleep(100);
         attempts++;
         if(attempts > 50)
         {
            Print(ERROR_LOG_PREFIX, "RSI data timeout untuk ", m_symbol);
            return(false);
         }
      }

      if(ENABLE_DEBUG_LOG)
         Print(DEBUG_LOG_PREFIX, "RSI initialized untuk ", m_symbol,
               " | Period: ", RSI_PERIOD);

      return(true);
   }

   //+----------------------------------------------------------+
   //| Dapatkan nilai RSI saat ini                                |
   //+----------------------------------------------------------+
   double GetRSIValue(int shift = 0)
   {
      double buffer[];
      ArraySetAsSeries(buffer, true);

      if(CopyBuffer(m_rsiHandle, 0, 0, shift + 1, buffer) <= 0)
         return(50.0); // Default netral jika gagal baca

      if(ArraySize(buffer) <= shift)
         return(50.0);

      return(buffer[shift]);
   }

   //+----------------------------------------------------------+
   //| Tentukan zona sinyal RSI                                    |
   //+----------------------------------------------------------+
   ENUM_RSI_SIGNAL_ZONE DetectZone(double rsi)
   {
      if(rsi < RSI_LEVEL_EXTREME)   return(RSI_ZONE_EXTREME_BUY);
      if(rsi < RSI_LEVEL_WARNING)   return(RSI_ZONE_WARNING_BUY);
      if(rsi > RSI_LEVEL_SELL_EXT)  return(RSI_ZONE_EXTREME_SELL);
      if(rsi > RSI_LEVEL_SELL_WARN)  return(RSI_ZONE_WARNING_SELL);
      return(RSI_ZONE_NEUTRAL);
   }

   //+----------------------------------------------------------+
   //| Cek apakah candle saat ini sudah close (ONCE per candle)  |
   //+----------------------------------------------------------+
   bool IsNewCandle()
   {
      datetime currentCandle = iTime(m_symbol, m_tf, 0);
      if(currentCandle != m_lastCandle)
      {
         m_lastCandle = currentCandle;
         return(true);
      }
      return(false);
   }

   //+----------------------------------------------------------+
   //| Ambil sinyal lengkap untuk candle saat ini                 |
   //| Sinyal hanya valid setelah candle benar-benar close        |
   //+----------------------------------------------------------+
   RSI_Signal AnalyzeSignal()
   {
      RSI_Signal sig;
      sig.symbol    = m_symbol;
      sig.timeframe = m_tf;
      sig.signalTime = TimeCurrent();

      double rsiCurrent = GetRSIValue(0);  // Candle saat ini (belum close)
      double rsiPrev     = GetRSIValue(1);  // Candle sebelumnya (sudah close)

      sig.rsiValue = rsiCurrent;
      sig.rsiPrev   = rsiPrev;
      sig.zone      = DetectZone(rsiCurrent);

      // Sinyal terkonfirmasi HANYA jika candle sebelumnya sudah close
      // Ini mencegah sinyal palsu saat candle masih формируется
      sig.isConfirmed = IsNewCandle() && (sig.rsiPrev > 0);

      if(ENABLE_DEBUG_LOG && sig.isConfirmed)
      {
         Print(DEBUG_LOG_PREFIX, "RSI Analysis → Zone: ", EnumToString(sig.zone),
               " | RSI Current: ", DoubleToString(rsiCurrent, 2),
               " | RSI Prev: ",    DoubleToString(rsiPrev, 2));
      }

      m_lastSignal = sig;
      return(sig);
   }

   //+----------------------------------------------------------+
   //| Cek apakah kondisi spread masih layak                       |
   //+----------------------------------------------------------+
   bool IsSpreadAcceptable()
   {
      double spread = GetCurrentSpread();
      if(spread > MAX_SPREAD)
      {
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "Spread terlalu tinggi: ", spread,
                  " (max: ", MAX_SPREAD, ")");
         return(false);
      }
      return(true);
   }

   //+----------------------------------------------------------+
   //| CEK UTAMA: Apakah boleh Buy sekarang?                      |
   //| Syarat:                                                   |
   //|   1. RSI < 15 (ekstrem bawah) → BUY                       |
   //|   2. Candle sebelumnya close di atas level                |
   //|   3. Spread masih layak                                   |
   //+----------------------------------------------------------+
   bool IsBuySignal()
   {
      RSI_Signal sig = AnalyzeSignal();

      if(!sig.isConfirmed)
         return(false);

      if(!IsSpreadAcceptable())
         return(false);

      // Konfirmasi Buy: candle sebelumnya close DI BAWAH level ekstrem
      // dan candle saat ini bergerak naik melewati level
      bool rsiCrossedUp = (sig.rsiPrev < RSI_LEVEL_EXTREME) &&
                          (sig.rsiValue >= RSI_LEVEL_EXTREME);

      // Alt: RSI sudah di zona ekstrem dan mulai recovered
      bool rsiExtreme = (sig.rsiValue < RSI_LEVEL_EXTREME);

      if(rsiCrossedUp || rsiExtreme)
      {
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "🎯 SINYAL BUY | RSI: ",
                  DoubleToString(sig.rsiValue, 2),
                  " | Zone: EXTREME_BUY");
         return(true);
      }

      return(false);
   }

   //+----------------------------------------------------------+
   //| CEK UTAMA: Apakah boleh Sell sekarang?                     |
   //| Syarat:                                                   |
   //|   1. RSI > 85 (ekstrem atas) → SELL                      |
   //|   2. Candle sebelumnya close di atas level                |
   //|   3. Spread masih layak                                   |
   //+----------------------------------------------------------+
   bool IsSellSignal()
   {
      RSI_Signal sig = AnalyzeSignal();

      if(!sig.isConfirmed)
         return(false);

      if(!IsSpreadAcceptable())
         return(false);

      // Konfirmasi Sell: candle sebelumnya close DI ATAS level ekstrem
      // dan candle saat ini bergerak turun melewati level
      bool rsiCrossedDown = (sig.rsiPrev > RSI_LEVEL_SELL_EXT) &&
                            (sig.rsiValue <= RSI_LEVEL_SELL_EXT);

      // Alt: RSI sudah di zona ekstrem atas
      bool rsiExtreme = (sig.rsiValue > RSI_LEVEL_SELL_EXT);

      if(rsiCrossedDown || rsiExtreme)
      {
         if(ENABLE_DEBUG_LOG)
            Print(DEBUG_LOG_PREFIX, "🎯 SINYAL SELL | RSI: ",
                  DoubleToString(sig.rsiValue, 2),
                  " | Zone: EXTREME_SELL");
         return(true);
      }

      return(false);
   }

   //+----------------------------------------------------------+
   //| Getter: Ambil sinyal terakhir                              |
   //+----------------------------------------------------------+
   RSI_Signal GetLastSignal() { return(m_lastSignal); }
   double GetLastRSI()        { return(m_lastSignal.rsiValue); }
};

//+------------------------------------------------------------------+
//|  BUFFER - Wajib dideklarasikan di EA utama                       |
//+------------------------------------------------------------------+
double  m_rsiBuffer[];   // Buffer untuk copy data RSI

#endif // RSI_TRIGGER_MQH
