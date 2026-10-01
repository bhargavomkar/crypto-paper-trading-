# Paper-only architecture

## Authority boundaries

```text
Market Monitor -> Asset Analysis -> Portfolio & Risk -> Paper Broker -> Ledger/UI
       |                 |                  |                 |
  observations only   proposals only    approve/clip/reject  simulated fills only
```

The monitor cannot read the allocation or create orders. The analysis agent receives market features and creates bounded signal proposals; it cannot execute them. The portfolio/risk agent is the only order authority and enforces exposure, class, loss, drawdown, and kill-switch policies. The broker has no real-trading implementation.

## Production-oriented next steps

1. Replace the synthetic monitor with licensed, normalized market data and quality checks (stale-feed age, sequence gaps, crossed markets, session calendars).
2. Persist immutable `MarketEvent`, `SignalProposal`, `RiskDecision`, `PaperOrder`, and `PaperFill` records with UTC timestamps, version IDs, and correlation IDs.
3. Add replay/backtest parity, a realistic fill model (spread, latency, partial fills), and a reconciliation job.
4. Add authentication, authorization, audit retention, alerting, and a configuration-review workflow. Keep the default deployment paper-only.
5. Require independent legal/compliance, security, and risk review before connecting any regulated broker or exchange. Do not enable autonomous real-money trading.

## Instrument registry

Every asset needs a canonical record before it is admitted: symbol, asset class, venue, quote currency, tick/lot size, contract multiplier, trading calendar, margin policy, and status. This prevents mixing crypto spot, FX pairs, commodity futures, and equities under one unsafe sizing model.
