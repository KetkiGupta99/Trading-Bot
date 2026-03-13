"""
Low-level Binance Spot Testnet client.

Testnet URL : https://testnet.binance.vision
API docs    : https://binance-docs.github.io/apidocs/spot/en/

Handles:
  - HMAC-SHA256 request signing
  - HTTP communication via `requests`
  - Server time synchronisation (timestamp offset)
  - Structured logging of every request and response
  - Raising typed exceptions on API / network errors
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

# Binance Spot Testnet — login via https://testnet.binance.vision (GitHub OAuth)
TESTNET_BASE_URL = "https://testnet.binance.vision"
DEFAULT_RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error body."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on connection / timeout failures."""
    

class BinanceSpotClient:
    """
    Thin wrapper around the Binance Spot REST API (Testnet).

    Args:
        api_key: Testnet API key (from testnet.binance.vision).
        api_secret: Testnet API secret.
        base_url: Base URL (defaults to Spot Testnet).
        recv_window: Allowed clock drift in milliseconds.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
        timeout: int = 10,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})

        # Compute offset between local clock and server clock once at startup
        self._time_offset_ms: int = self._sync_server_time()
        logger.debug("Server time offset: %d ms", self._time_offset_ms)

    def _sync_server_time(self) -> int:
        """Return (server_time_ms - local_time_ms) to compensate for clock skew."""
        try:
            resp = self._session.get(
                f"{self.base_url}/api/v3/time", timeout=self.timeout
            )
            resp.raise_for_status()
            server_ms: int = resp.json()["serverTime"]
            local_ms = int(time.time() * 1000)
            return server_ms - local_ms
        except requests.RequestException as exc:
            logger.warning("Could not sync server time, using local clock: %s", exc)
            return 0

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset_ms

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Any:
        """
        Execute an HTTP request, optionally signing the payload.
        Returns the parsed JSON (dict or list).
        Raises BinanceAPIError or BinanceNetworkError on failure.
        """
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug(
            "→ %s %s | params: %s",
            method.upper(),
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() in ("POST", "DELETE") else None,
                timeout=self.timeout,
            )
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.Timeout as exc:
            logger.error("Request timed out after %ds: %s", self.timeout, exc)
            raise BinanceNetworkError(f"Request timed out: {exc}") from exc
        except requests.RequestException as exc:
            logger.error("Unexpected network error: %s", exc)
            raise BinanceNetworkError(f"Network error: {exc}") from exc

        logger.debug("HTTP %d | body: %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %d): %s", response.status_code, response.text[:200])
            raise BinanceAPIError(-1, f"Non-JSON response: {response.text[:200]}")

        # Binance returns error bodies as {"code": <negative int>, "msg": "..."}
        if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
            code = data["code"]
            msg = data.get("msg", "Unknown error")
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        if not response.ok:
            logger.error("HTTP %d: %s", response.status_code, response.text[:200])
            raise BinanceAPIError(response.status_code, response.text[:200])

        return data

    # Public API methods

    def get_account(self) -> Dict[str, Any]:
        """Fetch spot account information including balances."""
        return self._request("GET", "/api/v3/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance Spot Testnet.

        Args:
            symbol: Trading pair (e.g. BTCUSDT).
            side: BUY or SELL.
            order_type: MARKET, LIMIT, or STOP_LOSS_LIMIT (bonus).
            quantity: Order quantity.
            price: Limit price (required for LIMIT / STOP_LOSS_LIMIT).
            stop_price: Stop trigger price (required for STOP_LOSS_LIMIT).
            time_in_force: GTC / IOC / FOK (for LIMIT orders).

        Returns:
            Raw API response dict.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if order_type == "STOP_LOSS_LIMIT":
            if price is None or stop_price is None:
                raise ValueError("Both price and stop_price are required for STOP_LOSS_LIMIT orders.")
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )
        result = self._request("POST", "/api/v3/order", params=params)
        logger.info(
            "Order placed successfully. orderId=%s status=%s",
            result.get("orderId"), result.get("status"),
        )
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order %d on %s", order_id, symbol)
        return self._request("DELETE", "/api/v3/order", params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Fetch all open orders, optionally filtered by symbol."""
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/api/v3/openOrders", params=params)