#!/usr/bin/env python3
"""Local, multi-asset paper-trading platform; no brokers, keys, or live orders."""
from __future__ import annotations
import argparse, json, math, random, threading, time
from collections import deque
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Asset:
    symbol: str; name: str; asset_class: str; price: float; volatility: float

UNIVERSE = (Asset("BTC-USD","Bitcoin","Crypto",65000,.0018), Asset("ETH-USD","Ethereum","Crypto",3200,.0022), Asset("SOL-USD","Solana","Crypto",145,.003), Asset("EURUSD","Euro / US Dollar","FX",1.08,.00025), Asset("GBPUSD","Pound / US Dollar","FX",1.27,.0003), Asset("USDJPY","US Dollar / Yen","FX",150,.0003), Asset("XAUUSD","Gold","Commodity",2350,.00065), Asset("XAGUSD","Silver","Commodity",30,.0011), Asset("WTI","WTI Crude Oil","Commodity",77,.0012), Asset("SPY","S&P 500 ETF","Equity",520,.00055), Asset("QQQ","Nasdaq 100 ETF","Equity",450,.00075), Asset("AAPL","Apple","Equity",190,.0011))

@dataclass
class RiskLimits:
    max_single_asset_fraction: float=.12; max_gross_exposure_fraction: float=.55; max_trade_fraction: float=.04
    max_drawdown_fraction: float=.05; max_loss_fraction: float=.03; max_class_fraction: float=.30; fee_bps: float=6; slippage_bps: float=2

@dataclass
class Signal:
    symbol: str; action: str; score: float; confidence: float; target_fraction: float; rationale: str; model_version: str

class MarketMonitorAgent:
    """Tracks synthetic market state; never accesses balances or submits trades."""
    name="Market Monitor"
    def __init__(self, assets: tuple[Asset,...], rng: random.Random):
        self.assets,self.rng=assets,rng; self.prices={a.symbol:a.price for a in assets}; self.fast=dict(self.prices); self.slow=dict(self.prices)
        self.avg_gain={a.symbol:0.0 for a in assets}; self.avg_loss={a.symbol:0.0 for a in assets}; self.history={a.symbol:deque([a.price],maxlen=96) for a in assets}
    def tick(self):
        for a in self.assets:
            previous=self.prices[a.symbol]; p=max(a.price*.02,previous*(1+self.rng.gauss(0,a.volatility)+.00004*(a.price/previous-1))); self.prices[a.symbol]=p
            self.fast[a.symbol]=.22*p+.78*self.fast[a.symbol]; self.slow[a.symbol]=.055*p+.945*self.slow[a.symbol]
            change=(p/previous-1)*100; self.avg_gain[a.symbol]=.14*max(change,0)+.86*self.avg_gain[a.symbol]; self.avg_loss[a.symbol]=.14*max(-change,0)+.86*self.avg_loss[a.symbol]; self.history[a.symbol].append(p)
    def state(self): return [{"symbol":a.symbol,"name":a.name,"class":a.asset_class,"price":round(self.prices[a.symbol],4),"trend":round((self.fast[a.symbol]/self.slow[a.symbol]-1)*10000,2)} for a in self.assets]
    def candles(self):
        result={}
        for symbol, values in self.history.items():
            points=list(values); bars=[]
            for i in range(0,len(points)-3,4):
                group=points[i:i+4]; bars.append({"open":round(group[0],4),"high":round(max(group),4),"low":round(min(group),4),"close":round(group[-1],4)})
            result[symbol]=bars[-20:]
        return result

class AssetAnalysisAgent:
    """Analyzes every watched asset; outputs explainable proposals, not orders."""
    name="Algorithm Research"
    model_version="ema-rsi-v1-paper"
    def analyse(self, monitor: MarketMonitorAgent):
        result=[]
        for a in monitor.assets:
            momentum=(monitor.fast[a.symbol]/monitor.slow[a.symbol]-1)*600
            rsi=100 if monitor.avg_loss[a.symbol]==0 else 100-100/(1+monitor.avg_gain[a.symbol]/monitor.avg_loss[a.symbol])
            score=max(-1,min(1,.72*momentum+.28*((rsi-50)/50))); confidence=min(.8,abs(score)*.75+.08)
            action="BUY" if score>.12 else "SELL" if score<-.12 else "HOLD"
            target=score*.08*confidence if action=="BUY" else 0.0
            result.append(Signal(a.symbol,action,score,confidence,target,f"EMA momentum + RSI={rsi:.1f}; synthetic data only",self.model_version))
        return result

