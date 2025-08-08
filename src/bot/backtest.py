"""Backtester (stub)."""

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--years", type=int, default=1)
    parser.parse_args()
    print("Backtest placeholder")

if __name__ == "__main__":
    main()
