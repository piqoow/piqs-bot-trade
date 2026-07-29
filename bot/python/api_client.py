"""
PiqsBot - API Client Module
=============================
Modul untuk mengirim data trade ke web server backend.
"""

import requests
import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class APIStatus(Enum):
    """API Response Status"""
    SUCCESS = "success"
    ERROR_NETWORK = "error_network"
    ERROR_TIMEOUT = "error_timeout"
    ERROR_RESPONSE = "error_response"
    ERROR_REJECTED = "error_rejected"
    PENDING = "pending"


@dataclass
class TradeLogData:
    """Data trade untuk dikirim ke server"""
    ticket: int
    trade_type: str           # "BUY" atau "SELL"
    lot: float
    price_open: float
    price_close: float
    profit: float
    symbol: str
    time_open: int            # Timestamp
    time_close: int           # Timestamp
    ip_address: str
    magic: int
    sl_points: int
    tp_points: int
    rsi_value: float
    api_key: str


class APIClient:
    """
    API Client
    ==========

    Fungsi utama:
    - Kirim data trade ke backend PHP
    - Retry dengan exponential backoff
    - Track success/fail counters
    """

    def __init__(
        self,
        url: str = "https://your-server.com/backend/log_trade.php",
        api_key: str = "pk_live_piqs_xauusd_2024",
        timeout: int = 5,
        retry_count: int = 3,
        debug: bool = True
    ):
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.retry_count = retry_count
        self.debug = debug

        # Counters
        self._success_count = 0
        self._fail_count = 0
        self._last_status: Optional[APIStatus] = None
        self._last_error: Optional[str] = None
        self._last_response: Optional[str] = None

    def _get_ip_address(self) -> str:
        """Get IP address publik"""
        try:
            response = requests.get("https://api.ipify.org", timeout=3)
            if response.status_code == 200:
                return response.text
        except Exception:
            pass
        return "127.0.0.1"

    def _encode_post_data(self, data: TradeLogData) -> dict:
        """Encode data ke format POST"""
        return {
            "ticket": str(data.ticket),
            "type": data.trade_type,
            "lot": f"{data.lot:.2f}",
            "price_open": f"{data.price_open:.5f}",
            "price_close": f"{data.price_close:.5f}",
            "profit": f"{data.profit:.2f}",
            "symbol": data.symbol,
            "time_open": str(data.time_open),
            "time_close": str(data.time_close),
            "ip_address": data.ip_address,
            "magic": str(data.magic),
            "sl_pts": f"{data.sl_points:.1f}",
            "tp_pts": f"{data.tp_points:.1f}",
            "rsi_value": f"{data.rsi_value:.2f}",
            "api_key": data.api_key
        }

    def _parse_response(self, response_text: str) -> bool:
        """
        Parse response dari server

        Returns:
            True jika sukses
        """
        self._last_response = response_text

        # Response kosong
        if not response_text or len(response_text.strip()) == 0:
            self._last_error = "Empty response from server"
            return False

        # Check untuk success indicators
        response_lower = response_text.lower()
        if any(x in response_lower for x in ["success", "ok", "200"]):
            return True

        # Check untuk error indicators
        if any(x in response_lower for x in ["error", "fail", "unauthorized"]):
            self._last_error = f"Server error: {response_text}"
            return False

        # Response tidak diketahui, anggap sukses
        return True

    def ping_server(self) -> bool:
        """
        Test koneksi ke server

        Returns:
            True jika server reachable
        """
        try:
            payload = {
                "api_key": self.api_key,
                "ping": "1"
            }
            response = requests.post(
                self.url,
                data=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                text = response.text
                if "pong" in text.lower() or "ok" in text.lower():
                    if self.debug:
                        print("[API] Server reachable!")
                    return True

            if self.debug:
                print(f"[API] Ping failed | Code: {response.status_code}")
            return False

        except requests.exceptions.Timeout:
            if self.debug:
                print("[API] Ping timeout")
            return False
        except requests.exceptions.ConnectionError:
            if self.debug:
                print("[API] Connection error")
            return False
        except Exception as e:
            if self.debug:
                print(f"[API] Ping error: {e}")
            return False

    def send_trade_log(self, data: TradeLogData) -> APIStatus:
        """
        Kirim data trade ke server

        Args:
            data: TradeLogData object

        Returns:
            APIStatus enum
        """
        post_data = self._encode_post_data(data)
        self._last_status = APIStatus.PENDING

        if self.debug:
            print(f"[API] Sending trade log | Ticket: {data.ticket} | Profit: {data.profit}")

        # Retry loop dengan exponential backoff
        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.post(
                    self.url,
                    data=post_data,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    if self._parse_response(response.text):
                        self._success_count += 1
                        self._last_status = APIStatus.SUCCESS
                        if self.debug:
                            print(f"[API] Trade log TERKIRIM | Ticket: {data.ticket}")
                        return APIStatus.SUCCESS
                    else:
                        # Response ada tapi tidak sesuai format
                        if attempt == self.retry_count:
                            self._fail_count += 1
                            self._last_status = APIStatus.ERROR_RESPONSE
                            if self.debug:
                                print(f"[API] Invalid response: {self._last_response}")
                            return APIStatus.ERROR_RESPONSE
                else:
                    self._last_error = f"HTTP {response.status_code}"
                    self._last_status = APIStatus.ERROR_REJECTED

            except requests.exceptions.Timeout:
                self._last_error = "Connection timeout"
                self._last_status = APIStatus.ERROR_TIMEOUT
            except requests.exceptions.ConnectionError:
                self._last_error = "Network unavailable"
                self._last_status = APIStatus.ERROR_NETWORK
            except Exception as e:
                self._last_error = str(e)
                self._last_status = APIStatus.ERROR_NETWORK

            # Wait sebelum retry
            if attempt < self.retry_count:
                sleep_time = attempt * 1.0  # 1s, 2s, 3s...
                if self.debug:
                    print(f"[API] Retry dalam {sleep_time}s...")
                time.sleep(sleep_time)

        # Semua retry gagal
        self._fail_count += 1
        if self.debug:
            print(f"[API] Gagal kirim log setelah {self.retry_count} percobaan")
        return self._last_status

    # =========================================================================
    # GETTERS
    # =========================================================================

    def get_success_count(self) -> int:
        """Get jumlah request sukses"""
        return self._success_count

    def get_fail_count(self) -> int:
        """Get jumlah request gagal"""
        return self._fail_count

    def get_last_status(self) -> Optional[APIStatus]:
        """Get status terakhir"""
        return self._last_status

    def get_last_error(self) -> Optional[str]:
        """Get error message terakhir"""
        return self._last_error

    def get_last_response(self) -> Optional[str]:
        """Get response terakhir"""
        return self._last_response

    def reset_counters(self):
        """Reset counters"""
        self._success_count = 0
        self._fail_count = 0
