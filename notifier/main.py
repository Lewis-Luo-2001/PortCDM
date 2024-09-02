import os
import time
from datetime import datetime, timedelta
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from config import notification_mapping, INOUT_PILOTAGE_EVENTS, BERTH_ORDER_EVENTS

def send_line_notify(message, token):
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Bearer {token}'
    }
    data = {'message': message}
    return requests.post(url, headers=headers, data=data)

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host='db'
    )

def get_recent_ship_statuses(interval):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            interval_ago = datetime.now() - timedelta(seconds=interval)
            
            query = '''
                WITH ranked_events AS (
                    SELECT 
                        se.*,
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number, se.event_name ORDER BY se.event_time DESC) as rn
                    FROM ship_events se
                    WHERE se.event_name IN ('修改進港預報', '修改出港預報')
                ),
                latest_event AS (
                    SELECT 
                        se.*,
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number ORDER BY se.event_time DESC) as rn
                    FROM ship_events se
                )
                SELECT 
                    ss.ship_name,
                    ss.ship_voyage_number,
                    eta.event_content_time as eta,
                    etd.event_content_time as etd,
                    le.event_name as latest_event_name,
                    le.event_time as latest_event_time,
                    le.navigation_status as navigation_status,
                    le.event_content_time as latest_event_content_time,
                    le.event_source as latest_event_source,
                    ss.updated_at,
                    sv.pass_10_miles_time,
                    sv.pass_5_miles_time,
                    sv.updated_at as ship_voyage_updated_at
                FROM ship_status ss
                LEFT JOIN ranked_events eta ON ss.ship_voyage_number = eta.ship_voyage_number 
                    AND eta.event_name = '修改進港預報' AND eta.rn = 1
                LEFT JOIN ranked_events etd ON ss.ship_voyage_number = etd.ship_voyage_number 
                    AND etd.event_name = '修改出港預報' AND etd.rn = 1
                LEFT JOIN latest_event le ON ss.ship_voyage_number = le.ship_voyage_number AND le.rn = 1
                LEFT JOIN ship_voyage sv ON ss.ship_voyage_number = sv.ship_voyage_number
                WHERE ss.updated_at >= %s OR sv.updated_at >= %s
                ORDER BY GREATEST(COALESCE(le.event_time, '1970-01-01'), COALESCE(sv.updated_at, '1970-01-01'))
            '''
            
            cur.execute(query, (interval_ago, interval_ago))
            return [process_row(row) for row in cur.fetchall()]

def get_berth_and_previous_pilotage_time(ship_voyage_number, ship_name):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            berth_query = '''
                SELECT berth_number
                FROM ship_events
                WHERE ship_voyage_number = %s
                AND berth_number IS NOT NULL
                ORDER BY event_time DESC
                LIMIT 1
            '''
            
            cur.execute(berth_query, (ship_voyage_number,))
            result = cur.fetchone()
            berth_number = result['berth_number'] if result else None
            
            if not berth_number:
                return None, None
            
            pilotage_query = '''
                WITH current_ship AS (
                    SELECT pilotage_time
                    FROM ship_berth_order
                    WHERE berth_number = %s AND CONCAT(ship_name_chinese, ship_name_english) = %s
                    AND pilotage_time IS NOT NULL
                    ORDER BY pilotage_time DESC
                    LIMIT 1
                ),
                previous_ship AS (
                    SELECT pilotage_time
                    FROM ship_berth_order
                    WHERE berth_number = %s 
                    AND pilotage_time IS NOT NULL
                    AND pilotage_time < (SELECT pilotage_time FROM current_ship)
                    ORDER BY pilotage_time DESC
                    LIMIT 1
                )
                SELECT pilotage_time AS previous_pilotage_time
                FROM previous_ship
            '''
            
            cur.execute(pilotage_query, (berth_number, ship_name, berth_number))
            result = cur.fetchone()
            previous_pilotage_time = result['previous_pilotage_time'] if result else None
            
            return berth_number, previous_pilotage_time

