#!/usr/bin/env python3
"""Unit tests for AdvancedStockScanner logic without external API calls."""

import sys
import types
import unittest
from math import isclose
from typing import Iterable, List


def _ensure_numpy_stub() -> None:
    """Provide a minimal numpy replacement with just mean()."""
    numpy_stub = types.ModuleType("numpy")

    def mean(values: Iterable[float]) -> float:
        values_list = list(values)
        return sum(values_list) / len(values_list) if values_list else 0.0

    numpy_stub.mean = mean  # type: ignore[attr-defined]
    sys.modules["numpy"] = numpy_stub


def _ensure_pandas_stub() -> None:
    """Provide a minimal pandas replacement to satisfy imports."""
    pandas_stub = types.ModuleType("pandas")

    class DataFrame:  # pragma: no cover - placeholder
        pass

    pandas_stub.DataFrame = DataFrame  # type: ignore[attr-defined]
    sys.modules["pandas"] = pandas_stub


def _ensure_mock_alpaca_modules() -> None:
    """Provide lightweight stand-ins when the Alpaca SDK is unavailable."""
    if "alpaca.data.historical" in sys.modules:
        return

    alpaca_pkg = types.ModuleType("alpaca")
    data_pkg = types.ModuleType("alpaca.data")
    historical_pkg = types.ModuleType("alpaca.data.historical")
    requests_pkg = types.ModuleType("alpaca.data.requests")
    timeframe_pkg = types.ModuleType("alpaca.data.timeframe")
    models_pkg = types.ModuleType("alpaca.data.models")

    class StockHistoricalDataClient:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):
            pass

    class StockBarsRequest:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):
            pass

    class TimeFrame:  # pragma: no cover - simple stub
        Day = "1Day"

    class Bar:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):
            pass

    historical_pkg.StockHistoricalDataClient = StockHistoricalDataClient
    requests_pkg.StockBarsRequest = StockBarsRequest
    timeframe_pkg.TimeFrame = TimeFrame
    models_pkg.Bar = Bar

    data_pkg.historical = historical_pkg
    data_pkg.requests = requests_pkg
    data_pkg.timeframe = timeframe_pkg
    data_pkg.models = models_pkg
    alpaca_pkg.data = data_pkg

    sys.modules["alpaca"] = alpaca_pkg
    sys.modules["alpaca.data"] = data_pkg
    sys.modules["alpaca.data.historical"] = historical_pkg
    sys.modules["alpaca.data.requests"] = requests_pkg
    sys.modules["alpaca.data.timeframe"] = timeframe_pkg
    sys.modules["alpaca.data.models"] = models_pkg


try:  # pragma: no cover - prefer real dependency when available
    import numpy  # type: ignore # noqa: F401
except ModuleNotFoundError:
    _ensure_numpy_stub()

try:  # pragma: no cover - prefer real dependency when available
    import pandas  # type: ignore # noqa: F401
except ModuleNotFoundError:
    _ensure_pandas_stub()

_ensure_mock_alpaca_modules()

from analyst.breakout.advanced_scanner import AdvancedStockScanner  # type: ignore


class DummyBar:
    """Simple data container mirroring the Alpaca Bar attributes needed for tests."""

    def __init__(self, high: float, low: float, close: float, volume: float) -> None:
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def make_growth_bars(
    start: float,
    growth: float,
    count: int,
    volume: float,
    spread: float,
) -> List[DummyBar]:
    """Create synthetic OHLC bars with controlled growth and volatility."""
    bars: List[DummyBar] = []
    price = start

    for _ in range(count):
        high = price * (1 + spread / 2)
        low = price * (1 - spread / 2)
        bars.append(DummyBar(high, low, price, volume))
        price *= 1 + growth

    return bars


class TestAdvancedStockScanner(unittest.TestCase):
    def setUp(self) -> None:
        # Bypass __init__ to avoid creating a real API client.
        self.scanner = AdvancedStockScanner.__new__(AdvancedStockScanner)

    def test_calculate_adr_percent_requires_minimum_bars(self) -> None:
        bars = make_growth_bars(10.0, 0.0, 10, 1_000_000, 0.04)
        self.assertEqual(self.scanner.calculate_adr_percent(bars), 0.0)

    def test_calculate_adr_percent_returns_average_range(self) -> None:
        bars = [DummyBar(high=120.0, low=100.0, close=110.0, volume=1_000_000) for _ in range(20)]
        adr = self.scanner.calculate_adr_percent(bars)
        self.assertTrue(isclose(adr, 20.0, rel_tol=1e-9))

    def test_calculate_relative_strength_requires_minimum_bars(self) -> None:
        stock = make_growth_bars(50.0, 0.02, 10, 1_000_000, 0.04)
        spy = make_growth_bars(50.0, 0.02, 10, 1_000_000, 0.04)
        self.assertEqual(self.scanner.calculate_relative_strength(stock, spy), 1.0)

    def test_calculate_relative_strength_detects_outperformance(self) -> None:
        stock = make_growth_bars(50.0, 0.03, 25, 1_000_000, 0.04)
        spy = make_growth_bars(50.0, 0.01, 25, 1_000_000, 0.04)
        rs = self.scanner.calculate_relative_strength(stock, spy)
        self.assertGreater(rs, 2.5)

    def test_apply_filters_flags_expected_failures(self) -> None:
        low_price_bars = make_growth_bars(4.0, 0.0, 20, 100_000, 0.02)
        spy_bars = make_growth_bars(100.0, 0.01, 20, 1_000_000, 0.04)

        result = self.scanner.apply_filters("LOW", low_price_bars, spy_bars)

        self.assertFalse(result["passed"])
        self.assertTrue(any("Price" in reason for reason in result["reasons"]))
        self.assertTrue(any("Avg volume" in reason for reason in result["reasons"]))
        self.assertTrue(any("ADR" in reason for reason in result["reasons"]))
        self.assertTrue(any("RS" in reason for reason in result["reasons"]))

    def test_apply_filters_identifies_passing_symbol(self) -> None:
        strong_bars = make_growth_bars(50.0, 0.03, 30, 1_500_000, 0.10)
        spy_bars = make_growth_bars(50.0, 0.01, 30, 1_000_000, 0.04)

        result = self.scanner.apply_filters("STRONG", strong_bars, spy_bars)

        self.assertTrue(result["passed"])
        self.assertEqual(result["reasons"], [])
        self.assertGreater(result["adr_percent"], 5.0)
        self.assertGreater(result["relative_strength"], 1.0)
        self.assertGreater(result["avg_volume"], 500000)


if __name__ == "__main__":
    unittest.main()
