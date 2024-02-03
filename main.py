from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
from pytz import timezone
from dotenv import load_dotenv
import pandas as pd
import os

load_dotenv()

TARGET_VOL = 0.15
TKR = "SPY"
RF_TKR = "SHY"

print("Starting setup")
client = StockHistoricalDataClient(
    api_key=os.getenv("API_KEY"), secret_key=os.getenv("API_SECRET")
)


# get todays date
def subtract_trading_days(start_date, trading_days):
    # Assuming trading days are Monday to Friday
    current_date = start_date
    while trading_days > 0:
        current_date += timedelta(days=-1)
        if current_date.weekday() < 5:  # Monday to Friday are 0 to 4
            trading_days -= 1
    return current_date


today = datetime.now(timezone("America/New_York"))
t_minus22 = subtract_trading_days(today, 25)

print(today, t_minus22)

request = StockBarsRequest(
    symbol_or_symbols=[TKR],
    start=t_minus22,
    end=today,
    timeframe=TimeFrame.Day,
    feed="iex",
)

print("Requesting data...")


result = client.get_stock_bars(request)
# print(result.df)

vwap = pd.DataFrame(result.df["vwap"])
vwap["diff"] = result.df["vwap"].diff(1).shift(-1)
vwap["rm"] = vwap["diff"] / vwap["vwap"]

print(vwap)

# get standard deviation of the vwap

std = vwap["rm"].std()
print(std)

annual_vol = std * (252**0.5)

leverage = TARGET_VOL / annual_vol

print(f"Rolling annual Volatility: {annual_vol:.2f}")
print(f"Target Volatility: {TARGET_VOL:.2f}")
print(f"Leverage: {leverage:.2f}")


# At this point we want to hold SPY with a leverage of our variable leverage
# We can put anything not in SPY into treasuries


trading_client = TradingClient(os.getenv("API_KEY"), os.getenv("API_SECRET"))
latest_quote_request = StockLatestQuoteRequest(symbol_or_symbols=TKR)
latest_quote = client.get_stock_latest_quote(latest_quote_request)
positions = trading_client.get_all_positions()
buying_power = trading_client.get_account().buying_power
cash = trading_client.get_account().cash
print(f"Buying Power: {buying_power}")
print(f"Positions: {positions}")
print(f"Cash: {cash}")


# preparing order data
market_order_data = MarketOrderRequest(
    symbol=TKR, qty=0.0001, side=OrderSide.BUY, time_in_force=TimeInForce.DAY
)

# Market order
# market_order = trading_client.submit_order(order_data=market_order_data)
