"""Main entry point for trader application."""

import asyncio

from apps.trader.runtime import main

if __name__ == "__main__":
    asyncio.run(main())