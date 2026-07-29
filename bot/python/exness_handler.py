"""
PiqsBot - Exness Web API Handler
==================================
Connect langsung ke Exness TANPA MT5 terminal.
Menggunakan Exness Web API v2.

Dokumentasi: https://api.exness.com/
"""

import requests
import hmac
import hashlib
import time
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class OrderType(Enum):
    """Order type"""
    BUY = "buy"
    SELL = "sell"


class OrderFillType(Enum):
    """Order fill type"""
    FOK = "fok"
    IOC = "ioc"
    MARKET = "market"


class ExnessAPI:
    """
    Exness Web API Client
    ======================

    Connect langsung ke Exness tanpa MT5 terminal.
    Menggunakan OAuth2 authentication.

    Usage:
        api = ExnessAPI(
            login="414090289",
            password="Piqsang@0307",
            server="Exness-MT5Trial6",
            account_type="trading"
        )
        api.connect()
        api.get_balance()
        api.place_order("XAUUSD", "buy", 0.1, 150, 100)
    """

    # API Endpoints
    BASE_URL = "https://api.exness.com"
    API_V2 = "/api/v2"

    def __init__(
        self,
        login: str = "",
        password: str = "",
        server: str = "",
        account_type: str = "trading",
        debug: bool = True
    ):
        self.login = login
        self.password = password
        self.server = server
        self.account_type = account_type
        self.debug = debug

        # Auth tokens
        self.access_token = ""
        self.refresh_token = ""
        self.token_expires = 0

        # Session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        # Account info
        self.account_info = {}

    def _generate_signature(self, timestamp: str, method: str, path: str) -> str:
        """Generate HMAC signature for authentication"""
        message = f"{timestamp}{method.upper()}{path}"
        signature = hmac.new(
            self.password.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make HTTP request to API"""
        url = f"{self.BASE_URL}{endpoint}"
        timestamp = str(int(time.time()))

        headers = {
            "Timestamp": timestamp,
            "Signature": self._generate_signature(timestamp, method, endpoint)
        }

        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unknown method: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                if self.debug:
                    print(f"[ExnessAPI] Error {response.status_code}: {response.text}")
                return {"error": response.text, "status_code": response.status_code}

        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"[ExnessAPI] Request failed: {e}")
            return {"error": str(e)}

    def authenticate(self) -> bool:
        """
        Authenticate ke Exness API menggunakan username/password

        Returns:
            True jika berhasil
        """
        endpoint = f"{self.API_V2}/auth/login"

        data = {
            "login": self.login,
            "password": self.password,
            "server": self.server,
            "account_type": self.account_type
        }

        result = self._make_request("POST", endpoint, data)

        if "access_token" in result:
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token", "")
            self.token_expires = time.time() + result.get("expires_in", 3600)

            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })

            if self.debug:
                print(f"[ExnessAPI] Authenticated as {self.login}")
            return True

        if self.debug:
            print(f"[ExnessAPI] Auth failed: {result}")
        return False

    def refresh_access_token(self) -> bool:
        """Refresh access token"""
        if not self.refresh_token:
            return self.authenticate()

        endpoint = f"{self.API_V2}/auth/refresh"

        result = self._make_request("POST", endpoint, {
            "refresh_token": self.refresh_token
        })

        if "access_token" in result:
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token", self.refresh_token)
            self.token_expires = time.time() + result.get("expires_in", 3600)

            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            return True

        return self.authenticate()

    def is_authenticated(self) -> bool:
        """Check if token still valid"""
        return bool(self.access_token) and time.time() < self.token_expires - 60

    def connect(self) -> bool:
        """Connect dan authenticate"""
        if not self.login or not self.password:
            if self.debug:
                print("[ExnessAPI] No credentials provided")
            return False
        return self.authenticate()

    # =========================================================================
    # ACCOUNT INFO
    # =========================================================================

    def get_account_info(self) -> Optional[dict]:
        """Get account information"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/account/info"
        result = self._make_request("GET", endpoint)

        if "login" in result:
            self.account_info = result
            return result

        return None

    def get_balance(self) -> float:
        """Get account balance"""
        info = self.get_account_info()
        if info:
            return float(info.get("balance", 0))
        return 0

    def get_equity(self) -> float:
        """Get account equity"""
        info = self.get_account_info()
        if info:
            return float(info.get("equity", 0))
        return 0

    def get_margin_level(self) -> float:
        """Get margin level"""
        info = self.get_account_info()
        if info:
            return float(info.get("margin_level", 0))
        return 0

    # =========================================================================
    # SYMBOL INFO
    # =========================================================================

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get symbol information"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/symbols/{symbol}"
        result = self._make_request("GET", endpoint)

        if "symbol" in result:
            return result
        return None

    def get_price(self, symbol: str) -> Optional[dict]:
        """Get current price for symbol"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/symbols/{symbol}/price"
        result = self._make_request("GET", endpoint)

        if "bid" in result:
            return result
        return None

    # =========================================================================
    # TRADING
    # =========================================================================

    def place_order(
        self,
        symbol: str,
        order_type: str,  # "buy" or "sell"
        volume: float,
        sl_points: int = 0,
        tp_points: int = 0,
        comment: str = "",
        fill_type: str = "fok"
    ) -> Optional[dict]:
        """
        Place a new order

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")
            order_type: "buy" or "sell"
            volume: Lot size
            sl_points: Stop loss in points (0 = no SL)
            tp_points: Take profit in points (0 = no TP)
            comment: Order comment
            fill_type: "fok", "ioc", or "market"

        Returns:
            Order result dict
        """
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/orders"

        # Get current price for calculation
        price_data = self.get_price(symbol)
        if not price_data:
            if self.debug:
                print(f"[ExnessAPI] Failed to get price for {symbol}")
            return None

        bid = float(price_data.get("bid", 0))
        ask = float(price_data.get("ask", 0))
        point = float(price_data.get("point", 0.01))
        digit = int(price_data.get("digit", 2))

        # Calculate prices
        if order_type.lower() == "buy":
            price = ask
            sl = round(bid - sl_points * point, digit) if sl_points > 0 else 0
            tp = round(ask + tp_points * point, digit) if tp_points > 0 else 0
        else:
            price = bid
            sl = round(ask + sl_points * point, digit) if sl_points > 0 else 0
            tp = round(bid - tp_points * point, digit) if tp_points > 0 else 0

        data = {
            "symbol": symbol,
            "volume": volume,
            "type": order_type.lower(),
            "price": price,
            "sl": sl,
            "tp": tp,
            "comment": comment,
            "fill_type": fill_type
        }

        if self.debug:
            print(f"[ExnessAPI] Placing order: {data}")

        result = self._make_request("POST", endpoint, data)

        if "order_id" in result or "id" in result:
            if self.debug:
                print(f"[ExnessAPI] Order placed successfully")
            return result
        else:
            if self.debug:
                print(f"[ExnessAPI] Order failed: {result}")
            return result

    def close_order(self, order_id: int) -> Optional[dict]:
        """Close an order by ID"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/orders/{order_id}"
        result = self._make_request("DELETE", endpoint)

        return result

    def modify_order(self, order_id: int, sl: float = 0, tp: float = 0) -> Optional[dict]:
        """Modify order SL/TP"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/orders/{order_id}"

        data = {"sl": sl, "tp": tp}
        result = self._make_request("PUT", endpoint, data)

        return result

    # =========================================================================
    # POSITIONS
    # =========================================================================

    def get_positions(self, symbol: str = "") -> List[dict]:
        """Get open positions"""
        if not self.is_authenticated():
            if not self.connect():
                return []

        endpoint = f"{self.API_V2}/positions"

        params = {}
        if symbol:
            params["symbol"] = symbol

        result = self._make_request("GET", endpoint, params)

        if isinstance(result, list):
            return result
        elif "positions" in result:
            return result["positions"]
        return []

    def get_position(self, position_id: int) -> Optional[dict]:
        """Get single position by ID"""
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/positions/{position_id}"
        result = self._make_request("GET", endpoint)

        if "id" in result or "position_id" in result:
            return result
        return None

    def close_position(self, position_id: int, volume: float = 0) -> Optional[dict]:
        """
        Close a position

        Args:
            position_id: Position ID
            volume: Volume to close (0 = close all)

        Returns:
            Result dict
        """
        if not self.is_authenticated():
            if not self.connect():
                return None

        endpoint = f"{self.API_V2}/positions/{position_id}/close"

        data = {}
        if volume > 0:
            data["volume"] = volume

        result = self._make_request("POST", endpoint, data)

        return result

    # =========================================================================
    # HISTORY
    # =========================================================================

    def get_history(self, from_time: int = 0, to_time: int = 0) -> List[dict]:
        """Get trade history"""
        if not self.is_authenticated():
            if not self.connect():
                return []

        endpoint = f"{self.API_V2}/history"

        params = {}
        if from_time > 0:
            params["from"] = from_time
        if to_time > 0:
            params["to"] = to_time

        result = self._make_request("GET", endpoint, params)

        if isinstance(result, list):
            return result
        elif "history" in result:
            return result["history"]
        return []

    # =========================================================================
    # CANDLES
    # =========================================================================

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "M15",
        count: int = 100
    ) -> List[dict]:
        """
        Get candle data

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
            count: Number of candles

        Returns:
            List of candles
        """
        if not self.is_authenticated():
            if not self.connect():
                return []

        endpoint = f"{self.API_V2}/candles/{symbol}"

        params = {
            "timeframe": timeframe,
            "count": count
        }

        result = self._make_request("GET", endpoint, params)

        if isinstance(result, list):
            return result
        elif "candles" in result:
            return result["candles"]
        return []

    def get_closes(self, symbol: str, timeframe: str = "M15", count: int = 100) -> List[float]:
        """Get close prices for RSI calculation"""
        candles = self.get_candles(symbol, timeframe, count)
        return [float(c.get("close", 0)) for c in candles if "close" in c]


# =============================================================================
# CONVENIENCE CLASS - Wrapper untuk compatibility dengan bot
# =============================================================================

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


class ExnessHandler:
    """
    Exness Handler - Wrapper untuk PiqsBot
    ======================================

    Interface yang sama dengan MT5Handler tapi untuk Exness API.
    Ini membuat bot bisa switch antara MT5 dan Exness.
    """

    def __init__(
        self,
        login: str = "414090289",
        password: str = "Piqsang@0307",
        server: str = "Exness-MT5Trial6",
        debug: bool = True
    ):
        self.debug = debug
        self.api = ExnessAPI(
            login=login,
            password=password,
            server=server,
            debug=debug
        )
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize connection"""
        if self.debug:
            print("="*50)
            print("Connecting to Exness API...")
            print(f"Login: {self.api.login}")
            print(f"Server: {self.api.server}")
            print("="*50)

        if not self.api.connect():
            if self.debug:
                print("[ExnessHandler] Connection FAILED")
            return False

        # Get account info
        info = self.api.get_account_info()
        if info:
            if self.debug:
                print("="*50)
                print("Exness Connected!")
                print(f"Account: {info.get('login')}")
                print(f"Balance: ${float(info.get('balance', 0)):.2f}")
                print(f"Equity: ${float(info.get('equity', 0)):.2f}")
                print(f"Server: {info.get('server')}")
                print("="*50)
        else:
            if self.debug:
                print("[ExnessHandler] Failed to get account info")
            return False

        self.initialized = True
        return True

    def shutdown(self):
        """Shutdown connection"""
        self.initialized = False
        if self.debug:
            print("[ExnessHandler] Connection closed")

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get symbol info"""
        if not self.initialized:
            return None
        return self.api.get_symbol_info(symbol)

    def get_tick(self, symbol: str) -> Optional[TickData]:
        """Get last tick"""
        if not self.initialized:
            return None

        price = self.api.get_price(symbol)
        if price:
            spread = 0
            if "spread" in price:
                spread = int(price["spread"])
            elif "ask" in price and "bid" in price:
                spread = int((float(price["ask"]) - float(price["bid"])) * 100)

            return TickData(
                symbol=symbol,
                bid=float(price.get("bid", 0)),
                ask=float(price.get("ask", 0)),
                time=float(price.get("time", time.time())),
                spread=spread
            )
        return None

    def get_rates(self, symbol: str, timeframe: int = 15, count: int = 100) -> List[dict]:
        """Get candle data"""
        if not self.initialized:
            return []

        tf_map = {1: "M1", 5: "M5", 15: "M15", 30: "M30", 60: "H1", 240: "H4", 1440: "D1"}
        tf = tf_map.get(timeframe, "M15")

        return self.api.get_candles(symbol, tf, count)

    def get_closes(self, symbol: str, timeframe: int = 15, count: int = 100) -> List[float]:
        """Get close prices"""
        if not self.initialized:
            return []
        return self.api.get_closes(symbol, "M15" if timeframe == 15 else "H1", count)

    def get_current_bar_time(self, symbol: str, timeframe: int = 15) -> float:
        """Get current bar timestamp"""
        candles = self.get_rates(symbol, timeframe, 1)
        if candles:
            return float(candles[0].get("time", 0))
        return 0

    def get_positions(self, symbol: str = "", magic: int = 0) -> List[PositionInfo]:
        """Get open positions"""
        if not self.initialized:
            return []

        positions = self.api.get_positions(symbol)

        result = []
        for pos in positions:
            pos_type = OrderType.BUY if pos.get("type", "").lower() == "buy" else OrderType.SELL

            result.append(PositionInfo(
                ticket=int(pos.get("id", pos.get("position_id", 0))),
                symbol=pos.get("symbol", ""),
                type=pos_type,
                volume=float(pos.get("volume", 0)),
                price_open=float(pos.get("price_open", pos.get("open_price", 0))),
                price_current=float(pos.get("current_price", 0)),
                sl=float(pos.get("sl", 0)),
                tp=float(pos.get("tp", 0)),
                profit=float(pos.get("profit", 0)),
                magic=int(pos.get("magic", magic)),
                comment=pos.get("comment", "")
            ))

        return result

    def has_open_position(self, symbol: str, magic: int = 0) -> bool:
        """Check if has open position"""
        return len(self.get_positions(symbol, magic)) > 0

    def get_position_count(self, symbol: str, magic: int = 0) -> int:
        """Get position count"""
        return len(self.get_positions(symbol, magic))

    def calculate_lot_risk(self, symbol: str, sl_points: int, risk_percent: float = 2.0) -> float:
        """Calculate lot based on risk"""
        # Simplified calculation for gold
        info = self.api.get_account_info()
        if not info:
            return 0.1

        balance = float(info.get("balance", 10000))
        risk_amount = balance * (risk_percent / 100)

        # Point value untuk XAUUSD
        point_value = 0.01  # Approximate

        if sl_points > 0:
            lot = risk_amount / (sl_points * point_value * 100)  # 100 oz per lot
        else:
            lot = 0.1

        return min(max(lot, 0.01), 1.0)

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
        """Open new position"""
        if not self.initialized:
            return None

        ot = "buy" if order_type == OrderType.BUY else "sell"

        result = self.api.place_order(
            symbol=symbol,
            order_type=ot,
            volume=volume,
            sl_points=sl_points,
            tp_points=tp_points,
            comment=comment or f"PiqsBot_{magic}"
        )

        if result and ("order_id" in result or "id" in result):
            ticket = result.get("order_id", result.get("id", 0))
            if self.debug:
                print(f"[ExnessHandler] Position opened | Ticket: #{ticket}")
            return int(ticket)

        if self.debug:
            print(f"[ExnessHandler] Open failed: {result}")
        return None

    def close_position(self, ticket: int, volume: float, deviation: int = 10) -> bool:
        """Close position"""
        if not self.initialized:
            return False

        result = self.api.close_position(ticket, volume if volume > 0 else 0)

        if result and result.get("done"):
            if self.debug:
                print(f"[ExnessHandler] Position #{ticket} closed")
            return True

        if self.debug:
            print(f"[ExnessHandler] Close failed: {result}")
        return False

    def modify_position(self, ticket: int, sl: float, tp: float) -> bool:
        """Modify position SL/TP"""
        if not self.initialized:
            return False

        result = self.api.modify_order(ticket, sl, tp)

        if result and result.get("done"):
            if self.debug:
                print(f"[ExnessHandler] Position #{ticket} modified")
            return True

        if self.debug:
            print(f"[ExnessHandler] Modify failed: {result}")
        return False

    def get_balance(self) -> float:
        """Get balance"""
        return self.api.get_balance()

    def get_equity(self) -> float:
        """Get equity"""
        return self.api.get_equity()

    def get_margin_level(self) -> float:
        """Get margin level"""
        return self.api.get_margin_level()

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.initialized and self.api.is_authenticated()

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
