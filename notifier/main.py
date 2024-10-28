import os
import time
from datetime import datetime, timedelta
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from config import original_token, line_notify_tokens, notification_mapping, INOUT_PILOTAGE_EVENTS, BERTH_ORDER_EVENTS, berth_message_type_for_pier

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
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number, se.event_name ORDER BY se.event_time DESC) AS rn
                    FROM ship_events se
                    WHERE se.event_name IN ('修改進港預報', '修改出港預報')
                ),
                latest_event AS (
                    SELECT 
                        se.*,
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number ORDER BY se.event_time DESC) AS rn
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
        
def get_berth_and_previous_pilotage_time_updated(interval):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            interval_ago = datetime.now() - timedelta(seconds=interval)

            query = '''
                WITH updated_ship AS (
                    SELECT 
                        ROW_NUMBER() OVER (ORDER BY berth_number ASC, berthing_time ASC, pilotage_time ASC) AS row_index,
                        * 
                    FROM public.ship_berth_order
                ),
                target_ship AS (
                    SELECT 
                        ROW_NUMBER() OVER (ORDER BY berth_number ASC, berthing_time ASC, pilotage_time ASC) AS row_index,
                        * ,
                        CONCAT(ship_name_chinese, ship_name_english) AS ship_name
                    FROM public.ship_berth_order
                ),
                ranked_events AS (
                    SELECT 
                        se.*,
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number, se.event_name ORDER BY se.event_time DESC) AS rn
                    FROM ship_events se
                    WHERE se.event_name IN ('修改進港預報', '修改出港預報')
                ),
                latest_event AS (
                    SELECT 
                        se.*,
                        ROW_NUMBER() OVER (PARTITION BY se.ship_voyage_number ORDER BY se.event_time DESC) AS rn
                    FROM ship_events se
                )
                SELECT 
                    updated_ship.row_index,
                    target_ship.berth_number,
                    updated_ship.berthing_time,
                    updated_ship.pilotage_time,
                    ship_status.ship_voyage_number,
                    target_ship.ship_name,
                    eta.event_content_time as eta,
                    etd.event_content_time as etd,
                    updated_ship.updated_at
                FROM updated_ship
                LEFT JOIN target_ship ON target_ship.row_index = updated_ship.row_index + 1
                JOIN ship_status ON ship_status.ship_name = target_ship.ship_name
                LEFT JOIN ranked_events eta ON ship_status.ship_voyage_number = eta.ship_voyage_number 
                    AND eta.event_name = '修改進港預報' AND eta.rn = 1
                LEFT JOIN ranked_events etd ON ship_status.ship_voyage_number = etd.ship_voyage_number 
                    AND etd.event_name = '修改出港預報' AND etd.rn = 1
                LEFT JOIN latest_event le ON ship_status.ship_voyage_number = le.ship_voyage_number AND le.rn = 1
                WHERE
                    target_ship.berth_number = updated_ship.berth_number and
                    updated_ship.updated_at >= %s;
            '''

            cur.execute(query, (interval_ago,))
            return [process_row_for_berth_order(row) for row in cur.fetchall()]

def get_ship_berth_and_port_agent():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

                query = '''
                SELECT
                    temp_table.berth_number,
                    temp_table.port_agent,
                    temp_table.ship_name_chinese
                FROM (
                    SELECT
                        sbo.berth_number,
                        sbo.port_agent,
                        sbo.ship_name_chinese,
                        sbo.updated_at,
                        ROW_NUMBER() OVER(PARTITION BY sbo.ship_name_chinese ORDER BY sbo.updated_at DESC) AS rn
                    FROM ship_berth_order sbo
                ) AS temp_table
                WHERE temp_table.rn = 1;
                '''
                cur.execute(query)
                
                return [row for row in cur.fetchall()]

