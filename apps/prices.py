import requests
import asyncio
from aiogram import Bot
import apps.db.requests as rq
import random

CRYPTO_PRICES = {"btc": 50000, "eth": 3000, "usdt": 1, "usdc": 1, "sol": 150}
MIN_USD_AMOUNT = 15

async def update_prices(bot: Bot):
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,usd-coin,solana&vs_currencies=usd"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                CRYPTO_PRICES["btc"] = data["bitcoin"]["usd"]
                CRYPTO_PRICES["eth"] = data["ethereum"]["usd"]
                CRYPTO_PRICES["usdt"] = data["tether"]["usd"]
                CRYPTO_PRICES["usdc"] = data["usd-coin"]["usd"]
                CRYPTO_PRICES["sol"] = data["solana"]["usd"]
                print("Prices updated:", CRYPTO_PRICES)
            else:
                print(f"Error fetching prices: {response.status_code}")
        except Exception as e:
            print(f"Price update error: {e}")
        await asyncio.sleep(300)

async def simulate_trading(bot: Bot):
    while True:
        stats = await rq.get_platform_stats()
        if stats:
            fluctuation = stats.TotalCapital * random.uniform(-3, 3)
            await rq.update_platform_stats(fluctuation)
            print(f"Capital updated: ${stats.TotalCapital:,.2f}")
        await asyncio.sleep(600)  

async def get_min_amount(currency):
    price = CRYPTO_PRICES.get(currency, 1.0)
    return MIN_USD_AMOUNT / price

async def update_prices_task(bot: Bot):
    asyncio.create_task(update_prices(bot))
    asyncio.create_task(simulate_trading(bot))