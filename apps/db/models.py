from sqlalchemy import BigInteger, ForeignKey, Integer, Enum, Float, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import select
from datetime import datetime
from random import randint as rand

engine = create_async_engine(url="sqlite+aiosqlite:///database.sqlite3", echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'Users'
    Id: Mapped[int] = mapped_column(primary_key=True)
    TgId: Mapped[int] = mapped_column(BigInteger, unique=True)
    ReferrerId: Mapped[int] = mapped_column(BigInteger, ForeignKey('Users.TgId'), nullable=True)

class Staking(Base):
    __tablename__ = 'Stakings'
    Id: Mapped[int] = mapped_column(primary_key=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("Users.Id"))
    Currency: Mapped[str] = mapped_column(String(10))
    Amount: Mapped[float] = mapped_column(Float)
    Period: Mapped[int] = mapped_column(Integer)
    DailyRate: Mapped[float] = mapped_column(Float)
    Status: Mapped[str] = mapped_column(Enum("Pending", "Active", "Completed"), default="Pending")
    StakingAddress: Mapped[str] = mapped_column(String(100))
    StartDate: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # Исправлено

class ReferralReward(Base):
    __tablename__ = 'ReferralRewards'
    Id: Mapped[int] = mapped_column(primary_key=True)
    ReferrerId: Mapped[int] = mapped_column(ForeignKey("Users.Id"))
    RefereeId: Mapped[int] = mapped_column(ForeignKey("Users.Id"))
    StakingId: Mapped[int] = mapped_column(ForeignKey("Stakings.Id"))
    Amount: Mapped[float] = mapped_column(Float)

class PlatformStats(Base):
    __tablename__ = 'PlatformStats'
    Id: Mapped[int] = mapped_column(primary_key=True)
    TotalCapital: Mapped[float] = mapped_column(Float, default=rand(80000, 250000))
    ActiveStakes: Mapped[float] = mapped_column(Float, default=rand(20000, 80000))

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        stats = await session.scalar(select(PlatformStats))
        if not stats:
            stats = PlatformStats(TotalCapital=216000, ActiveStakes=108000)
            session.add(stats)
            await session.commit()