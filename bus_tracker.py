import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# Configuration
API_URL = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=a295cc1cfb7f9b610adb7f92c9847c5d7a05e19d107d5734798ef9346496da55&stId=115000230&busRouteId=210000037&ord=54"
DISPLAY_BUS_NAME = "71부천"
NOTIFY_MINUTES = 0

def parse_xml(xml_string):
    items = []
    try:
        root = ET.fromstring(xml_string)
        for item in root.findall('.//itemList'):
            bus_info = {
                'arrmsg1': item.find('arrmsg1').text.strip() if item.find('arrmsg1') is not None else "",
                'stationNm1': item.find('stationNm1').text.strip() if item.find('stationNm1') is not None else "",
                'arrmsg2': item.find('arrmsg2').text.strip() if item.find('arrmsg2') is not None else "",
                'stationNm2': item.find('stationNm2').text.strip() if item.find('stationNm2') is not None else ""
            }
            items.append(bus_info)
    except ET.ParseError:
        pass
    return items

def parse_minutes(time_str):
    if "곧 도착" in time_str:
        return 0
    match = re.search(r'(\d+)분', time_str)
    return int(match.group(1)) if match else 999

def check_and_notify(bus):
    if "운행종료" in bus['arrmsg1'] or "출발대기" in bus['arrmsg1']:
        return
    
    minutes = parse_minutes(bus['arrmsg1'])
    if minutes <= NOTIFY_MINUTES:
        print(f"🚌 {DISPLAY_BUS_NAME}번 버스 곧 도착!")
        print(f"{bus['arrmsg1']}")
        print(f"(현위치: {bus['stationNm1']})")

def display_bus_info(bus):
    print("🚌 71 - 공항동천주교회")
    print(f"업데이트: {datetime.now().strftime('%H:%M')}")
    print("-" * 30)
    
    if not bus:
        print("운행 정보 없음")
        return
    
    print("1️⃣ 곧 도착")
    print(f"  {bus['arrmsg1'] if bus['arrmsg1'] else '정보 없음'}")
    if bus['stationNm1']:
        print(f"  (현위치: {bus['stationNm1']})")
    
    print()
    print("2️⃣ 다음 버스")
    print(f"  {bus['arrmsg2'] if bus['arrmsg2'] else '정보 없음'}")
    if bus['stationNm2']:
        print(f"  (현위치: {bus['stationNm2']})")

def main():
    try:
        response = requests.get(API_URL)
        xml_data = response.text
        bus_list = parse_xml(xml_data)
        
        target_bus = bus_list[0] if bus_list else None
        
        if target_bus:
            check_and_notify(target_bus)
        
        display_bus_info(target_bus)
        
    except requests.RequestException as e:
        print(f"API 요청 실패: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
