"""
Order placement logic and result formatting.

Acts as the business-logic layer between the CLI and the raw API client.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceSpotClient, BinanceAPIError, BinanceNetworkError

logger = logging.getLogger("trading_bot.orders")


def place_order(
    client: BinanceSpotClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
) -> Dict[str, Any]:
    try:
        raw = client.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
        return {"success": True, "order": raw, "error": None}
    except BinanceAPIError as exc:
        logger.error("API error placing order: %s", exc)
        return {"success": False, "order": None, "error": str(exc)}
    except BinanceNetworkError as exc:
        logger.error("Network error placing order: %s", exc)
        return {"success": False, "order": None, "error": str(exc)}
    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        return {"success": False, "order": None, "error": f"Unexpected error: {exc}"}


def format_order_summary(params: Dict[str, Any]) -> str:
    lines = [
        "Order Request",
        f"Symbol     : {params.get('symbol')}",
        f"Side       : {params.get('side')}",
        f"Type       : {params.get('order_type')}",
        f"Quantity   : {params.get('quantity')}",
    ]
    if params.get("price"):
        lines.append(f"Price      : {params.get('price')}")
    if params.get("stop_price"):
        lines.append(f"Stop Price : {params.get('stop_price')}")
    return "\n".join(lines)


def format_order_response(order: Dict[str, Any]) -> str:
    # Binance Spot MARKET orders: fill price is inside fills[], not avgPrice
    fills = order.get("fills") or []
    if fills:
        total_qty = sum(float(f["qty"]) for f in fills)
        if total_qty > 0:
            weighted = sum(float(f["price"]) * float(f["qty"]) for f in fills)
            avg_price_str = f"{weighted / total_qty:.2f}"
        else:
            avg_price_str = "N/A"
    else:
        p = order.get("price", "0")
        avg_price_str = p if float(p) > 0 else "N/A (pending fill)"

    lines = [
        "─── Order Response ────────────────────────────",
        f"│  Order ID     : {order.get('orderId')}",
        f"│  Client OID   : {order.get('clientOrderId', 'N/A')}",
        f"│  Symbol       : {order.get('symbol')}",
        f"│  Side         : {order.get('side')}",
        f"│  Type         : {order.get('type')}",
        f"│  Status       : {order.get('status')}",
        f"│  Quantity     : {order.get('origQty')}",
        f"│  Executed Qty : {order.get('executedQty', '0')}",
        f"│  Avg Price    : {avg_price_str}",
        f"│  Time in Force: {order.get('timeInForce', 'N/A')}",
        "───────────────────────────────────────────────",
    ]
    return "\n".join(lines)