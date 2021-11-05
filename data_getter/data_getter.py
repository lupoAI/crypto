import json
import pickle
import datetime
import os

import pandas as pd
import requests

BASE = "https://api.binance.com"
API_PATHS = {"TIME": BASE + "/api/v3/time",
             'DEPTH': BASE + "/api/v3/depth",
             "EXCHANGE_INFO": BASE + "/api/v3/exchangeInfo",
             "RECENT_TRADES": BASE + "/api/v3/trades",
             "HISTORICAL_TRADES": BASE + "/api/v3/historicalTrades",
             "AGGREGATE_TRADES": BASE + "/api/v3/aggTrades",
             "CANDLES": BASE + "/api/v3/klines",
             "AVG_PRICE": BASE + "/api/v3/avgPrice",
             "24H": BASE + "/api/v3/ticker/24hr",
             "PRICE": BASE + "/api/v3/ticker/price",
             "ORDER_BOOK": BASE + "/api/v3/ticker/bookTicker"}

VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]

VALID_INTERVALS_TO_TIME = {"1m": 60 * 1000,
                           "3m": 3 * 60 * 1000,
                           "5m": 5 * 60 * 1000,
                           "15m": 15 * 60 * 1000,
                           "30m": 30 * 60 * 1000,
                           "1h": 60 * 60 * 1000,
                           "2h": 2 * 60 * 60 * 1000,
                           "4h": 4 * 60 * 60 * 1000,
                           "6h": 6 * 60 * 60 * 1000,
                           "8h": 8 * 60 * 60 * 1000,
                           "12h": 12 * 60 * 60 * 1000,
                           "1d": 24 * 60 * 60 * 1000,
                           "3d": 3 * 24 * 60 * 60 * 1000,
                           "1w": 7 * 24 * 60 * 60 * 1000,
                           "1M": 30 * 24 * 60 * 60 * 1000}

CANDLES_HEADERS = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
                   'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']


# #TODO get them dynamically from api
# request
# REQUEST_WEIGHT =


# TODO write tests for these methods

class DataGetter:

    def __init__(self, symbol: str, pandas: bool = False, base_save_path=None):
        self.symbol = symbol
        self.api_paths = API_PATHS
        self.pandas = pandas
        self.base_save_path = base_save_path
        self.used_weight = 0

    def _handle_default_options(self, data, name_file=None):
        if self.pandas:
            res = pd.DataFrame(data)
            if self.base_save_path is not None:
                res.to_csv(os.path.join(self.base_save_path, name_file + ".csv"))
        else:
            res = data
            if self.base_save_path is not None:
                with open(os.path.join(self.base_save_path, name_file + ".p"), 'wb') as handle:
                    pickle.dump(res, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return res

    @staticmethod
    def _get_current_time_string():
        return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    def _handle_request(self, request_type, params=None):
        if request_type not in self.api_paths:
            raise ValueError("Unknown Request Type")
        endpoint = self.api_paths[request_type]
        req = requests.get(endpoint, params=params)
        # TODO add something to use all the extra information that requests returns
        if not req.ok:
            # TODO Change to something different than ValueError
            raise ValueError(req.text, req.status_code)
        # X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)
        self.used_weight += int(req.headers['x-mbx-used-weight'])
        res = json.loads(req.content)
        return res

    def get_server_time(self):
        res = self._handle_request("TIME")
        return res['serverTime']

    def get_exchange_info(self, get_all=False, get_rate_limit=False):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#exchange-information
        """

        params = {} if get_all else {"symbol": self.symbol}
        res = self._handle_request("EXCHANGE_INFO", params=params)
        if get_all:
            res = res["symbols"] if not get_rate_limit else res['rateLimits']
        file_name = "exchangeInfo" if get_all else f"{self.symbol}_exchangeInfo"
        if get_rate_limit:
            file_name = "rateLimits"

        return self._handle_default_options(res, file_name)

    def get_partial_book_depth(self, limit: int):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#order-book
        """
        valid_limits = [5, 10, 20, 50, 100, 500, 1000, 5000]
        if limit not in valid_limits:
            raise ValueError(f"limit should be any of {valid_limits}")

        params = {"symbol": self.symbol, "limit": limit}
        res = self._handle_request("DEPTH", params=params)
        file_name = f"{self.symbol}_depth_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_recent_trades(self, limit: int = 500):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#recent-trades-list
        """
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "limit": limit}
        res = self._handle_request("RECENT_TRADES", params=params)
        file_name = f"{self.symbol}_recentTrades_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_historical_trades(self, limit: int = 500, from_id: str = None):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#old-trade-lookup-market_data
        """
        if from_id is None:
            return self.get_recent_trades(limit=limit)
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "limit": limit, "fromId": from_id}
        res = self._handle_request("HISTORICAL_TRADES", params=params)
        file_name = f"{self.symbol}_historicalTrades_{from_id}"

        return self._handle_default_options(res, file_name)

    def get_aggregate_trade_list(self, from_id=None, start_time=None, end_time=None, limit=500):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#compressed-aggregate-trades-list
        """
        if (start_time is not None) and (end_time is not None):
            if end_time - start_time > 3600000:
                raise ValueError("start_time and end_time cannot be more than 1 hour apart")
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "limit": limit, "fromId": from_id,
                  "startTime": start_time, "endTime": end_time}
        params = {k: v for k, v in params.items() if v is not None}
        res = self._handle_request("AGGREGATE_TRADES", params=params)
        file_name = f"{self.symbol}_aggTrades_{from_id}"
        raise self._handle_default_options(res, file_name)

    def get_candles(self, interval, start_time=None, end_time=None, limit=500):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
        """
        if interval not in VALID_INTERVALS:
            raise ValueError("Invalid Interval")
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "interval": interval, "limit": limit, "startTime": start_time,
                  "endTime": end_time}
        params = {k: v for k, v in params.items() if v is not None}
        res = self._handle_request("CANDLES", params=params)
        if (start_time is not None) and (end_time is not None):
            file_name = f"{self.symbol}_candles_{interval}_{start_time}_{end_time}"
        else:
            file_name = f"{self.symbol}_candles_{interval}_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_avg_price(self):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#current-average-price
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("AVG_PRICE", params=params)
        file_name = f"{self.symbol}_avgPrice_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_24h_stats(self):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#24hr-ticker-price-change-statistics
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("24H", params=params)
        file_name = f"{self.symbol}_24h_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_price(self):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#symbol-price-ticker
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("PRICE", params=params)
        file_name = f"{self.symbol}_price_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)

    def get_order_book(self):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#symbol-order-book-ticker
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("ORDER_BOOK", params=params)
        file_name = f"{self.symbol}_orderBook_{self._get_current_time_string()}"

        return self._handle_default_options(res, file_name)


if __name__ == "__main__":
    import time
    base_save_path = r"G:\crypto\data\exchange"
    data_getter = DataGetter(symbol=None, pandas=True, base_save_path=base_save_path)
    data_getter.get_exchange_info(get_all=True, get_rate_limit=True)
    # base_save_path = r"G:\crypto\data\symbols"
    # btcusdt = DataGetter("NULSBTC", pandas=True, base_save_path=base_save_path)
    # server_time = btcusdt.get_server_time()
    # interval = "1w"
    # interval_time = VALID_INTERVALS_TO_TIME[interval]
    # limit = 1000
    # end_time = int(time.time() * 1000) - 1#server_time
    # start_time = end_time - limit * interval_time
    # for i in range(2):
    #     data = btcusdt.get_candles(interval, start_time, end_time, limit)
    #     end_time = start_time
    #     start_time = end_time - limit * interval_time
