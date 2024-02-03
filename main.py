from dotenv import load_dotenv
import os

from trader import Trader

load_dotenv()

alpaca = Trader()
alpaca.run()
