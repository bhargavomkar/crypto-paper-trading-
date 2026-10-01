# Project guide: Multi-Asset Paper Trading Terminal

## What this project is

This is a local, paper-only quant-trading terminal. You enter a **simulated** USD allocation, and the application models how a portfolio could react to systematic trading signals across crypto, foreign exchange, commodities, and equities.

No money is deposited, no exchange or broker account is connected, and no trade is sent to a real market. Every price, order, fill, balance, and profit/loss value is generated in the local simulation.

## Where quant trading is used

Quantitative trading means making portfolio decisions with defined, testable rules instead of discretionary clicks. In this project, the quant layer is used in four places:

1. **Market simulation** — the Market Monitor creates BTC, ETH, FX, gold, oil, ETF, and stock-like price ticks. It keeps short- and slow-moving price averages and constructs synthetic candlestick bars.
2. **Signal research** — the Algorithm Research Agent combines two technical features:
   - **EMA momentum:** compares a fast exponential moving average with a slow moving average to estimate trend direction.
   - **RSI-style strength:** compares recent upward and downward changes to avoid treating all trends as equally strong.
3. **Portfolio construction** — a BUY proposal produces a target portfolio weight rather than an unlimited order. SELL and HOLD proposals instruct the portfolio agent to reduce/avoid exposure in the long-only paper portfolio.
4. **Risk management** — the Portfolio & Risk Agent limits individual positions, asset-class exposure, gross exposure, trade size, loss, and drawdown before it can request a simulated fill.

The EMA/RSI model is intentionally simple and explainable. It is a learning and integration model, not evidence of a profitable strategy.

## Agents and responsibilities

```text
Market Monitor -> Algorithm Research -> Portfolio & Risk -> Paper Broker -> Terminal
```

| Component | What it does | What it cannot do |
|---|---|---|
| Market Monitor | Produces and tracks simulated market observations | Read allocation or create trades |
| Algorithm Research | Produces BUY / SELL / HOLD proposals with a score and confidence | Execute any order |
| Portfolio & Risk | Caps, approves, or rejects proposals against risk policy | Connect to a broker or access real funds |
| Paper Broker | Records synthetic orders, fills, cash, positions, and P&L | Send real orders |
| Dashboard | Displays profile, P&L, signals, charts, and activity | Change the paper-only boundary |

This separation is important: a research model should not be able to access capital or bypass risk rules.

## Current technology

| Area | Technology used | Purpose |
|---|---|---|
| Backend | Python 3 standard library | Application logic without third-party runtime dependencies |
| Web server | `ThreadingHTTPServer` | Serves the local dashboard and JSON status endpoints |
| Front end | HTML, CSS, vanilla JavaScript | Portfolio controls, tables, and live dashboard refresh |
| Charts | HTML Canvas | Draws local synthetic candlestick and equity charts |
| Quant logic | EMA momentum plus RSI-style strength | Produces bounded, explainable paper signals |
| Risk controls | Python policy checks | Applies exposure caps, stop-loss, drawdown kill switch, and flattening |
| Tests | Python `unittest` | Checks agent actions, risk limits, P&L profile data, candles, and flattening |
| Source control | Git and GitHub | Versioning and publishing the project |

## Instruments currently simulated

- **Crypto:** BTC-USD, ETH-USD, SOL-USD
- **FX:** EUR/USD, GBP/USD, USD/JPY
- **Commodities:** Gold, silver, WTI crude oil
- **Equities/ETFs:** SPY, QQQ, Apple

The watchlist is an initial allowlist, not “every market.” A production platform needs an instrument registry with venue, quote currency, lot size, tick size, contract multiplier, margin rules, and trading-session calendar for each instrument.

## Understanding the dashboard P&L

- **Paper allocation:** the simulated starting capital set in the terminal.
- **Paper equity:** simulated cash plus the current simulated market value of open positions.
- **Total P&L:** paper equity minus paper allocation.
- **Realized P&L:** P&L recorded when a paper position is sold.
- **Unrealized P&L:** the current paper gain/loss on an open position.
- **Drawdown:** percentage decline from the highest simulated equity value reached so far.

These metrics only describe this local simulation. They do not reflect a bank, broker, exchange, wallet, tax obligation, or real investment return.

## Risk controls currently implemented

- 12% maximum allocation to one asset
- 30% maximum allocation to one asset class
- 55% maximum gross portfolio exposure
- 4% maximum trade size
- 3% portfolio loss stop
- 5% drawdown kill switch
- Simulated transaction fees and slippage
- Stop-and-flatten control

## What would be required for a real production system

The project is not HFT or a real trading service. A production-grade deployment would require, at minimum:

1. Licensed real-time market data and data-quality monitoring.
2. Regulated broker/exchange integrations with an explicit human approval process.
3. Secure secrets storage, authentication, authorization, audit logs, and incident response.
4. Persistent ledger storage, reconciliation, idempotent order handling, and recovery from failures.
5. Proper backtesting, walk-forward validation, forward paper trading, and independent model/risk review.
6. Jurisdiction-specific legal, compliance, tax, and suitability review.

Do not use the current signals as personal investment advice or connect this prototype to real money.

## Running the project

```powershell
cd C:\Users\kardk\Documents\Codex\2026-10-01\cr\outputs\crypto_paper_agent
python .\paper_agent.py --allocation 10000
```

Open `http://127.0.0.1:8787` in a browser. Use **Set paper allocation**, then **Start paper agents** to begin the local simulation.
