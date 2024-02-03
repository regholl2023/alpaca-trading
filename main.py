from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockQuotesRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
import os

load_dotenv()

print("Starting setup")
client = StockHistoricalDataClient(
    api_key=os.getenv("API_KEY"), secret_key=os.getenv("API_SECRET")
)
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 10)
request = StockQuotesRequest(
    symbol_or_symbols=["AAPL"], start=start_date, end=end_date, limit=100
)
print("Requesting data...")
result = client.get_stock_quotes(request)
print(result.df.head())
