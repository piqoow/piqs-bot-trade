<?php
/**
 * PiqsScalper Trading Dashboard
 * XAUUSD M15 RSI Scalper - Web Monitor
 * @author PiqsBot
 * @version 1.0.0
 */

require_once __DIR__ . '/config.php';

$database = db();

// Overall Statistics
$statsSql = "SELECT
    COUNT(*) as total_trades,
    COALESCE(SUM(profit), 0) as total_profit,
    COALESCE(AVG(profit), 0) as avg_profit,
    COALESCE(MAX(profit), 0) as max_profit,
    COALESCE(MIN(profit), 0) as min_profit,
    COALESCE(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END), 0) as win_count,
    COALESCE(SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END), 0) as loss_count,
    COALESCE(COUNT(DISTINCT ip_address), 0) as unique_ips
FROM trade_logs";

$statsResult = $database->fetchOne($statsSql);

$totalTrades = (int)($statsResult['total_trades'] ?? 0);
$winCount = (int)($statsResult['win_count'] ?? 0);
$winRate = $totalTrades > 0 ? round(($winCount / $totalTrades) * 100, 2) : 0;
$totalProfit = (float)($statsResult['total_profit'] ?? 0);
$avgProfit = (float)($statsResult['avg_profit'] ?? 0);
$maxProfit = (float)($statsResult['max_profit'] ?? 0);
$minProfit = (float)($statsResult['min_profit'] ?? 0);
$uniqueIps = (int)($statsResult['unique_ips'] ?? 0);
$lossCount = (int)($statsResult['loss_count'] ?? 0);

// IP Group Statistics
$ipGroupSql = "SELECT
    ip_address,
    COUNT(*) as trade_count,
    SUM(profit) as group_profit,
    AVG(profit) as avg_profit,
    MAX(profit) as max_profit,
    MIN(profit) as min_profit,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losses,
    MAX(time_close) as last_trade,
    MIN(time_open) as first_trade
FROM trade_logs
GROUP BY ip_address
ORDER BY ip_address ASC";

$ipGroups = $database->fetchAll($ipGroupSql);

// Pagination
$page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
$filterIp = isset($_GET['ip']) ? trim($_GET['ip']) : '';
$offset = ($page - 1) * ROWS_PER_PAGE;

if (!empty($filterIp)) {
    $safeIp = $database->escape($filterIp);
    $countSql = "SELECT COUNT(*) as total FROM trade_logs WHERE ip_address = '" . $safeIp . "'";
    $tradesSql = "SELECT * FROM trade_logs WHERE ip_address = '" . $safeIp . "' ORDER BY ip_address ASC, time_close DESC LIMIT " . ROWS_PER_PAGE . " OFFSET " . $offset;
} else {
    $countSql = "SELECT COUNT(*) as total FROM trade_logs";
    $tradesSql = "SELECT * FROM trade_logs ORDER BY ip_address ASC, time_close DESC LIMIT " . ROWS_PER_PAGE . " OFFSET " . $offset;
}

$countResult = $database->fetchOne($countSql);
$totalRows = (int)($countResult['total'] ?? 0);
$pagination = getPagination($page, $totalRows, ROWS_PER_PAGE);
$trades = $database->fetchAll($tradesSql);

// Helper Functions
function getProfitClass($profit) {
    if ($profit > 0) return 'profit';
    if ($profit < 0) return 'loss';
    return 'neutral';
}

