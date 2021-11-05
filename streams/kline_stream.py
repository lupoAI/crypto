import websocket
import logging
from itertools import product
from pprint import pprint
import sys
import json

from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s")
LOG_FILE = "../logs/test_stream.log"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger


my_logger = get_logger("STREAM")

BASE = "wss://stream.binance.com:9443"


def on_open(ws):
    print("CONNECTION OPENED")
    my_logger.info("CONNECTION OPENED")


def on_close(ws):
    print("CONNECTION CLOSED")
    my_logger.info("CONNECTION CLOSED")


def on_message(ws, message):
    json_message = json.loads(message)
    # pprint(json_message)
    candle = json_message['k']
    is_candle_closed = candle['x']
    if is_candle_closed:
        pprint(candle)


def on_message_multiple(ws, message):
    json_message = json.loads(message)
    pprint(json_message)
    # candle = json_message['k']
    # is_candle_closed = candle['x']
    # if is_candle_closed:
    #     pprint(candle)


def on_error(ws, message):
    print(ws)
    print(message)
    print("ERROR")


def kline(symbol, interval):
    socket = BASE + f"/ws/{symbol}@kline_{interval}"
    ws = websocket.WebSocketApp(socket, on_open=on_open, on_close=on_close, on_message=on_message, on_error=on_error)
    ws.run_forever()


def kline_multiple(symbols, intervals):
    socket = BASE + "/stream?streams="
    streams = []
    for s, i in product(symbols, intervals):
        streams += [f"{s}@kline_{i}"]
    socket = socket + '/'.join(streams)
    ws = websocket.WebSocketApp(socket, on_open=on_open, on_close=on_close, on_message=on_message_multiple,
                                on_error=on_error)
    ws.run_forever()


if __name__ == "__main__":
    kline("btcusdt", "1m")
    # kline_multiple(["btcusdt"], ['1m', '5m'])
