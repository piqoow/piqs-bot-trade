#!/usr/bin/env python3
"""
PiqsBot - Main Trading Bot
===========================
XAUUSD M15 RSI Scalper untuk MetaTrader 5

Fitur:
- RSI-based signal (extreme levels)
- Money Management (fixed/risk-based lot)
- Trailing Stop & Break Even
- Web Logging ke backend PHP
- Daily Loss Protection

Usage:
    python piqs_bot.py

Author: PiqsBot Trade
Version: 2.0.1 (MT5 Edition)
"""

import sys
import os
import time
import signal
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TradingConfig, APIConfig, BotConfig,
    TRADING, API, BOT,
    print_config, update_config, is_trading_hours
)
from rsi_trigger import RSITrigger, RSISignal, RSIZone
from money_management import MoneyManager, LotMode
from mt5_handler import MT5Handler, OrderType, PositionInfo
from api_client import APIClient, TradeLogData, APIStatus


class PiqsBot:
    """
    PiqsBot - Main Trading Bot
    ===========================

    Arsitektur modular:
    - MT5Handler: Koneksi ke MetaTrader 5
    - RSITrigger: Logic sinyal RSI
    - MoneyManager: Lot sizing & risk control
    - APIClient: Web logging
    """

    def __init__(self):
        # Configuration
        self.symbol = TRADING.symbol  # "XAUUSDm" untuk Exness
        self.timeframe = TRADING.timeframe
        self.magic = TRADING.magic

        # Modules - MT5 Handler
        self.mt5 = MT5Handler(debug=BOT.debug)

        self.rsi = RSITrigger(
            symbol=self.symbol,
            period=TRADING.rsi_period,
            extreme_buy=TRADING.rsi_extreme_buy,
            extreme_sell=TRADING.rsi_extreme_sell,
            warning_buy=TRADING.rsi_warning_buy,
            warning_sell=TRADING.rsi_warning_sell
        )

        self.mm = MoneyManager(
            mode=TRADING.lot_mode,
            fixed_lot=TRADING.lot_size,
            risk_percent=TRADING.risk_percent,
            max_lot=TRADING.max_lot,
            max_daily_trades=TRADING.max_daily_trades,
            max_daily_loss=TRADING.max_daily_loss_percent
        )

        self.api = APIClient(
            url=API.url,
            api_key=API.api_key,
            timeout=API.timeout // 1000,
            retry_count=API.retry_count,
            debug=BOT.debug
        )

        # State tracking
        self.running = False
        self.pause_mode = False
        self.last_bar_time = 0
        self.last_trade_bar = 0
        self.consecutive_loss = 0

        # Counters
        self.tick_counter = 0
        self.api_success = 0
        self.api_fail = 0

        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        import sys
        # Non-reentrant shutdown
        if not hasattr(self, '_shutting_down'):
            self._shutting_down = True
            try:
                sys.stderr.write("\n" + "="*50 + "\n")
                sys.stderr.write("SHUTDOWN SIGNAL RECEIVED\n")
                sys.stderr.write("="*50 + "\n")
                sys.stderr.flush()
            except:
                pass
        self.stop()

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def initialize(self) -> bool:
        """
        Initialize semua komponen

        Returns:
            True jika berhasil
        """
        print("\n" + "="*50)
        print("PiqsBot v2.0.1 - INITIALIZING")
        print("Using: MetaTrader 5")
        print("="*50)

        # Initialize MT5
        if not self.mt5.initialize():
            print("ERROR: Gagal connect ke MT5!")
            print("Pastikan MT5 sudah running dan terminal enabled")
            return False

        # Verify symbol
        info = self.mt5.get_symbol_info(self.symbol)
        if info is None:
            print(f"WARNING: Symbol {self.symbol} tidak tersedia")
            print("Pastikan symbol XAUUSD ada di Market Watch")
        else:
            print(f"Symbol: {self.symbol}")
            print(f"Spread: {info['spread']} pts")
            print(f"Point: {info['point']}")

        # Check RSI data
        closes = self.mt5.get_closes(self.symbol, self.timeframe, 50)
        if len(closes) < 20:
            print(f"WARNING: RSI data mungkin belum cukup ({len(closes)} candles)")
            print("Tunggu beberapa menit untuk data terisi...")

        # Ping API server (optional)
        if API.enabled:
            if self.api.ping_server():
                print("API Server: Connected")
            else:
                print("API Server: Not reachable (logging disabled)")

        print("="*50)
        print("PiqsBot READY!")
        print("="*50 + "\n")

        return True

    def shutdown(self):
        """Shutdown semua komponen"""
        print("\n" + "="*50)
        print("PiqsBot - SHUTTING DOWN")
        print("="*50)
        print(f"API Success: {self.api_success} | Failed: {self.api_fail}")
        print(f"Daily Trades: {self.mm.get_daily_trade_count()}")
        print(f"Daily Loss: ${self.mm.get_daily_loss():.2f}")
        print("="*50)
        self.mt5.shutdown()

    # =========================================================================
    # MAIN LOOP
    # =========================================================================

    def start(self):
        """Start bot main loop"""
        if not self.initialize():
            return

        self.running = True
        print(f"\n[*] Starting main loop (interval: {BOT.tick_interval}s)")
        print("[*] Press Ctrl+C to stop\n")

        try:
            while self.running:
                self._tick()
                time.sleep(BOT.tick_interval)

        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def stop(self):
        """Stop bot"""
        self.running = False

    def _tick(self):
        """Main tick - dipanggil setiap interval"""
        self.tick_counter += 1

        if BOT.debug and self.tick_counter % 20 == 0:
            self._print_status()

        # Cek apakah ada candle baru
        current_bar = self.mt5.get_current_bar_time(self.symbol, self.timeframe)
        if current_bar == self.last_bar_time:
            return  # Masih candle yang sama
        self.last_bar_time = current_bar

        # Cek trading hours
        if not is_trading_hours():
            if BOT.debug:
                print("[*] Di luar jam trading - monitoring only")
            self._manage_positions()  # Tetap manage posisi yang terbuka
            return

        # Cek pause mode
        if self.pause_mode:
            if self.mm.reset_pause():
                self.pause_mode = False
                print("[*] PAUSE mode OFF - new trading day")
            return

        # Manage open positions
        self._manage_positions()

        # Check untuk sinyal baru
        self._check_signal()

    def _print_status(self):
        """Print status ke console"""
        balance = self.mt5.get_balance()
        equity = self.mt5.get_equity()
        pos_count = self.mt5.get_position_count(self.symbol, self.magic)
        rsi = self.rsi.get_last_rsi()

        stats = self.mm.get_daily_stats()

        print(f"\n{'='*50}")
        print(f"PiqsBot Status | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        print(f"Balance: ${balance:.2f} | Equity: ${equity:.2f}")
        print(f"Positions: {pos_count} | Daily Trades: {stats.trade_count}/{TRADING.max_daily_trades}")
        print(f"RSI: {rsi:.2f} | Daily Loss: ${stats.total_loss:.2f}")
        print(f"API: {self.api_success} success, {self.api_fail} failed")
        if self.pause_mode:
            print("⚠️  PAUSED - Consecutive losses detected")
        print(f"{'='*50}\n")

    # =========================================================================
    # SIGNAL CHECKING
    # =========================================================================

    def _check_signal(self):
        """Cek dan eksekusi sinyal"""
        # Cegah double trade
        if self.last_trade_bar == self.last_bar_time:
            return

        # Cek apakah boleh trade
        can_trade, reason = self.mm.can_open_trade(
            self.mt5.get_position_count(self.symbol, self.magic)
        )
        if not can_trade:
            if BOT.debug:
                print(f"[*] Skip signal - {reason}")
            return

        # Cek apakah sudah ada posisi
        if self.mt5.has_open_position(self.symbol, self.magic):
            if BOT.debug:
                print("[*] Posisi sudah terbuka")
            return

        # Get RSI data
        closes = self.mt5.get_closes(self.symbol, self.timeframe, 50)
        if len(closes) < 20:
            return

        # Analyze RSI
        signal_data = self.rsi.analyze(closes, self.last_bar_time)

        # Execute trade
        if self.rsi.is_buy_signal(signal_data):
            self._execute_trade(OrderType.BUY, signal_data.value)
            self.last_trade_bar = self.last_bar_time

        elif self.rsi.is_sell_signal(signal_data):
            self._execute_trade(OrderType.SELL, signal_data.value)
            self.last_trade_bar = self.last_bar_time

    def _execute_trade(self, order_type: OrderType, rsi_value: float):
        """Eksekusi trade baru"""
        # Calculate lot
        if TRADING.lot_mode == "risk_based":
            lot = self.mt5.calculate_lot_risk(
                self.symbol,
                TRADING.stop_loss_pts,
                TRADING.risk_percent
            )
        else:
            lot = TRADING.lot_size

        # Open position
        ticket = self.mt5.open_position(
            symbol=self.symbol,
            order_type=order_type,
            volume=lot,
            sl_points=TRADING.stop_loss_pts,
            tp_points=TRADING.take_profit_pts,
            magic=self.magic,
            comment=TRADING.comment
        )

        if ticket:
            print("="*50)
            print(f"✅ ORDER TERSEDIA | Ticket: #{ticket}")
            print(f"Type: {'BUY' if order_type == OrderType.BUY else 'SELL'}")
            print(f"Lot: {lot:.2f} | RSI: {rsi_value:.2f}")
            print(f"SL: {TRADING.stop_loss_pts} pts | TP: {TRADING.take_profit_pts} pts")
            print("="*50)

    # =========================================================================
    # POSITION MANAGEMENT
    # =========================================================================

    def _manage_positions(self):
        """Manage semua posisi terbuka"""
        positions = self.mt5.get_positions(self.symbol, self.magic)

        for pos in positions:
            self._trailing_stop(pos)
            self._check_close_signal(pos)

    def _trailing_stop(self, pos: PositionInfo):
        """
        Trailing stop sederhana

        Trailing logic:
        - Buy: SL naik mengikuti harga jika profit > trailing_distance
        - Sell: SL turun mengikuti harga jika profit > trailing_distance
        """
        trailing_pts = TRADING.trailing_stop_pts

        # Get symbol info
        info = self.mt5.get_symbol_info(pos.symbol)
        if info is None:
            return

        point = info["point"]

        # Get current price
        tick = self.mt5.get_tick(pos.symbol)
        if tick is None:
            return

        current_price = tick.bid if pos.type == OrderType.BUY else tick.ask

        if pos.type == OrderType.BUY:
            # Calculate new SL
            new_sl = current_price - trailing_pts * point

            # Current SL
            current_sl = pos.sl

            # Move SL if profit enough
            if current_sl == 0:
                # Break Even
                new_sl = pos.price_open
            else:
                # Only move up
                if new_sl <= current_sl:
                    return

            # Only if profit enough
            profit_distance = (current_price - pos.price_open) / point
            if profit_distance < trailing_pts:
                return

            # Modify SL
            self.mt5.modify_position(pos.ticket, new_sl, pos.tp)

            if BOT.debug:
                print(f"[*] TS Update BUY #{pos.ticket} | New SL: {new_sl:.2f}")

        elif pos.type == OrderType.SELL:
            new_sl = current_price + trailing_pts * point

            if pos.sl == 0:
                new_sl = pos.price_open
            else:
                if new_sl >= pos.sl:
                    return

            profit_distance = (pos.price_open - current_price) / point
            if profit_distance < trailing_pts:
                return

            self.mt5.modify_position(pos.ticket, new_sl, pos.tp)

            if BOT.debug:
                print(f"[*] TS Update SELL #{pos.ticket} | New SL: {new_sl:.2f}")

    def _check_close_signal(self, pos: PositionInfo):
        """
        Close posisi jika RSI sinyal berlawanan

        Logic:
        - Buy position + RSI Extreme Sell → Close
        - Sell position + RSI Extreme Buy → Close
        """
        closes = self.mt5.get_closes(self.symbol, self.timeframe, 20)
        if len(closes) < 2:
            return

        signal_data = self.rsi.analyze(closes, self.last_bar_time)

        should_close = False
        reason = ""

        if pos.type == OrderType.BUY and self.rsi.should_close_buy(signal_data):
            should_close = True
            reason = f"RSI Extreme Sell ({signal_data.value:.2f})"

        elif pos.type == OrderType.SELL and self.rsi.should_close_sell(signal_data):
            should_close = True
            reason = f"RSI Extreme Buy ({signal_data.value:.2f})"

        if should_close:
            self._close_position(pos, reason)

    def _close_position(self, pos: PositionInfo, reason: str):
        """Close posisi dengan reason"""
        success = self.mt5.close_position(pos.ticket, pos.volume)

        if success:
            print("="*50)
            print(f"✅ POSITION CLOSED | Ticket: #{pos.ticket}")
            print(f"Reason: {reason}")
            print(f"Profit: ${pos.profit:.2f}")
            print("="*50)

            # Record trade
            self.mm.record_trade(pos.profit)

            # Check consecutive loss
            if pos.profit < 0:
                self.consecutive_loss += 1
                if self.consecutive_loss >= TRADING.max_consecutive_loss:
                    print(f"⚠️  {self.consecutive_loss}x consecutive loss - PAUSE mode aktif")
                    self.pause_mode = True
            else:
                self.consecutive_loss = 0

            # Send to API
            self._send_trade_log(pos, reason)

    def _send_trade_log(self, pos: PositionInfo, close_reason: str):
        """Kirim data trade ke API server"""
        if not API.enabled:
            return

        log_data = TradeLogData(
            ticket=pos.ticket,
            trade_type="BUY" if pos.type == OrderType.BUY else "SELL",
            lot=pos.volume,
            price_open=pos.price_open,
            price_close=pos.price_current,
            profit=pos.profit,
            symbol=pos.symbol,
            time_open=int(time.time()),
            time_close=int(time.time()),
            ip_address=self.api._get_ip_address(),
            magic=pos.magic,
            sl_points=TRADING.stop_loss_pts,
            tp_points=TRADING.take_profit_pts,
            rsi_value=self.rsi.get_last_rsi(),
            api_key=API.api_key
        )

        status = self.api.send_trade_log(log_data)

        if status == APIStatus.SUCCESS:
            self.api_success += 1
        else:
            self.api_fail += 1


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    print_config()

    # Create and start bot
    bot = PiqsBot()
    bot.start()


if __name__ == "__main__":
    main()
