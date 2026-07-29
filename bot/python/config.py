"""
PiqsBot - Configuration Module
==============================
Semua konfigurasi centralized di sini.
Easy to modify, easy to rollback.
"""

import os
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# TRADING CONFIGURATION
# =============================================================================

@dataclass
class TradingConfig:
    """Trading Settings"""
    symbol: str = "XAUUSDm"            # Symbol trading (XAUUSDm untuk Exness)
    timeframe: int = 15                 # Timeframe in minutes (M15)
    magic: int = 20240728               # Magic number untuk identifikasi
    comment: str = "PiqsBot_RSI_v2"     # Comment untuk order

    # RSI Levels (AGGRESIF - threshold lebih rendah)
    rsi_period: int = 14                # RSI Period
    rsi_extreme_buy: float = 25.0      # Level kritis buy (RSI < 25) - AGGRESIF
    rsi_warning_buy: float = 35.0       # Level warning buy (RSI < 35)
    rsi_warning_sell: float = 65.0     # Level warning sell (RSI > 65)
    rsi_extreme_sell: float = 75.0     # Level kritis sell (RSI > 75) - AGGRESIF

    # Money Management (AGGRESIF)
    lot_mode: str = "fixed"            # fixed, risk_based, minimum
    lot_size: float = 0.02            # Lot tetap (kecil - 0.02)
    risk_percent: float = 2.0          # Risk per trade (%)
    max_lot: float = 0.02               # Maximum lot
    max_daily_trades: int = 20         # Max trades per day (AGGRESIF)

    # Stop Loss & Take Profit (AGGRESIF)
    stop_loss_pts: int = 100           # SL: 100 points (lebih ketat)
    take_profit_pts: int = 80         # TP: 80 points (lebih cepat profit)

    # Spread Protection
    max_spread: int = 50               # Max spread (AGGRESIF - lebih toleran)

    # Trading Hours (Server Time)
    session_start: int = 0            # Start hour (00:00 - 24 jam)
    session_end: int = 23             # End hour (23:59)

    # Trailing Stop (AGGRESIF)
    trailing_stop_pts: int = 30        # Trailing distance (lebih ketat)
    trailing_step: int = 5             # Step for trailing

    # Risk Control (AGGRESIF)
    max_consecutive_loss: int = 4       # Pause after N consecutive losses
    max_daily_loss_percent: float = 10.0  # Max daily loss (%)


@dataclass
class APIConfig:
    """API/Web Logging Settings"""
    enabled: bool = True                # Enable web logging
    url: str = "https://your-server.com/backend/log_trade.php"
    api_key: str = "pk_live_piqs_xauusd_2024"
    timeout: int = 5000                # Timeout in ms
    retry_count: int = 3               # Retry attempts


@dataclass
class BotConfig:
    """Bot General Settings"""
    debug: bool = True                  # Enable debug logging
    log_to_file: bool = True           # Save log to file
    log_dir: str = "logs"              # Log directory
    tick_interval: float = 0.5         # Tick check interval (seconds)


# =============================================================================
# CONFIGURATION INSTANCES
# =============================================================================

TRADING = TradingConfig()
API = APIConfig()
BOT = BotConfig()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_config() -> TradingConfig:
    """Get trading configuration"""
    return TRADING


def update_config(**kwargs):
    """Update trading configuration dynamically"""
    global TRADING
    for key, value in kwargs.items():
        if hasattr(TRADING, key):
            setattr(TRADING, key, value)
            if BOT.debug:
                print(f"[CONFIG] {key} = {value}")


def update_api_config(**kwargs):
    """Update API configuration dynamically"""
    global API
    for key, value in kwargs.items():
        if hasattr(API, key):
            setattr(API, key, value)


def is_trading_hours() -> bool:
    """Check if current time is within trading hours"""
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    return TRADING.session_start <= current_hour <= TRADING.session_end


def print_config():
    """Print current configuration"""
    print("\n" + "="*50)
    print("PiqsBot Configuration v2.0.0")
    print("="*50)
    print(f"Symbol: {TRADING.symbol}")
    print(f"Timeframe: M{TRADING.timeframe}")
    print(f"RSI Period: {TRADING.rsi_period}")
    print(f"RSI Buy Level: < {TRADING.rsi_extreme_buy}")
    print(f"RSI Sell Level: > {TRADING.rsi_extreme_sell}")
    print(f"Lot Mode: {TRADING.lot_mode}")
    print(f"Lot Size: {TRADING.lot_size}")
    print(f"SL: {TRADING.stop_loss_pts} pts | TP: {TRADING.take_profit_pts} pts")
    print(f"Max Daily Trades: {TRADING.max_daily_trades}")
    print(f"Trading Hours: {TRADING.session_start}:00 - {TRADING.session_end}:00")
    print(f"API Logging: {'Enabled' if API.enabled else 'Disabled'}")
    print("="*50 + "\n")
