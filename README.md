# BTC/USDT Paper Agent

## What I am building

I am building a safe, local-first foundation for an autonomous multi-asset quant paper-trading platform: I set a paper allocation, internal market-monitoring, asset-analysis, and portfolio-risk agents turn defined signals into simulated trades, and risk controls can stop and flatten the portfolio automatically. The immediate goal is to validate the workflow, controls, and observability before considering any live-market integration.

Allocate simulated USD, then start a local event-driven multi-asset paper-trading platform. The dashboard runs at `http://127.0.0.1:8787` and requires only Python 3.

```powershell
cd C:\Users\kardk\Documents\Codex\2026-10-01\cr\outputs\crypto_paper_agent
python .\paper_agent.py --allocation 10000
```

The allocation is **not** a deposit and nothing can be traded live. The platform has no network calls, no API-key support, no exchange/broker connectivity, and no mechanism to access funds. All price streams are synthetic and results are not evidence of profitability.

## Current universe and agents

- Watchlist: BTC, ETH, SOL; EUR/USD, GBP/USD, USD/JPY; gold, silver, WTI crude; SPY, QQQ, and Apple. The architecture supports more symbols but does not claim coverage of every instrument.
- **Market Monitor Agent** tracks simulated crypto, FX, commodity, and equity observations. It cannot access the allocation or submit orders.
- **Asset Analysis Agent** analyzes each watched instrument with an explainable, bounded momentum signal. It produces proposals only.
- **Portfolio & Risk Agent** is the sole approval gate. It clips or rejects proposals under exposure limits before the paper broker can simulate a fill.

Built-in controls: 12% maximum per asset, 30% maximum per asset class, 55% gross exposure cap, 4% maximum trade size, 3% loss stop, 5% drawdown kill switch, simulated fees/slippage, and stop-and-flatten.

## Production-readiness boundary

"HFT" is a specialized production discipline involving co-location, exchange-specific connectivity, queue-position models, regulated-broker controls, audited market data, order-state recovery, monitoring, and compliance. This repository is a safe learning/paper-trading prototype, not production HFT, a live-investment service, or investment advice. A real deployment requires licensed/legal review, data and broker agreements, independent risk controls, security review, comprehensive backtesting, forward paper trading, and explicit human approval for any live trading.