class PaperBroker:
    """Only paper execution is implemented. It cannot send real orders."""
    def __init__(self, allocation:float): self.cash=allocation; self.positions={}; self.avg_cost={}; self.realized={}; self.trades=[]
    def equity(self, prices): return self.cash+sum(q*prices[s] for s,q in self.positions.items())
    def trade(self,symbol,quantity,mid,limits,why):
        if abs(quantity)<1e-12:return
        fill=mid*(1+limits.slippage_bps/10000*(1 if quantity>0 else -1)); notional=abs(quantity)*fill; fee=notional*limits.fee_bps/10000
        if quantity>0 and notional+fee>self.cash: quantity=max(0,(self.cash-fee)/fill); notional=quantity*fill; fee=notional*limits.fee_bps/10000
        if quantity<0 and -quantity>self.positions.get(symbol,0): quantity=-self.positions.get(symbol,0); notional=abs(quantity)*fill; fee=notional*limits.fee_bps/10000
        if abs(quantity)<1e-12:return
        before=self.positions.get(symbol,0.0)
        if quantity>0:
            self.avg_cost[symbol]=((before*self.avg_cost.get(symbol,0.0))+quantity*fill+fee)/(before+quantity)
        else:
            closed=min(before,-quantity); self.realized[symbol]=self.realized.get(symbol,0.0)+closed*(fill-self.avg_cost.get(symbol,fill))-fee
        self.positions[symbol]=before+quantity
        if abs(self.positions[symbol])<1e-10:
            self.positions.pop(symbol); self.avg_cost.pop(symbol,None)
        self.cash-=quantity*fill+fee; self.trades.append({"time":time.strftime("%H:%M:%S"),"symbol":symbol,"side":"BUY" if quantity>0 else "SELL","quantity":round(abs(quantity),7),"fill":round(fill,4),"fee":round(fee,2),"why":why})
    def flatten(self,prices,limits,why):
        for s,q in list(self.positions.items()): self.trade(s,-q,prices[s],limits,why)
    def pnl_by_asset(self, prices):
        symbols=set(prices) | set(self.realized) | set(self.positions)
        return [{"symbol":s,"realized":round(self.realized.get(s,0.0),2),"unrealized":round(self.positions.get(s,0.0)*(prices[s]-self.avg_cost.get(s,prices[s])),2),"total":round(self.realized.get(s,0.0)+self.positions.get(s,0.0)*(prices[s]-self.avg_cost.get(s,prices[s])),2)} for s in sorted(symbols)]

class PortfolioRiskAgent:
    """Independent risk gate and sole agent permitted to request paper execution."""
    name="Portfolio & Risk"
    def __init__(self,limits):self.limits=limits
    def rebalance(self,broker,monitor,signals,classes):
        prices,equity=monitor.prices,broker.equity(monitor.prices); gross=sum(q*prices[s] for s,q in broker.positions.items()); class_value={}
        for s,q in broker.positions.items(): class_value[classes[s]]=class_value.get(classes[s],0)+q*prices[s]
        for signal in signals:
            target=min(max(0,signal.target_fraction*equity),self.limits.max_single_asset_fraction*equity); current=broker.positions.get(signal.symbol,0)*prices[signal.symbol]; delta=target-current; cls=classes[signal.symbol]
            if delta>0: delta=min(delta,max(0,self.limits.max_class_fraction*equity-class_value.get(cls,0)),max(0,self.limits.max_gross_exposure_fraction*equity-gross))
            delta=max(-self.limits.max_trade_fraction*equity,min(self.limits.max_trade_fraction*equity,delta))
            if abs(delta)>=max(5,equity*.001):
                broker.trade(signal.symbol,delta/prices[signal.symbol],prices[signal.symbol],self.limits,signal.rationale); gross+=delta; class_value[cls]=class_value.get(cls,0)+delta

