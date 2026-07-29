<?php
//+------------------------------------------------------------------+
//|  db.php - MySQL Database Connection                              |
//|  XAUUSD Scalping Bot - Backend                                   |
//|                                                                  |
//|  FILE INI WAJIB BERNAMA 'db.php' - Jangan rename!               |
//|                                                                  |
//|  Konfigurasi:                                                    |
//|    - Host database                                               |
//|    - Nama database                                               |
//|    - Username & password                                         |
//|    - Charset UTF-8                                               |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|  CONFIGURATION - ISI SESUAIKAN DENGAN SERVER ANDA               |
//+------------------------------------------------------------------+

// Host database MySQL
define('DB_HOST', 'localhost');

// Nama database yang sudah dibuat
define('DB_NAME', 'piqs_trading');

// Username MySQL
define('DB_USER', 'piqs_user');

// Password MySQL
define('DB_PASS', 'YOUR_SECURE_PASSWORD_HERE');

// Charset - STANDAR UTF-8
define('DB_CHARSET', 'utf8mb4');

//+------------------------------------------------------------------+
//|  DATABASE CONNECTION CLASS                                       |
//+------------------------------------------------------------------+

class DatabaseConnection
{
    /**
     * @var mysqli|null
     */
    private $connection = null;

    /**
     * @var DatabaseConnection|null
     */
    private static $instance = null;

    /**
     * Konstruktor - koneksi langsung saat objek dibuat
     */
    private function __construct()
    {
        $this->connect();
    }

    /**
     * Singleton pattern - memastikan hanya 1 koneksi database
     * Usage: $db = DatabaseConnection::getInstance();
     */
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Buat koneksi ke MySQL
     * Menampilkan error detail jika koneksi gagal
     */
    private function connect()
    {
        // Set charset sebelum koneksi
        mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

        try {
            $this->connection = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);

            // Set charset untuk support emoji & karakter khusus
            $this->connection->set_charset(DB_CHARSET);

            // Options untuk production
            $this->connection->options(MYSQLI_OPT_CONNECT_TIMEOUT, 5);
            $this->connection->options(MYSQLI_OPT_READ_TIMEOUT, 10);

        } catch (mysqli_sql_exception $e) {
            // Log error tapi jangan tampilkan detail di production
            error_log('[db.php] MySQL Connection Error: ' . $e->getMessage());

            // Kirim generic error response
            $this->sendError('Database connection failed. Please try again later.');
        }
    }

    /**
     * Ambil koneksi mysqli
     * @return mysqli
     */
    public function getConnection()
    {
        // Reconnect jika koneksi sudah timeout/mati
        if ($this->connection === null || !$this->connection->ping()) {
            $this->connect();
        }
        return $this->connection;
    }

    /**
     * Escape string untuk mencegah SQL Injection
     * @param string $value
     * @return string
     */
    public function escape($value)
    {
        return $this->getConnection()->real_escape_string($value);
    }

    /**
     * Jalankan query dengan error handling
     * @param string $sql
     * @return mysqli_result|bool
     */
    public function query($sql)
    {
        $result = $this->getConnection()->query($sql);

        if ($result === false) {
            error_log('[db.php] Query Error: ' . $this->getConnection()->error . ' | SQL: ' . $sql);
        }

        return $result;
    }

    /**
     * Jalankan prepared statement untuk query yang berulang
     * LEBIH AMAN dari query biasa - gunakan ini untuk data dari EA
     * @param string $sql
     * @param string $types
     * @param array $params
     * @return mysqli_stmt|bool
     */
    public function prepare($sql, $types = '', $params = [])
    {
        $stmt = $this->getConnection()->prepare($sql);

        if ($stmt === false) {
            error_log('[db.php] Prepare Error: ' . $this->getConnection()->error);
            return false;
        }

        if (!empty($params)) {
            // Bind parameter: 's' = string, 'i' = integer, 'd' = double
            $stmt->bind_param($types, ...$params);
        }

        return $stmt;
    }

    /**
     * Eksekusi prepared statement dan return affected rows
     * @param string $sql
     * @param string $types
     * @param array $params
     * @return bool
     */
    public function execute($sql, $types = '', $params = [])
    {
        $stmt = $this->prepare($sql, $types, $params);

        if ($stmt === false) {
            return false;
        }

        $execResult = $stmt->execute();
        $stmt->close();

        return $execResult;
    }

    /**
     * Ambil last insert ID
     * @return int|string
     */
    public function lastInsertId()
    {
        return $this->getConnection()->insert_id;
    }

    /**
     * Ambil semua baris hasil query sebagai array asosiatif
     * @param string $sql
     * @return array
     */
    public function fetchAll($sql)
    {
        $result = $this->query($sql);

        if ($result === false) {
            return [];
        }

        $rows = [];
        while ($row = $result->fetch_assoc()) {
            $rows[] = $row;
        }
        $result->free();

        return $rows;
    }

    /**
     * Ambil satu baris sebagai array asosiatif
     * @param string $sql
     * @return array|null
     */
    public function fetchOne($sql)
    {
        $result = $this->query($sql);

        if ($result === false) {
            return null;
        }

        $row = $result->fetch_assoc();
        $result->free();

        return $row;
    }

    /**
     * Tutup koneksi database
     */
    public function close()
    {
        if ($this->connection !== null) {
            $this->connection->close();
            $this->connection = null;
        }
    }

    /**
     * Kirim error response JSON dan exit
     * @param string $message
     * @param int $code
     */
    private function sendError($message, $code = 500)
    {
        http_response_code($code);
        header('Content-Type: application/json');
        echo json_encode([
            'success' => false,
            'error' => $message
        ]);
        exit;
    }

    /**
     * Destruktor - auto cleanup
     */
    public function __destruct()
    {
        $this->close();
    }
}

