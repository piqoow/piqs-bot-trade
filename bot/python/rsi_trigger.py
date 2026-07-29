"""
PiqsBot - RSI Trigger Module
=============================
Logika pemicu sinyal trading berdasarkan RSI dengan 3 zona:
- Kritis (Extreme): RSI < 15 atau RSI > 85
- Warning: RSI < 30 atau RSI > 70
- Netral: RSI 30-70
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple


class RSIZone(Enum):
    """Zona sinyal RSI"""
    UNKNOWN = "unknown"
    EXTREME_BUY = "extreme_buy"      # RSI < 15
    WARNING_BUY = "warning_buy"      # RSI < 30
    NEUTRAL = "neutral"              # RSI 30-70
    WARNING_SELL = "warning_sell"   # RSI > 70
    EXTREME_SELL = "extreme_sell"    # RSI > 85


@dataclass
class RSISignal:
    """Struktur sinyal RSI"""
    zone: RSIZone
    value: float
    value_prev: float
    is_confirmed: bool
    timestamp: float
    symbol: str
    timeframe: int


class RSITrigger:
    """
    RSI Trigger Module
    ==================

    Fungsi utama:
    - Hitung RSI value
    - Deteksi zona sinyal
    - Generate buy/sell signal
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        period: int = 14,
        extreme_buy: float = 15.0,
        extreme_sell: float = 85.0,
        warning_buy: float = 30.0,
        warning_sell: float = 70.0
    ):
        self.symbol = symbol
        self.period = period
        self.extreme_buy = extreme_buy
        self.extreme_sell = extreme_sell
        self.warning_buy = warning_buy
        self.warning_sell = warning_sell

        self._last_signal: Optional[RSISignal] = None
        self._last_candle_time: float = 0

    def detect_zone(self, rsi: float) -> RSIZone:
        """
        Deteksi zona RSI berdasarkan nilai

        Args:
            rsi: Nilai RSI saat ini

        Returns:
            RSIZone enum
        """
        if rsi < self.extreme_buy:
            return RSIZone.EXTREME_BUY
        elif rsi < self.warning_buy:
            return RSIZone.WARNING_BUY
        elif rsi > self.extreme_sell:
            return RSIZone.EXTREME_SELL
        elif rsi > self.warning_sell:
            return RSIZone.WARNING_SELL
        else:
            return RSIZone.NEUTRAL

    def calculate_rsi(self, prices: list) -> Tuple[float, float]:
        """
        Hitung RSI dari array harga

        Args:
            prices: List harga penutupan

        Returns:
            Tuple of (RSI saat ini, RSI sebelumnya)
        """
        if len(prices) < self.period + 1:
            return 50.0, 50.0  # Default netral

        # Calculate price changes
        deltas = []
        for i in range(1, len(prices)):
            deltas.append(prices[i] - prices[i-1])

        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]

        # Calculate average gains and losses
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period

        # Handle zero division
        if avg_loss == 0:
            return 100.0, 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # RSI previous (shift 1)
        avg_gain_prev = sum(gains[-self.period-1:-1]) / self.period
        avg_loss_prev = sum(losses[-self.period-1:-1]) / self.period

        if avg_loss_prev == 0:
            rsi_prev = 50.0
        else:
            rs_prev = avg_gain_prev / avg_loss_prev
            rsi_prev = 100 - (100 / (1 + rs_prev))

        return round(rsi, 2), round(rsi_prev, 2)

    def is_new_candle(self, current_time: float) -> bool:
        """Cek apakah ini candle baru"""
        is_new = current_time != self._last_candle_time
        if is_new:
            self._last_candle_time = current_time
        return is_new

    def analyze(self, prices: list, current_time: float) -> RSISignal:
        """
        Analisis lengkap sinyal RSI

        Args:
            prices: List harga
            current_time: Timestamp candle saat ini

        Returns:
            RSISignal object
        """
        rsi_current, rsi_prev = self.calculate_rsi(prices)
        zone = self.detect_zone(rsi_current)

        signal = RSISignal(
            zone=zone,
            value=rsi_current,
            value_prev=rsi_prev,
            is_confirmed=self.is_new_candle(current_time),
            timestamp=current_time,
            symbol=self.symbol,
            timeframe=self.period
        )

        self._last_signal = signal
        return signal

    def is_buy_signal(self, signal: RSISignal) -> bool:
        """
        Cek apakah conditions untuk BUY terpenuhi

        BUY Signal conditions:
        1. RSI < 15 (extreme) ATAU RSI crosses up dari < 15
        2. Candle sudah confirmed (close)
        """
        if not signal.is_confirmed:
            return False

        # RSI crosses up from extreme zone
        crossed_up = (signal.value_prev < self.extreme_buy and
                     signal.value >= self.extreme_buy)

        # RSI still in extreme zone
        extreme = signal.value < self.extreme_buy

        return crossed_up or extreme

    def is_sell_signal(self, signal: RSISignal) -> bool:
        """
        Cek apakah conditions untuk SELL terpenuhi

        SELL Signal conditions:
        1. RSI > 85 (extreme) ATAU RSI crosses down dari > 85
        2. Candle sudah confirmed (close)
        """
        if not signal.is_confirmed:
            return False

        # RSI crosses down from extreme zone
        crossed_down = (signal.value_prev > self.extreme_sell and
                        signal.value <= self.extreme_sell)

        # RSI still in extreme zone
        extreme = signal.value > self.extreme_sell

        return crossed_down or extreme

    def should_close_buy(self, signal: RSISignal) -> bool:
        """Cek apakah posisi BUY harus ditutup (RSI extreme sell)"""
        return signal.zone == RSIZone.EXTREME_SELL

    def should_close_sell(self, signal: RSISignal) -> bool:
        """Cek apakah posisi SELL harus ditutup (RSI extreme buy)"""
        return signal.zone == RSIZone.EXTREME_BUY

    def get_last_signal(self) -> Optional[RSISignal]:
        """Get sinyal terakhir"""
        return self._last_signal

    def get_last_rsi(self) -> float:
        """Get nilai RSI terakhir"""
        if self._last_signal:
            return self._last_signal.value
        return 50.0

    def __repr__(self) -> str:
        return (f"RSITrigger(symbol={self.symbol}, period={self.period}, "
                f"buy_extreme={self.extreme_buy}, sell_extreme={self.extreme_sell})")
