from utils.fetch import fetch_webpage
from utils.extract import extract_port_data, extract_event_data
from utils.save import save_to_csv, save_to_html
import pandas as pd

def main(url: str, output_csv_path: str, output_html_path: str, ship_content_id_prefix: str, cols: list[str], event_url: str, event_cols: str) -> None:
    # Fetch the webpage
    html = fetch_webpage(url)
    save_to_html(html, output_html_path)

    # Extract the ship data
    result_df = pd.DataFrame(columns=cols)
    ship_id = 0
    while True:
        ids = [f"{ship_content_id_prefix}{ship_id}_{num}" for num in range(0, 14)]

        # Check if the ship content exists
        result, df = extract_port_data(html, ids, cols)
        if result == False:
            break

        # Append the ship data to the dataframe
        result_df = pd.concat([result_df, df], ignore_index=True)

        # Move to the next ship
        ship_id += 1

    # Extract the ship id and voyage number from the dataframe
    result_df['船編'] = result_df['船編航次'].str.slice(0, 6)
    result_df['航次'] = result_df['船編航次'].str.slice(6, 10)

    # Save the ship data to csv
    save_to_csv(result_df, output_csv_path)

    # Extract the event data of all ships
    for index, row in result_df.iterrows():
        url = event_url + f"?SP_ID={row['船編']}&SP_SERIAL={row['航次']}"
        html = fetch_webpage(url)
        result, df = extract_event_data(html, event_cols)
        if result:
            save_to_csv(df, f"output/event_{row['船編']}_{row['航次']}.csv")    


if __name__ == '__main__':
    from config import url, output_html_path, output_csv_path, ship_content_id_prefix, cols, event_url, event_cols
    main(url, output_csv_path, output_html_path, ship_content_id_prefix, cols, event_url, event_cols)
