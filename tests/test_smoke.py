import importlib

def test_imports():
    modules = [
        "bot.config",
        "bot.logger",
        "bot.exchange",
        "bot.risk",
        "bot.position",
        "bot.strategy",
        "bot.paper",
        "bot.backtest",
        "bot.runner",
        "bot.notifier",
        "bot.metrics",
    ]
    for m in modules:
        importlib.import_module(m)


def test_runner_stub_runs(monkeypatch):
    from bot import runner

    class Args:
        paper = True
        config = "config/config.example.yaml"

    monkeypatch.setattr(runner.argparse, "ArgumentParser", lambda: _Parser(Args))
    runner.main()


class _Parser:
    def __init__(self, args):
        self.args = args
    def add_argument(self, *a, **k):
        pass
    def parse_args(self):
        return self.args
