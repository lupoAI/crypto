import logging
from binance import Client
import json


with open('../config.json') as config_file:
    config = json.load(config_file)

key = config['API_KEY']
secret = config['SECRET_KEY']

client = Client(key)
trades = client.get_aggregate_trades(symbol='BNBBTC')
candles = client.get_historical_klines(symbol='BNBBTC')
historical_trades = client.get_historical_trades()
print("Done")