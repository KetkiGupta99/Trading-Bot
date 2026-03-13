# Binance Spot Testnet Trading Bot

A **Python-based trading bot** with both a **CLI interface** and a **Streamlit Web UI** for placing orders on the **Binance Spot Testnet** (USDT pairs).
This project allows users to safely test trading strategies without using real money.

## Live Demo

**Try the Web App:**
https://trading-bot-app.streamlit.app/

---

## Overview

This trading bot interacts with the **Binance Spot Testnet API** to place and manage orders.
It includes input validation, structured logging, and error handling to ensure reliable operation.

Users can interact with the bot in two ways:

* **CLI Interface** – for terminal-based order execution
* **Web UI** – an easy-to-use interface built with Streamlit

## Features

| Feature | Details |
|--------|--------|
| **Order Types** | Supports `MARKET`, `LIMIT`, and `STOP_LOSS_LIMIT` orders |
| **Sides** | Supports both `BUY` and `SELL` orders |
| **Interfaces** | CLI interface (`cli.py`) and Web UI using Streamlit (`streamlit run app.py`) |
| **Validation** | Validates `symbol`, `side`, `type`, `quantity`, and `price` before making any API call |
| **Logging** | Structured logs written to `logs/trading_bot_YYYYMMDD.log` |
| **Error Handling** | Handles API errors, network failures, and invalid user inputs gracefully |
| **Testnet** | Uses **Binance Spot Testnet**, so no real money is used |
| **Authentication** | Supports login via **GitHub OAuth** |

## Project Structure

```
trading_bot/
├── app.py                  # Streamlit web UI
├── cli.py                  # CLI entry point
├── bot/
│   ├── __init__.py
│   ├── client.py           # Binance REST client (HMAC signing, HTTP)
│   ├── orders.py           # Order placement logic
│   ├── validators.py       # Input validation
│   └── logging_config.py   # File + console logging setup
├── logs/
│   └── trading_bot_YYYYMMDD.log
├── .env.example            # Example environment variables
├── .gitignore
├── requirements.txt
└── README.md
```
##  Setup

### 1️ Get Testnet API Credentials

1. Go to https://testnet.binance.vision
2. Click **Log In with GitHub**
3. Navigate to **API Keys → Generate HMAC_SHA256 Key**
4. Copy the **API Key** and **Secret Key**

   *  The **secret key is shown only once**, so store it safely.

---

### 2️ Clone Repository and Install Dependencies

```bash
git clone https://github.com/KetkiGupta99/Trading-Bot.git
cd Trading-Bot

python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

---

### 3️ Configure API Credentials

Create a `.env` file in the project root and add:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

##  Running the Web UI

Start the Streamlit interface:

```bash
streamlit run app.py
```

The application will open at:

```
http://localhost:8501
```

---

#  Running the CLI

## Place a MARKET Order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --yes
```

## Place a LIMIT Order

```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 120000 --yes
```

## Place a STOP_LOSS_LIMIT Order

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_LOSS_LIMIT --quantity 0.001 --price 79000 --stop-price 80000 --yes
```

## Check Account Balances

```bash
python cli.py account
```

## List Open Orders

```bash
python cli.py open-orders --symbol BTCUSDT
```

---

#  Sample CLI Output

```
─── Order Request ─────────────────────────────
│  Symbol     : BTCUSDT
│  Side       : BUY
│  Type       : MARKET
│  Quantity   : 0.001
───────────────────────────────────────────────

2026-03-14T00:48:41Z | INFO     | trading_bot.client | Placing order: symbol=BTCUSDT side=BUY type=MARKET qty=0.001 price=None stopPrice=None
2026-03-14T00:48:42Z | INFO     | trading_bot.client | Order placed successfully. orderId=16579778 status=FILLED

─── Order Response ────────────────────────────
│  Order ID     : 16579778
│  Client OID   : e2wgikPtPdjRo6ouaswntc
│  Symbol       : BTCUSDT
│  Side         : BUY
│  Type         : MARKET
│  Status       : FILLED
│  Quantity     : 0.00100000
│  Executed Qty : 0.00100000
│  Avg Price    : 71255.28
│  Time in Force: GTC
───────────────────────────────────────────────

Order placed successfully!
```

---

#  Logging

Logs are written to:

```
logs/trading_bot_YYYYMMDD.log
```

(one file per UTC day)

### Log Levels

* **File handler — DEBUG level**
  Captures every API request and raw response.

* **Console handler — INFO level**
  Shows order actions and results only.

### Sample Log

```
2026-03-13T23:33:28Z | INFO     | trading_bot.client | Order placed successfully. orderId=16539093 status=FILLED
2026-03-13T23:33:28Z | INFO     | trading_bot | Order placed via UI. orderId=16539093
2026-03-14T00:48:41Z | DEBUG    | trading_bot | Logging initialised. Log file: logs\trading_bot_20260313.log
2026-03-14T00:48:41Z | DEBUG    | trading_bot.client | Server time offset: -456 ms
2026-03-14T00:48:41Z | INFO     | trading_bot.client | Placing order: symbol=BTCUSDT side=BUY type=MARKET qty=0.001 price=None stopPrice=None
```
---

#  Assumptions

* All orders are executed on the **Binance Spot Testnet** available at
  `https://testnet.binance.vision`

* API credentials are loaded:

  * From the **`.env` file** when running locally
  * From **Streamlit Secrets** when the app is deployed

* **LIMIT orders** use `timeInForce = GTC` (**Good Till Cancelled**) by default.

* The **Binance Futures Testnet** (`https://testnet.binancefuture.com`) now requires **KYC verification**.
  This project uses the **Spot Testnet**, which only requires **GitHub login** to generate API keys.

---

## Note
Binance Spot Testnet may return error 451 (geo-restriction) from certain 
locations including India. Use a VPN connected to a US/EU server to run 
the bot. The code itself is correct and fully functional.
