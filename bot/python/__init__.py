# PiqsBot Trade - Python Trading Bot
# XAUUSD M15 RSI Scalper
# Version: 2.0.0

"""
PiqsBot - Python Trading Bot for MetaTrader 5

Dependencies:
    pip install MetaTrader5 pandas numpy requests schedule

Usage:
    python piqs_bot.py
"""

from .config import *
from .rsi_trigger import RSITrigger
from .money_management import MoneyManager
from .mt5_handler import MT5Handler
from .api_client import APIClient

__version__ = "2.0.0"
__author__ = "PiqsBot Trade"
