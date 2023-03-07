# Function which listens to a stream from the web and pushes it to a kdb server

import sys
import time
import json
import logging
import threading
import websocket
import requests

class KdbStream:

    def __init__(self, symbol, kdb_server):
        self.kdb_server = kdb_server
        self.symbol = symbol
        self.ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/" + self.symbol.lower() + "@aggTrade",
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever()

    def on_message(self, message):
        data = json.loads(message)
        try:
            self.kdb_server.send(qtemp.qtemp(kdb.qp.qp, kdb.qtype.qtype, kdb.q.q, data))
        except Exception as e:
            print("Error: ", e)

    def on_error(self, error):
        print(error)

    def on_close(self):
        print("### closed ###")

    def on_open(self):
        print("Connection established")
        def run(*args):
            while True:
                time.sleep(1)
            self.ws.close()
            print("thread terminating...")
        self.thread = threading.Thread(target=run)
        self.thread.start()