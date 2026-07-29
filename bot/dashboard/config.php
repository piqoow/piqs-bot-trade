<?php
//+------------------------------------------------------------------+
//|  config.php - Dashboard Database Configuration                   |
//|  XAUUSD Scalping Bot - Web Dashboard                            |
//|                                                                  |
//|  Copy setting dari db.php jika menggunakan server yang sama       |
//+------------------------------------------------------------------+

// Gunakan setting yang sama dengan backend
require_once __DIR__ . '/../backend/db.php';

// Nama aplikasi
define('APP_NAME', 'PiqsScalper Dashboard');
define('APP_VERSION', '1.0.0');
define('APP_TAGLINE', 'XAUUSD M15 RSI Scalping Monitor');

// Timezone
date_default_timezone_set('Asia/Jakarta');

// Rows per page untuk pagination
define('ROWS_PER_PAGE', 25);

// Format tanggal Indonesia
function formatTanggal($datetime)
{
    if (empty($datetime)) return '-';
    $date = new DateTime($datetime);
    $date->setTimezone(new DateTimeZone('Asia/Jakarta'));
    return $date->format('d M Y');
}

function formatWaktu($datetime)
{
    if (empty($datetime)) return '-';
    $date = new DateTime($datetime);
    $date->setTimezone(new DateTimeZone('Asia/Jakarta'));
    return $date->format('H:i:s');
}

function formatTanggalWaktu($datetime)
{
    if (empty($datetime)) return '-';
    $date = new DateTime($datetime);
    $date->setTimezone(new DateTimeZone('Asia/Jakarta'));
    return $date->format('d M Y, H:i');
}

//+------------------------------------------------------------------+
//|  PAGINATION HELPER                                               |
//+------------------------------------------------------------------+

function getPagination($currentPage, $totalRows, $perPage = ROWS_PER_PAGE)
{
    $totalPages = ceil($totalRows / $perPage);
    $currentPage = max(1, min($currentPage, $totalPages));

    return [
        'current'   => $currentPage,
        'total'     => $totalPages,
        'per_page'  => $perPage,
        'offset'    => ($currentPage - 1) * $perPage,
        'has_prev'  => $currentPage > 1,
        'has_next'  => $currentPage < $totalPages,
        'prev_page' => $currentPage - 1,
        'next_page' => $currentPage + 1,
        'total_rows' => $totalRows
    ];
}
?>
