# BTC/USDT Paper Agent

## What I am building

I am building a safe, local-first foundation for an autonomous crypto quant-trading agent: I set a paper allocation, the agent turns a defined strategy into simulated BTC/USDT trades, and risk controls can stop and flatten the portfolio automatically. The immediate goal is to validate the workflow, controls, and observability before considering any live-market integration.

Allocate simulated USD, then start a local event-driven BTC/USDT paper-trading agent. The dashboard runs at `http://127.0.0.1:8787` and requires only Python 3.

```powershell
cd C:\Users\kardk\Documents\Codex\2026-10-01\cr\outputs\crypto_paper_agent
python .\paper_agent.py --allocation 10000
```

The allocation is **not** a deposit and nothing can be traded live. The agent has no network calls, no API-key support, no exchange connectivity, and no mechanism to access funds. Its BTC-like price stream is synthetic and results are not evidence of profitability.

Built-in controls: 25% maximum position, 5% maximum trade size, 3% loss stop, 5% drawdown kill switch, simulated fees/slippage, and stop-and-flatten.

"HFT" is a specialized production discipline involving co-location, exchange-specific connectivity, queue-position models, and monitoring. This is a safe learning/paper-trading prototype, not HFT or investment advice.
