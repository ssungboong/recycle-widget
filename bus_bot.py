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
        "url": "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?serviceKey=a295cc1cfb7f9b610adb7f92c9847c5d7a05e19d107d5734798ef9346496da55&stId=115000230&busRouteId=210000037&ord=54"
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
    """로그 출력용 함수 (시간 포함)"""
    current_time = get_korea_time().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {msg}")
    sys.stdout.flush()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={'chat_id': CHAT_ID, 'text': msg}, timeout=5)
        log(f"[전송 완료] {msg.replace(chr(10), ' ')}") # 줄바꿈 제거 후 로그
    except Exception as e:
        log(f"[전송 실패] {e}")

def parse_minutes(time_str):
    if not time_str: return 999
    if "도착" in time_str: return 0
    
    import re
    match = re.search(r'(\d+)분', time_str)
    if match:
        return int(match.group(1))
    return 999

def get_korea_time():
    tz_kr = pytz.timezone('Asia/Seoul')
    return datetime.now(tz_kr)

def check_bus_and_notify(schedule):
    """지정된 스케줄의 URL로 버스 조회"""
    try:
        response = requests.get(schedule['url'], timeout=10)
        
        if response.status_code != 200:
            log(f"API 오류({schedule['name']}): 상태 코드 {response.status_code}")
            return

        root = ET.fromstring(response.text)
        item = root.find(".//itemList")
        
        if item is None:
            return

        # 1, 2번째 도착 버스 체크
        check_single_bus(item, "1", schedule['name'])
        check_single_bus(item, "2", schedule['name'])
        
    except Exception as e:
        log(f"조회 중 에러 발생: {e}")

def check_single_bus(item, index, schedule_name):
    arrmsg = item.findtext(f"arrmsg{index}")
    plain_no = item.findtext(f"plainNo{index}")
    
    if not arrmsg or not plain_no:
        return

    # 이미 알림 보낸 차량이면 패스
    if plain_no in notified_vehicles:
        return

    minutes = parse_minutes(arrmsg)

    if minutes <= ARRIVAL_THRESHOLD_MIN:
        msg = (
            f"[{schedule_name}] 버스 발견!\n"
            f"차량: {plain_no}\n"
            f"시간: {arrmsg}\n"
            f"조건: {ARRIVAL_THRESHOLD_MIN}분 이내"
        )
        send_telegram(msg)
        notified_vehicles.add(plain_no)
        log(f"[알림 등록] {plain_no} - {schedule_name}")

def main():
    global last_alive_log
    log("🤖 버스 알림 봇 v3 시작 (오전/오후 이중화)")
    
    while True:
        try:
            now = get_korea_time()
            active_schedule = None

            # 현재 시간이 어떤 스케줄에 해당하는지 확인
            for schedule in SCHEDULES:
                start_time = now.replace(hour=schedule['start_hour'], minute=schedule['start_min'], second=0, microsecond=0)
                end_time = now.replace(hour=schedule['end_hour'], minute=schedule['end_min'], second=0, microsecond=0)
                
                if start_time <= now <= end_time:
                    active_schedule = schedule
                    break # 매칭되는 시간대를 찾으면 중단

            # 1. 활성 시간대인 경우 (오전 혹은 오후)
            if active_schedule:
                check_bus_and_notify(active_schedule)
                time.sleep(30) # 30초 대기
            
            # 2. 아무 시간대도 아닌 경우 (대기 모드)
            else:
                # 활성 시간대가 끝났고, 목록에 남은 차가 있다면 초기화
                if len(notified_vehicles) > 0:
                    log(f"[초기화] 시간대 종료. {len(notified_vehicles)}대 기록 삭제.")
                    notified_vehicles.clear()
                
                # 생존 신고 (1시간마다)
                if now.hour != last_alive_log:
                    log(f"대기 모드... ({now.hour}시)")
                    last_alive_log = now.hour
                
                time.sleep(60) # 1분 대기

        except Exception as e:
            log(f"[CRITICAL ERROR] {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()