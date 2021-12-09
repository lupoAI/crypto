import os

import numpy as np
import pandas as pd

from constants import CANDLES_HEADER, VALID_INTERVALS, VALID_INTERVALS_TO_TIME

# import dask.dataframe as dd
# from glob import glob

DATA_PATH = r"C:\Users\salom\PycharmProjects\crypto\data\symbols"


def ms_dt_parser(ms):
    return pd.to_datetime(int(ms) * 10e5)


class DataValidator:

    def __init__(self, symbol, data_path):
        self.symbol = symbol
        self.data_path = data_path

    def validate_candles(self, interval_1, interval_2):
        if interval_1 not in VALID_INTERVALS:
            raise ValueError('interval_1 is not a valid interval')
        if interval_2 not in VALID_INTERVALS:
            raise ValueError('interval_2 is not a valid interval')

        if VALID_INTERVALS_TO_TIME[interval_1] <= VALID_INTERVALS_TO_TIME[interval_2]:
            small_interval, large_interval = interval_1, interval_2
        else:
            small_interval, large_interval = interval_2, interval_1

        # path_small = os.path.join(self.data_path, f"{self.symbol}_{small_interval}_*")
        # path_large = os.path.join(self.data_path, f"{self.symbol}_{large_interval}_*")

        path_small = os.path.join(self.data_path, f"{self.symbol}_{small_interval}_2012_2021_inc.csv")
        path_large = os.path.join(self.data_path, f"{self.symbol}_{large_interval}_2012_2021_inc.csv")

        df_small = pd.read_csv(path_small, header=None, index_col=0, parse_dates=[0, 6], date_parser=ms_dt_parser)
        df_small.columns = CANDLES_HEADER[1:]
        df_large = pd.read_csv(path_large, header=None, index_col=0, parse_dates=[0, 6], date_parser=ms_dt_parser)
        df_large.columns = CANDLES_HEADER[1:]

        for start, end in zip(df_large.index[:-1], df_large.index[1:]):
            to_replicate = df_large.loc[start]
            sm_index = df_small.index
            relevant_small_date = df_small.loc[(sm_index >= start) & (sm_index < end)]

            assert to_replicate['open'] == relevant_small_date['open'].iloc[0]
            assert to_replicate['high'] == relevant_small_date['high'].max()
            assert to_replicate['low'] == relevant_small_date['low'].min()
            assert to_replicate['close'] == relevant_small_date['close'].iloc[-1]
            assert np.isclose(to_replicate['volume'], relevant_small_date['volume'].sum())
            assert np.isclose(to_replicate['quote_asset_volume'], relevant_small_date['quote_asset_volume'].sum())
            assert np.isclose(to_replicate['number_of_trades'], relevant_small_date['number_of_trades'].sum())
            assert np.isclose(to_replicate['taker_buy_base_asset_volume'],
                              relevant_small_date['taker_buy_base_asset_volume'].sum())
            assert np.isclose(to_replicate['taker_buy_quote_asset_volume'],
                              relevant_small_date['taker_buy_quote_asset_volume'].sum())

        print("Everything is expected")

        return df_small, df_large


if __name__ == "__main__":
    validator = DataValidator("ETHUSDT", DATA_PATH)
    small, large = validator.validate_candles("1d", "1w")
