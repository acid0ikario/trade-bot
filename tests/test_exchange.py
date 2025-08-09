import pytest
import ccxt

from bot.exchange import Exchange, ExchangeError
from bot.config import AppConfig, EnvVars


class FakeCCXTBinance:
    def __init__(self, *args, **kwargs):
        self.calls = {
            "fetch_ticker": 0,
            "fetch_ohlcv": 0,
            "fetch_balance": 0,
            "create_order": 0,
            "load_markets": 0,
            "market": 0,
        }
        self._ticker = {"last": 50000.0}
        self._ohlcv = [[1, 10, 11, 9, 10.5, 100]] * 5
        self._balance = {"free": {"USDT": 1234.56}}
        self._orders = []
        self._markets = {
            "BTC/USDT": {
                "symbol": "BTC/USDT",
                "info": {
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.0001", "minQty": "0.0001"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
                        {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    ]
                },
                "precision": {"price": 2, "amount": 6},
                "limits": {"amount": {"min": 0.0001}, "cost": {"min": 5}},
            }
        }
        self._transient_error_once = False

    def load_markets(self):
        self.calls["load_markets"] += 1
        return self._markets

    def market(self, symbol):
        self.calls["market"] += 1
        return self._markets[symbol]

    def fetch_ticker(self, symbol):
        self.calls["fetch_ticker"] += 1
        if self._transient_error_once:
            self._transient_error_once = False
            raise ccxt.NetworkError("transient")
        return self._ticker

    def fetch_ohlcv(self, symbol, timeframe, limit=500):
        self.calls["fetch_ohlcv"] += 1
        return self._ohlcv

    def fetch_balance(self):
        self.calls["fetch_balance"] += 1
        return self._balance

    def create_order(self, symbol, type_, side, amount, price=None, params=None):
        self.calls["create_order"] += 1
        order = {
            "id": f"order_{len(self._orders)+1}",
            "symbol": symbol,
            "type": type_,
            "side": side,
            "amount": amount,
            "price": price,
            "params": params,
        }
        self._orders.append(order)
        return order


@pytest.fixture
def cfg_env():
    cfg = AppConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        max_notional_per_trade_usdt=200,
        symbols_whitelist=["BTC/USDT"],
    )
    env = EnvVars()
    return cfg, env


@pytest.fixture(autouse=True)
def mock_ccxt(monkeypatch):
    fake = FakeCCXTBinance()
    monkeypatch.setattr("ccxt.binance", lambda *a, **k: fake)
    return fake


def test_price_fetch_returns_float(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    price = ex.get_price("BTC/USDT")
    assert isinstance(price, float) and price > 0


def test_missing_price_in_ticker_raises(cfg_env, mock_ccxt):
    cfg, env = cfg_env
    fake = mock_ccxt
    fake._ticker = {}
    ex = Exchange(cfg, env)
    with pytest.raises(ExchangeError):
        ex.get_price("BTC/USDT")


def test_ohlcv_shape(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    candles = ex.fetch_ohlcv("BTC/USDT", "1h", limit=5)
    assert isinstance(candles, list)
    assert len(candles[0]) == 6


def test_balance_returns_numeric(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    bal = ex.get_balance("USDT")
    assert isinstance(bal, float) and bal > 0


def test_buy_over_notional_raises(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    # price 50000, notional cap 200 => qty > 0.004 should raise
    with pytest.raises(ExchangeError):
        ex.create_market_buy("BTC/USDT", qty=0.01)


def test_symbol_not_in_whitelist_raises(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    with pytest.raises(ExchangeError):
        ex.get_price("ETH/USDT")


def test_qty_below_min_raises(cfg_env, monkeypatch):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    monkeypatch.setattr(ex, "get_price", lambda s: 50000.0)
    with pytest.raises(ExchangeError):
        ex.create_market_buy("BTC/USDT", 0.00001)


def test_qty_floored_to_lot_step(cfg_env, monkeypatch):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    # monkeypatch price to avoid cap raising
    monkeypatch.setattr(ex, "get_price", lambda s: 50000.0)
    # qty 0.00123 with step 0.0001 -> 0.0012
    def capture_create(symbol, type_, side, amount, price=None, params=None):
        assert abs(amount - 0.0012) < 1e-9
        return {"id": "1"}
    ex.client.create_order = capture_create  # type: ignore
    ex.create_market_buy("BTC/USDT", 0.00123)


def test_retries_on_transient_error_then_success(cfg_env, mock_ccxt):
    cfg, env = cfg_env
    fake = mock_ccxt
    fake._transient_error_once = True
    ex = Exchange(cfg, env, max_retries=2, backoff_base_delay=0.0)
    price = ex.get_price("BTC/USDT")
    assert isinstance(price, float)


def test_oco_returns_order_ids(cfg_env):
    cfg, env = cfg_env
    ex = Exchange(cfg, env)
    result = ex.place_oco_takeprofit_stoploss(
        "BTC/USDT", qty=0.001, tp_price=60000.0, sl_price=45000.0
    )
    assert "tp_order_id" in result and "sl_order_id" in result
