<?php
//+------------------------------------------------------------------+
//|  log_trade.php - API Endpoint untuk MQL5/Python Trading Bot       |
//|  XAUUSD Scalping Bot - Backend                                   |
//|                                                                  |
//|  Compatible with:                                               |
//|    - MQL5 Expert Advisor (PiqsScalper.mq5)                      |
//|    - Python Bot (piqs_bot.py)                                    |
//|                                                                  |
//|  Method: POST                                                    |
//|  Content-Type: application/x-www-form-urlencoded                |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|  CORS & SECURITY HEADERS                                          |
//+------------------------------------------------------------------+

// Allow dari semua origin (VPS bisa dari IP manapun)
// Untuk production, ganti * dengan domain spesifik EA Anda
header('Access-Control-Allow-Origin: *');

// Allow methods
header('Access-Control-Allow-Methods: POST, OPTIONS');

// Allow headers
header('Access-Control-Allow-Headers: Content-Type');

// Cache kontrol
header('Cache-Control: no-store, no-cache, must-revalidate');
header('Content-Type: application/json; charset=utf-8');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

//+------------------------------------------------------------------+
//|  LOAD DATABASE CONNECTION                                        |
//+------------------------------------------------------------------+
require_once __DIR__ . '/db.php';

//+------------------------------------------------------------------+
//|  CONSTANTS                                                        |
//+------------------------------------------------------------------+

// API Key yang harus匹配 dengan MQL5 Config.mqh
define('VALID_API_KEY', 'pk_live_piqs_xauusd_2024');

// Mode debug - tampilkan error detail
define('DEBUG_MODE', false);

//+------------------------------------------------------------------+
//|  HELPER FUNCTIONS                                                 |
//+------------------------------------------------------------------+

/**
 * Kirim response JSON dan exit
 */
