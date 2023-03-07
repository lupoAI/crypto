import concurrent.futures
import glob
import json
import os
import pickle
import threading
import time
import traceback
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests

from constants import VALID_INTERVALS, VALID_INTERVALS_TO_TIME, CANDLES_HEADER, CANDLES_HEADER_TYPES, \
    CANDLES_HEADER_TYPES_AN

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
INTERVAL_TO_BUCKETS = {"1m": 6,
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
START_HIST = '31/12/2016'
THREADS = 10
BUFFER = 4
REQUESTS_PER_MINUTE = 1200


# #TODO get them dynamically from api
# TODO modify all print into logs
# request
# REQUEST_WEIGHT =

class DataGetterSymbol:

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

    def _get_url(self, request_type, params=None):
        if request_type not in self.api_paths:
            raise ValueError("Unknown Request Type")
        endpoint = self.api_paths[request_type]
        if params is None:
            return endpoint
        query = "&".join("{}={}".format(quote_plus(str(k)), quote_plus(str(v))) for k, v in params.items())
        url = "{}?{}".format(endpoint, query)
        return url

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

    def get_candles(self, interval, start_time=None, end_time=None, limit=500, save=True, return_url=False):
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
        if return_url:
            return self._get_url("CANDLES", params=params)
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

    def get_historical_candles(self, start_date, interval, end_date=None, update=False, partition_by_date=False):
        global THREADS

        data = []
        empty_requests = 0
        exceptions = 0
        stop_execution = False
        lock = threading.Lock()

        def threaded_get_candles(time_range):

            global THREADS
            global REQUESTS_PER_MINUTE
            global BUFFER
            nonlocal data
            nonlocal exceptions
            nonlocal empty_requests
            nonlocal stop_execution
            nonlocal lock

            if stop_execution:
                return None

            temp = pd.DataFrame()

            try:
                temp = self.get_candles(interval, start_time=time_range[0], end_time=time_range[1], limit=1000,
                                        save=False)
                with lock:
                    data.append(temp)
            except Exception as err:
                print(err)
                # TODO implement better exception handling
                print(f"error for {time_range[0]} and {time_range[1]}")
                print(traceback.format_exc())

                with lock:
                    exceptions += 1

                if exceptions >= 10:
                    with lock:
                        stop_execution = True
                        raise
            finally:
                time.sleep(((THREADS + BUFFER) * 60) / REQUESTS_PER_MINUTE)

            if len(temp) == 0:
                with lock:
                    empty_requests += 1
                if empty_requests == 10:
                    print("Finished Data")
                    with lock:
                        stop_execution = True

        file_name = f"{self.symbol}_{interval}.csv"
        file_name = os.path.join(self.base_save_path, file_name)

        file_exists = os.path.exists(file_name)

        end_time = self.get_server_time() if end_date is None else int(
            (pd.to_datetime(end_date, dayfirst=True) + pd.DateOffset(days=1)).to_datetime64().view('<i8') / 10e5) - 1
        interval_milliseconds = VALID_INTERVALS_TO_TIME[interval]

        if file_exists and (not update):
            return None
        else:
            if not file_exists:
                start_time = int(pd.to_datetime(start_date, dayfirst=True).to_datetime64().view('<i8') / 10e5)
            else:
                data = pd.read_csv(file_name, header=None, skiprows=1)
                data = data.astype(CANDLES_HEADER_TYPES_AN)
                start_time = int(data.iloc[-1, 0] + interval_milliseconds)
                data = [data]

            range_m = np.arange(start_time, end_time, interval_milliseconds * 1000)

            if len(range_m) == 0:
                return None
            elif len(range_m) == 1:
                range_start = [start_time]
                range_end = [end_time]
            else:
                range_start = range_m[:-1]
                range_end = range_m[1:] - 1
                range_start = np.append(range_start, range_m[-1])
                range_end = np.append(range_end, end_time)

            start_end_range = zip(range_start[::-1], range_end[::-1])

            started_threading = time.time()
            executor = concurrent.futures.ThreadPoolExecutor(THREADS)
            executor.map(threaded_get_candles, start_end_range)
            executor.shutdown(wait=True)
            print(f"Threading took {time.time() - started_threading} seconds")

            data = pd.concat(data, ignore_index=True)
            if len(data) == 0:
                return None
            data = data.sort_values(by=0)
            data.columns = CANDLES_HEADER
            data = data.drop_duplicates(subset=CANDLES_HEADER[0])
            data = data.astype(CANDLES_HEADER_TYPES)
            if not partition_by_date:
                data.to_csv(file_name, index=False)
            else:
                data['date'] = pd.to_datetime(data['open_time'].values * 1000000).date
                data['sym'] = self.symbol

                dates = data['date'].unique()
                print("Saving by date")
                for date in dates:
                    df_date = data[data['date'] == date]
                    date_path = os.path.join(self.base_save_path,
                                             str(date).replace(" ", "").replace(":", "").replace("-", "")) + ".csv"
                    if not os.path.exists(date_path):
                        df_date.to_csv(date_path, index=False)
                    else:
                        df_date.to_csv(date_path, index=False, mode='a', header=False)

    def get_urls_for_historical_candles(self, start_date, end_date, interval="1m"):

        start_time = int(pd.to_datetime(start_date, dayfirst=True).to_datetime64().view('<i8') / 10e5)
        end_time = int(
            (pd.to_datetime(end_date, dayfirst=True) + pd.DateOffset(days=1)).to_datetime64().view('<i8') / 10e5) - 1
        interval_milliseconds = VALID_INTERVALS_TO_TIME[interval]

        range_m = np.arange(start_time, end_time, interval_milliseconds * 1000)

        if len(range_m) == 0:
            return None
        elif len(range_m) == 1:
            range_start = [start_time]
            range_end = [end_time]
        else:
            range_start = range_m[:-1]
            range_end = range_m[1:] - 1
            range_start = np.append(range_start, range_m[-1])
            range_end = np.append(range_end, end_time)

        start_end_range = zip(range_start[::-1], range_end[::-1])

        urls = [self.get_candles(interval, start_time=st, end_time=et, limit=1000, return_url=True) for st, et in
                start_end_range]

        return urls

    def get_all_historical_candles(self, start_date):
        for interval in VALID_INTERVALS[::-1]:
            self.get_historical_candles(start_date, interval)
            print(f"gotten {interval}")

    def get_candles_from_millisecond_range(self, start, end, interval):
        global THREADS

        interval_milliseconds = VALID_INTERVALS_TO_TIME[interval]

        range_m = np.arange(start, end, interval_milliseconds * 1000)
        if len(range_m) == 0:
            return None
        elif len(range_m) == 1:
            range_start = [int(start)]
            range_end = [int(end)]
        else:
            range_start = range_m[:-1]
            range_end = range_m[1:] - 1
            range_start = np.append(range_start, range_m[-1]).astype(int)
            range_end = np.append(range_end, end).astype(int)

        data = []
        start_end_range = zip(range_start[::-1], range_end[::-1])
        empty_requests = 0
        exceptions = 0
        stop_execution = False
        lock = threading.Lock()

        def threaded_get_candles(time_range):

            global THREADS
            global REQUESTS_PER_MINUTE
            global BUFFER
            nonlocal data
            nonlocal exceptions
            nonlocal empty_requests
            nonlocal stop_execution
            nonlocal lock

            if stop_execution:
                return None

            temp = pd.DataFrame()
            try:
                temp = self.get_candles(interval, start_time=time_range[0], end_time=time_range[1], limit=1000,
                                        save=False)
                with lock:
                    data.append(temp)
            except Exception as err:
                print(err)
                # TODO implement better exception handling
                print(f"error for {time_range[0]} and {time_range[1]}")
                print(traceback.format_exc())

                with lock:
                    exceptions += 1

                if exceptions == 10:
                    with lock:
                        stop_execution = True
                        raise
            finally:
                time.sleep(((THREADS + BUFFER) * 60) / REQUESTS_PER_MINUTE)

            if len(temp) == 0:
                with lock:
                    empty_requests += 1
                if empty_requests == 10:
                    print("Finished Data")
                    stop_execution = True

        started_threading = time.time()
        executor = concurrent.futures.ThreadPoolExecutor(THREADS)
        executor.map(threaded_get_candles, start_end_range)
        executor.shutdown(wait=True)
        print(f"Threading took {time.time() - started_threading} seconds")

        data = pd.concat(data)
        if len(data) == 0:
            return None
        data = data.sort_values(by=0)

        data.columns = CANDLES_HEADER

        return data

    def fill_candle_data_gaps(self, interval):
        file_name = f"{self.symbol}_{interval}_*"
        file = glob.glob(os.path.join(self.base_save_path, file_name))
        if len(file) != 1:
            # TODO make better error
            raise ValueError(f"file is {file}")

        data = pd.read_csv(file[0])

        interval_milliseconds = VALID_INTERVALS_TO_TIME[interval]
        diff = data.open_time.diff()
        is_gap = diff.fillna(interval_milliseconds) > interval_milliseconds
        gap_end = data.open_time[is_gap].values - 1
        gap_start = (data.open_time.shift()[is_gap] + interval_milliseconds).values.astype(np.int64)
        if len(gap_end) == 0:
            print("there are no gaps")
            return None

        gap_data = []
        for st, nd in zip(gap_start, gap_end):
            gap_data += [self.get_candles_from_millisecond_range(st, nd, interval)]

        gap_data = [x for x in gap_data if x is not None]
        gap_data = [x for x in gap_data if len(x) > 1]
        if len(gap_data) == 0:
            print("no extra data was found")
            return None

        new_data = [data] + gap_data
        new_data = pd.concat(new_data)
        new_data = new_data.sort_values(by='open_time')

        new_data.to_csv(file[0], index=False)


def get_param_from_url(url, param_name):
    return [i.split("=")[-1] for i in url.split("?", 1)[-1].split("&") if i.startswith(param_name + "=")]


class ThreadedRequester:
    data = []
    empty_requests = 0
    exceptions = 0
    stop_execution = False
    lock = threading.Lock()

    @classmethod
    def threaded_get_requests(cls, url):

        global THREADS
        global REQUESTS_PER_MINUTE
        global BUFFER

        if cls.stop_execution:
            return None

        try:
            temp = cls.get_url(url)
            symbol = get_param_from_url(url, "symbol")[0]
            # start_time = get_param_from_url(url, "startTime")[0]
            # temp['date'] = pd.to_datetime(start_time * 1000000).date().strftime("%Y-%m-%d")
            temp["symbol"] = symbol
            with cls.lock:
                cls.data.append(temp)
        except Exception as err:
            print(err)
            # TODO implement better exception handling
            print(f"error for {url}")
            print(traceback.format_exc())

            with cls.lock:
                cls.exceptions += 1

            if cls.exceptions >= 10:
                with cls.lock:
                    cls.stop_execution = True
                    raise
        finally:
            time.sleep(((THREADS + BUFFER) * 60) / REQUESTS_PER_MINUTE)

    @classmethod
    def get_url(cls, url):
        req = requests.get(url)
        if not req.ok:
            raise ValueError(req.text, req.status_code)
        return pd.DataFrame(json.loads(req.content))

    @classmethod
    def get_urls_data(cls, urls):
        cls.data = []
        cls.empty_requests = 0
        cls.exceptions = 0
        cls.stop_execution = False
        executor = concurrent.futures.ThreadPoolExecutor(THREADS)
        executor.map(cls.threaded_get_requests, urls)
        executor.shutdown(wait=True)
        return cls.data


class DataGetterSymbolList:

    def __init__(self, symbols: str, pandas: bool = False, base_save_path=None):
        self.symbols = symbols
        self.pandas = pandas
        self.base_save_path = base_save_path
        self.symbols_data_getters = [DataGetterSymbol(symbol, pandas, base_save_path) for symbol in symbols]


class BinanceRequestException(Exception):
    pass


if __name__ == "__main__":
    import datetime

    base_save_p = r"D:\crypto\data\dates2"
    exchange_info_path = r"G:\crypto\data\exchange"
    date_to_start = '02/01/2022'
    date_range = pd.date_range(pd.to_datetime(date_to_start, dayfirst=True), datetime.date.today(), freq='1D').strftime(
        '%d/%m/%Y').tolist()

    exchange_info = DataGetterSymbol("None", pandas=True, base_save_path=None).get_exchange_info(get_all=True,
                                                                                                 save=False)
    coins_to_get = exchange_info.loc[:, 'symbol']

    for coin in coins_to_get:
        print(f"{coin}: Started")
        c = DataGetterSymbol(coin, pandas=True, base_save_path=base_save_p)
        c.get_historical_candles(START_HIST, '1m')
        print(f"{coin}: Done")

    # for dt in date_range:
    #     print("Getting data for ", dt)
    #     end_points = []
    #     for coin in coins_to_get:
    #         c = DataGetterSymbol(coin, pandas=True, base_save_path=base_save_p)
    #         end_points += c.get_urls_for_historical_candles(dt, dt)
    #     date_data = ThreadedRequester.get_urls_data(end_points)
    #     date_data = pd.concat(date_data)
    #     date_data.columns = CANDLES_HEADER + ['sym']
    #     date_data = date_data.astype(CANDLES_HEADER_TYPES | {'sym': str})
    #     date_data = date_data.sort_values(by=['sym','open_time'])
    #     date_data.to_csv(os.path.join(base_save_p, f"{pd.to_datetime(dt, dayfirst=True).strftime('%Y%m%d')}.csv"), index=False)

    print("Done")

    # coin = 'BTCUSDT'
    # print(f"{coin}: Started")
    # c = DataGetterSymbol(coin, pandas=True, base_save_path=base_save_p)
    # c.get_historical_candles('01/01/2022', '1m', end_date='01/01/2022', update=True)
    # print(f"{coin}: Done")
    #
    # c = DataGetterSymbol("BTCUSDT", pandas=True, base_save_path=base_save_p)
    # c.fill_candle_data_gaps('1m')

    # coins_to_get = ["ETHUSDT", "BUSDUSDT", "BTCUSDT"]
    # base_save_path = "/Users/tanisha/Desktop/crypto/data/symbols"
    # for coin in coins_to_get:
    #     c = DataGetter(coin, pandas=True, base_save_path=base_save_path)
    #     c.get_all_historical_candles(START_HIST)
