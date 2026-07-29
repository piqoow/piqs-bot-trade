# PiqsBot Trade - Python Trading Bot

XAUUSD M15 RSI Scalper untuk MetaTrader 5

**Version:** 2.0.0  
**Platform:** Python 3.8+  
**Broker:** Exness, IC Markets, dll (MT5)

---

## 📁 Struktur Project

```
piqs-bot-trade/
├── bot/
│   ├── python/                    ← Python Trading Bot
│   │   ├── piqs_bot.py           ← Main bot file
│   │   ├── config.py             ← Configuration
│   │   ├── rsi_trigger.py        ← RSI logic
│   │   ├── money_management.py   ← Lot & risk
│   │   ├── mt5_handler.py        ← MT5 connection
│   │   ├── api_client.py        ← Web logging
│   │   ├── __init__.py
│   │   └── requirements.txt
│   ├── backend/                   ← PHP Backend
│   │   ├── log_trade.php        ← API endpoint
│   │   └── db.php               ← Database connection
│   └── dashboard/                 ← Web Dashboard
│       ├── index.php
│       └── config.php
└── README.md
```

---

## 🚀 Instalasi

### 1. Install Python Dependencies

```bash
cd bot/python
pip install -r requirements.txt
```

Atau install manual:

```bash
pip install MetaTrader5 requests
```

### 2. Install MetaTrader 5

Pastikan MT5 sudah terinstall dan running di komputer/VPS Anda.

### 3. Enable DLL Imports (Optional)

Jika bot tidak bisa connect, enable **"Allow DLL imports"** di:
```
MT5 → Tools → Options → Expert Advisors → ✓ Allow DLL imports
```

---

## ⚙️ Konfigurasi

### Edit `config.py`

```python
# === Trading Settings ===
symbol = "XAUUSD"              # Symbol
timeframe = 15                  # M15
magic = 20240728               # Magic number

# === RSI Levels ===
rsi_extreme_buy = 15.0         # Buy signal: RSI < 15
rsi_extreme_sell = 85.0        # Sell signal: RSI > 85

# === Money Management ===
lot_mode = "FIXED"             # FIXED, RISK_BASED, MINIMUM
lot_size = 0.10                # Lot tetap
risk_percent = 2.0             # Risk 2% (jika RISK_BASED)

# === Stop Loss & Take Profit ===
stop_loss_pts = 150            # SL 150 points = 15 pips
take_profit_pts = 100          # TP 100 points = 10 pips

# === Trading Hours ===
session_start = 9              # 09:00
session_end = 21              # 21:00

# === API Settings ===
API.url = "https://your-server.com/backend/log_trade.php"
API.api_key = "pk_live_piqs_xauusd_2024"
```

---

## 🎮 Menjalankan Bot

### Mode Normal (Terminal)

```bash
cd bot/python
python piqs_bot.py
```

### Mode Screen (VPS/Linux)

```bash
# Install screen
sudo apt install screen

# Create screen session
screen -S piqsbot

# Run bot
cd bot/python
python piqs_bot.py

# Detach: Ctrl+A, D
# Reattach: screen -r piqsbot
```

### Mode Service (Systemd/Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/piqsbot.service
```

```ini
[Unit]
Description=PiqsBot Trading Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/piqs-bot-trade/bot/python
ExecStart=/usr/bin/python3 piqs_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable piqsbot
sudo systemctl start piqsbot
sudo systemctl status piqsbot
```

---

## 📊 Trading Logic

### RSI Signal

```
RSI < 15  → 🟢 EXTREME BUY  → Open BUY position
RSI < 30  → 🟡 WARNING BUY  → Hold
RSI 30-70 → ⚪ NEUTRAL      → No action
RSI > 70  → 🟡 WARNING SELL → Hold
RSI > 85  → 🔴 EXTREME SELL → Open SELL position
```

### Trade Flow

```
1. Cek Trading Hours (09:00 - 21:00)
2. Cek RSI Zone
3. RSI < 15 → BUY
4. RSI > 85 → SELL
5. Auto Trailing Stop
6. Close jika RSI berlawanan
```

---

## 🔧 Troubleshooting

### Error: "Initialize failed"

```bash
# Pastikan MT5 sudah running
# Pastikan MT5 terminal enabled
```

### Error: "Symbol not found"

```python
# Pastikan symbol XAUUSD tersedia di MT5
# Tambahkan symbol: Market Watch → Right Click → Show All
```

### Error: "Cannot connect to MT5"

```bash
# 1. Restart MT5
# 2. Enable DLL imports
# 3. Run as Administrator
```

### Error: "Permission denied"

```bash
# chmod +x piqs_bot.py
```

---

## 📈 Risk Management

### Fitur Protection

| Protection | Default | Description |
|------------|---------|-------------|
| Max Daily Trades | 10 | Pause setelah 10 trades |
| Max Daily Loss | 5% | Pause jika loss > 5% |
| Consecutive Loss | 3 | Pause setelah 3x loss |
| Max Lot | 1.0 | Maksimum lot per trade |
| Spread Check | 30 pts | Skip jika spread > 30 |

---

## 🌐 Web Logging

Bot bisa kirim data trade ke web server Anda:

1. Setup web server dengan `backend/log_trade.php`
2. Buat database MySQL
3. Update API URL di `config.py`

### Database Setup

```sql
CREATE DATABASE piqs_trading CHARACTER SET utf8mb4;
```

Jalankan SQL di `backend/db.php` untuk create tables.

---

## 📝 Logs

Bot menampilkan log di terminal:

```
==================================================
PiqsBot v2.0.0 - INITIALIZING
==================================================
Symbol: XAUUSD
Spread: 20 pts
==================================================
PiqsBot READY!
==================================================

[*] Starting main loop (interval: 0.5s)
[*] Press Ctrl+C to stop

==================================================
✅ ORDER TERSEDIA | Ticket: #123456
Type: BUY
Lot: 0.10 | RSI: 12.50
SL: 150 pts | TP: 100 pts
==================================================
```

---

## ⚠️ Disclaimer

**PERINGATAN: Trading forex/commodities memiliki risiko tinggi.**

- Bot ini hanya TOOL bantu, bukan jaminan profit
- Selalu monitor bot Anda
- Jangan gunakan money management yang terlalu agresif
- BACKTEST dulu sebelum live trading

---

## 📞 Support

- Email: rofik47@gmail.com
- GitHub: (repository)

---

**Happy Trading! 🚀**
