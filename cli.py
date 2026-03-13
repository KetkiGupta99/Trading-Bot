#!/usr/bin/env python3
"""
cli.py — CLI entry point for the Binance Spot Testnet trading bot.

Examples:
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --yes
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 120000 --yes
  python cli.py place --symbol BTCUSDT --side SELL --type STOP_LOSS_LIMIT --quantity 0.001 --price 79000 --stop-price 80000 --yes
  python cli.py account
  python cli.py open-orders --symbol BTCUSDT
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Setup logging AFTER imports so print() works immediately
from bot.logging_config import setup_logging
logger = setup_logging()

from bot.client import BinanceSpotClient, BinanceAPIError, BinanceNetworkError
from bot.validators import ValidationError, validate_all


def build_client():
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print("[ERROR] BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env")
        sys.exit(1)
    return BinanceSpotClient(api_key=api_key, api_secret=api_secret)


def get_avg_price(order):
    """Extract avg fill price - for MARKET orders it's inside fills[]."""
    fills = order.get("fills") or []
    if fills:
        total_qty = sum(float(f["qty"]) for f in fills)
        if total_qty > 0:
            weighted = sum(float(f["price"]) * float(f["qty"]) for f in fills)
            return f"{weighted / total_qty:.2f}"
    price = order.get("price", "0")
    return price if float(price) > 0 else "N/A (pending)"


def print_order_request(params):
    print()
    print("─── Order Request ─────────────────────────────")
    print(f"│  Symbol     : {params['symbol']}")
    print(f"│  Side       : {params['side']}")
    print(f"│  Type       : {params['order_type']}")
    print(f"│  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"│  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"│  Stop Price : {params['stop_price']}")
    print("───────────────────────────────────────────────")
    print()


def print_order_response(order):
    print()
    print("─── Order Response ────────────────────────────")
    print(f"│  Order ID     : {order.get('orderId')}")
    print(f"│  Client OID   : {order.get('clientOrderId', 'N/A')}")
    print(f"│  Symbol       : {order.get('symbol')}")
    print(f"│  Side         : {order.get('side')}")
    print(f"│  Type         : {order.get('type')}")
    print(f"│  Status       : {order.get('status')}")
    print(f"│  Quantity     : {order.get('origQty')}")
    print(f"│  Executed Qty : {order.get('executedQty', '0')}")
    print(f"│  Avg Price    : {get_avg_price(order)}")
    print(f"│  Time in Force: {order.get('timeInForce', 'N/A')}")
    print("───────────────────────────────────────────────")
    print()


def cmd_place(args):
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        print(f"\n[VALIDATION ERROR] {exc}\n")
        sys.exit(1)

    print_order_request(params)

    if not args.yes:
        try:
            confirm = input("Proceed with this order? [y/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if confirm not in ("y", "yes"):
            print("Order cancelled.")
            sys.exit(0)

    client = build_client()

    try:
        order = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
        print_order_response(order)
        print("Order placed successfully!")
        logger.info("Order placed. orderId=%s status=%s", order.get("orderId"), order.get("status"))
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n Order failed: {exc}\n")
        logger.error("Order failed: %s", exc)
        sys.exit(1)


def cmd_account(args):
    client = build_client()
    try:
        info = client.get_account()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)

    all_balances = info.get("balances", [])
    locked = [b for b in all_balances if float(b.get("locked", 0)) > 0]
    free_nonzero = sorted(
        [b for b in all_balances if float(b.get("free", 0)) > 0],
        key=lambda b: float(b["free"]), reverse=True
    )[:20]

    seen, display = set(), []
    for b in locked + free_nonzero:
        if b["asset"] not in seen:
            seen.add(b["asset"])
            display.append(b)

    print()
    print("─── Account Balances (top 20 + locked) ────────")
    for b in display:
        locked_val = float(b.get("locked", 0))
        locked_str = f"  locked={locked_val:.8f}" if locked_val > 0 else ""
        print(f"│  {b['asset']:<10}  free={float(b['free']):.8f}{locked_str}")
    print(f"│  ({len(display)} shown of {len(free_nonzero)} assets with balance)")
    print("───────────────────────────────────────────────")
    print()


def cmd_open_orders(args):
    client = build_client()
    try:
        orders = client.get_open_orders(symbol=args.symbol.upper() if args.symbol else None)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)

    if not orders:
        print("\nNo open orders.\n")
        return

    print()
    print(f"─── Open Orders ({len(orders)}) ───────────────────────────")
    for o in orders:
        print(f"│  id={o['orderId']}  {o['symbol']}  {o['side']}  {o['type']}  qty={o['origQty']}  price={o.get('price', 'N/A')}  status={o['status']}")
    print("───────────────────────────────────────────────")
    print()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Spot Testnet Trading Bot",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    place_p = sub.add_parser("place", help="Place a new order")
    place_p.add_argument("--symbol", required=True)
    place_p.add_argument("--side", required=True, help="BUY or SELL")
    place_p.add_argument("--type", required=True, dest="type", help="MARKET | LIMIT | STOP_LOSS_LIMIT")
    place_p.add_argument("--quantity", required=True)
    place_p.add_argument("--price", default=None)
    place_p.add_argument("--stop-price", dest="stop_price", default=None)
    place_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    place_p.set_defaults(func=cmd_place)

    acct_p = sub.add_parser("account", help="Show account balances")
    acct_p.set_defaults(func=cmd_account)

    oo_p = sub.add_parser("open-orders", help="List open orders")
    oo_p.add_argument("--symbol", default=None)
    oo_p.set_defaults(func=cmd_open_orders)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)