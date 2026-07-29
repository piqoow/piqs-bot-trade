"""
PiqsBot - MetaTrader 5 Handler Module
======================================
Modul untuk koneksi dan interaksi dengan MetaTrader 5
Menggunakan library MetaTrader5 (mt5)
"""

import MetaTrader5 as mt5
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime
import time


class OrderType(Enum):
    """Order type"""
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5


class TradeAction(Enum):
    """Trade action type"""
    DEAL = 0
    PENDING = 1


@dataclass
class TickData:
    """Data tick"""
    symbol: str
    bid: float
    ask: float
    time: float
    spread: int


@dataclass
class PositionInfo:
    """Informasi posisi"""
    ticket: int
    symbol: str
    type: OrderType
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    magic: int
    comment: str


@dataclass
class CandleData:
    """Data candle/bar"""
    time: float
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int


class MT5Handler:
    """
    MetaTrader 5 Handler
    =====================

    Fungsi utama:
    - Initialize MT5 connection
    - Get price data
    - Open/close positions
    - Get positions info
    - Calculate lots dengan benar
    """

    def __init__(self, debug: bool = True):
        self.debug = debug
        self.initialized = False
        self.terminal_info = None
        self.account_info = None

    def initialize(self) -> bool:
        """
        Initialize MT5 connection

        Returns:
            True jika berhasil
        """
        if not mt5.initialize():
            if self.debug:
                print(f"[MT5] Initialize GAGAL | Error: {mt5.last_error()}")
            return False

        self.terminal_info = mt5.terminal_info()
        self.account_info = mt5.account_info()

        if self.debug:
            print("="*50)
            print("MT5 Connected Successfully!")
            print(f"Terminal: {self.terminal_info.name}")
            print(f"Server: {self.terminal_info.server}")
            print(f"Account: {self.account_info.login}")
            print(f"Balance: ${self.account_info.balance:.2f}")
            print(f"Equity: ${self.account_info.equity:.2f}")
            print("="*50)

        self.initialized = True
        return True

    def shutdown(self):
        """Tutup koneksi MT5"""
        if self.initialized:
            mt5.shutdown()
            self.initialized = False
            if self.debug:
                print("[MT5] Connection closed")

    # =========================================================================
    # PRICE DATA
    # =========================================================================

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get symbol info"""
        info = mt5.symbol_info(symbol)
        if info is None:
            if self.debug:
                print(f"[MT5] Symbol {symbol} tidak ditemukan")
            return None

        return {
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.spread,
            "digits": info.digits,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "point": info.point,
            "tick_value": info.trade_tick_value,
            "tick_size": info.trade_tick_size,
            "contract_size": info.contract_size
        }

    def get_tick(self, symbol: str) -> Optional[TickData]:
        """Get last tick untuk symbol"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return TickData(
            symbol=symbol,
            bid=tick.bid,
            ask=tick.ask,
            time=tick.time,
            spread=tick.spread
        )

    def get_rates(self, symbol: str, timeframe: int = 15,
                  count: int = 100) -> Optional[List[CandleData]]:
        """
        Get historical candle data

        Args:
            symbol: Symbol name
            timeframe: Timeframe in minutes (1, 5, 15, 30, 60, etc.)
            count: Number of candles to retrieve

        Returns:
            List of CandleData
        """
        # MT5 timeframe constants
        tf_map = {
            1: mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
            1440: mt5.TIMEFRAME_D1
        }

        tf = tf_map.get(timeframe, mt5.TIMEFRAME_M15)

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            if self.debug:
                print(f"[MT5] Gagal ambil rates | Error: {mt5.last_error()}")
            return None

        candles = []
        for rate in rates:
            candles.append(CandleData(
                time=rate[0],
                open=rate[1],
                high=rate[2],
                low=rate[3],
                close=rate[4],
                tick_volume=int(rate[5]),
                spread=int(rate[6]),
                real_volume=int(rate[7])
            ))

        return candles

    def get_closes(self, symbol: str, timeframe: int = 15,
                   count: int = 100) -> List[float]:
        """Get list closing prices untuk RSI calculation"""
        candles = self.get_rates(symbol, timeframe, count)
        if candles is None:
            return []
        return [c.close for c in candles]

    def get_current_bar_time(self, symbol: str, timeframe: int = 15) -> float:
        """Get timestamp candle saat ini"""
        candles = self.get_rates(symbol, timeframe, 1)
        if candles:
            return candles[0].time
        return 0

    # =========================================================================
    # POSITIONS
    # =========================================================================

    def get_positions(self, symbol: str = "", magic: int = 0) -> List[PositionInfo]:
        """
        Get semua posisi terbuka

        Args:
            symbol: Filter by symbol (kosong = semua)
            magic: Filter by magic number (0 = semua)

        Returns:
            List of PositionInfo
        """
        positions = mt5.positions_get()

        result = []
        for pos in positions:
            # Apply filters
            if symbol and pos.symbol != symbol:
                continue
            if magic and pos.magic != magic:
                continue

            pos_type = OrderType.BUY if pos.type == mt5.ORDER_TYPE_BUY else OrderType.SELL

            result.append(PositionInfo(
                ticket=pos.ticket,
                symbol=pos.symbol,
                type=pos_type,
                volume=pos.volume,
                price_open=pos.price_open,
                price_current=pos.price_current,
                sl=pos.sl,
                tp=pos.tp,
                profit=pos.profit,
                magic=pos.magic,
                comment=pos.comment
            ))

        return result

    def has_open_position(self, symbol: str, magic: int) -> bool:
        """Cek apakah ada posisi terbuka untuk symbol"""
        positions = self.get_positions(symbol, magic)
        return len(positions) > 0

    def get_position_count(self, symbol: str, magic: int) -> int:
        """Get jumlah posisi terbuka"""
        return len(self.get_positions(symbol, magic))

    # =========================================================================
    # TRADING
    # =========================================================================

    def calculate_lot_risk(self, symbol: str, sl_points: int,
                           risk_percent: float = 2.0) -> float:
        """
        Hitung lot berdasarkan risk %

        Args:
            symbol: Symbol name
            sl_points: Stop loss dalam points
            risk_percent: Risk percentage

        Returns:
            Lot size
        """
        info = self.get_symbol_info(symbol)
        if info is None:
            return 0.1  # Default

        balance = self.account_info.balance
        risk_amount = balance * (risk_percent / 100.0)

        # Point value per lot
        # Untuk XAUUSD: tick_value biasanya dalam cents
        point_value = info["tick_value"] / info["tick_size"] * info["point"]

        # Lot = Risk Amount / (SL Points × Point Value)
        if point_value > 0 and sl_points > 0:
            lot = risk_amount / (sl_points * point_value)
        else:
            lot = 0.1

        # Apply limits
        lot = min(lot, info["volume_max"])
        lot = max(lot, info["volume_min"])

        # Round to step
        step = info["volume_step"]
        lot = round(lot / step) * step

        return lot

    def open_position(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        sl_points: int,
        tp_points: int,
        magic: int,
        comment: str = "",
        deviation: int = 10
    ) -> Optional[int]:
        """
        Buka posisi baru

        Args:
            symbol: Symbol name
            order_type: BUY atau SELL
            volume: Lot size
            sl_points: Stop loss dalam points
            tp_points: Take profit dalam points
            magic: Magic number
            comment: Comment
            deviation: Deviation points

        Returns:
            Ticket number jika berhasil, None jika gagal
        """
        tick = self.get_tick(symbol)
        if tick is None:
            if self.debug:
                print(f"[MT5] Gagal dapat tick untuk {symbol}")
            return None

        # Get symbol info for point calculation
        info = self.get_symbol_info(symbol)
        point = info["point"] if info else 0.01
        digits = info["digits"] if info else 2

        # Calculate prices
        if order_type == OrderType.BUY:
            price = tick.ask
            sl = round(price - sl_points * point, digits)
            tp = round(price + tp_points * point, digits)
        else:
            price = tick.bid
            sl = round(price + sl_points * point, digits)
            tp = round(price - tp_points * point, digits)

        # Build request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if order_type == OrderType.BUY else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_FOK,
            "type_time": mt5.ORDER_TIME_GTC
        }

        if self.debug:
            print("="*50)
            print(f"OPEN {order_type.name} | {symbol}")
            print(f"Price: {price} | SL: {sl} | TP: {tp}")
            print(f"Volume: {volume} | Magic: {magic}")
            print("="*50)

        result = mt5.order_send(request)

        if result is None:
            if self.debug:
                print(f"[MT5] OrderSend GAGAL | Error: {mt5.last_error()}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            if self.debug:
                print(f"[MT5] Order REJECTED | Retcode: {result.retcode}")
                print(f"      Comment: {result.comment}")
            return None

        if self.debug:
            print(f"[MT5] Order SUCCESS | Ticket: #{result.order}")

        return result.order

    def close_position(self, ticket: int, volume: float,
                       deviation: int = 10) -> bool:
        """
        Tutup posisi

        Args:
            ticket: Ticket number
            volume: Volume to close
            deviation: Deviation points

        Returns:
            True jika berhasil
        """
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            if self.debug:
                print(f"[MT5] Position #{ticket} tidak ditemukan")
            return False

        pos = positions[0]
        symbol = pos.symbol

        tick = self.get_tick(symbol)
        if tick is None:
            return False

        # Opposite order type
        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": 0,
            "comment": "Close by PiqsBot",
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if self.debug:
                print(f"[MT5] Position #{ticket} closed | Profit: {pos.profit}")
            return True

        if self.debug:
            print(f"[MT5] Close GAGAL | Retcode: {result.retcode if result else 'None'}")
        return False

    def modify_position(self, ticket: int, sl: float, tp: float) -> bool:
        """
        Modifikasi SL/TP posisi

        Args:
            ticket: Ticket number
            sl: New stop loss
            tp: New take profit

        Returns:
            True jika berhasil
        """
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp,
            "magic": 0
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if self.debug:
                print(f"[MT5] Position #{ticket} modified | SL: {sl} | TP: {tp}")
            return True

        if self.debug:
            print(f"[MT5] Modify GAGAL | Retcode: {result.retcode if result else 'None'}")
        return False

    # =========================================================================
    # ACCOUNT INFO
    # =========================================================================

    def get_balance(self) -> float:
        """Get account balance"""
        if self.account_info:
            return self.account_info.balance
        return 0

    def get_equity(self) -> float:
        """Get account equity"""
        if self.account_info:
            return self.account_info.equity
        return 0

    def get_margin_level(self) -> float:
        """Get margin level percentage"""
        if self.account_info:
            return self.account_info.margin_level or 0
        return 0

    def is_connected(self) -> bool:
        """Cek apakah MT5 terhubung"""
        return mt5.terminal_info() is not None

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()
