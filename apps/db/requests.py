from sqlalchemy import select
from apps.db.models import async_session, User, Staking, ReferralReward, PlatformStats
import random
from datetime import datetime

async def set_user(tg_id, referrer_id=None, bot=None):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.TgId == tg_id))
        if not user:
            if referrer_id == 210:
                referrer_id = None  
                if bot:
                    await bot.send_message(tg_id, f"🎉 Promo code activated! You will get +$15 to your first stake.")
            
            user = User(TgId=tg_id, ReferrerId=referrer_id)
            session.add(user)
            await session.commit()
            user = await session.scalar(select(User).where(User.TgId == tg_id))
            
            if referrer_id:
                referrer = await session.scalar(select(User).where(User.TgId == referrer_id))
                if referrer:
                    await bot.send_message(referrer.TgId, f"🎉 A new referral has registered using your link!")
        return user

async def get_user(tg_id):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.TgId == tg_id))

async def add_staking(user_id, currency, amount, period, daily_rate, address):
    async with async_session() as session:
        staking = Staking(
            UserId=user_id,
            Currency=currency,
            Amount=amount,
            Period=period,
            DailyRate=daily_rate,
            StakingAddress=address,
            StartDate=datetime.utcnow()
        )
        session.add(staking)
        await session.commit()
        return await session.scalar(select(Staking).where(Staking.Id == staking.Id))

async def confirm_staking(staking_id):
    async with async_session() as session:
        staking = await session.scalar(select(Staking).where(Staking.Id == staking_id))
        if staking:
            staking.Status = "Active"
            user = await session.scalar(select(User).where(User.Id == staking.UserId))
            if user and user.ReferrerId:
                referrer = await session.scalar(select(User).where(User.TgId == user.ReferrerId))
                if referrer:
                    reward_amount = staking.Amount * staking.DailyRate * staking.Period / 100 * 0.01
                    reward = ReferralReward(ReferrerId=referrer.Id, RefereeId=user.Id, StakingId=staking.Id, Amount=reward_amount)
                    session.add(reward)
            stats = await session.scalar(select(PlatformStats))
            if stats:
                usd_value = staking.Amount * await get_price(staking.Currency)
                stats.ActiveStakes += usd_value
                stats.TotalCapital += usd_value * 0.02
            await session.commit()
            return staking
        return None

async def get_user_stakings(user_id):
    async with async_session() as session:
        return (await session.execute(select(Staking).where(Staking.UserId == user_id))).scalars().all()

async def get_referrals(user_id):
    async with async_session() as session:
        return (await session.execute(select(User).where(User.ReferrerId == user_id))).scalars().all()

async def get_referral_rewards(user_id):
    async with async_session() as session:
        return (await session.execute(select(ReferralReward).where(ReferralReward.ReferrerId == user_id))).scalars().all()

async def get_platform_stats():
    async with async_session() as session:
        stats = await session.scalar(select(PlatformStats))
        if not stats:
            stats = PlatformStats(TotalCapital=216000, ActiveStakes=108000)
            session.add(stats)
            await session.commit()
        return stats

async def update_platform_stats(amount_usd):
    async with async_session() as session:
        stats = await session.scalar(select(PlatformStats))
        if stats:
            fluctuation = amount_usd * random.uniform(-0.05, 0.05)
            stats.TotalCapital += fluctuation
            await session.commit()

async def get_price(currency):
    from apps.prices import CRYPTO_PRICES
    return CRYPTO_PRICES.get(currency, 1.0)

async def get_user_balance(user_id):
    async with async_session() as session:
        referral_rewards = (await session.execute(select(ReferralReward).where(ReferralReward.ReferrerId == user_id))).scalars().all()
        stakings = (await session.execute(select(Staking).where(Staking.UserId == user_id))).scalars().all()
        
        total_balance = sum([r.Amount for r in referral_rewards]) if referral_rewards else 0
        for staking in stakings:
            if staking.Status == "Active" and staking.StartDate:
                days_passed = (datetime.utcnow() - staking.StartDate).days
                if days_passed >= staking.Period:
                    total_balance += staking.Amount + (staking.Amount * staking.DailyRate * staking.Period / 100)
                    staking.Status = "Completed"
        
        await session.commit()
        return total_balance

async def request_withdrawal(user_id, amount):
    async with async_session() as session:
        balance = await get_user_balance(user_id)
        if balance >= amount:
            print(f"Withdrawal requested: {amount} BTC for user {user_id}")
            return True
        return False