# Python program for booking SRT ticket.


매진된 SRT 표의 예매를 도와주는 파이썬 프로그램입니다.  
원하는 표가 나올 때 까지 새로고침하여 예약을 시도합니다.

감사하게도 `https://github.com/kminito/srt_reservation.git`의 오픈소스를 참고하였습니다.
결제를 10분 안에 해야하기 때문에 예약 성공시 슬랙 알림 기능을 추가하였습니다.
원치 않는 시간대는 제외하기 위해서 기차 예약 시작 지점을 추가 하였습니다.

## 다운
```cmd
git clone https://github.com/Wanderlust-sol/srt_reservation.git
```
  
## 필요
- 파이썬 3.9에서 테스트 했습니다.

```py
pip install -r requirements.txt
```


## Arguments
    dpt: SRT 출발역
    arr: SRT 도착역
    dt: 출발 날짜 YYYYMMDD 형태 ex) 20220115
    tm: 출발 시간 hh 형태, 반드시 짝수 ex) 06, 08, 14, ...
    ps: 승객 인원수 (default: 1)
    num: 검색 결과 중 예약 가능 여부 확인할 기차의 수 (default : 2)
    num_s: 검색 결과 중 예약 가능 여부 확인할 기차의 시작 지점 (default : 1)
    reserve: 예약 대기가 가능할 경우 선택 여부 (default : False)

    station_list = ["수서", "동탄", "평택지제", "천안아산", "오송", "대전", "김천(구미)", "동대구",
    "신경주", "울산(통도사)", "부산", "공주", "익산", "정읍", "광주송정", "나주", "목포"]



## 간단 사용법

회원번호 1234567890  
비밀번호 000000  
동탄 -> 동대구, 2022년 01월 17일 오전 8시 이후 기차  
검색 결과 중 상위 2개가 예약 가능할 경우 예약

```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08
```

**Optional**  
예약대기 사용 및 검색 결과 상위 3개의 예약 가능 여부 확인
```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --num 3 --reserve True
```

검색 결과 중 8시 이후 3번째 기차 시간대부터 5번째 기차 시간대까지만 예약 하고 싶을 경우

```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --num 5 --num_s 3
```

검색 결과 중 8시 이후 승객 2명 예약 하고 싶을 경우

```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --ps 2
```

**실행 결과**

![](./img/img1.png)

## 기타  
명절 승차권 예약에는 사용이 불가합니다.  