def process_row(row):
    latest_event = row['latest_event_name']
    if row['ship_voyage_updated_at'] > row['updated_at']:
        if row['pass_5_miles_time']:
            latest_event = '通過5浬時間'
            row['latest_event_content_time'] = row['pass_5_miles_time'] 
            row['latest_event_source'] = "VTS轉檔"
        elif row['pass_10_miles_time']:
            latest_event = '通過10浬時間'
            row['latest_event_content_time'] = row['pass_10_miles_time']
            row['latest_event_source'] = "VTS轉檔"
        
    return {
        '訊息格式': '一般訊息',
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

def process_row_for_berth_order(row):
    if row['berthing_time'] is not None:
        trigger_event = '靠泊'
    else:
        trigger_event = '引水'
    trigger_event_time = row['berthing_time'] if row['berthing_time'] is not None else row['pilotage_time']
    return {
        '訊息格式': '接靠順序',
        '船名': row['ship_name'],
        '船編': row['ship_voyage_number'][:6],
        '航次': row['ship_voyage_number'][6:10],
        'ETA': row['eta'],
        'ETD': row['etd'],
        '碼頭代號': row['berth_number'],
        '觸發事件': trigger_event,
        '事件時間': trigger_event_time,
        '更新時間': row['updated_at']
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
    return f"""

船名: {row['船名']}
船編: {row['船編']}
航次: {row['航次']}
ETA: {format_datetime(row['ETA'])}
ETD: {format_datetime(row['ETD'])}

碼頭代號: {row['碼頭代號']}
前一艘船舶{row['觸發事件']}時間: {format_datetime(row['事件時間'])}

更新時間: 
{format_datetime(row['更新時間']) if row['更新時間'] else "N/A"}"""

def notification_filter(row, stakeholder) -> bool:
    yang_ming_or_wan_hai = "陽明海運" in row["港代"] or "萬海航運公司" in row["港代"]
    pier_1042_1043 = row['碼頭代號'] in {'1042', '1043'}
    pier_1120_1121 = row['碼頭代號'] in {'1120', '1121'}
    
    stakeholder_conditions = {
        'Pilot': yang_ming_or_wan_hai or pier_1042_1043 or pier_1120_1121,
        'CIQS': yang_ming_or_wan_hai or pier_1042_1043 or pier_1120_1121,
        'PierLienHai': pier_1042_1043,
        'PierSelfOperated': pier_1120_1121,
        'ShippingCompanyYangMing': "陽明海運" in row["港代"],
        'ShippingAgentWanHai': "萬海航運公司" in row["港代"],
        'Unmooring': yang_ming_or_wan_hai,
        'LoadingUnloading': pier_1042_1043 or pier_1120_1121,
        'Tugboat': yang_ming_or_wan_hai
    }

    return stakeholder_conditions.get(stakeholder, False)

def send_notifications(row, line_notify_tokens, original_token):
    latest_event = row['最新消息']
    message = format_message(row)
    
    if message is None:
        return
    if latest_event in notification_mapping:
        send_to_test_group = False
        send_stakeholders = []

        for stakeholder in notification_mapping[latest_event]:
            if notification_filter(row, stakeholder):
                send_to_test_group = True
                send_stakeholders.append(stakeholder)

                token = line_notify_tokens.get(stakeholder)
                if not token:
                    print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 無法發送通知: {row["船名"]} to {stakeholder}, TOKEN 未設置')
                    continue

                response = send_line_notify(message, token)
                status = '成功' if response.status_code == 200 else '失敗'
                print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 通知發送{status}: {row["船名"]} to {stakeholder}')
        
        if original_token and send_to_test_group:
            stakeholders_list = "\n".join(send_stakeholders)
            message_with_stakeholders = f"\n通知對象: \n{stakeholders_list}" + message
            response = send_line_notify(message_with_stakeholders, original_token)
            status = '成功' if response.status_code == 200 else '失敗'
            print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 通知發送{status}: {row["船名"]} - 事件: {latest_event}')
    else:
        print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 非目標事件: {row["船名"]} - {latest_event}')

def send_notifications_for_berth_order(row, original_token):
    message = format_previous_pilotage_message(row)
    if message is None:
        return

    if original_token:
        response = send_line_notify(message, original_token)
        status = '成功' if response.status_code == 200 else '失敗'
        print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 通知發送{status}: {row["船名"]} - 事件: 碼頭{row["碼頭代號"]}-{row["觸發事件"]}')

def combine_ship_and_berth_and_port_agent(rows):
    ship_berths = get_ship_berth_and_port_agent()
    
    for row in rows:
        for ship_berth in ship_berths:
            if ship_berth['ship_name_chinese'] in row["船名"]:
                if row['最新消息'] in berth_message_type_for_pier:
                    row.update({'碼頭代號': ship_berth['berth_number']})
                
                row.update({'港代': ship_berth['port_agent']})
    return(rows)

def main():
    interval_time = int(os.getenv('INTERVAL_TIME', 180))

    while True:
        print(f'{(datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")} 查看資料庫有無更新')
        interval = interval_time + 1
        rows = []
        rows.extend(get_recent_ship_statuses(interval))
        rows.extend(get_berth_and_previous_pilotage_time_updated(interval))
        rows = combine_ship_and_berth_and_port_agent(rows)
    
        for row in rows:
            try:
                if row['訊息格式'] == '接靠順序':
                    send_notifications_for_berth_order(row, original_token)
                else:
                    send_notifications(row, line_notify_tokens, original_token)
            except Exception as e:
                print(f"Failed to send notification: {str(e)}")

        time.sleep(interval_time)

if __name__ == "__main__":
    main()
