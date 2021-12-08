import datetime
import datetime as dt
import json
import os
import pickle
import traceback

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

from constants import VALID_INTERVALS, VALID_INTERVALS_TO_TIME, CANDLES_HEADERS

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
INTERVAL_TO_BUCKETS = {"1m": 1,
                       "3m": 1,
                       "5m": 1,
                       "15m": 5,
                       "30m": 5,
                       "1h": 10,
                       "2h": 10,
                       "4h": 10,
                       "6h": 10,
                       "8h": 10,
                       "12h": 10,
                       "1d": 10,
                       "3d": 10,
                       "1w": 10,
                       "1M": 10}
START_HIST = '31/12/2009'

# #TODO get them dynamically from api
# request
# REQUEST_WEIGHT =


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
            if (self.base_save_path is not None) and (name_file is not None):
                res.to_csv(os.path.join(self.base_save_path, name_file + ".csv"), header=False, index=False)
        else:
            res = data
            if (self.base_save_path is not None) and (name_file is not None):
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

    def get_exchange_info(self, get_all=False, get_rate_limit=False, save=True):
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
        file_name = file_name if save else None

        return self._handle_default_options(res, file_name)

    def get_partial_book_depth(self, limit: int, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#order-book
        """
        valid_limits = [5, 10, 20, 50, 100, 500, 1000, 5000]
        if limit not in valid_limits:
            raise ValueError(f"limit should be any of {valid_limits}")

        params = {"symbol": self.symbol, "limit": limit}
        res = self._handle_request("DEPTH", params=params)
        file_name = f"{self.symbol}_depth_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_recent_trades(self, limit: int = 500, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#recent-trades-list
        """
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "limit": limit}
        res = self._handle_request("RECENT_TRADES", params=params)
        file_name = f"{self.symbol}_recentTrades_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_historical_trades(self, limit: int = 500, from_id: str = None, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#old-trade-lookup-market_data
        """
        if from_id is None:
            return self.get_recent_trades(limit=limit)
        if limit > 1000:
            raise ValueError(f"limit should be less or equal to 1000")

        params = {"symbol": self.symbol, "limit": limit, "fromId": from_id}
        res = self._handle_request("HISTORICAL_TRADES", params=params)
        file_name = f"{self.symbol}_historicalTrades_{from_id}" if save else None

        return self._handle_default_options(res, file_name)

    def get_aggregate_trade_list(self, from_id=None, start_time=None, end_time=None, limit=500, save=True):
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
        file_name = f"{self.symbol}_aggTrades_{from_id}" if save else None
        raise self._handle_default_options(res, file_name)

    def get_candles(self, interval, start_time=None, end_time=None, limit=500, save=True):
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

        file_name = file_name if save else None

        return self._handle_default_options(res, file_name)

    def get_avg_price(self, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#current-average-price
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("AVG_PRICE", params=params)
        file_name = f"{self.symbol}_avgPrice_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_24h_stats(self, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#24hr-ticker-price-change-statistics
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("24H", params=params)
        file_name = f"{self.symbol}_24h_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_price(self, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#symbol-price-ticker
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("PRICE", params=params)
        file_name = f"{self.symbol}_price_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_order_book(self, save=True):
        """
        refer to https://binance-docs.github.io/apidocs/spot/en/#symbol-order-book-ticker
        """
        params = {"symbol": self.symbol}
        res = self._handle_request("ORDER_BOOK", params=params)
        file_name = f"{self.symbol}_orderBook_{self._get_current_time_string()}" if save else None

        return self._handle_default_options(res, file_name)

    def get_historical_candles(self, start_date, interval):
        date_range = pd.date_range(start=start_date, end=dt.date.today(), freq='Y')
        if date_range[-1].date() != dt.date.today():
            date_range = date_range.append(pd.Index([pd.Timestamp.now()]))
        date_range = date_range + dt.timedelta(days=1)
        date_range_str = date_range.strftime("%Y")[::-1]
        date_range_milliseconds = list(map(int, (date_range.view('<i8') / 1e6)))[::-1]
        interval_milliseconds = VALID_INTERVALS_TO_TIME[interval]
        interval_bucket = INTERVAL_TO_BUCKETS[interval]

        i = 0
        last = False
        while True:

            start_ind = min(len(date_range_str) - 1, interval_bucket * (i + 1))
            if start_ind == len(date_range_str):
                last = True

            start_date_str = date_range_str[start_ind]
            end_date_str = date_range_str[interval_bucket * i]

            file_name = f"{self.symbol}_{interval}_{start_date_str}_{end_date_str}"
            file_path = os.path.join(self.base_save_path, file_name + ".csv")
            file_path_inc = os.path.join(self.base_save_path, file_name + "_inc.csv")
            if os.path.exists(file_path) or os.path.exists(file_path_inc):
                if last:
                    break
                i += 1
                continue

            start_date_m = date_range_milliseconds[start_ind]
            end_date_m = date_range_milliseconds[interval_bucket * i]

            expected_rows = (end_date_m - start_date_m) / interval_milliseconds

            range_m = np.arange(start_date_m, end_date_m, interval_milliseconds * 1000)
            if len(range_m) == 0:
                break
            elif len(range_m) == 1:
                range_start = [start_date_m]
                range_end = [end_date_m]
            else:
                range_start = range_m[:-1]
                range_end = range_m[1:] - 1
                range_start = np.append(range_start, range_m[-1])
                range_end = np.append(range_end, end_date_m)

            data = pd.DataFrame()

            start_end_range = zip(range_start, range_end)
            exceptions = 0
            for st, nd in tqdm(start_end_range):
                try:
                    temp = self.get_candles(interval, start_time=st, end_time=nd, limit=1000, save=False)
                    data = data.append(temp)
                except Exception:
                    # TODO implement better exception handling
                    print(f"error for {st} and {nd}")
                    print(traceback.format_exc())
                    exceptions += 1
                    if exceptions == 10:
                        raise BinanceRequestException

            if len(data) == 0:
                break

            start_time_data = data.iloc[0, 0]

            # TODO maybe implement fix that changes start year in file path
            # start_time_year = pd.to_datetime(data.loc[0,0] * 1e6).strftime("%Y")
            # if start_time_year != start_date_str:

            if i == 0:
                file_name += "_inc"
                file_path = os.path.join(self.base_save_path, file_name + ".csv")

            data.to_csv(file_path, header=CANDLES_HEADERS, index=False)

            # We break the loop if we have less rows than expected and we
            if last or (len(data) < 0.1 * expected_rows) or (
                    range_start[0] + 10 * interval_milliseconds < start_time_data):
                print(f"finished for symbol {self.symbol} and interval {interval}")
                break

            i += 1

    def get_all_historical_candles(self, start_date):
        for interval in VALID_INTERVALS[::-1]:
            self.get_historical_candles(start_date, interval)
            print(f"gotten {interval}")


class BinanceRequestException(Exception):
    pass


if __name__ == "__main__":
    coins_to_get = ["ETHUSDT", "BUSDUSDT", "BTCUSDT"]
    base_save_path = "/Users/tanisha/Desktop/crypto/data/symbols"
    for coin in coins_to_get:
        c = DataGetter(coin, pandas=True, base_save_path=base_save_path)
        c.get_all_historical_candles(START_HIST)