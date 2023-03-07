import websocket
import pandas as pd
import os
import logging
from itertools import product
from pprint import pprint
import sys
import json

from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s")
LOG_BASE = os.path.join(__file__, "..", "..", "logs")
BASE = "wss://stream.binance.com:9443"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler(log_filename):
    file_handler = TimedRotatingFileHandler(os.path.join(LOG_BASE, log_filename + '.log'), when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name.upper())
    logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler(logger_name))
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger


class KlineStream:

    def __init__(self, logger):
        self.logger = logger
        self.streams = {}

        self.stream_name = None

    def on_open(self, ws):
        print("CONNECTION OPENED")
        self.logger.info("CONNECTION OPENED")

    def on_close(self, ws, mes1, mes2):
        print(mes1, mes2)
        print("CONNECTION CLOSED")
        self.logger.info("CONNECTION CLOSED")

    def on_message(self, ws, message):
        json_message = json.loads(message)
        # pprint(json_message)
        candle = json_message['k']
        is_candle_closed = candle['x']
        if is_candle_closed:
            pprint(candle)

    def on_message_multiple(self, ws, message):
        json_message = json.loads(message)
        pprint(json_message)
        # candle = json_message['k']
        # is_candle_closed = candle['x']
        # if is_candle_closed:
        #     pprint(candle)

    def on_error(self, ws, message):
        print(ws)
        print(message)
        print("ERROR")

    def kline(self, symbol, interval):
        self.stream_name = f"{symbol}@kline_{interval}"
        self.streams[self.stream_name] = pd.DataFrame()
        socket = BASE + f"/ws/{self.stream_name}"
        ws = websocket.WebSocketApp(socket, on_open=self.on_open, on_close=self.on_close, on_message=self.on_message,
                                    on_error=self.on_error)
        ws.run_forever()

    def kline_multiple(self, symbols, intervals):
        socket = BASE + "/stream?streams="
        streams = []
        for s, i in product(symbols, intervals):
            streams += [f"{s}@kline_{i}"]
        socket = socket + '/'.join(streams)
        ws = websocket.WebSocketApp(socket, on_open=self.on_open, on_close=self.on_close,
                                    on_message=self.on_message_multiple, on_error=self.on_error)
        ws.run_forever()


# if __name__ == "__main__":
#     kline("btcusdt", "1m")
    # kline_multiple(["btcusdt"], ['1m', '5m'])
