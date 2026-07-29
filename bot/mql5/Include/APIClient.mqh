//+------------------------------------------------------------------+
//|  APIClient.mqh - Web Logging Module                              |
//|  Modul ini menangani SEMUA komunikasi HTTP ke backend PHP         |
//|  Menggunakan WebRequest() native MQL5                           |
//+------------------------------------------------------------------+

#ifndef API_CLIENT_MQH
#define API_CLIENT_MQH

#include <Object.mqh>
#include "Config.mqh"

//+------------------------------------------------------------------+
//|  ENUM: HTTP Method                                               |
//+------------------------------------------------------------------+
enum ENUM_HTTP_METHOD
{
   HTTP_METHOD_GET    = 0,
   HTTP_METHOD_POST   = 1
};

//+------------------------------------------------------------------+
//|  ENUM: API Response Status                                       |
//+------------------------------------------------------------------+
enum ENUM_API_STATUS
{
   API_SUCCESS        = 0,
   API_ERROR_NETWORK  = 1,
   API_ERROR_TIMEOUT  = 2,
   API_ERROR_RESPONSE = 3,
   API_ERROR_REJECTED = 4,
   API_ERROR_PENDING  = 5
};

//+------------------------------------------------------------------+
//|  STRUCT: Trade Log Data                                           |
//+------------------------------------------------------------------+
struct TradeLogData
{
   ulong              ticket;
   string             tradeType;
   double             lot;
   double             priceOpen;
   double             priceClose;
   double             profit;
   string             symbol;
   datetime           timeOpen;
   datetime           timeClose;
   string             ipAddress;
   long               magic;
   double             slPoints;
   double             tpPoints;
   double             rsiValue;
};

//+------------------------------------------------------------------+
//|  CLASS: CAPIClient                                                |
//|  Mengirim data trade ke endpoint PHP via WebRequest()            |
//+------------------------------------------------------------------+
class CAPIClient
{
private:
   ENUM_API_STATUS    m_lastStatus;    // Status terakhir
   string             m_lastError;      // Error message terakhir
   string             m_lastResponse;  // Response server terakhir
   int                m_successCount;  // Counter sukses
   int                m_failCount;     // Counter gagal
   datetime           m_lastAttempt;   // Waktu attempt terakhir

   //+----------------------------------------------------+
   //| Encode data ke format POST                           |
   //+----------------------------------------------------+
   string EncodePostData(TradeLogData &data)
   {
      string result = "";

      result += FIELD_TICKET      + "=" + (string)data.ticket      + "&";
      result += FIELD_TYPE         + "=" + data.tradeType           + "&";
      result += FIELD_LOT          + "=" + DoubleToString(data.lot, 2)      + "&";
      result += FIELD_PRICE_OPEN   + "=" + DoubleToString(data.priceOpen, 5) + "&";
      result += FIELD_PRICE_CLOSE  + "=" + DoubleToString(data.priceClose, 5)+ "&";
      result += FIELD_PROFIT       + "=" + DoubleToString(data.profit, 2)   + "&";
      result += FIELD_SYMBOL       + "=" + data.symbol              + "&";
      result += FIELD_TIME_OPEN    + "=" + IntegerToString((int)data.timeOpen)    + "&";
      result += FIELD_TIME_CLOSE   + "=" + IntegerToString((int)data.timeClose)   + "&";
      result += FIELD_IP          + "=" + data.ipAddress           + "&";
      result += FIELD_MAGIC       + "=" + (string)data.magic       + "&";
      result += FIELD_SLPTS        + "=" + DoubleToString(data.slPoints, 1)  + "&";
      result += FIELD_TPTS         + "=" + DoubleToString(data.tpPoints, 1)  + "&";
      result += FIELD_RSI_VALUE    + "=" + DoubleToString(data.rsiValue, 2)  + "&";
      result += FIELD_API_KEY      + "=" + API_SECRET_KEY;

      return(result);
   }

   //+----------------------------------------------------+
   //| Parse response dari server                           |
   //+----------------------------------------------------+
   bool ParseResponse(string response)
   {
      m_lastResponse = response;

      // Cek response kosong
      if(StringLen(response) == 0)
      {
         m_lastError = "Empty response from server";
         return(false);
      }

      // Response sukses biasanya mengandung "success" atau "ok"
      if(StringFind(response, "success") >= 0 ||
         StringFind(response, "ok") >= 0 ||
         StringFind(response, "200") >= 0)
      {
         m_lastStatus = API_SUCCESS;
         return(true);
      }

      // Response error mengandung "error" atau "fail"
      if(StringFind(response, "error") >= 0 ||
         StringFind(response, "fail") >= 0 ||
         StringFind(response, "unauthorized") >= 0)
      {
         m_lastError = "Server returned error: " + response;
         m_lastStatus = API_ERROR_REJECTED;
         return(false);
      }

      // Response tidak diketahui, tapi dianggap sukses
      return(true);
   }

public:
   //+----------------------------------------------------+
   //| Konstruktor                                        |
   //+----------------------------------------------------+
   CAPIClient()
   {
      m_lastStatus     = API_ERROR_PENDING;
      m_lastError      = "";
      m_lastResponse   = "";
      m_successCount   = 0;
      m_failCount      = 0;
      m_lastAttempt    = 0;
   }