class PaperPlatform:
    def __init__(self,allocation=10000,seed=42):
        self.lock,self.rng=threading.RLock(),random.Random(seed); self.assets,self.limits=UNIVERSE,RiskLimits(); self.monitor=MarketMonitorAgent(self.assets,self.rng); self.analysis=AssetAnalysisAgent(); self.risk=PortfolioRiskAgent(self.limits); self.allocation=float(allocation); self.broker=PaperBroker(self.allocation); self.peak_equity=self.allocation; self.running=False; self.halted=False; self.reason="Ready — paper money only"; self.history=[]
    def allocate(self,amount):
        if not math.isfinite(amount) or not 100<=amount<=10000000:raise ValueError("Allocation must be between $100 and $10,000,000.")
        with self.lock:
            if self.running or self.broker.positions:raise ValueError("Stop and flatten before replacing the allocation.")
            self.allocation=self.peak_equity=amount; self.broker=PaperBroker(amount); self.history=[]; self.halted=False; self.reason="Ready — paper money only"
    def start(self):
        with self.lock:
            if self.halted:raise ValueError("Risk halt active. Reset allocation to re-arm.")
            if self.running:return
            self.running=True; self.reason="Paper agents monitoring and rebalancing"; threading.Thread(target=self._loop,daemon=True).start()
    def stop(self):
        with self.lock:
            self.running=False; self.broker.flatten(self.monitor.prices,self.limits,"manual flatten")
            if not self.halted:self.reason="Stopped — all paper positions flattened"
    def _loop(self):
        while True:
            with self.lock:
                if not self.running:return
                self.monitor.tick(); equity=self.broker.equity(self.monitor.prices); self.peak_equity=max(self.peak_equity,equity); drawdown=1-equity/self.peak_equity; loss=1-equity/self.allocation
                if drawdown>=self.limits.max_drawdown_fraction or loss>=self.limits.max_loss_fraction:
                    self.broker.flatten(self.monitor.prices,self.limits,"risk kill switch"); self.running=False; self.halted=True; self.reason="HALTED: drawdown/loss limit reached; paper portfolio flattened"
                else:self.risk.rebalance(self.broker,self.monitor,self.analysis.analyse(self.monitor),{a.symbol:a.asset_class for a in self.assets})
                self.history.append({"t":time.time(),"equity":round(self.broker.equity(self.monitor.prices),2)})
            time.sleep(.25)
    def snapshot(self):
        with self.lock:
            equity=self.broker.equity(self.monitor.prices)
            positions=[{"symbol":s,"quantity":round(q,7),"notional":round(q*self.monitor.prices[s],2)} for s,q in self.broker.positions.items()]
            signals=[asdict(signal) for signal in self.analysis.analyse(self.monitor)]
            pnl=round(equity-self.allocation,2)
            return {"allocation_usd":round(self.allocation,2),"cash_usd":round(self.broker.cash,2),"equity_usd":round(equity,2),"pnl_usd":pnl,"pnl_pct":round((equity/self.allocation-1)*100,3),"drawdown_pct":round((equity/self.peak_equity-1)*100,3),"running":self.running,"halted":self.halted,"reason":self.reason,"limits":asdict(self.limits),"profile":{"label":"Paper Portfolio","mode":"SIMULATED · NO REAL FUNDS","allocation":round(self.allocation,2),"equity":round(equity,2),"total_pnl":pnl},"agents":[{"name":self.monitor.name,"job":"Tracks 12 simulated symbols; no portfolio access"},{"name":self.analysis.name,"job":"Sends BUY/SELL/HOLD proposals; cannot submit orders"},{"name":self.risk.name,"job":"Approves, clips, or rejects simulated orders"}],"market":self.monitor.state(),"candles":self.monitor.candles(),"signals":signals,"positions":positions,"asset_pnl":self.broker.pnl_by_asset(self.monitor.prices),"trades":self.broker.trades[-16:],"history":self.history[-120:]}

APP,ROOT=PaperPlatform(),Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_json(self,data,status=200):
        payload=json.dumps(data).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def do_GET(self):
        if self.path=="/api/status":self.send_json(APP.snapshot())
        elif self.path in ("/","/index.html"):
            body=(ROOT/"index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        else:self.send_json({"error":"Not found"},404)
    def do_POST(self):
        try:
            body=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
            if self.path=="/api/allocate":APP.allocate(float(body["amount"]))
            elif self.path=="/api/start":APP.start()
            elif self.path=="/api/stop":APP.stop()
            else:raise ValueError("Unknown action")
            self.send_json(APP.snapshot())
        except (ValueError,KeyError,json.JSONDecodeError) as exc:self.send_json({"error":str(exc)},400)
def main():
    parser=argparse.ArgumentParser(description="Local multi-asset paper-trading platform"); parser.add_argument("--port",type=int,default=8787); parser.add_argument("--allocation",type=float,default=10000); args=parser.parse_args(); APP.allocate(args.allocation); print(f"Dashboard: http://127.0.0.1:{args.port}",flush=True); print("No network, broker, exchange credentials, live prices, or real orders.",flush=True); ThreadingHTTPServer(("127.0.0.1",args.port),Handler).serve_forever()
if __name__=="__main__":main()
