import json

with open("config.json", "r") as file:
    config = json.load(file)

BOT_TOKEN = config.get("BOT_TOKEN")
BYBIT_API_KEY = config.get("BYBIT_API_KEY")
BYBIT_API_SECRET = config.get("BYBIT_API_SECRET")

if not BOT_TOKEN or not BYBIT_API_KEY or not BYBIT_API_SECRET:
    raise ValueError("Missing BOT_TOKEN, BYBIT_API_KEY, or BYBIT_API_SECRET in config.json")