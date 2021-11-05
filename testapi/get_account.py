import logging
from binance.spot import Spot as Client
from binance.lib.utils import config_logging
import json

config_logging(logging, logging.DEBUG)

with open('../config.json') as config_file:
    config = json.load(config_file)

key = config['test_api_key']
secret = config['test_secret_key']

client = Client(key, secret, base_url="https://testnet.binance.vision")
logging.info(client.account(recvWindow=6000))
