import os
import pandas as pd
import dask.dataframe as dd
from glob import glob

from constants import CANDLES_HEADERS, VALID_INTERVALS, VALID_INTERVALS_TO_TIME

DATA_PATH = "/Users/tanisha/Desktop/crypto/data/symbols"

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

        path_small = os.path.join(self.data_path, f"{self.symbol}_{small_interval}_*")
        path_large = os.path.join(self.data_path, f"{self.symbol}_{large_interval}_*")

        df_small = dd.read_csv(path_small)
        df_large = dd.read_csv(path_large)

        return df_small, df_large


if __name__ == "__main__":
    validator = DataValidator("ETHUSDT", DATA_PATH)
    small, large = validator.validate_candles("1d", "1w")
    print("Done")
