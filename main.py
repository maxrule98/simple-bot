"""
Trading Bot - Entry Point
Modular cryptocurrency trading bot with configurable strategies
"""
from bot.config import BotConfig, TradingConfig, ExchangeConfig, DatabaseConfig
from bot.scanner import MarketScanner
from bot.strategies.price_change import PriceChangeStrategy


def main():
    print("Trading Bot Starting...")

if __name__ == "__main__":
    main()
