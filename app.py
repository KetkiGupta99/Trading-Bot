"""
app.py — Streamlit UI for the Binance Spot Testnet trading bot.

Run with:
    streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv
from bot.client import BinanceSpotClient, BinanceAPIError, BinanceNetworkError
from bot.validators import validate_all, ValidationError
from bot.logging_config import setup_logging

load_dotenv()
logger = setup_logging()

# Read credentials — Streamlit Cloud uses st.secrets, local dev uses .env
def get_env(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Binance Testnet Bot",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Binance Spot Testnet Trading Bot")
st.caption("Connected to testnet.binance.vision — all trades are simulated")

# ── Sidebar: API credentials ──────────────────────────────────────────────────
with st.sidebar:
    st.header("🔑 API Credentials")
    api_key    = st.text_input("API Key",    value=get_env("BINANCE_API_KEY"),    type="password")
    api_secret = st.text_input("API Secret", value=get_env("BINANCE_API_SECRET"), type="password")

    if api_key and api_secret:
        st.success("Credentials loaded")
    else:
        st.warning("Enter your testnet API key and secret")

    st.divider()
    st.markdown("**Testnet:** [testnet.binance.vision](https://testnet.binance.vision)")
    st.markdown("Login with GitHub → API Keys → Generate")


def get_client():
    if not api_key or not api_secret:
        st.error("API credentials are missing. Fill them in the sidebar.")
        st.stop()
    return BinanceSpotClient(api_key=api_key, api_secret=api_secret)


def get_avg_price(order):
    fills = order.get("fills") or []
    if fills:
        total_qty = sum(float(f["qty"]) for f in fills)
        if total_qty > 0:
            weighted = sum(float(f["price"]) * float(f["qty"]) for f in fills)
            return f"{weighted / total_qty:.2f}"
    price = order.get("price", "0")
    return price if float(price) > 0 else "N/A"


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_place, tab_account, tab_orders, tab_logs = st.tabs([
    "🛒 Place Order", "💰 Account", "📋 Open Orders", "📄 Logs"
])


# ── Tab 1: Place Order ────────────────────────────────────────────────────────
with tab_place:
    st.subheader("Place a New Order")

    col1, col2 = st.columns(2)

    with col1:
        symbol     = st.text_input("Symbol", value="BTCUSDT").upper()
        side       = st.selectbox("Side", ["BUY", "SELL"])
        order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP_LOSS_LIMIT"])
        quantity   = st.text_input("Quantity", value="0.001")

    with col2:
        price = None
        stop_price = None

        if order_type in ("LIMIT", "STOP_LOSS_LIMIT"):
            price = st.text_input("Limit Price (USDT)", value="")

        if order_type == "STOP_LOSS_LIMIT":
            stop_price = st.text_input("Stop Price (USDT)", value="")

        if order_type == "MARKET":
            st.info("Market orders execute immediately at the best available price.")

    st.divider()

    # Order summary preview
    st.markdown("**Order Summary**")
    summary_cols = st.columns(5)
    summary_cols[0].metric("Symbol", symbol)
    summary_cols[1].metric("Side", side)
    summary_cols[2].metric("Type", order_type)
    summary_cols[3].metric("Quantity", quantity)
    if price:
        summary_cols[4].metric("Price", price)

    place_btn = st.button("🚀 Place Order", type="primary", use_container_width=True)

    if place_btn:
        # Validate
        try:
            params = validate_all(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price if price else None,
                stop_price=stop_price if stop_price else None,
            )
        except ValidationError as e:
            st.error(f"Validation Error: {e}")
            st.stop()

        # Place order
        with st.spinner("Placing order..."):
            try:
                client = get_client()
                order = client.place_order(
                    symbol=params["symbol"],
                    side=params["side"],
                    order_type=params["order_type"],
                    quantity=params["quantity"],
                    price=params["price"],
                    stop_price=params["stop_price"],
                )
                logger.info("Order placed via UI. orderId=%s", order.get("orderId"))
            except (BinanceAPIError, BinanceNetworkError) as e:
                st.error(f"Order Failed: {e}")
                logger.error("Order failed via UI: %s", e)
                st.stop()

        st.success("✅ Order placed successfully!")

        # Display response
        res_cols = st.columns(4)
        res_cols[0].metric("Order ID",     order.get("orderId"))
        res_cols[1].metric("Status",       order.get("status"))
        res_cols[2].metric("Executed Qty", order.get("executedQty", "0"))
        res_cols[3].metric("Avg Price",    get_avg_price(order))

        with st.expander("Raw API Response"):
            st.json(order)


# ── Tab 2: Account Balances ───────────────────────────────────────────────────
with tab_account:
    st.subheader("Account Balances")

    if st.button("🔄 Refresh Balances"):
        with st.spinner("Fetching account..."):
            try:
                client = get_client()
                info = client.get_account()
            except (BinanceAPIError, BinanceNetworkError) as e:
                st.error(f"Error: {e}")
                st.stop()

        balances = [
            {
                "Asset":  b["asset"],
                "Free":   float(b["free"]),
                "Locked": float(b["locked"]),
            }
            for b in info.get("balances", [])
            if float(b.get("free", 0)) > 0 or float(b.get("locked", 0)) > 0
        ]

        balances.sort(key=lambda x: x["Free"], reverse=True)

        if balances:
            st.dataframe(
                balances,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Free":   st.column_config.NumberColumn(format="%.8f"),
                    "Locked": st.column_config.NumberColumn(format="%.8f"),
                },
            )
            st.caption(f"{len(balances)} assets with balance")
        else:
            st.info("No assets with positive balance.")
    else:
        st.info("Click **Refresh Balances** to load your account.")


# ── Tab 3: Open Orders ────────────────────────────────────────────────────────
with tab_orders:
    st.subheader("Open Orders")

    filter_symbol = st.text_input("Filter by symbol (optional)", value="").upper()

    if st.button("🔄 Refresh Orders"):
        with st.spinner("Fetching open orders..."):
            try:
                client = get_client()
                orders = client.get_open_orders(symbol=filter_symbol if filter_symbol else None)
            except (BinanceAPIError, BinanceNetworkError) as e:
                st.error(f"Error: {e}")
                st.stop()

        if orders:
            rows = [
                {
                    "Order ID": o["orderId"],
                    "Symbol":   o["symbol"],
                    "Side":     o["side"],
                    "Type":     o["type"],
                    "Quantity": float(o["origQty"]),
                    "Price":    float(o.get("price", 0)),
                    "Status":   o["status"],
                }
                for o in orders
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No open orders found.")
    else:
        st.info("Click **Refresh Orders** to load open orders.")


# ── Tab 4: Logs ───────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("Log Viewer")

    log_dir = "logs"
    if not os.path.exists(log_dir):
        st.info("No logs folder found yet. Place an order first.")
    else:
        log_files = sorted(
            [f for f in os.listdir(log_dir) if f.endswith(".log")],
            reverse=True,
        )

        if not log_files:
            st.info("No log files yet.")
        else:
            selected = st.selectbox("Select log file", log_files)
            lines = st.slider("Lines to show", min_value=10, max_value=200, value=50, step=10)

            with open(os.path.join(log_dir, selected), encoding="utf-8") as f:
                content = f.readlines()

            last_lines = content[-lines:]

            # Colour-code by level
            formatted = ""
            for line in last_lines:
                if "ERROR" in line:
                    formatted += f":red[{line.rstrip()}]\n\n"
                elif "WARNING" in line:
                    formatted += f":orange[{line.rstrip()}]\n\n"
                elif "INFO" in line:
                    formatted += f":green[{line.rstrip()}]\n\n"
                else:
                    formatted += f"{line.rstrip()}\n\n"

            st.markdown(formatted)
            st.caption(f"Showing last {min(lines, len(content))} of {len(content)} lines")