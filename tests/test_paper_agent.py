import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paper_agent import PaperPlatform  # noqa: E402


class PaperPlatformTests(unittest.TestCase):
    def test_monitor_has_cross_asset_universe(self):
        platform = PaperPlatform(1_000)
        classes = {asset["class"] for asset in platform.snapshot()["market"]}
        self.assertEqual(classes, {"Crypto", "FX", "Commodity", "Equity"})

    def test_analysis_and_risk_create_only_long_capped_positions(self):
        platform = PaperPlatform(10_000)
        platform.monitor.tick()
        platform.risk.rebalance(platform.broker, platform.monitor,
                                platform.analysis.analyse(platform.monitor),
                                {asset.symbol: asset.asset_class for asset in platform.assets})
        equity = platform.broker.equity(platform.monitor.prices)
        self.assertTrue(all(qty >= 0 for qty in platform.broker.positions.values()))
        self.assertLessEqual(sum(qty * platform.monitor.prices[symbol] for symbol, qty in platform.broker.positions.items()),
                             platform.limits.max_gross_exposure_fraction * equity + 0.01)

    def test_stop_flattens_paper_positions(self):
        platform = PaperPlatform(10_000)
        platform.broker.positions["BTC-USD"] = .01
        platform.broker.cash -= .01 * platform.monitor.prices["BTC-USD"]
        platform.stop()
        self.assertEqual(platform.broker.positions, {})


if __name__ == "__main__":
    unittest.main()
