# -*- coding: utf-8 -*-
import os
import time
import requests
from random import randint
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import platform
import logging
import shutil

from srt_reservation.exceptions import InvalidStationNameError, InvalidDateError, InvalidDateFormatError, InvalidTimeFormatError
from srt_reservation.validation import station_list

# chromedriver_path = r'C:\workspace\chromedriver.exe'
# 맥 os에 맞는 path로 수정
# chromedriver_path = '/usr/local/bin/chromedriver'

# 슬랙 웹훅 주소. 없을시 빈 url 주소인 "" 로 변경해주세요.
slack_webhook_url = 'https://hooks.slack.com/services/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'

class SRT:
    def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm, psg_info_per_prnb=1, num_trains_to_check=2, num_trains_to_check_start = 1, want_reserve=False):
        """
        :param dpt_stn: SRT 출발역
        :param arr_stn: SRT 도착역
        :param dpt_dt: 출발 날짜 YYYYMMDD 형태 ex) 20220115
        :param dpt_tm: 출발 시간 hh 형태, 반드시 짝수 ex) 06, 08, 14, ...
        :param psg_info_per_prnb: 성인 인원 수 ex) 1, 2, 3, ...
        :param num_trains_to_check: 검색 결과 중 예약 가능 여부 확인할 기차의 수 ex) 2일 경우 상위 2개 확인
        :param num_trains_to_check_start: 검색 결과 중 예약 가능 여부 확인할 기차의 수 검색 시작 지점
        :param want_reserve: 예약 대기가 가능할 경우 선택 여부
        """
        self.login_id = None
        self.login_psw = None

        self.dpt_stn = dpt_stn
        self.arr_stn = arr_stn
        self.dpt_dt = dpt_dt
        self.dpt_tm = dpt_tm
        self.psg_info_per_prnb = psg_info_per_prnb

        self.num_trains_to_check = num_trains_to_check
        self.num_trains_to_check_start = num_trains_to_check_start
        self.want_reserve = want_reserve
        self.driver = None

        self.is_booked = False  # 예약 완료 되었는지 확인용
        self.cnt_refresh = 0  # 새로고침 회수 기록

        self.check_input()

    def check_input(self):
        if self.dpt_stn not in station_list:
            raise InvalidStationNameError(f"출발역 오류. '{self.dpt_stn}' 은/는 목록에 없습니다.")
        if self.arr_stn not in station_list:
            raise InvalidStationNameError(f"도착역 오류. '{self.arr_stn}' 은/는 목록에 없습니다.")
        if not str(self.dpt_dt).isnumeric():
            raise InvalidDateFormatError("날짜는 숫자로만 이루어져야 합니다.")
        try:
            datetime.strptime(str(self.dpt_dt), '%Y%m%d')
        except ValueError:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")

    def set_log_info(self, login_id, login_psw):
        self.login_id = login_id
        self.login_psw = login_psw

    def run_driver(self):
        try:
            # 기존 ChromeDriver 캐시 제거
            cache_path = os.path.expanduser('~/.wdm/drivers/chromedriver')
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)
            
            # Chrome 옵션 설정
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # M1/M2 Mac 확인 및 설정
            if platform.system() == "Darwin" and platform.processor() == 'arm':
                chrome_options.add_argument('--disable-gpu')
                os.environ['WDM_ARCHITECTURE'] = 'arm64'  # 명시적으로 arm64 아키텍처 지정
            
            # ChromeDriver 설치 및 서비스 설정
            driver_path = ChromeDriverManager().install()
            
            # 실행 권한 확인 및 부여
            os.chmod(driver_path, 0o755)
            
            service = Service(driver_path)
            
            print(f"ChromeDriver 경로: {driver_path}")
            print(f"시스템 아키텍처: {platform.processor()}")
            
            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            
        except Exception as e:
            print(f"ChromeDriver 초기화 실패: {str(e)}")
            print(f"운영체제: {platform.system()}")
            print(f"프로세서: {platform.processor()}")
            print(f"Python 버전: {platform.python_version()}")
            raise e

    def login(self):
        self.driver.get('https://etk.srail.co.kr/cmc/01/selectLoginForm.do')
        self.driver.implicitly_wait(15)
        self.driver.find_element(By.ID, 'srchDvNm01').send_keys(str(self.login_id))
        self.driver.find_element(By.ID, 'hmpgPwdCphd01').send_keys(str(self.login_psw))
        self.driver.find_element(By.XPATH, '//*[@id="login-form"]/fieldset/div[1]/div[1]/div[2]/div/div[2]/input').click()
        self.driver.implicitly_wait(5)
        return self.driver

    def check_login(self):
        menu_text = self.driver.find_element(By.CSS_SELECTOR, "#wrap > div.header.header-e > div.global.clear > div").text
        if "환영합니다" in menu_text:
            return True
        else:
            return False

    def go_search(self):
        # 기차 조회 페이지로 이동
        self.driver.get('https://etk.srail.kr/hpg/hra/01/selectScheduleList.do')
        self.driver.implicitly_wait(5)

        # 출발지 입력
        elm_dpt_stn = self.driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        elm_dpt_stn.send_keys(self.dpt_stn)

        # 도착지 입력
        elm_arr_stn = self.driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        elm_arr_stn.send_keys(self.arr_stn)

        # 출발 날짜 입력
        elm_dpt_dt = self.driver.find_element(By.ID, "dptDt")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_dt)
        Select(self.driver.find_element(By.ID, "dptDt")).select_by_value(self.dpt_dt)

        # 출발 시간 입력
        elm_dpt_tm = self.driver.find_element(By.ID, "dptTm")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_tm)
        Select(self.driver.find_element(By.ID, "dptTm")).select_by_visible_text(self.dpt_tm)

        # 성인 인원 수 입력
        elm_psg_info_per_prnb = self.driver.find_element(By.ID, "psgInfoPerPrnb1")
        Select(self.driver.find_element(By.ID, "psgInfoPerPrnb1")).select_by_value(str(self.psg_info_per_prnb))

        print("기차를 조회합니다")
        print(f"출발역:{self.dpt_stn} , 도착역:{self.arr_stn}\n날짜:{self.dpt_dt}, 시간: {self.dpt_tm}시 이후\n{self.num_trains_to_check}개의 기차 중 예약")
        print(f"예약 대기 사용: {self.want_reserve}")

        self.driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
        self.driver.implicitly_wait(5)
        time.sleep(1)

    def book_ticket(self, standard_seat, i):
        # standard_seat는 일반석 검색 결과 텍스트
        
        if "예약하기" in standard_seat:
            print("예약 가능 클릭")

            # Error handling in case that click does not work
            try:
                self.driver.find_element(By.CSS_SELECTOR,
                                         f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a").click()
            except ElementClickInterceptedException as err:
                print(err)
                self.driver.find_element(By.CSS_SELECTOR,
                                         f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a").send_keys(
                    Keys.ENTER)
            finally:
                self.driver.implicitly_wait(3)

            # 예약이 성공하면
            if self.driver.find_elements(By.ID, 'isFalseGotoMain'):
                self.is_booked = True
                
                self.send_message("예약 성공!")
                print("예약 성공")

                return self.driver
            else:
                print("잔여석 없음. 다시 검색")
                self.driver.back()  # 뒤로가기
                self.driver.implicitly_wait(5)

    # 슬랙봇 연동
    def send_message(self, msg):
        if slack_webhook_url != "":
            try:
                url = slack_webhook_url
                data = {'text': msg}
                response = requests.post(url=url, json=data)
                
                # 응답 상태 확인
                if response.status_code != 200:
                    print(f"슬랙 메시지 전송 실패. 상태 코드: {response.status_code}")
                    print(f"에러 메시지: {response.text}")
                else:
                    print("슬랙 메시지 전송 성공")
                    
            except Exception as e:
                print(f"슬랙 메시지 전송 중 에러 발생: {str(e)}")
        else:
            print("슬랙 웹훅 URL이 설정되지 않았습니다.")

                

    def refresh_result(self):
        submit = self.driver.find_element(By.XPATH, "//input[@value='조회하기']")
        self.driver.execute_script("arguments[0].click();", submit)
        self.cnt_refresh += 1
        print(f"새로고침 {self.cnt_refresh}회")
        self.driver.implicitly_wait(10)
        time.sleep(0.5)

    def reserve_ticket(self, reservation, i):
        if "신청하기" in reservation:
            print("예약 대기 완료")
            self.driver.find_element(By.CSS_SELECTOR,
                                     f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8) > a").click()
            self.is_booked = True
            return self.is_booked

    def check_result(self):
        while True:
            try:
                # 명시적으로 테이블이 나타날 때까지 최대 10초 대기
                table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody"))
                )
            
                for i in range(self.num_trains_to_check_start, self.num_trains_to_check+1):
                    try:
                        # 각 행이 클릭 가능할 때까지 대기
                        row = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 
                                f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i})"))
                        )
                        
                        standard_seat = row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text
                        reservation = row.find_element(By.CSS_SELECTOR, "td:nth-child(8)").text
                    
                    except (StaleElementReferenceException, TimeoutException):
                        print(f"{i}번째 열을 찾을 수 없습니다.")
                        standard_seat = "매진"
                        reservation = "매진"
                        continue

                    if self.book_ticket(standard_seat, i):
                        return self.driver

                    if self.want_reserve:
                        self.reserve_ticket(reservation, i)

                if self.is_booked:
                    return self.driver
                else:
                    time.sleep(randint(2, 4))
                    self.refresh_result()
                
            except TimeoutException:
                print("검색 결과 테이블을 찾을 수 없습니다. 새로고침합니다.")
                self.refresh_result()

    def run(self, login_id, login_psw):
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()
        self.go_search()
        self.check_result()

#
# if __name__ == "__main__":
#     srt_id = os.environ.get('srt_id')
#     srt_psw = os.environ.get('srt_psw')
#
#     srt = SRT("동탄", "동대구", "20220917", "08")
#     srt.run(srt_id, srt_psw)