function getTypeClass($type) {
    return strtolower($type);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_NAME; ?> - <?php echo APP_TAGLINE; ?></title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }

        /* Header */
        .header {
            background: rgba(15, 15, 25, 0.95);
            border: 1px solid rgba(240, 185, 11, 0.3);
            border-radius: 12px;
            padding: 20px 30px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header-left { display: flex; align-items: center; gap: 15px; }
        .logo {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #f0b90b 0%, #f7931a 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: bold;
            color: #0a0a0f;
        }
        .header-info h1 {
            font-size: 1.5rem;
            color: #fff;
            margin-bottom: 4px;
        }
        .badge {
            display: inline-block;
            background: linear-gradient(135deg, #f0b90b 0%, #e6a00d 100%);
            color: #0a0a0f;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .server-time {
            text-align: right;
            color: #888;
            font-size: 0.85rem;
        }
        .server-time strong { color: #f0b90b; }

        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(240, 185, 11, 0.2);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.3s ease;
        }
        .stat-card:hover {
            border-color: rgba(240, 185, 11, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        .stat-label {
            color: #888;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
        }
        .stat-value.profit { color: #3fb950; }
        .stat-value.loss { color: #f85149; }
        .stat-value.neutral { color: #888; }
        .stat-value.win-rate { color: #f0b90b; }
        .stat-sub {
            font-size: 0.8rem;
            color: #666;
            margin-top: 5px;
        }

        /* Section Title */
        .section-title {
            color: #fff;
            font-size: 1.25rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(240, 185, 11, 0.3);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section-title::before {
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, #f0b90b 0%, #f7931a 100%);
            border-radius: 2px;
        }

        /* IP Groups Grid */
        .ip-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .ip-card {
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(240, 185, 11, 0.15);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        .ip-card:hover {
            border-color: rgba(240, 185, 11, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .ip-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .ip-address {
            font-family: 'Monaco', 'Consolas', monospace;
            color: #f0b90b;
            font-weight: 600;
            font-size: 1rem;
        }
        .trade-count {
            background: rgba(240, 185, 11, 0.15);
            color: #f0b90b;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .ip-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .ip-stat {
            background: rgba(255, 255, 255, 0.03);
            padding: 10px;
            border-radius: 8px;
        }
        .ip-stat-label { font-size: 0.7rem; color: #666; text-transform: uppercase; }
        .ip-stat-value { font-size: 1.1rem; font-weight: 600; margin-top: 2px; }
        .ip-stat-value.profit { color: #3fb950; }
        .ip-stat-value.loss { color: #f85149; }

        /* Filter Bar */
        .filter-bar {
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(240, 185, 11, 0.15);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
        }
        .filter-form { display: flex; align-items: center; gap: 10px; }
        .filter-input {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(240, 185, 11, 0.2);
            border-radius: 8px;
            padding: 10px 15px;
            color: #fff;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
            width: 200px;
        }
        .filter-input:focus {
            outline: none;
            border-color: #f0b90b;
        }
        .filter-input::placeholder { color: #666; }
        .filter-btn {
            background: linear-gradient(135deg, #f0b90b 0%, #e6a00d 100%);
            color: #0a0a0f;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .filter-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(240, 185, 11, 0.3); }
        .filter-clear {
            color: #888;
            text-decoration: none;
            font-size: 0.9rem;
            padding: 10px;
        }
        .filter-clear:hover { color: #f0b90b; }

        /* Table */
        .table-container {
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(240, 185, 11, 0.15);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .table-scroll { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; min-width: 1000px; }
        th {
            background: rgba(240, 185, 11, 0.1);
            color: #f0b90b;
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid rgba(240, 185, 11, 0.2);
            white-space: nowrap;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }
        tr:hover { background: rgba(255, 255, 255, 0.02); }
        tr:last-child td { border-bottom: none; }
        .ticket { font-family: 'Monaco', 'Consolas', monospace; color: #888; }
        .type { font-weight: 600; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; }
        .type.buy { background: rgba(63, 185, 80, 0.15); color: #3fb950; }
        .type.sell { background: rgba(248, 81, 73, 0.15); color: #f85149; }
        .type.unknown { background: rgba(136, 136, 136, 0.15); color: #888; }
        .profit-val { font-weight: 600; }
        .profit-val.profit { color: #3fb950; }
        .profit-val.loss { color: #f85149; }
        .profit-val.neutral { color: #888; }
        .symbol { font-family: 'Monaco', 'Consolas', monospace; color: #f0b90b; }
        .rsi { font-family: 'Monaco', 'Consolas', monospace; }
        .ip-badge {
            display: inline-block;
            background: rgba(240, 185, 11, 0.1);
            border: 1px solid rgba(240, 185, 11, 0.3);
            color: #f0b90b;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        .time { color: #888; font-size: 0.85rem; }
        .lot { color: #e0e0e0; }

        /* Pagination */
        .pagination {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .pagination a, .pagination span {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 40px;
            height: 40px;
            padding: 0 12px;
            background: rgba(20, 20, 35, 0.9);
            border: 1px solid rgba(240, 185, 11, 0.2);
            border-radius: 8px;
            color: #e0e0e0;
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        .pagination a:hover {
            border-color: #f0b90b;
            color: #f0b90b;
        }
        .pagination .active {
            background: linear-gradient(135deg, #f0b90b 0%, #e6a00d 100%);
            color: #0a0a0f;
            font-weight: 600;
            border-color: #f0b90b;
        }
        .pagination .disabled {
            opacity: 0.4;
            pointer-events: none;
        }
        .pagination .info {
            background: transparent;
            border: none;
            color: #888;
            font-size: 0.85rem;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 30px 0;
            color: #666;
            font-size: 0.85rem;
        }
        .footer a { color: #f0b90b; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        .empty-state-icon { font-size: 3rem; margin-bottom: 15px; opacity: 0.5; }
        .empty-state h3 { color: #e0e0e0; margin-bottom: 8px; }

        /* Responsive */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .header { padding: 15px; }
            .header-info h1 { font-size: 1.2rem; }
            .stat-card { padding: 16px; }
            .stat-value { font-size: 1.5rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
            .ip-grid { grid-template-columns: 1fr; }
            .filter-bar { flex-direction: column; align-items: stretch; }
            .filter-form { flex-direction: column; }
            .filter-input { width: 100%; }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr; }
            .logo { width: 40px; height: 40px; font-size: 22px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-left">
                <div class="logo">P</div>
                <div class="header-info">
                    <h1><?php echo APP_NAME; ?></h1>
                    <span class="badge">M15 RSI Scalper v<?php echo APP_VERSION; ?></span>
                </div>
            </div>
            <div class="server-time">
                Server Time: <strong><?php echo date('d M Y, H:i:s'); ?></strong><br>
                <small>Asia/Jakarta (GMT+7)</small>
            </div>
        </header>

        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Profit</div>
                <div class="stat-value <?php echo getProfitClass($totalProfit); ?>">
                    <?php echo $totalProfit >= 0 ? '+' : ''; ?>$<?php echo number_format($totalProfit, 2); ?>
                </div>
                <div class="stat-sub"><?php echo $uniqueIps; ?> unique IPs</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value win-rate"><?php echo $winRate; ?>%</div>
                <div class="stat-sub"><?php echo number_format($winCount); ?>W / <?php echo number_format($lossCount); ?>L</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value neutral"><?php echo number_format($totalTrades); ?></div>
                <div class="stat-sub">Avg: $<?php echo number_format($avgProfit, 2); ?>/trade</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Best / Worst Trade</div>
                <div class="stat-value profit">+$<?php echo number_format($maxProfit, 2); ?></div>
                <div class="stat-sub">Worst: <?php echo $minProfit >= 0 ? '+' : ''; ?>$<?php echo number_format($minProfit, 2); ?></div>
            </div>
        </div>

        <!-- IP Groups -->
        <h2 class="section-title">Trading by IP Address</h2>
        <div class="ip-grid">
            <?php if (empty($ipGroups)): ?>
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>No trading data yet</h3>
                    <p>Start trading to see IP statistics</p>
                </div>
            <?php else: ?>
                <?php foreach ($ipGroups as $ip):
                    $ipWinRate = $ip['trade_count'] > 0 ? round(($ip['wins'] / $ip['trade_count']) * 100, 1) : 0;
                    $ipProfitClass = getProfitClass($ip['group_profit']);
                ?>
                    <div class="ip-card">
                        <div class="ip-header">
                            <span class="ip-address"><?php echo htmlspecialchars($ip['ip_address']); ?></span>
                            <span class="trade-count"><?php echo $ip['trade_count']; ?> trades</span>
                        </div>
                        <div class="ip-stats">
                            <div class="ip-stat">
                                <div class="ip-stat-label">Total P/L</div>
                                <div class="ip-stat-value <?php echo $ipProfitClass; ?>">
                                    <?php echo $ip['group_profit'] >= 0 ? '+' : ''; ?>$<?php echo number_format($ip['group_profit'], 2); ?>
                                </div>
                            </div>
                            <div class="ip-stat">
                                <div class="ip-stat-label">Win Rate</div>
                                <div class="ip-stat-value" style="color: <?php echo $ipWinRate >= 50 ? '#3fb950' : '#f85149'; ?>">
                                    <?php echo $ipWinRate; ?>%
                                </div>
                            </div>
                            <div class="ip-stat">
                                <div class="ip-stat-label">Avg Profit</div>
                                <div class="ip-stat-value <?php echo getProfitClass($ip['avg_profit']); ?>">
                                    <?php echo $ip['avg_profit'] >= 0 ? '+' : ''; ?>$<?php echo number_format($ip['avg_profit'], 2); ?>
                                </div>
                            </div>
                            <div class="ip-stat">
                                <div class="ip-stat-label">Last Trade</div>
                                <div class="ip-stat-value" style="color: #888; font-size: 0.9rem;">
                                    <?php echo formatTanggal($ip['last_trade']); ?>
                                </div>
                            </div>
                        </div>
                    </div>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>

        <!-- Filter Bar -->
        <div class="filter-bar">
            <form method="GET" class="filter-form">
                <?php if (!empty($filterIp)): ?>
                    <input type="hidden" name="ip" value="<?php echo htmlspecialchars($filterIp); ?>">
                <?php endif; ?>
                <input type="text" name="ip" class="filter-input" placeholder="Filter by IP Address..." value="<?php echo htmlspecialchars($filterIp); ?>">
                <button type="submit" class="filter-btn">Filter</button>
                <?php if (!empty($filterIp)): ?>
                    <a href="?" class="filter-clear">Clear Filter</a>
                <?php endif; ?>
            </form>
            <div style="color: #888; font-size: 0.9rem;">
                Showing <?php echo count($trades); ?> of <?php echo number_format($totalRows); ?> trades
                <?php if (!empty($filterIp)): ?>
                    (filtered by: <?php echo htmlspecialchars($filterIp); ?>)
                <?php endif; ?>
            </div>
        </div>

        <!-- Trade Table -->
        <div class="table-container">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Ticket</th>
                            <th>Type</th>
                            <th>Lot</th>
                            <th>Open</th>
                            <th>Close</th>
                            <th>P/L</th>
                            <th>Symbol</th>
                            <th>RSI</th>
                            <th>IP Address</th>
                            <th>Close Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (empty($trades)): ?>
                            <tr>
                                <td colspan="10">
                                    <div class="empty-state">
                                        <div class="empty-state-icon">📋</div>
                                        <h3>No trades found</h3>
                                        <p>No trading records available<?php echo !empty($filterIp) ? ' for this IP address' : ''; ?></p>
                                    </div>
                                </td>
                            </tr>
                        <?php else: ?>
                            <?php foreach ($trades as $trade):
                                $profitClass = getProfitClass($trade['profit']);
                                $typeClass = getTypeClass($trade['trade_type']);
                            ?>
                                <tr>
                                    <td class="ticket">#<?php echo $trade['ticket']; ?></td>
                                    <td><span class="type <?php echo $typeClass; ?>"><?php echo htmlspecialchars($trade['trade_type']); ?></span></td>
                                    <td class="lot"><?php echo number_format($trade['lot'], 2); ?></td>
                                    <td><?php echo number_format($trade['price_open'], 5); ?></td>
                                    <td><?php echo number_format($trade['price_close'], 5); ?></td>
                                    <td class="profit-val <?php echo $profitClass; ?>">
                                        <?php echo $trade['profit'] >= 0 ? '+' : ''; ?>$<?php echo number_format($trade['profit'], 2); ?>
                                    </td>
                                    <td class="symbol"><?php echo htmlspecialchars($trade['symbol']); ?></td>
                                    <td class="rsi"><?php echo number_format($trade['rsi_value'], 2); ?></td>
                                    <td><span class="ip-badge"><?php echo htmlspecialchars($trade['ip_address']); ?></span></td>
                                    <td class="time"><?php echo formatTanggalWaktu($trade['time_close']); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Pagination -->
        <?php if ($pagination['total'] > 1): ?>
            <div class="pagination">
                <?php if ($pagination['has_prev']): ?>
                    <a href="?page=<?php echo $pagination['prev_page']; ?><?php echo !empty($filterIp) ? '&ip=' . urlencode($filterIp) : ''; ?>">&laquo; Prev</a>
                <?php else: ?>
                    <span class="disabled">&laquo; Prev</span>
                <?php endif; ?>

                <?php
                $start = max(1, $pagination['current'] - 2);
                $end = min($pagination['total'], $pagination['current'] + 2);
                if ($start > 1): ?>
                    <a href="?page=1<?php echo !empty($filterIp) ? '&ip=' . urlencode($filterIp) : ''; ?>">1</a>
                    <?php if ($start > 2): ?>
                        <span class="info">...</span>
                    <?php endif; ?>
                <?php endif; ?>

                <?php for ($i = $start; $i <= $end; $i++): ?>
                    <?php if ($i == $pagination['current']): ?>
                        <span class="active"><?php echo $i; ?></span>
                    <?php else: ?>
                        <a href="?page=<?php echo $i; ?><?php echo !empty($filterIp) ? '&ip=' . urlencode($filterIp) : ''; ?>"><?php echo $i; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>

                <?php if ($end < $pagination['total']): ?>
                    <?php if ($end < $pagination['total'] - 1): ?>
                        <span class="info">...</span>
                    <?php endif; ?>
                    <a href="?page=<?php echo $pagination['total']; ?><?php echo !empty($filterIp) ? '&ip=' . urlencode($filterIp) : ''; ?>"><?php echo $pagination['total']; ?></a>
                <?php endif; ?>

                <?php if ($pagination['has_next']): ?>
                    <a href="?page=<?php echo $pagination['next_page']; ?><?php echo !empty($filterIp) ? '&ip=' . urlencode($filterIp) : ''; ?>">Next &raquo;</a>
                <?php else: ?>
                    <span class="disabled">Next &raquo;</span>
                <?php endif; ?>
            </div>
        <?php endif; ?>

        <!-- Footer -->
        <footer class="footer">
            <p><?php echo APP_NAME; ?> v<?php echo APP_VERSION; ?> &bull; <?php echo APP_TAGLINE; ?></p>
            <p style="margin-top: 8px;">Page rendered at <?php echo date('d M Y H:i:s T'); ?></p>
        </footer>
    </div>
</body>
</html>
