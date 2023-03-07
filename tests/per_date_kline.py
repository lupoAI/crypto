import logging
from binance import Client
import json


with open('../config.json') as config_file:
    config = json.load(config_file)

key = config['API_KEY']
# secret = config['SECRET_KEY']

client = Client(key)

info = client.get_exchange_info()

symbols = [symbol['symbol'] for symbol in info['symbols']]


print(info)