import os
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
)
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from datetime import timedelta, datetime
from pytz import timezone
import pandas as pd
import numpy as np

TARGET_VOL = 0.15
TKR = "SPY"
RF_TKR = "SHY"
MARGIN_MULTIPLIER = 2


class Trader:
    def __init__(self):
        self.historical_client = StockHistoricalDataClient(
            api_key=os.getenv("API_KEY"), secret_key=os.getenv("API_SECRET")
        )
        self.trading_client = TradingClient(
            os.getenv("API_KEY"), os.getenv("API_SECRET")
        )

    def subtract_trading_days(self, start_date, trading_days):
        # Assuming trading days are Monday to Friday
        current_date = start_date
        while trading_days > 0:
            current_date += timedelta(days=-1)
            if current_date.weekday() < 5:  # Monday to Friday are 0 to 4
                trading_days -= 1
        return current_date

    def run(self):
        print("Starting setup")
        today = datetime.now(timezone("America/New_York"))
        t_minus22 = self.subtract_trading_days(today, 25)
        request = StockBarsRequest(
            symbol_or_symbols=[TKR],
            start=t_minus22,
            end=today,
            timeframe=TimeFrame.Day,
            feed="iex",
        )
        result = self.historical_client.get_stock_bars(request)
        vwap = pd.DataFrame(result.df["vwap"])
        vwap["diff"] = result.df["vwap"].diff(1).shift(-1)
        vwap["rm"] = vwap["diff"] / vwap["vwap"]
        std = vwap["rm"].std()
        annual_vol = std * (252**0.5)
        leverage = TARGET_VOL / annual_vol
        print(f"Rolling annual Volatility: {annual_vol:.2f}")
        print(f"Target Volatility: {TARGET_VOL:.2f}")
        print(f"Leverage: {leverage:.2f}")
        latest_quote_request = StockLatestQuoteRequest(symbol_or_symbols=TKR)
        latest_quote = self.historical_client.get_stock_latest_quote(
            latest_quote_request
        )[TKR]
        positions = self.trading_client.get_all_positions()
        buying_power = float(self.trading_client.get_account().buying_power)
        cash = self.trading_client.get_account().cash
        print(f"Buying Power: {buying_power}")
        print(f"Positions: {positions}")
        print(f"Cash: {cash}")
        # Get current positions for SPY and SHY
        tkr_position = [x for x in positions if x.symbol == TKR]
        rf_position = [x for x in positions if x.symbol == RF_TKR]

        tkr_position_value = 0
        if len(tkr_position) > 0:
            tkr_position_value = tkr_position[0].market_value
        rf_position_value = 0
        if len(rf_position) > 0:
            rf_position_value = rf_position[0].market_value

        # rebalance portfolio
        if leverage > 1:
            # If leverage is more than 1 hold no treasuries only SPY
            # amount we want in spy is acount value * leverage
            new_tkr_position_value = buying_power / MARGIN_MULTIPLIER * leverage
            new_rf_position_value = 0
        else:
            # Leverage less than 1 mix between treasuries and SPY
            new_tkr_position_value = buying_power / MARGIN_MULTIPLIER * leverage
            new_rf_position_value = buying_power / MARGIN_MULTIPLIER * (1 - leverage)

        change_in_tkr = new_tkr_position_value - tkr_position_value
        change_in_rf = new_rf_position_value - rf_position_value

        self.rebalance(TKR, change_in_tkr, latest_quote)
        self.rebalance(RF_TKR, change_in_rf, latest_quote)

    def rebalance(self, ticker: str, position_change, latest_quote):
        if position_change > 0:
            market_order_data = MarketOrderRequest(
                symbol=ticker,
                notional=np.round(position_change, 2),
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            print(f"Buying {np.round(position_change, 2)} of {ticker}")
            _ = self.trading_client.submit_order(order_data=market_order_data)
        elif position_change < 0:
            market_order_data = MarketOrderRequest(
                symbol=ticker,
                notional=np.round(position_change, 2),
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            print(f"Selling {np.round(position_change, 2)} of {ticker}")
            _ = self.trading_client.submit_order(order_data=market_order_data)
