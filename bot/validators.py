"""
Input validation helpers for CLI arguments and order parameters.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LOSS_LIMIT"}


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def validate_symbol(symbol: str) -> str:
    """Normalise and validate a trading symbol (e.g. BTCUSDT)."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Must contain only letters and digits (e.g. BTCUSDT)."
        )
    if len(symbol) < 3:
        raise ValidationError(f"Symbol '{symbol}' is too short.")
    return symbol


def validate_side(side: str) -> str:
    """Validate order side (BUY or SELL)."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type (MARKET, LIMIT, STOP_MARKET)."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str) -> Decimal:
    """Parse and validate order quantity."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Parse and validate price.

    - Required for LIMIT and STOP_MARKET orders.
    - Ignored for MARKET orders.
    """
    if order_type == "MARKET":
        if price is not None:
            # Silently ignore price for market orders rather than erroring
            return None
        return None

    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(stop_price: Optional[str], order_type: str) -> Optional[Decimal]:
    """Parse and validate stop price (required for STOP_LOSS_LIMIT orders)."""
    if order_type != "STOP_LOSS_LIMIT":
        return None

    if stop_price is None:
        raise ValidationError("Stop price (--stop-price) is required for STOP_LOSS_LIMIT orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValidationError(f"Invalid stop price '{stop_price}'. Must be a positive number.")
    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than zero, got {sp}.")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> dict:
    """
    Run all validators and return a clean, typed parameter dict.

    Raises:
        ValidationError: If any field is invalid.
    """
    validated_type = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validated_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, validated_type),
        "stop_price": validate_stop_price(stop_price, validated_type),
    }