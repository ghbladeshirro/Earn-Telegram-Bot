from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚀 Stake BTC Now!", callback_data="stake")],
    [InlineKeyboardButton(text="💼 My Portfolio", callback_data="status"), InlineKeyboardButton(text="🎁 Refer & Earn", callback_data="referral")],
    [InlineKeyboardButton(text="ℹ️ About Platform", callback_data="about")]
])

currency_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="₿ Stake BTC", callback_data="currency_btc")],
    [InlineKeyboardButton(text="↩️ Back", callback_data="cancel")]
])

staking_periods = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚡ 7 Days (1.5% APR/day)", callback_data="period_7"), InlineKeyboardButton(text="🔥 15 Days (2.0% APR/day)", callback_data="period_15")],
    [InlineKeyboardButton(text="💎 30 Days (2.5% APR/day)", callback_data="period_30"), InlineKeyboardButton(text="🌟 45 Days (3.2% APR/day)", callback_data="period_45")],
    [InlineKeyboardButton(text="↩️ Back", callback_data="cancel")]
])

confirm_send_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Confirm Send", callback_data="confirm_send"), InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
])

confirm_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Confirm Staking", callback_data="confirm"), InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
])

cancel_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="↩️ Cancel & Back", callback_data="cancel")]
])

back_to_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏠 Back to Main", callback_data="cancel")]
])

portfolio_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💸 Withdraw Funds", callback_data="withdraw")],
    [InlineKeyboardButton(text="🏠 Back to Main", callback_data="cancel")]
])

withdraw_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📤 Request Withdrawal", callback_data="request_withdraw"), InlineKeyboardButton(text="↩️ Back", callback_data="cancel")]
])