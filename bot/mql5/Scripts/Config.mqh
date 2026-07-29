//+------------------------------------------------------------------+
//|  PiqsScalper - Central Configuration                             |
//|  XAUUSD M15 RSI Scalping Bot                                     |
//|  Version: 1.0.0                                                   |
//+------------------------------------------------------------------+
//|  GUNAKAN FILE INI UNTUK SEMUA KONSTANTA GLOBAL                    |
//|  Rollover/modifikasi di sini untuk rollback cepat               |
//+------------------------------------------------------------------+

#ifndef CONFIG_MQH
#define CONFIG_MQH

//+------------------------------------------------------------------+
//|  SERVER & ENDPOINT CONFIGURATION                                  |
//+------------------------------------------------------------------+
//  ⚠️  Ganti URL_ENDPOINT dengan URL server Anda yang sebenarnya
//  Contoh: "https://api.piqstrade.com/backend/log_trade.php"
//  Pastikan URL sudah HTTPS untuk WebRequest() MQL5
//+------------------------------------------------------------------+
#define URL_ENDPOINT        "https://your-server.com/backend/log_trade.php"
#define API_TIMEOUT_MS      5000        // Timeout koneksi: 5 detik
#define API_RETRY_COUNT     3          // Jumlah percobaan ulang jika gagal

//+------------------------------------------------------------------+
//|  SYMBOL & TIMEFRAME                                              |
//+------------------------------------------------------------------+
#define SYMBOL_NAME         "XAUUSD"
#define TIMEFRAME_WORK      PERIOD_M15  // 15 Menit chart

//+------------------------------------------------------------------+
//|  RSI MULTI-TIERED LEVELS                                         |
//+------------------------------------------------------------------+
//  Level Kritis:   Buy Zone < 15  |  Sell Zone > 85
//  Level Warning:  Buy Zone < 30  |  Sell Zone > 70
//  Level Netral:   30 - 70
//+------------------------------------------------------------------+
#define RSI_PERIOD          14          // Periode RSI bawaan
#define RSI_LEVEL_EXTREME   15          // Level ekstrem (kritis)
#define RSI_LEVEL_WARNING   30          // Level warning bawah
#define RSI_LEVEL_SELL_WARN 70          // Level warning atas
#define RSI_LEVEL_SELL_EXT  85          // Level ekstrem atas (kritis)

//+------------------------------------------------------------------+
//|  MONEY MANAGEMENT                                                |
//+------------------------------------------------------------------+
#define LOT_SIZE            0.10        // Lot tetap per transaksi
#define MAX_LOT             1.0         // Batas lot maksimum
#define RISK_PERCENT        2.0         // Risk per trade (%)
#define MAX_DAILY_TRADES    10          // Batas transaksi per hari
#define MAX_SPREAD          30          // Spread maksimal (poin)
#define STOP_LOSS_PTS       150         // SL dalam poin (15 pip untuk 5-digit)
#define TAKE_PROFIT_PTS     100         // TP dalam poin (10 pip untuk 5-digit)

//+------------------------------------------------------------------+
//|  TRADING HOURS (Broker Server Time)                              |
//+------------------------------------------------------------------+
//  Format: jam_mulai * 3600 + menit_mulai
#define SESSION_START       9*3600      // 09:00 server
#define SESSION_END         21*3600     // 21:00 server

//+------------------------------------------------------------------+
//|  TRADE MAGICS & COMMENT                                          |
//+------------------------------------------------------------------+
#define MAGIC_NUMBER        20240728    // ID unik EA
#define EXPERT_COMMENT      "PiqsScalper_RSI"
#define EXPERT_PREFIX       "Piqs_"

//+------------------------------------------------------------------+
//|  LOGGING & DEBUGGING                                             |
//+------------------------------------------------------------------+
#define ENABLE_DEBUG_LOG     true        // Aktifkan log debugging
#define DEBUG_LOG_PREFIX    "[Piqs-DBG] "
#define ERROR_LOG_PREFIX    "[Piqs-ERR] "

//+------------------------------------------------------------------+
//|  API DATA FIELDS                                                 |
//+------------------------------------------------------------------+
//  Field-name yang dikirim ke endpoint PHP
#define FIELD_TICKET         "ticket"
#define FIELD_TYPE           "type"
#define FIELD_LOT            "lot"
#define FIELD_PRICE_OPEN     "price_open"
#define FIELD_PRICE_CLOSE    "price_close"
#define FIELD_PROFIT         "profit"
#define FIELD_SYMBOL         "symbol"
#define FIELD_TIME_OPEN      "time_open"
#define FIELD_TIME_CLOSE     "time_close"
#define FIELD_IP             "ip_address"
#define FIELD_MAGIC          "magic"
#define FIELD_SLPTS          "sl_pts"
#define FIELD_TPTS           "tp_pts"
#define FIELD_RSI_VALUE      "rsi_value"
#define FIELD_API_KEY        "api_key"

//  ⚠️  Ganti dengan API key rahasia Anda
#define API_SECRET_KEY       "pk_live_piqs_xauusd_2024"

//+------------------------------------------------------------------+
//|  HELPER MACROS                                                   |
//+------------------------------------------------------------------+
#define ToString(e)         EnumToString(e)
#define IsTradingHour()     (Hour() >= 9 && Hour() <= 21)

//+------------------------------------------------------------------+
#endif // CONFIG_MQH
