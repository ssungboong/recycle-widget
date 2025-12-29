import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
import re
import urllib3
import pytz
import sys
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
TELEGRAM_TOKEN = "8105104121:AAGP6M9J0UJjCrfK7KAdxrfo52ZknylOJgc"
CHAT_ID = "5237321857"

# 알림 기준 (공통)
ARRIVAL_THRESHOLD_MIN = 15

# 시간대별 스케줄 및 URL 설정
SCHEDULES = [
    {
        "name": "🌅 오전 출근",
        "start_hour": 6, "start_min": 20,
        "end_hour": 6, "end_min": 50,
        "url": "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=1f1eda59e3fadd58decc5e8c1e4880209068877f1519a964cc58489e7d7eb7e2&stId=115000230&busRouteId=210000037&ord=54"
    },
    {
        "name": "🌇 오후 퇴근",
        "start_hour": 16, "start_min": 25,
        "end_hour": 16, "end_min": 40,
        "url": "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=a295cc1cfb7f9b610adb7f92c9847c5d7a05e19d107d5734798ef9346496da55&stId=212000452&busRouteId=210000037&ord=37"
    }
]

# ---------------- [시스템 변수] ----------------

notified_vehicles = set()
last_alive_log = -1

# ---------------- [함수 정의] ----------------

def log(msg):
    """로그 출력용 함수"""
    current_time = get_korea_time().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {msg}")
    sys.stdout.flush()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={'chat_id': CHAT_ID, 'text': msg}, timeout=5)
        log(f"[전송 완료] 메시지 발송됨")
    except Exception as e:
        log(f"[전송 실패] {e}")

def get_korea_time():
    tz_kr = pytz.timezone('Asia/Seoul')
    return datetime.now(tz_kr)

def calculate_arrival_time(arrmsg):
    """ '3분40초후' 등의 텍스트를 분석하여 현재 시각에 더함 """
    now = get_korea_time()
    added_seconds = 0
    
    # '곧도착', '잠시후' 등은 0초로 계산
    if "도착" in arrmsg or "진입" in arrmsg:
        pass 
    else:
        # 분 추출
        min_match = re.search(r'(\d+)분', arrmsg)
        if min_match:
            added_seconds += int(min_match.group(1)) * 60
            
        # 초 추출
        sec_match = re.search(r'(\d+)초', arrmsg)
        if sec_match:
            added_seconds += int(sec_match.group(1))
            
    # 현재 시간 + 남은 시간
    arrival_dt = now + timedelta(seconds=added_seconds)
    return arrival_dt.strftime("%H:%M")

def parse_minutes(arrmsg):
    """ 알림 조건(12분) 비교용 단순 분 추출 """
    if not arrmsg: return 999
    if "도착" in arrmsg: return 0
    match = re.search(r'(\d+)분', arrmsg)
    if match: return int(match.group(1))
    return 999

def format_arrmsg(arrmsg):
    """ 가독성을 위해 텍스트 포맷팅 (띄어쓰기 추가) """
    # '3분40초후' -> '3분 40초 후' 등으로 보기 좋게 변경
    formatted = arrmsg.replace("분", "분 ").replace("초", "초 ")
    return formatted

def check_bus_and_notify(schedule):
    try:
        response = requests.get(schedule['url'], timeout=10)
        if response.status_code != 200:
            log(f"API 오류: {response.status_code}")
            return

        root = ET.fromstring(response.text)
        item = root.find(".//itemList")
        if item is None: return

        check_single_bus(item, "1", schedule['name'])
        check_single_bus(item, "2", schedule['name'])
        
    except Exception as e:
        log(f"에러 발생: {e}")

def check_single_bus(item, index, schedule_name):
    arrmsg = item.findtext(f"arrmsg{index}")   # 도착 시간 메시지
    plain_no = item.findtext(f"plainNo{index}") # 차량 번호
    station_nm = item.findtext(f"stationNm{index}") # 현재 버스 위치 (역 이름)
    
    if not arrmsg or not plain_no:
        return

    # 이미 알림 보낸 차량이면 패스
    if plain_no in notified_vehicles:
        return

    minutes = parse_minutes(arrmsg)

    if minutes <= ARRIVAL_THRESHOLD_MIN:
        # 1. 도착 예정 시간 계산 (HH:MM)
        arrival_time_str = calculate_arrival_time(arrmsg)
        
        # 2. 메시지 포맷팅 (요청하신 형식)
        formatted_arrmsg = format_arrmsg(arrmsg)
        
        msg = (
            f"{plain_no}: {formatted_arrmsg}\n"
            f"도착 예정: {arrival_time_str}\n"
            f"현재 위치: {station_nm}"
        )
        
        send_telegram(msg)
        notified_vehicles.add(plain_no)
        log(f"[알림 등록] {plain_no} ({schedule_name})")

def main():
    global last_alive_log
    log("🤖 버스 알림 봇 v4 시작 (포맷 변경됨)")
    
    while True:
        try:
            now = get_korea_time()
            active_schedule = None

            for schedule in SCHEDULES:
                start_time = now.replace(hour=schedule['start_hour'], minute=schedule['start_min'], second=0, microsecond=0)
                end_time = now.replace(hour=schedule['end_hour'], minute=schedule['end_min'], second=0, microsecond=0)
                
                if start_time <= now <= end_time:
                    active_schedule = schedule
                    break

            if active_schedule:
                check_bus_and_notify(active_schedule)
                time.sleep(30)
            else:
                if len(notified_vehicles) > 0:
                    log(f"[초기화] {len(notified_vehicles)}대 기록 삭제.")
                    notified_vehicles.clear()
                
                if now.hour != last_alive_log:
                    log(f"대기 중... ({now.hour}시)")
                    last_alive_log = now.hour
                
                time.sleep(60)

        except Exception as e:
            log(f"[CRITICAL ERROR] {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()