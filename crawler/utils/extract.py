from bs4 import BeautifulSoup
import pandas as pd
from typing import Tuple, List

def extract_ship_data(html: str, ids: list[str], cols: list[str]) -> Tuple[bool, pd.DataFrame]:
    """
    Extracts ship data from the given HTML content based on specified IDs.

    Args:
        html (str): The HTML content of the webpage.
        ids (List[str]): A list of HTML element IDs to find the ship data.
        cols (List[str]): A list of column names for the resulting DataFrame.

    Returns:
        Tuple[bool, pd.DataFrame]: A tuple where the first element is a boolean indicating
                                   whether the extraction was successful, and the second element
                                   is a DataFrame containing the extracted data.
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    data = []
    for id in ids:
        content = soup.find(id=id)
        if content:
            cleaned_content = content.get_text(strip=True)
            img = content.find('img')
            if img and 'src' in img.attrs:
                img_src = img['src']
                if 'ok.png' in img_src:
                    cleaned_content += 'YES'
                elif 'red.gif' in img_src:
                    cleaned_content += 'RED'
            if cleaned_content == '':
                cleaned_content = 'NO'
            data.append(cleaned_content)
        else:
            return False, pd.DataFrame()
    return True, pd.DataFrame([data], columns=cols)

def extract_event_data(html: str, cols: list[str]) -> Tuple[bool, pd.DataFrame]:
    """
    Extracts event data from the given HTML content.

    Args:
        html (str): The HTML content of the webpage.

    Returns:
        Tuple[bool, List[str]]: A tuple where the first element is a boolean indicating
                                whether the extraction was successful, and the second element
                                is a list of event data.
    """

    soup = BeautifulSoup(html, 'html.parser')
    result_df = pd.DataFrame(columns=cols)
    event_id_prefix = 'ASPx_船舶事件_tccell'

    event_num = 0
    done = False
    while True:
        event_data = []
        event_ids = [f"{event_id_prefix}{event_num}_{num}" for num in range(0, 7)]

        for event_id in event_ids:
            content = soup.find(id=event_id)
            if content:
                event_data.append(content.get_text(strip=True))
            else:
                done = True
                break

        if done:
            break
        result_df = pd.concat([result_df, pd.DataFrame([event_data], columns=cols)], ignore_index=True)
        event_num += 1

    return True, result_df

def extract_miles_data(html: str, cols: List[str]) -> List[str]:
    """
    Extracts mile passing data from the given HTML content.

    Args:
        html (str): The HTML content of the webpage.
        cols (List[str]): List of column names for the mile data.

    Returns:
        List[str]: A list containing the extracted mile passing data.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    miles_prefix = "ASPx_港外船舶進港_tccell0_"
    miles_ids = [f"{miles_prefix}{num}" for num in range(2, 4)]
    
    event_data = []
    for miles_id in miles_ids:
        content = soup.find(id=miles_id)
        
        if content:
            data = content.get_text(strip=True)
            event_data.append(data if data else "null")
        else:
            event_data.append("null")
    
    if len(event_data) != len(cols):
        raise ValueError(f"Mismatch between extracted data ({len(event_data)}) and provided columns ({len(cols)})")
    
    return event_data