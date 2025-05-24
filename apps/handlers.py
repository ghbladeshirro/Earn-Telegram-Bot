from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import apps.keyboards as kb
import apps.db.requests as rq
import asyncio
from apps.prices import CRYPTO_PRICES, get_min_amount, MIN_USD_AMOUNT
from config import BYBIT_API_KEY, BYBIT_API_SECRET
import requests
import hmac
import hashlib
import time
from datetime import datetime

router = Router()

STAKING_PLANS = {
    "btc": {"7": 1.5, "15": 2.0, "30": 2.5, "45": 3.2}
}
MIN_WITHDRAWAL_USD = 10

class StakingStates(StatesGroup):
    selecting_currency = State()
    selecting_period = State()
    entering_amount = State()
    confirming_send = State()
    awaiting_payment = State()
    confirming_transaction = State()
    withdrawing = State()

async def get_deposit_address(currency, chain="BTC"):
    endpoint = "https://api.bybit.com/v5/asset/deposit/query-address"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    params = f"coin={currency.upper()}&chainType={chain}"
    query_string = f"{timestamp}{BYBIT_API_KEY}{recv_window}{params}"
    signature = hmac.new(BYBIT_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }
    url = f"{endpoint}?{params}"
    
    print(f"Requesting deposit address for {currency.upper()} on {chain}")
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        print(f"API Response: {data}")
        if data["retCode"] == 0:
            chains = data["result"]["chains"]
            for chain_info in chains:
                if chain_info["chainType"] == chain:
                    return chain_info["addressDeposit"]
            return None
        else:
            print(f"API Error: {data['retMsg']} (ErrCode: {data['retCode']})")
            return None
    except Exception as e:
        print(f"Exception in get_deposit_address: {str(e)}")
        return None

async def check_payment(currency, amount, address, timeout=1200):
    endpoint = "https://api.bybit.com/v5/asset/deposit/query-record"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    params = f"coin={currency.upper()}"
    query_string = f"{timestamp}{BYBIT_API_KEY}{recv_window}{params}"
    signature = hmac.new(BYBIT_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }
    url = f"{endpoint}?{params}"
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            print(f"Check Payment Response: {data}")
            if data["retCode"] == 0:
                records = data["result"]["rows"]
                for record in records:
                    if (record["coin"] == currency.upper() and 
                        float(record["amount"]) == amount and 
                        record["toAddress"] == address and 
                        record["status"] == "Success"):
                        return True
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error checking payment: {e}")
            await asyncio.sleep(60)
    return False

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: Command = None):
    referrer_id = int(command.args) if command and command.args and command.args.isdigit() else None
    user = await rq.set_user(message.from_user.id, referrer_id, bot)
    if user is None:
        await message.answer("⚠️ Error initializing user. Please try again.")
        return
    
    stakings = await rq.get_user_stakings(user.Id)
    total_staked = sum([s.Amount * await rq.get_price(s.Currency) for s in stakings]) if stakings else 0
    active_stakings = len([s for s in stakings if s.Status == "Active"]) if stakings else 0
    
    await message.answer(
        f"🌌 *Welcome to Quantum Surge Stake Bot!* 🌌\n\n"
        f"💰 *Stake BTC & Grow Your Wealth!*\n"
        f"🔥 *Why Us?*\n"
        f"  • High-Yield Staking (up to 3.2% APR)\n"
        f"  • Powered by AI & Pro Traders\n"
        f"  • Secure Deposits\n\n"
        f"📊 *Your Stats:*\n"
        f"  • Staked: ${total_staked:.0f} (BTC {total_staked / CRYPTO_PRICES['btc']:,.6f})\n"
        f"  • Active Stakes: {active_stakings}\n\n"
        f"👇 *Let’s Get Started!*",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )

@router.callback_query(F.data == "stake")
async def process_stake(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"₿ *Stake Your BTC!*\n\n"
        f"💡 Stake BTC to earn daily rewards!\n"
        f"🔒 Your funds are securely managed.\n\n"
        f"Choose your asset:",
        reply_markup=kb.currency_buttons,
        parse_mode="Markdown"
    )
    await state.set_state(StakingStates.selecting_currency)
    await callback.answer()

