import os

import pandas as pd


def change_format(dir, new_dir):
    # function that reads all csv files in a directory and saves copy of them in a new directory
    # in a parquet using pandas
    for file in os.listdir(dir):
        if file.endswith('.csv'):
            print(file)
            df = pd.read_csv(os.path.join(dir, file))
            df.to_parquet(os.path.join(new_dir, file.replace("_1m", "").replace('csv', 'parquet')))


def check_dir_memory_usage(dir):
    # function that checks file sizeof all files in a directory
    total_size = 0
    for file in os.listdir(dir):
        total_size += os.path.getsize(os.path.join(dir, file))
    print('Total size of files in directory: ' + str(total_size // 1000000) + ' MB')


def rename_files_in_directory(dir):
    # function that renames all files in a directory
    for file in os.listdir(dir):
        os.rename(os.path.join(dir, file), os.path.join(dir, file.replace("_1m", "")))


def find_list_of_files(dir):
    # function that returns a list of all files in a directory
    files = []
    for file in os.listdir(dir):
        files.append(file.replace(".csv", ""))
    return files


if __name__ == '__main__':
    # change_format(r'D:\crypto\data\symbols', r'D:\crypto\data\symbols_reformatted')
    # check_dir_memory_usage(r'D:\crypto\data\symbols')
    # check_dir_memory_usage(r'D:\crypto\data\symbols_reformatted')
    # rename_files_in_directory(r'D:\crypto\data\symbols')
    list_of_files = find_list_of_files(r'D:\crypto\data\symbols')
    print("Done")
