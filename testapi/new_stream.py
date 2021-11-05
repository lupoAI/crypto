import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import json

config_logging(logging, logging.DEBUG)

with open('../config.json') as config_file:
    config = json.load(config_file)

key = config['reading_api_key']
secret = config['reading_api_secret']

client = Client(key)
logging.info(client.new_isolated_margin_listen_key(symbol="BTCUSDT"))