@router.callback_query(F.data.startswith("currency_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1]
    min_amount = await get_min_amount(currency)
    await state.update_data(currency=currency)
    print(f"Currency set to: {currency}")
    await callback.message.edit_text(
        f"₿ *Stake BTC*\n\n"
        f"💰 Min Stake: {min_amount:.6f} BTC (~${MIN_USD_AMOUNT})\n"
        f"📈 Select your staking plan:",
        reply_markup=kb.staking_periods,
        parse_mode="Markdown"
    )
    await state.set_state(StakingStates.selecting_period)
    await callback.answer()

@router.callback_query(F.data.startswith("period_"))
async def process_period(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split("_")[1]
    await state.update_data(period=period)
    print(f"Period set to: {period}")
    await callback.message.edit_text(
        f"💸 *Enter BTC Amount*\n\n"
        f"📝 Type the amount you want to stake (e.g., 0.002 BTC):",
        reply_markup=kb.cancel_button,
        parse_mode="Markdown"
    )
    await state.set_state(StakingStates.entering_amount)
    await callback.answer()

@router.message(StakingStates.entering_amount)
async def process_amount(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    currency = user_data.get("currency")
    period = user_data.get("period")
    
    print(f"Processing amount - Currency: {currency}, Period: {period}")
    
    if not currency or not period:
        await message.answer(
            "❌ *Error:* Something went wrong. Please start over by selecting 'Stake BTC Now!'",
            reply_markup=kb.back_to_main,
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    try:
        amount = float(message.text)
        min_amount = await get_min_amount(currency)
        usd_value = amount * CRYPTO_PRICES.get(currency, 1.0)
        if usd_value < MIN_USD_AMOUNT:
            await message.answer(f"❌ Minimum stake is {min_amount:.6f} BTC (~${MIN_USD_AMOUNT})!")
            return
    except ValueError:
        await message.answer("❌ Please enter a valid amount (e.g., 0.002)!")
        return
    
    rate = STAKING_PLANS[currency][period]
    staking_address = await get_deposit_address(currency)
    if not staking_address:
        await message.answer("⚠️ Error fetching deposit address. Please try again later.")
        return
    
    await state.update_data(amount=amount, address=staking_address, rate=rate)
    
    await message.answer(
        f"💳 *Deposit Your BTC*\n\n"
        f"🌟 *Why Stake?*\n"
        f"  • Earn {rate}% APR over {period} days\n"
        f"  • Projected Yield: {amount * rate * int(period) / 100:.6f} BTC\n\n"
        f"💰 *Amount:* {amount:.6f} BTC (${usd_value:,.2f})\n"
        f"📤 *Send to Wallet:*\n"
        f"`{staking_address}`\n\n"
        f"⚠️ *Important:*\n"
        f"  • Send exactly {amount:.6f} BTC\n"
        f"  • Confirm below after sending\n",
        parse_mode="Markdown",
        reply_markup=kb.confirm_send_button
    )
    await state.set_state(StakingStates.confirming_send)

@router.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    currency = user_data.get("currency")
    period = user_data.get("period")
    amount = user_data.get("amount")
    staking_address = user_data.get("address")
    rate = user_data.get("rate")
    
    if not all([currency, period, amount, staking_address, rate]):
        await callback.message.edit_text(
            "❌ *Error:* Something went wrong. Please start over.",
            reply_markup=kb.back_to_main,
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    user = await rq.get_user(callback.from_user.id)
    staking = await rq.add_staking(user.Id, currency, amount, int(period), rate, staking_address)
    await state.update_data(staking_id=staking.Id)
    
    usd_value = amount * CRYPTO_PRICES.get(currency, 1.0)
    
    await callback.message.edit_text(
        f"💳 *Deposit Confirmed*\n\n"
        f"💰 *Amount:* {amount:.6f} BTC (${usd_value:,.2f})\n"
        f"📅 *Staking Plan:* {period} days at {rate}% APR\n"
        f"📤 *Sent to:* `{staking_address}`\n\n"
        f"🔄 *Status:* Awaiting payment confirmation...\n"
        f"⏳ We’ll check your deposit within 20 min!",
        parse_mode="Markdown",
        reply_markup=kb.cancel_button
    )
    await state.set_state(StakingStates.awaiting_payment)
    
    async def check_payment_task():
        if await check_payment(currency, amount, staking_address):
            await bot.send_message(
                callback.message.chat.id,
                f"✅ *Deposit Confirmed!*\n\n"
                f"💰 {amount:.6f} BTC (${usd_value:,.2f})\n"
                f"📅 Staking for {period} days at {rate}% APR\n"
                f"👉 Confirm to activate your staking!",
                parse_mode="Markdown",
                reply_markup=kb.confirm_button
            )
            await state.set_state(StakingStates.confirming_transaction)
            await rq.update_platform_stats(usd_value)
        else:
            await bot.send_message(
                callback.message.chat.id,
                f"❌ *Deposit Not Received*\n\n"
                f"⏳ We waited 20 min but didn’t detect {amount:.6f} BTC.\n"
                f"📞 Contact support if you sent it!",
                parse_mode="Markdown",
                reply_markup=kb.back_to_main
            )
            await state.clear()
    asyncio.create_task(check_payment_task())
    await callback.answer()

@router.callback_query(F.data == "confirm")
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    staking = await rq.confirm_staking(user_data.get("staking_id"))
    if staking is None:
        await callback.message.edit_text("❌ Staking not found.", reply_markup=kb.back_to_main)
        await state.clear()
        return
    
    usd_value = staking.Amount * await rq.get_price(staking.Currency)
    await callback.message.edit_text(
        f"🎉 *Staking Activated!*\n\n"
        f"💰 *Amount:* {staking.Amount:.6f} BTC (${usd_value:,.2f})\n"
        f"📅 *Period:* {staking.Period} days\n"
        f"📈 *APR:* {staking.DailyRate}%\n"
        f"💸 *Expected Yield:* {staking.Amount * staking.DailyRate * staking.Period / 100:.6f} BTC\n"
        f"✅ *Status:* Active\n\n"
        f"👉 Check progress in 'My Portfolio'!",
        parse_mode="Markdown",
        reply_markup=kb.back_to_main
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "status")
async def process_status(callback: CallbackQuery, state: FSMContext):
    user = await rq.get_user(callback.from_user.id)
    if user is None:
        await callback.message.edit_text("⚠️ User not found. Use - /start", reply_markup=kb.back_to_main)
        return
    
    stakings = await rq.get_user_stakings(user.Id)
    if not stakings:
        await callback.message.edit_text(
            f"💼 *Your Portfolio*\n\n"
            f"📉 *No Active Stakes Yet!*\n"
            f"🚀 Stake BTC now to start earning!",
            reply_markup=kb.portfolio_menu,
            parse_mode="Markdown"
        )
    else:
        total_yield = sum([s.Amount * s.DailyRate * s.Period / 100 for s in stakings if s.Status == "Active"])
        status_text = f"💼 *Your Portfolio*\n\n"
        current_date = datetime.utcnow()
        for i, s in enumerate(stakings, 1):
            usd_value = s.Amount * await rq.get_price(s.Currency)
            start_date = s.StartDate
            days_passed = (current_date - start_date).days if start_date else 0
            days_progress = f"{min(days_passed, s.Period)}/{s.Period}" if start_date else "N/A"
            status_text += (
                f"🔹 *Stake #{i}*\n"
                f"  • Amount: {s.Amount:.6f} BTC (${usd_value:,.2f})\n"
                f"  • Start Date: {start_date.strftime('%Y-%m-%d') if start_date else 'N/A'}\n"
                f"  • Progress: {days_progress} days\n"
                f"  • APR: {s.DailyRate}%\n"
                f"  • Yield: {s.Amount * s.DailyRate * s.Period / 100:.6f} BTC\n"
                f"  • Wallet: `{s.StakingAddress}`\n"
                f"  • Status: {s.Status}\n"
                f"{'─' * 20}\n"
            )
        status_text += f"💸 *Total Yield:* {total_yield:.6f} BTC\n"
        status_text += "🌟 Manage your stakes below!"
        await callback.message.edit_text(status_text, parse_mode="Markdown", reply_markup=kb.portfolio_menu)
    await callback.answer()

@router.callback_query(F.data == "withdraw")
async def process_withdraw(callback: CallbackQuery, state: FSMContext):
    user = await rq.get_user(callback.from_user.id)
    if user is None:
        await callback.message.edit_text("⚠️ User not found. Use - /start", reply_markup=kb.back_to_main)
        return
    
    balance_btc = await rq.get_user_balance(user.Id)
    balance_usd = balance_btc * CRYPTO_PRICES["btc"]
    
    if balance_usd < MIN_WITHDRAWAL_USD:
        await callback.message.edit_text(
            f"💸 *Withdraw Funds*\n\n"
            f"💰 *Available Balance:* {balance_btc:.6f} BTC (${balance_usd:,.2f})\n"
            f"❌ *Insufficient Funds*\n"
            f"  • Minimum withdrawal: ${MIN_WITHDRAWAL_USD}\n"
            f"  • Stake more to unlock withdrawals!",
            parse_mode="Markdown",
            reply_markup=kb.back_to_main
        )
    else:
        await callback.message.edit_text(
            f"💸 *Withdraw Funds*\n\n"
            f"💰 *Available Balance:* {balance_btc:.6f} BTC (${balance_usd:,.2f})\n"
            f"📤 Request withdrawal below:\n"
            f"  • Min: ${MIN_WITHDRAWAL_USD}\n"
            f"  • Processing within 24h",
            parse_mode="Markdown",
            reply_markup=kb.withdraw_button
        )
        await state.set_state(StakingStates.withdrawing)
    await callback.answer()

@router.callback_query(F.data == "request_withdraw")
async def request_withdrawal(callback: CallbackQuery, state: FSMContext):
    user = await rq.get_user(callback.from_user.id)
    balance_btc = await rq.get_user_balance(user.Id)
    balance_usd = balance_btc * CRYPTO_PRICES["btc"]
    
    if balance_usd < MIN_WITHDRAWAL_USD:
        await callback.message.edit_text(
            f"❌ *Withdrawal Failed*\n\n"
            f"💰 *Available Balance:* {balance_btc:.6f} BTC (${balance_usd:,.2f})\n"
            f"⚠️ Minimum withdrawal is ${MIN_WITHDRAWAL_USD}!",
            parse_mode="Markdown",
            reply_markup=kb.back_to_main
        )
    else:
        success = await rq.request_withdrawal(user.Id, balance_btc)
        if success:
            await callback.message.edit_text(
                f"✅ *Withdrawal Requested!*\n\n"
                f"💰 *Amount:* {balance_btc:.6f} BTC (${balance_usd:,.2f})\n"
                f"⏳ *Status:* Processing\n"
                f"📅 You’ll receive funds within 24h!",
                parse_mode="Markdown",
                reply_markup=kb.back_to_main
            )
        else:
            await callback.message.edit_text(
                f"❌ *Withdrawal Failed*\n\n"
                f"⚠️ Insufficient funds or error occurred!",
                parse_mode="Markdown",
                reply_markup=kb.back_to_main
            )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "referral")
async def process_referral(callback: CallbackQuery):
    user = await rq.get_user(callback.from_user.id)
    if user is None:
        await callback.message.edit_text("⚠️ User not found. Use - /start", reply_markup=kb.back_to_main)
        return
    
    referrals = await rq.get_referrals(user.TgId)
    rewards = await rq.get_referral_rewards(user.Id)
    referral_yield = sum(reward.Amount for reward in rewards) if rewards else 0
    
    await callback.message.edit_text(
        f"🎁 *Referral Program*\n\n"
        f"💰 *Earn 1% APR Bonus from Friends!*\n"
        f"🔗 *Your Link:*\n"
        f"`t.me/CoinVirtueBot?start={user.TgId}`\n\n"
        f"👥 *Referrals:* {len(referrals)}\n"
        f"💸 *Bonus Earned:* ${referral_yield:,.2f}\n\n"
        f"📢 Invite more to boost your profits!",
        parse_mode="Markdown",
        reply_markup=kb.back_to_main
    )
    await callback.answer()

@router.callback_query(F.data == "about")
async def process_about(callback: CallbackQuery):
    stats = await rq.get_platform_stats()
    await callback.message.edit_text(
        f"🌐 *Quantum Surge Stake Bot*\n\n"
        f"💡 *Who We Are:*\n"
        f"  • AI-Powered Staking Platform\n"
        f"  • Managed by 10+ Year Trading Experts\n"
        f"  • Secure Deposits\n\n"
        f"📈 *Platform Stats:*\n"
        f"  • Total Capital: ${stats.TotalCapital:,.0f}\n"
        f"  • Active Stakes: ${stats.ActiveStakes:,.0f}\n\n"
        f"🚀 *Join the Future of Wealth!*",
        parse_mode="Markdown",
        reply_markup=kb.back_to_main
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    user = await rq.get_user(callback.from_user.id)
    stats = await rq.get_platform_stats()
    
    stakings = await rq.get_user_stakings(user.Id) if user else []
    total_staked = sum([s.Amount * await rq.get_price(s.Currency) for s in stakings]) if stakings else 0
    active_stakings = len([s for s in stakings if s.Status == "Active"]) if stakings else 0
    
    await state.clear()
    await callback.message.edit_text(
        f"🏠 *Main Menu*\n\n"
        f"🌌 *Quantum Surge Stake Bot*\n"
        f"💰 *Your Stats:*\n"
        f"  • Staked: ${total_staked:.0f} (BTC {total_staked / CRYPTO_PRICES['btc']:,.6f})\n"
        f"  • Active Stakes: {active_stakings}\n\n"
        f"📈 *Platform Stats:*\n"
        f"  • Total Capital: ${stats.TotalCapital:,.0f}\n"
        f"  • Active Stakes: ${stats.ActiveStakes:,.0f}\n\n"
        f"👇 *What’s Next?*",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )
    await callback.answer()