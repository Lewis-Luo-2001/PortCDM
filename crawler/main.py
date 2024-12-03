import os
import time
from typing import List
from utils.fetch import fetch_ship_webpage, fetch_webpage, fetch_ship_berth_order
from utils.extract import extract_ship_data, extract_event_data, extract_miles_data
from utils.save import save_to_csv, save_to_html, save_to_db
import pandas as pd
from datetime import datetime, timedelta

def fetch_ship_data(url: str, output_csv_path: str, output_html_path: str, ship_content_id_prefix: str, cols: list[str]) -> pd.DataFrame:
    # Fetch the webpage
    html = fetch_ship_webpage(url)
    save_to_html(html, output_html_path)

    # Extract the ship data
    result_df = pd.DataFrame(columns=cols)
    ship_id = 0
    while True:
        ids = [f"{ship_content_id_prefix}{ship_id}_{num}" for num in range(14)]

        result, df = extract_ship_data(html, ids, cols)
        if not result:
            break

        result_df = pd.concat([result_df, df], ignore_index=True)
        ship_id += 1

    save_to_csv(result_df, output_csv_path)

    save_to_db(result_df, table_name='ship_status')

    return result_df

def fetch_ship_event_data(ship_df: pd.DataFrame, event_url: str, event_cols: list[str]) -> None:
    # Extract the ship id and voyage number from the ship dataframe
    ship_df['船編'] = ship_df['船編航次'].str.slice(0, 6)
    ship_df['航次'] = ship_df['船編航次'].str.slice(6, 10)

    # Extract the event data of all ships
    for index, row in ship_df.iterrows():
        url = event_url + f"?SP_ID={row['船編']}&SP_SERIAL={row['航次']}"
        html = fetch_webpage(url)
        result, df = extract_event_data(html, event_cols)
        if result:
            df['船編航次'] = row['船編航次']
            save_to_db(df, table_name='ship_events')
            
def fetch_ship_berth_order_data(url: str, output_csv_path: str) -> None:
    ship_berth_order_data = fetch_ship_berth_order(url)
    ship_berth_order_df = pd.DataFrame(ship_berth_order_data)

    # filter out the same 船席,動態,中文船名 only keep the latest
    ship_berth_order_df = ship_berth_order_df.drop_duplicates(subset=['船席', '動態', '中文船名'], keep='last')

    berth_order_csv_path = output_csv_path.replace('.csv', '_ship_berth_order.csv')
    save_to_csv(ship_berth_order_df, berth_order_csv_path)

    save_to_db(ship_berth_order_df, table_name='ship_berth_order')

def fetch_ship_pass_5_and_10_miles(ship_df: pd.DataFrame, miles_pass_url: str, miles_cols: List[str], output_csv_path: str) -> None:
    cols = ["船編航次"] + miles_cols
    
    def fetch_miles_data(row):
        url = f"{miles_pass_url}?SP_ID={row['船編']}&SP_SERIAL={row['航次']}"
        html = fetch_webpage(url)
        miles_time = extract_miles_data(html, miles_cols)
        return [row['船編航次']] + miles_time

    ship_pass_time_data = ship_df.apply(fetch_miles_data, axis=1, result_type='expand').values.tolist()
    
    ship_pass_time_df = pd.DataFrame(ship_pass_time_data, columns=cols)
    
    ship_pass_time_csv_path = output_csv_path.replace('.csv', '_ship_pass_time.csv')
    save_to_csv(ship_pass_time_df, ship_pass_time_csv_path)

    save_to_db(ship_pass_time_df, table_name='ship_voyage') 

if __name__ == '__main__':
    from config import url, ship_berth_order_url, event_url, miles_pass_url, output_html_path, output_csv_path, ship_content_id_prefix, cols, event_url, event_cols, miles_cols

    print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 爬取網站資料')

    try:
        ship_df = fetch_ship_data(url, output_csv_path, output_html_path, ship_content_id_prefix, cols)

        fetch_ship_event_data(ship_df, event_url, event_cols)

        fetch_ship_pass_5_and_10_miles(ship_df, miles_pass_url, miles_cols, output_csv_path)

        fetch_ship_berth_order_data(ship_berth_order_url, output_csv_path)

        print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 爬取資料完成')
    except Exception as e:
        print(f"An error occurred: {str(e)}")

