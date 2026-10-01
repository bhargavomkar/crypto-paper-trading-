#!/usr/bin/env python3
"""Local-only BTC/USDT paper-trading agent.

This application never holds credentials, moves money, or submits exchange
orders.  "Allocate" means allocate simulated USD to an isolated paper ledger.
It is deliberately event-driven, but it is *not* real HFT infrastructure.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import threading
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


@dataclass
class RiskLimits:
    max_position_fraction: float = 0.25
    max_trade_fraction: float = 0.05
    max_drawdown_fraction: float = 0.05
    max_loss_fraction: float = 0.03
    fee_bps: float = 6.0
    slippage_bps: float = 2.0


class PaperAgent:
    def __init__(self, allocation: float = 10_000.0, seed: int = 42) -> None:
        self.lock = threading.RLock()
        self.rng = random.Random(seed)
        self.limits = RiskLimits()
        self.allocation = float(allocation)
        self.cash = float(allocation)
        self.position_btc = 0.0
        self.price = 65_000.0
        self.anchor = self.price
        self.fast_ema = self.price
        self.slow_ema = self.price
        self.peak_equity = self.allocation
        self.running = False
        self.halted = False
        self.reason = "Ready — paper funds only"
        self.trades: list[dict[str, Any]] = []
        self.history: list[dict[str, float]] = []
        self._worker: threading.Thread | None = None

    def equity(self) -> float:
        return self.cash + self.position_btc * self.price

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            equity = self.equity()
            return {
                "allocation_usd": round(self.allocation, 2),
                "cash_usd": round(self.cash, 2),
                "equity_usd": round(equity, 2),
                "pnl_usd": round(equity - self.allocation, 2),
                "pnl_pct": round((equity / self.allocation - 1) * 100, 3),
                "price": round(self.price, 2),
                "position_btc": round(self.position_btc, 8),
                "position_notional_usd": round(self.position_btc * self.price, 2),
                "drawdown_pct": round((equity / self.peak_equity - 1) * 100, 3),
                "running": self.running,
                "halted": self.halted,
                "reason": self.reason,
                "limits": asdict(self.limits),
                "trades": self.trades[-12:],
                "history": self.history[-120:],
            }

    def allocate(self, amount: float) -> None:
        if not math.isfinite(amount) or amount < 100 or amount > 10_000_000:
            raise ValueError("Allocation must be between $100 and $10,000,000.")
        with self.lock:
            if self.running or abs(self.position_btc) > 1e-12:
                raise ValueError("Stop the agent and flatten its position before replacing allocation.")
            self.allocation = amount
            self.cash = amount
            self.peak_equity = amount
            self.halted = False
            self.reason = "Ready — paper funds only"
            self.history.clear()
            self.trades.clear()

    def start(self) -> None:
        with self.lock:
            if self.halted:
                raise ValueError("Risk halt is active. Reset allocation after flattening to restart.")
            if self.running:
                return
            self.running = True
            self.reason = "Autotrading simulated BTC/USDT ticks"
            self._worker = threading.Thread(target=self._loop, daemon=True)
            self._worker.start()

    def stop(self, flatten: bool = True) -> None:
        with self.lock:
            self.running = False
            if flatten and abs(self.position_btc) > 1e-12:
                self._trade(-self.position_btc, "manual flatten")
            if not self.halted:
                self.reason = "Stopped — paper position flattened"

    def _loop(self) -> None:
        while True:
            with self.lock:
                if not self.running:
                    return
                self._tick()
            time.sleep(0.25)  # 4 simulated events/sec, intentionally not HFT.

    def _tick(self) -> None:
        # Synthetic BTC-like price process; it is reproducible and not a price feed.
        shock = self.rng.gauss(0, 0.0016)
        reversion = 0.00008 * (self.anchor / self.price - 1)
        self.price = max(500.0, self.price * (1 + shock + reversion))
        self.fast_ema = 0.24 * self.price + 0.76 * self.fast_ema
        self.slow_ema = 0.06 * self.price + 0.94 * self.slow_ema
        equity = self.equity()
        self.peak_equity = max(self.peak_equity, equity)
        drawdown = 1 - equity / self.peak_equity
        loss = 1 - equity / self.allocation
        if drawdown >= self.limits.max_drawdown_fraction or loss >= self.limits.max_loss_fraction:
            self._trade(-self.position_btc, "risk kill switch")
            self.running = False
            self.halted = True
            self.reason = "HALTED: drawdown/loss limit reached; paper position flattened"
        else:
            signal = (self.fast_ema - self.slow_ema) / self.price
            target = max(-self.limits.max_position_fraction,
                         min(self.limits.max_position_fraction, signal * 220))
            target_btc = target * equity / self.price
            delta = target_btc - self.position_btc
            max_delta = self.limits.max_trade_fraction * equity / self.price
            if abs(delta) > max_delta * 0.20:
                self._trade(max(-max_delta, min(max_delta, delta)), "EMA momentum signal")
        self.history.append({"t": time.time(), "equity": round(self.equity(), 2), "price": round(self.price, 2)})

    def _trade(self, quantity: float, rationale: str) -> None:
        if abs(quantity) < 1e-12:
            return
        side = "BUY" if quantity > 0 else "SELL"
        fill = self.price * (1 + (self.limits.slippage_bps / 10_000) * (1 if quantity > 0 else -1))
        notional = abs(quantity) * fill
        fee = notional * self.limits.fee_bps / 10_000
        if quantity > 0 and notional + fee > self.cash:
            quantity = max(0.0, (self.cash - fee) / fill)
            notional = quantity * fill
            fee = notional * self.limits.fee_bps / 10_000
        self.position_btc += quantity
        self.cash -= quantity * fill + fee
        self.trades.append({"time": time.strftime("%H:%M:%S"), "side": side,
                            "btc": round(abs(quantity), 7), "fill": round(fill, 2),
                            "fee": round(fee, 2), "why": rationale})


APP = PaperAgent()
ROOT = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def _send(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/status":
            self._send(APP.snapshot())
        elif self.path in ("/", "/index.html"):
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            self._send({"error": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/allocate": APP.allocate(float(payload["amount"]))
            elif self.path == "/api/start": APP.start()
            elif self.path == "/api/stop": APP.stop()
            else: raise ValueError("Unknown action")
            self._send(APP.snapshot())
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._send({"error": str(exc)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local BTC paper-trading agent")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--allocation", type=float, default=10_000)
    args = parser.parse_args()
    APP.allocate(args.allocation)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Paper agent dashboard: http://127.0.0.1:{args.port}")
    print("No network, exchange keys, live prices, or real orders are used.")
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()


if __name__ == "__main__":
    main()
