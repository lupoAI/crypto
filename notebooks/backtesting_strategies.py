import os
import pandas as pd
import numpy as np
from glob import glob
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG

data_path = r"G:\crypto\data\symbols"
file_pattern = "*_1m.csv"
available_ticker_paths = glob(os.path.join(data_path, file_pattern))
available_tickers = [x.replace(data_path + '\\', "").replace("_1m.csv", "") for x in available_ticker_paths]
ticker_to_path = {k:v for k, v in zip(available_tickers, available_ticker_paths)}

@np.vectorize
def ms_dt_parser(ms):
    return pd.to_datetime(int(ms) * 10e5)

########################################################################################################################
ticker_to_analyse = 'ETHUSDT'
########################################################################################################################

data = pd.read_csv(ticker_to_path[ticker_to_analyse], index_col=0, parse_dates=[0], date_parser=ms_dt_parser, nrows=100000)
data_strategy = data[['open', 'high', 'low', 'close', 'volume']].copy()
data_strategy.columns = [x.title() for x in data_strategy.columns]

def ewma(data, halflife):
    data_df = pd.DataFrame(data)
    data_df = data_df.ewm(halflife=halflife).mean()
    return data_df[data_df.columns[0]].values

class EWMAcross(Strategy):
    fast_hl = 1000
    slow_hl = 2000

    def init(self):
        close = self.data.Close
        self.fast_ewma = self.I(ewma, close, self.fast_hl)
        self.slow_ewma = self.I(ewma, close, self.slow_hl)

    def next(self):
        if crossover(self.fast_ewma, self.slow_ewma):
            self.buy()
        elif crossover(self.slow_ewma, self.fast_ewma):
            self.sell()


bt = Backtest(data_strategy, EWMAcross,
              cash=10000, commission=0.002,
              exclusive_orders=True)

output = bt.run()

bt.plot()