   //+----------------------------------------------------+
   //| Kirim data trade ke server (MAIN FUNCTION)         |
   //|                                                      |
   //| Parameter:                                          |
   //|   data - TradeLogData struct berisi data trade     |
   //|   silent - jika true, tidak print error ke log    |
   //|                                                      |
   //| Return: ENUM_API_STATUS                             |
   //+----------------------------------------------------+
   ENUM_API_STATUS SendTradeLog(TradeLogData &data, bool silent = false)
   {
      string postData = EncodePostData(data);
      string headers = "Content-Type: application/x-www-form-urlencoded\r\n";

      char   postResult[];
      string resultHeaders;
      int    responseCode = -1;

      if(ENABLE_DEBUG_LOG && !silent)
         Print(DEBUG_LOG_PREFIX, "Mengirim trade log | Ticket: ", data.ticket,
               " | Profit: ", DoubleToString(data.profit, 2),
               " | IP: ", data.ipAddress);

      // Retry loop dengan exponential backoff
      for(int attempt = 1; attempt <= API_RETRY_COUNT; attempt++)
      {
         ResetLastError();

         int timeout = API_TIMEOUT_MS * attempt; // Timeout naik setiap retry

         responseCode = WebRequest(
            HTTP_METHOD_POST,
            URL_ENDPOINT,
            headers,
            timeout,
            postData,
            postResult,
            resultHeaders
         );

         m_lastAttempt = TimeCurrent();

         if(ENABLE_DEBUG_LOG && !silent)
            Print(DEBUG_LOG_PREFIX, "Attempt ", attempt, "/", API_RETRY_COUNT,
                  " | Response Code: ", responseCode,
                  " | Error: ", GetLastError());

         // HTTP 200 = Sukses
         if(responseCode == 200)
         {
            string response = CharArrayToString(postResult);
            if(ParseResponse(response))
            {
               m_successCount++;
               m_lastStatus = API_SUCCESS;
               if(ENABLE_DEBUG_LOG && !silent)
                  Print(DEBUG_LOG_PREFIX, "Trade log TERKIRIM | Ticket: ", data.ticket);
               return(API_SUCCESS);
            }
            else
            {
               // Response ada tapi bukan format expected
               if(attempt == API_RETRY_COUNT)
               {
                  m_failCount++;
                  m_lastStatus = API_ERROR_RESPONSE;
                  if(!silent)
                     Print(ERROR_LOG_PREFIX, "Invalid response: ", m_lastResponse);
                  return(API_ERROR_RESPONSE);
               }
            }
         }
         else if(responseCode == -1)
         {
            // WebRequest gagal - cek error code
            int err = GetLastError();
            if(err == 1009 || err == 1008) // NETWORK / NO_CONNECTION
            {
               m_lastError = "Network unavailable";
               m_lastStatus = API_ERROR_NETWORK;
            }
            else if(err == 1006) // TIMEOUT
            {
               m_lastError = "Connection timeout";
               m_lastStatus = API_ERROR_TIMEOUT;
            }
            else
            {
               m_lastError = "WebRequest error: " + IntegerToString(err);
               m_lastStatus = API_ERROR_NETWORK;
            }
         }
         else
         {
            // HTTP code lain (403, 500, dll)
            m_lastError = "HTTP Error: " + IntegerToString(responseCode);
            m_lastStatus = API_ERROR_REJECTED;
         }

         // Exponential backoff: tunggu sebelum retry
         if(attempt < API_RETRY_COUNT)
         {
            int sleepMs = attempt * 1000; // 1s, 2s, 3s...
            if(ENABLE_DEBUG_LOG && !silent)
               Print(DEBUG_LOG_PREFIX, "Retry dalam ", sleepMs, "ms...");
            Sleep(sleepMs);
         }
      }

      // Semua retry gagal
      m_failCount++;
      if(!silent)
         Print(ERROR_LOG_PREFIX, "Gagal kirim log setelah ", API_RETRY_COUNT,
               " percobaan | Ticket: ", data.ticket, " | Error: ", m_lastError);
      return(m_lastStatus);
   }

   //+----------------------------------------------------+
   //| CEK KONEKTIVITAS: Ping server dulu                  |
   //| Berguna saat EA startup                            |
   //+----------------------------------------------------+
   bool PingServer()
   {
      char postResult[];
      string resultHeaders;

      int code = WebRequest(
         HTTP_METHOD_POST,
         URL_ENDPOINT,
         "Content-Type: application/x-www-form-urlencoded\r\n",
         3000,
         FIELD_API_KEY + "=" + API_SECRET_KEY + "&ping=1",
         postResult,
         resultHeaders
      );

      if(code == 200)
      {
         string resp = CharArrayToString(postResult);
         if(StringFind(resp, "pong") >= 0 || StringFind(resp, "ok") >= 0)
         {
            if(ENABLE_DEBUG_LOG)
               Print(DEBUG_LOG_PREFIX, "Server reachable!");
            return(true);
         }
      }

      Print(ERROR_LOG_PREFIX, "Server ping failed | Code: ", code);
      return(false);
   }

   //+----------------------------------------------------+
   //| Getter status                                       |
   //+----------------------------------------------------+
   ENUM_API_STATUS GetLastStatus()  { return(m_lastStatus); }
   string          GetLastError()   { return(m_lastError); }
   string          GetLastResponse(){ return(m_lastResponse); }
   int             GetSuccessCount() { return(m_successCount); }
   int             GetFailCount()    { return(m_failCount); }
   datetime        GetLastAttempt()  { return(m_lastAttempt); }
};

//+------------------------------------------------------------------+
//|  INSTANCE GLOBAL - Di-inisialisasi di EA utama                   |
//+------------------------------------------------------------------+
CAPIClient  g_apiClient;

#endif // API_CLIENT_MQH
