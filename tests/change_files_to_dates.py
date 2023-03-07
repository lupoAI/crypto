import pandas as pd
import os

def change_from_symbols_to_dates(dir, new_dir):
    # function that reads all csv files in a directory and saves copy of them in a new directory
    # in a parquet using pandas
    for file in os.listdir(dir):
        if file.endswith('.csv'):
            print(file)
            df = pd.read_csv(os.path.join(dir, file))
            df['date'] = pd.to_datetime(df['open_time'].values * 1000000).date
            df['sym'] = file.replace('.csv', '')

            dates = df['date'].unique()
            for date in dates:
                df_date = df[df['date'] == date]
                date_path = os.path.join(new_dir, str(date).replace(" ", "").replace(":", "").replace("-", "")) + ".csv"
                if not os.path.exists(date_path):
                    df_date.to_csv(date_path, index=False)
                else:
                    df_date.to_csv(date_path, index=False, mode='a', header=False)


if __name__ == '__main__':
    change_from_symbols_to_dates(r'D:\crypto\data\symbols', r'D:\crypto\data\dates')