function sendResponse($success, $data = [], $message = '', $httpCode = 200)
{
    http_response_code($httpCode);
    echo json_encode([
        'success' => $success,
        'message' => $message,
        'data' => $data,
        'received_at' => date('Y-m-d H:i:s')
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Validasi input - amankan data dari EA
 */
function sanitizeInput($value, $type = 'string')
{
    if ($value === null || $value === '') {
        return null;
    }

    switch ($type) {
        case 'int':
            return (int) filter_var($value, FILTER_SANITIZE_NUMBER_INT);

        case 'float':
            return (float) filter_var($value, FILTER_SANITIZE_NUMBER_FLOAT,
                                       FILTER_FLAG_ALLOW_FRACTION);

        case 'string':
            return htmlspecialchars(trim($value), ENT_QUOTES, 'UTF-8');

        case 'ip':
            // Validasi IPv4 dan IPv6
            if (filter_var($value, FILTER_VALIDATE_IP)) {
                return $value;
            }
            return '0.0.0.0';

        default:
            return $value;
    }
}

/**
 * Validasi API Key
 */
function validateApiKey($key)
{
    if (empty($key)) {
        return false;
    }
    return hash_equals(VALID_API_KEY, $key);
}

//+------------------------------------------------------------------+
//|  HANDLE PING REQUEST (untuk connectivity check)                  |
//+------------------------------------------------------------------+
if (isset($_POST['ping'])) {
    sendResponse(true, [], 'pong');
}

//+------------------------------------------------------------------+
//|  MAIN: PROSES DATA TRADE                                         |
//+------------------------------------------------------------------+

// Pastikan request adalah POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    sendResponse(false, [], 'Method not allowed. Use POST.', 405);
}

//+------------------------------------------------------------------+
//|  1. VALIDASI API KEY                                              |
//+------------------------------------------------------------------+
$apiKey = isset($_POST['api_key']) ? $_POST['api_key'] : '';

if (!validateApiKey($apiKey)) {
    // Log attempt yang tidak sah
    $clientIP = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    error_log("[log_trade.php] Unauthorized access attempt from IP: $clientIP");
    sendResponse(false, [], 'Unauthorized', 401);
}

//+------------------------------------------------------------------+
//|  2. AMBIL DAN SANITASI DATA                                       |
//+------------------------------------------------------------------+

// Ambil IP client (VPS/EA)
$ipAddress = $_SERVER['REMOTE_ADDR']
           ?? $_SERVER['HTTP_X_FORWARDED_FOR']
           ?? $_SERVER['HTTP_X_REAL_IP']
           ?? '127.0.0.1';

// Parse IP dari X-Forwarded-For (jika ada proxy)
if (strpos($ipAddress, ',') !== false) {
    $ipAddress = trim(explode(',', $ipAddress)[0]);
}

// Sanitasi data dari EA
$tradeData = [
    'ticket'       => sanitizeInput($_POST['ticket'] ?? '', 'int'),
    'trade_type'   => strtoupper(sanitizeInput($_POST['type'] ?? '', 'string')),
    'lot'          => sanitizeInput($_POST['lot'] ?? '', 'float'),
    'price_open'   => sanitizeInput($_POST['price_open'] ?? '', 'float'),
    'price_close'  => sanitizeInput($_POST['price_close'] ?? '', 'float'),
    'profit'       => sanitizeInput($_POST['profit'] ?? '', 'float'),
    'symbol'       => sanitizeInput($_POST['symbol'] ?? '', 'string') ?: 'XAUUSD',
    'time_open'    => sanitizeInput($_POST['time_open'] ?? '', 'int'),
    'time_close'   => sanitizeInput($_POST['time_close'] ?? '', 'int'),
    'ip_address'   => sanitizeInput($ipAddress, 'ip'),
    'magic'        => sanitizeInput($_POST['magic'] ?? '', 'int'),
    'sl_points'    => sanitizeInput($_POST['sl_pts'] ?? '', 'float'),
    'tp_points'    => sanitizeInput($_POST['tp_pts'] ?? '', 'float'),
    'rsi_value'    => sanitizeInput($_POST['rsi_value'] ?? '', 'float'),
    'api_key'      => substr($apiKey, 0, 50), // Batasi panjang
];

// Validasi data minimal yang harus ada
if ($tradeData['ticket'] === null || $tradeData['ticket'] <= 0) {
    sendResponse(false, [], 'Invalid ticket number', 400);
}

if (!in_array($tradeData['trade_type'], ['BUY', 'SELL', 'UNKNOWN'])) {
    $tradeData['trade_type'] = 'UNKNOWN';
}

//+------------------------------------------------------------------+
//|  3. SIMPAN KE DATABASE (Prepared Statement - AMAN SQL Injection)  |
//+------------------------------------------------------------------+

try {
    $db = db();

    // SQL INSERT dengan ON DUPLICATE KEY UPDATE
    // Jika ticket sudah ada (EA retry), update saja bukan insert baru
    $sql = "INSERT INTO trade_logs (
                ticket, trade_type, lot, price_open, price_close,
                profit, symbol, time_open, time_close, ip_address,
                magic_number, sl_points, tp_points, rsi_value, api_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                trade_type   = VALUES(trade_type),
                lot          = VALUES(lot),
                price_close  = VALUES(price_close),
                profit       = VALUES(profit),
                time_close   = VALUES(time_close),
                rsi_value    = VALUES(rsi_value),
                updated_at   = CURRENT_TIMESTAMP";

    // Prepared statement - TIDAK PERNAH langsung concat user input ke SQL
    $stmt = $db->prepare($sql);

    if ($stmt === false) {
        throw new Exception('Failed to prepare statement: ' . $db->getConnection()->error);
    }

    // Bind parameter: i=int, s=string, d=double
    $stmt->bind_param(
        'isdddssisidddds',
        $tradeData['ticket'],
        $tradeData['trade_type'],
        $tradeData['lot'],
        $tradeData['price_open'],
        $tradeData['price_close'],
        $tradeData['profit'],
        $tradeData['symbol'],
        $tradeData['time_open'],
        $tradeData['time_close'],
        $tradeData['ip_address'],
        $tradeData['magic'],
        $tradeData['sl_points'],
        $tradeData['tp_points'],
        $tradeData['rsi_value'],
        $tradeData['api_key']
    );

    // Eksekusi
    $execResult = $stmt->execute();

    if ($execResult) {
        // Deteksi apakah insert baru atau update
        $insertId = $db->lastInsertId();
        $isNew = ($insertId > 0);

        $responseData = [
            'ticket'      => $tradeData['ticket'],
            'saved'       => true,
            'is_new'      => $isNew,
            'trade_type'  => $tradeData['trade_type'],
            'profit'      => $tradeData['profit'],
            'lot'         => $tradeData['lot'],
            'ip_address'  => $tradeData['ip_address'],
            'server_time' => date('Y-m-d H:i:s')
        ];

        $stmt->close();

        // Log success
        error_log(sprintf(
            "[log_trade.php] Trade saved | Ticket: #%d | %s | Profit: %.2f | IP: %s",
            $tradeData['ticket'],
            $tradeData['trade_type'],
            $tradeData['profit'],
            $tradeData['ip_address']
        ));

        sendResponse(true, $responseData, 'Trade logged successfully');

    } else {
        throw new Exception('Execute failed: ' . $stmt->error);
    }

} catch (mysqli_sql_exception $e) {
    error_log('[log_trade.php] MySQL Error: ' . $e->getMessage());
    sendResponse(false, [], 'Database error', 500);

} catch (Exception $e) {
    error_log('[log_trade.php] General Error: ' . $e->getMessage());
    sendResponse(false, [], 'Server error', 500);
}

//+------------------------------------------------------------------+
?>
