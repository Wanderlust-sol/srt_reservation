import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
from .main import SRT
from . import util
import threading

# .env 파일에서 환경변수 로드
load_dotenv()

# 대화 상태를 위한 상수
DPT_STN, ARR_STN, DATE, TIME, NUM_PEOPLE, NUM_TRAINS, NUM_TRAINS_START, WANT_RESERVE = range(8)

# 자주 사용하는 역 키보드
STATION_KEYBOARD = [
    ['수서', '동탄', '평택지제'],
    ['천안아산', '오송', '대전'],
    ['김천구미', '동대구', '신경주'],
    ['울산', '부산']
]

# 예/아니오 키보드
YES_NO_KEYBOARD = [['예', '아니오']]

def start(update, context):
    update.message.reply_text(
        '안녕하세요! SRT 예약 봇입니다.\n'
        '/reserve 명령어로 예약을 시작할 수 있습니다.\n'
        '/cancel 명령어로 언제든 예약을 취소할 수 있습니다.'
    )

def reserve(update, context):
    reply_markup = ReplyKeyboardMarkup(STATION_KEYBOARD, one_time_keyboard=True)
    update.message.reply_text('출발역을 선택해주세요:', reply_markup=reply_markup)
    return DPT_STN

def dpt_stn(update, context):
    context.user_data['dpt_stn'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(STATION_KEYBOARD, one_time_keyboard=True)
    update.message.reply_text('도착역을 선택해주세요:', reply_markup=reply_markup)
    return ARR_STN

def arr_stn(update, context):
    context.user_data['arr_stn'] = update.message.text
    update.message.reply_text(
        '날짜를 입력해주세요 (YYYYMMDD 형식)\n'
        '예: 20240401',
        reply_markup=ReplyKeyboardRemove()
    )
    return DATE

def date(update, context):
    context.user_data['date'] = update.message.text
    update.message.reply_text('시간을 입력해주세요 (HH 형식, 짝수)\n예: 06, 08, 14')
    return TIME

def time(update, context):
    context.user_data['time'] = update.message.text
    update.message.reply_text('예약할 인원 수를 입력해주세요 (숫자만)\n예: 1')
    return NUM_PEOPLE

def num_people(update, context):
    context.user_data['num_people'] = int(update.message.text)
    update.message.reply_text('검색할 기차의 수를 입력해주세요 (숫자만)\n예: 2')
    return NUM_TRAINS

def num_trains(update, context):
    context.user_data['num_trains'] = int(update.message.text)
    update.message.reply_text('검색 시작할 기차 순번을 입력해주세요 (숫자만)\n예: 1')
    return NUM_TRAINS_START

def num_trains_start(update, context):
    context.user_data['num_trains_start'] = int(update.message.text)
    reply_markup = ReplyKeyboardMarkup(YES_NO_KEYBOARD, one_time_keyboard=True)
    update.message.reply_text('예약 대기를 사용하시겠습니까?', reply_markup=reply_markup)
    return WANT_RESERVE

def want_reserve(update, context):
    context.user_data['want_reserve'] = True if update.message.text == '예' else False
    
    # 예약 실행
    def run_reservation():
        try:
            srt = SRT(
                context.user_data['dpt_stn'],
                context.user_data['arr_stn'],
                context.user_data['date'],
                context.user_data['time'],
                context.user_data['num_people'],
                context.user_data['num_trains'],
                context.user_data['num_trains_start'],
                context.user_data['want_reserve']
            )
            srt.run(
                os.getenv('SRT_ID'),
                os.getenv('SRT_PW')
            )
            update.message.reply_text("예약 시도가 완료되었습니다!")
        except Exception as e:
            update.message.reply_text(f"예약 중 오류가 발생했습니다: {str(e)}")

    update.message.reply_text(
        f"예약을 시도합니다...\n"
        f"출발: {context.user_data['dpt_stn']}\n"
        f"도착: {context.user_data['arr_stn']}\n"
        f"날짜: {context.user_data['date']}\n"
        f"시간: {context.user_data['time']}\n"
        f"인원: {context.user_data['num_people']}명\n"
        f"검색할 기차 수: {context.user_data['num_trains']}\n"
        f"시작 기차 순번: {context.user_data['num_trains_start']}\n"
        f"예약 대기 사용: {'예' if context.user_data['want_reserve'] else '아니오'}"
    )
    
    thread = threading.Thread(target=run_reservation)
    thread.start()
    
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text('예약이 취소되었습니다.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    updater = Updater(os.getenv('TELEGRAM_TOKEN'), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('reserve', reserve)],
        states={
            DPT_STN: [MessageHandler(Filters.text & ~Filters.command, dpt_stn)],
            ARR_STN: [MessageHandler(Filters.text & ~Filters.command, arr_stn)],
            DATE: [MessageHandler(Filters.text & ~Filters.command, date)],
            TIME: [MessageHandler(Filters.text & ~Filters.command, time)],
            NUM_PEOPLE: [MessageHandler(Filters.text & ~Filters.command, num_people)],
            NUM_TRAINS: [MessageHandler(Filters.text & ~Filters.command, num_trains)],
            NUM_TRAINS_START: [MessageHandler(Filters.text & ~Filters.command, num_trains_start)],
            WANT_RESERVE: [MessageHandler(Filters.text & ~Filters.command, want_reserve)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()