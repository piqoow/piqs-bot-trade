"""
PiqsBot - Money Management Module
==================================
Modul untuk kalkulasi lot sizing dan risk management.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class LotMode(Enum):
    """Mode kalkulasi lot"""
    FIXED = "fixed"                    # Lot tetap
    RISK_BASED = "risk_based"          # Hitung dari risk %
    MINIMUM = "minimum"                # Lot minimum broker


@dataclass
class RiskInfo:
    """Informasi risk untuk satu trade"""
    lot_size: float
    risk_amount: float
    risk_percent: float
    stop_loss_pts: int
    take_profit_pts: int
    potential_profit: float
    potential_loss: float
    is_valid: bool


@dataclass
class DailyStats:
    """Statistik harian"""
    trade_count: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    consecutive_loss: int = 0
    last_reset_date: str = ""


class MoneyManager:
    """
    Money Management Module
    ======================

    Fungsi utama:
    - Kalkulasi lot berdasarkan mode
    - Track statistik harian
    - Risk control
    """

    def __init__(
        self,
        mode: str = "FIXED",
        fixed_lot: float = 0.10,
        risk_percent: float = 2.0,
        max_lot: float = 1.0,
        max_daily_trades: int = 10,
        max_daily_loss: float = 5.0
    ):
        self.mode = LotMode(mode)
        self.fixed_lot = fixed_lot
        self.risk_percent = risk_percent
        self.max_lot = max_lot
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss = max_daily_loss

        # Daily tracking
        self._daily_stats = DailyStats()
        self._check_daily_reset()

    def _get_today_key(self) -> str:
        """Get date string for today"""
        return datetime.now().strftime("%Y-%m-%d")

    def _check_daily_reset(self):
        """Reset counter harian jika tanggal berubah"""
        today = self._get_today_key()
        if self._daily_stats.last_reset_date != today:
            self._daily_stats = DailyStats(last_reset_date=today)

    def calculate_lot(
        self,
        stop_loss_pts: int,
        symbol: str = "XAUUSD",
        balance: float = 0,
        tick_value: float = 0.01,
        tick_size: float = 0.01,
        point: float = 0.01
    ) -> float:
        """
        Kalkulasi lot berdasarkan mode

        Args:
            stop_loss_pts: Stop loss dalam points
            symbol: Symbol trading
            balance: Account balance
            tick_value: Tick value (nilai per tick)
            tick_size: Tick size
            point: Point size

        Returns:
            Lot size yang dihitung
        """
        lot = 0.0

        if self.mode == LotMode.FIXED:
            lot = self.fixed_lot

        elif self.mode == LotMode.RISK_BASED:
            lot = self._calculate_risk_based_lot(
                stop_loss_pts, balance, tick_value, tick_size, point
            )

        elif self.mode == LotMode.MINIMUM:
            lot = 0.01  # Minimum lot

        # Apply max lot protection
        lot = min(lot, self.max_lot)

        # Round to lot step (assume 0.01 step for gold)
        lot = round(lot, 2)

        return lot

    def _calculate_risk_based_lot(
        self,
        sl_points: int,
        balance: float,
        tick_value: float,
        tick_size: float,
        point: float
    ) -> float:
        """
        Kalkulasi lot berdasarkan risk %

        Formula:
        Lot = (Balance × Risk%) / (SL_Points × Point_Value)

        Untuk XAUUSD (Gold):
        - 1 lot = 100 oz
        - Tick value = 0.01 (cents)
        - Point = 0.01
        """
        if balance <= 0 or sl_points <= 0:
            return self.fixed_lot

        # Risk amount dalam mata uang
        risk_amount = balance * (self.risk_percent / 100.0)

        # Point value untuk 1 lot
        # Gold: tick_value biasanya 0.01, tick_size 0.01
        point_value = (tick_value / tick_size) * point

        # Lot = Risk Amount / (SL Points × Point Value)
        if point_value > 0:
            lot = risk_amount / (sl_points * point_value)
        else:
            lot = self.fixed_lot

        return lot

    def calculate_risk_info(
        self,
        lot_size: float,
        sl_points: int,
        tp_points: int,
        tick_value: float = 0.01,
        tick_size: float = 0.01,
        point: float = 0.01
    ) -> RiskInfo:
        """
        Hitung informasi risk lengkap

        Returns:
            RiskInfo object
        """
        point_value = (tick_value / tick_size) * point

        risk_amount = lot_size * sl_points * point_value
        potential_loss = risk_amount
        potential_profit = lot_size * tp_points * point_value

        return RiskInfo(
            lot_size=lot_size,
            risk_amount=risk_amount,
            risk_percent=self.risk_percent,
            stop_loss_pts=sl_points,
            take_profit_pts=tp_points,
            potential_profit=potential_profit,
            potential_loss=potential_loss,
            is_valid=lot_size > 0 and sl_points > 0
        )

    def can_open_trade(self, current_positions: int = 0) -> tuple[bool, str]:
        """
        Cek apakah boleh buka trade baru

        Returns:
            Tuple of (can_trade, reason)
        """
        self._check_daily_reset()

        # Cek batas transaksi harian
        if self._daily_stats.trade_count >= self.max_daily_trades:
            return False, f"Batas harian tercapai: {self._daily_stats.trade_count}/{self.max_daily_trades}"

        # Cek max daily loss
        balance = 10000  # Default, should get from MT5
        max_loss = balance * (self.max_daily_loss / 100)
        if self._daily_stats.total_loss >= max_loss:
            return False, f"Batas daily loss tercapai: {self._daily_stats.total_loss:.2f}"

        # Cek max positions
        if current_positions >= 2:
            return False, "Max positions sudah terbuka"

        return True, "OK"

    def record_trade(self, profit: float):
        """
        Catat transaksi setelah close

        Args:
            profit: Profit dari trade (bisa negatif)
        """
        self._check_daily_reset()
        self._daily_stats.trade_count += 1

        if profit < 0:
            self._daily_stats.total_loss += abs(profit)
            self._daily_stats.consecutive_loss += 1
        else:
            self._daily_stats.consecutive_loss = 0

        self._daily_stats.total_profit += max(0, profit)

    def should_pause(self) -> bool:
        """Cek apakah harus pause karena consecutive losses"""
        return self._daily_stats.consecutive_loss >= 3

    def reset_pause(self) -> bool:
        """
        Reset pause mode jika sudah jam baru

        Returns:
            True jika berhasil reset
        """
        current_hour = datetime.now().hour
        if current_hour == 9:  # Session start hour
            self._daily_stats.consecutive_loss = 0
            return True
        return False

    def get_daily_stats(self) -> DailyStats:
        """Get statistik harian"""
        self._check_daily_reset()
        return self._daily_stats

    def get_daily_trade_count(self) -> int:
        """Get jumlah trade hari ini"""
        self._check_daily_reset()
        return self._daily_stats.trade_count

    def get_daily_loss(self) -> float:
        """Get total loss hari ini"""
        self._check_daily_reset()
        return self._daily_stats.total_loss

    def set_mode(self, mode: str):
        """Ubah mode lot calculation"""
        self.mode = LotMode(mode)

    def __repr__(self) -> str:
        return (f"MoneyManager(mode={self.mode.value}, lot={self.fixed_lot}, "
                f"risk={self.risk_percent}%, daily_trades={self._daily_stats.trade_count})")
