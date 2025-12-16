import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
import re
import urllib3
import pytz
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
API_URL_MORNING = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=a295cc1cfb7f9b610adb7f92c9847c5d7a05e19d107d5734798ef9346496da55&stId=115000230&busRouteId=210000037&ord=54"
API_URL_EVENING = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=a295cc1cfb7f9b610adb7f92c9847c5d7a05e19d107d5734798ef9346496da55&stId=212000452&busRouteId=210000037&ord=37"
TELEGRAM_TOKEN = "8105104121:AAGP6M9J0UJjCrfK7KAdxrfo52ZknylOJgc"
CHAT_ID = "5237321857"
ALERT_THRESHOLD_MORNING = 12  # minutes
ALERT_THRESHOLD_EVENING = 15  # minutes
notified_buses = set()
KST = pytz.timezone('Asia/Seoul')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data, verify=False)

def parse_minutes(time_str):
    if "곧 도착" in time_str:
        return 0
    match = re.search(r'(\d+)분', time_str)
    return int(match.group(1)) if match else 999

def get_estimated_arrival(minutes):
    if minutes == 0:
        return "곧 도착"
    arrival_time = datetime.now(KST) + timedelta(minutes=minutes)
    return arrival_time.strftime("%H:%M")

def parse_xml(xml_string):
    try:
        root = ET.fromstring(xml_string)
        for item in root.findall('.//itemList'):
            return {
                'arrmsg1': item.find('arrmsg1').text.strip() if item.find('arrmsg1') is not None else "",
                'plainNo1': item.find('plainNo1').text.strip() if item.find('plainNo1') is not None else "",
                'stationNm1': item.find('stationNm1').text.strip() if item.find('stationNm1') is not None else "",
                'arrmsg2': item.find('arrmsg2').text.strip() if item.find('arrmsg2') is not None else "",
                'plainNo2': item.find('plainNo2').text.strip() if item.find('plainNo2') is not None else "",
                'stationNm2': item.find('stationNm2').text.strip() if item.find('stationNm2') is not None else ""
            }
    except:
        return None

def is_monitoring_time():
    now = datetime.now(KST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False, None
    
    # Morning: 06:20-06:50
    if (now.hour == 6 and now.minute >= 20) or (now.hour == 6 and now.minute <= 50):
        return True, "morning"
    
    # Evening: 16:25-16:40
    if now.hour == 16 and 25 <= now.minute <= 40:
        return True, "evening"
    
    return False, None

def check_bus():
    now = datetime.now(KST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S KST')}] Checking bus status...")
    
    is_monitoring, time_period = is_monitoring_time()
    if not is_monitoring:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Outside monitoring hours")
        return
    
    api_url = API_URL_MORNING if time_period == "morning" else API_URL_EVENING
    alert_threshold = ALERT_THRESHOLD_MORNING if time_period == "morning" else ALERT_THRESHOLD_EVENING
    route_name = "71번 버스" if time_period == "morning" else "71번 버스 (역방향)"
        
    try:
        response = requests.get(api_url, verify=False)
        bus_data = parse_xml(response.text)
        
        if not bus_data:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] No bus data received")
            return
        
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Bus 1: {bus_data['plainNo1']} - {bus_data['arrmsg1']}")
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Bus 2: {bus_data['plainNo2']} - {bus_data['arrmsg2']}")
        
        alerts = []
        
        # Check first bus
        if bus_data['arrmsg1'] and bus_data['plainNo1'] not in notified_buses:
            minutes1 = parse_minutes(bus_data['arrmsg1'])
            if minutes1 <= alert_threshold and minutes1 < 999:
                arrival1 = get_estimated_arrival(minutes1)
                station1 = f" (현재위치: {bus_data['stationNm1']})" if bus_data['stationNm1'] else ""
                alerts.append(f"🚌 버스 {bus_data['plainNo1']}: {bus_data['arrmsg1']} (도착예정: {arrival1}){station1}")
                notified_buses.add(bus_data['plainNo1'])
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Alert sent for bus {bus_data['plainNo1']}")
        
        # Check second bus
        if bus_data['arrmsg2'] and bus_data['plainNo2'] not in notified_buses:
            minutes2 = parse_minutes(bus_data['arrmsg2'])
            if minutes2 <= alert_threshold and minutes2 < 999:
                arrival2 = get_estimated_arrival(minutes2)
                station2 = f" (현재위치: {bus_data['stationNm2']})" if bus_data['stationNm2'] else ""
                alerts.append(f"🚌 버스 {bus_data['plainNo2']}: {bus_data['arrmsg2']} (도착예정: {arrival2}){station2}")
                notified_buses.add(bus_data['plainNo2'])
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Alert sent for bus {bus_data['plainNo2']}")
        
        if alerts:
            message = f"🚨 {route_name} 알림\n" + "\n".join(alerts)
            send_telegram_message(message)
        else:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] No alerts needed")
            
    except Exception as e:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")

print("Telegram bus bot started...")
print(f"Morning monitoring: 06:20-06:50 (threshold: {ALERT_THRESHOLD_MORNING} min)")
print(f"Evening monitoring: 16:25-16:40 (threshold: {ALERT_THRESHOLD_EVENING} min)")
print(f"Check interval: 30 seconds")
while True:
    check_bus()
    time.sleep(30)
