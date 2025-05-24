import asyncio
from aiogram import Bot, Dispatcher
from apps.handlers import router
from apps.db.models import async_main
from apps.prices import update_prices_task
from config import BOT_TOKEN, BYBIT_API_KEY, BYBIT_API_SECRET

async def main():
    print("Initializing database...")
    await async_main()
    print("Database initialized.")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    asyncio.create_task(update_prices_task(bot))
    
    print("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        print("Bot on")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Off")
    except Exception as e:
        print(f"Unexpected error: {e}")