def process_row(row):
    latest_event = row['latest_event_name']
    if row['ship_voyage_updated_at'] > row['updated_at']:
        if row['pass_5_miles_time']:
            latest_event = '通過5浬時間'
        elif row['pass_10_miles_time']:
            latest_event = '通過10浬時間'
        
    return {
        '船名': row['ship_name'],
        '船編': row['ship_voyage_number'][:6],
        '航次': row['ship_voyage_number'][6:10],
        'ETA': row['eta'],
        'ETD': row['etd'],
        '最新消息': convert_inout_pilotage_event(latest_event, row['navigation_status']),
        '事件時間': row['latest_event_content_time'],
        '事件來源': row['latest_event_source'],
        '更新時間': row['ship_voyage_updated_at'] if latest_event in BERTH_ORDER_EVENTS else row['latest_event_time'] 
    }

def convert_inout_pilotage_event(event_name, navigation_status):
    return f"{event_name} ({navigation_status})" if event_name in INOUT_PILOTAGE_EVENTS else event_name

def format_datetime(dt):
    if isinstance(dt, datetime):
        return (dt + timedelta(hours=8)).strftime("%Y/%m/%d %H:%M:%S")
    else:
        return dt

def format_message(row):
    return f"""

船名: {row['船名']}
船編: {row['船編']}
航次: {row['航次']}
ETA: {format_datetime(row['ETA'])}
ETD: {format_datetime(row['ETD'])}

最新事件: {row['最新消息']}
事件時間: {format_datetime(row['事件時間'])}
事件來源: {row['事件來源']}

更新時間: 
{format_datetime(row['更新時間']) if row['更新時間'] else "N/A"}"""

def format_previous_pilotage_message(row):
    berth_number, previous_pilotage_time = get_berth_and_previous_pilotage_time(row['船編'] + row['航次'], row['船名'])
    
    if not previous_pilotage_time:
        return None

    return f"""

船名: {row['船名']}
船編: {row['船編']}
航次: {row['航次']}
ETA: {format_datetime(row['ETA'])}
ETD: {format_datetime(row['ETD'])}

最新事件: {row['最新消息']}
碼頭代號: {berth_number or "N/A"}
前一艘靠泊船舶引水時間:
{format_datetime(previous_pilotage_time)}

更新時間: 
{format_datetime(row['更新時間']) if row['更新時間'] else "N/A"}"""

def send_notifications(row, line_notify_tokens, original_token):
    latest_event = row['最新消息']
    message = format_previous_pilotage_message(row) if latest_event in BERTH_ORDER_EVENTS else format_message(row)
    
    if message is None:
        return

    if latest_event in notification_mapping:
        for stakeholder in notification_mapping[latest_event]:
            token = line_notify_tokens.get(stakeholder)
            if not token:
                print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 無法發送通知: {row["船名"]} to {stakeholder}, TOKEN 未設置')
                continue

            response = send_line_notify(message, token)
            status = '成功' if response.status_code == 200 else '失敗'
            print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 通知發送{status}: {row["船名"]} to {stakeholder}')
        
        if original_token:
            stakeholders_list = "\n".join(notification_mapping[latest_event])
            message_with_stakeholders = f"\n通知對象: \n{stakeholders_list}" + message
            response = send_line_notify(message_with_stakeholders, original_token)
            status = '成功' if response.status_code == 200 else '失敗'
            print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 通知發送{status}: {row["船名"]} - 事件: {latest_event}')
    else:
        print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 非目標事件: {row["船名"]} - {latest_event}')

def main():
    original_token = os.getenv('LINE_NOTIFY_TOKEN')
    interval_time = int(os.getenv('INTERVAL_TIME', 180))

    line_notify_tokens = {
        'Pilot': os.getenv('LINE_NOTIFY_TOKEN_PILOT'),
        'Unmooring': os.getenv('LINE_NOTIFY_TOKEN_UNMOORING'),
        'Tugboat': os.getenv('LINE_NOTIFY_TOKEN_TUGBOAT'),
        'ShippingAgent': os.getenv('LINE_NOTIFY_TOKEN_SHIPPINGAGENT'),
        'ShippingCompany': os.getenv('LINE_NOTIFY_TOKEN_SHIPPINGCOMPANY'),
        'LoadingUnloading': os.getenv('LINE_NOTIFY_TOKEN_LOADINGUNLOADING')
    }

    while True:
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 查看資料庫有無更新')
        rows = get_recent_ship_statuses(interval_time+1)

        for row in rows:
            if "WAN HAI" in row['船名']:
                send_notifications(row, line_notify_tokens, original_token)

        time.sleep(interval_time)

if __name__ == "__main__":
    main()