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

CANDLES_HEADER = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
                  'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