//+------------------------------------------------------------------+
//|  QUICK ACCESS FUNCTION - Untuk convenience                        |
//+------------------------------------------------------------------+

/**
 * Ambil instance database (singleton)
 * Usage: $db = db();
 *
 * @return DatabaseConnection
 */
function db()
{
    return DatabaseConnection::getInstance();
}

//+------------------------------------------------------------------+
//|  DATABASE SETUP SCRIPT                                           |
//|  Jalankan script ini SEKALI untuk membuat tabel                  |
//|  Copy ke browser atau jalankan via CLI: php db_setup.php         |
//+------------------------------------------------------------------+

/*
-- ============================================================
-- DATABASE: piqs_trading
-- Buat dulu: CREATE DATABASE piqs_trading CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ============================================================

-- Tabel utama: trade_logs
-- Menyimpan semua history transaksi dari EA

CREATE TABLE IF NOT EXISTS trade_logs (
    -- Primary key: auto increment
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    -- Data dari MQL5 EA
    ticket          BIGINT UNSIGNED NOT NULL UNIQUE COMMENT 'Nomor ticket MT5',
    trade_type      ENUM('BUY','SELL','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    lot             DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT 'Volume lot',
    price_open      DECIMAL(18,5) NOT NULL DEFAULT 0 COMMENT 'Harga buka',
    price_close     DECIMAL(18,5) NOT NULL DEFAULT 0 COMMENT 'Harga tutup',
    profit          DECIMAL(15,4) NOT NULL DEFAULT 0 COMMENT 'Profit/Loss',
    symbol          VARCHAR(20) NOT NULL DEFAULT 'XAUUSD' COMMENT 'Symbol trading',
    time_open       DATETIME NOT NULL COMMENT 'Waktu buka posisi',
    time_close      DATETIME NOT NULL COMMENT 'Waktu tutup posisi',

    -- Data tambahan
    ip_address      VARCHAR(45) NOT NULL COMMENT 'IP VPS/Client (support IPv6)',
    magic_number    BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Magic number EA',
    sl_points       DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'Stop Loss dalam poin',
    tp_points       DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'Take Profit dalam poin',
    rsi_value       DECIMAL(6,2) NOT NULL DEFAULT 50 COMMENT 'Nilai RSI saat trade',
    api_key         VARCHAR(100) NOT NULL COMMENT 'API key yang digunakan',

    -- Metadata
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Index untuk performa query
    INDEX idx_ip_address     (ip_address),
    INDEX idx_symbol         (symbol),
    INDEX idx_trade_type     (trade_type),
    INDEX idx_time_close     (time_close),
    INDEX idx_profit         (profit),
    INDEX idx_created_at     (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Trade history dari PiqsScalper EA';

-- Tabel tambahan: api_logs (opsional - untuk audit trail)
CREATE TABLE IF NOT EXISTS api_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ip_address      VARCHAR(45) NOT NULL,
    endpoint        VARCHAR(255) NOT NULL,
    request_data    TEXT COMMENT 'Data POST yang diterima',
    response_status INT NOT NULL DEFAULT 200,
    response_body   TEXT,
    user_agent      VARCHAR(500),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ip        (ip_address),
    INDEX idx_created   (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert data contoh (test only - hapus setelah selesai testing)
INSERT INTO trade_logs (ticket, trade_type, lot, price_open, price_close, profit,
                        symbol, time_open, time_close, ip_address, magic_number,
                        sl_points, tp_points, rsi_value, api_key)
VALUES
(123456, 'BUY', 0.10, 2350.500, 2352.100, 16.00, 'XAUUSD',
 '2024-07-28 09:15:00', '2024-07-28 09:45:00', '192.168.1.100',
 20240728, 150.0, 100.0, 12.50, 'pk_live_piqs_xauusd_2024'),
(123457, 'SELL', 0.10, 2352.500, 2351.200, 13.00, 'XAUUSD',
 '2024-07-28 10:00:00', '2024-07-28 10:30:00', '192.168.1.100',
 20240728, 150.0, 100.0, 88.20, 'pk_live_piqs_xauusd_2024');

-- Grant privileges untuk user (jalankan sebagai root)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON piqs_trading.* TO 'piqs_user'@'localhost';
-- FLUSH PRIVILEGES;

*/
?>
