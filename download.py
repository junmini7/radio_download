import requests
from bs4 import BeautifulSoup as bs
import subprocess
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import date
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    PlainTextResponse,
    FileResponse,
    JSONResponse,
)
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
import os
import schedule
from threading import Thread
from fastapi_utils.tasks import repeat_every
import time
import math
from typing import List, Set, Dict, Tuple, Any
import shutil

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
now_downloading = {}
size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
music_directory = "/web/music/"
deleted_directory = "/web/deleted_music/"
quality_option = "128k"
download_events = [["18:00", 7200, '1fm'], ["01:00", 7200,'1fm']]
codecs = [["mp3", "libmp3lame"], ["m4a", "aac"]]
codec = codecs[0]
id_to_ko_name = {'1fm': "Classic FM", '2fm': 'Cool FM', 'worldradio': 'KBS WORLD Radio CH2',
                 'wink11': 'KBS WORLD Radio CH1', 'hanminjokradio': '한민족방송'}





def tdtoko(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}시간{minutes}분{seconds}초"


def tdtoen(time_diff:td):
    s=int(time_diff.total_seconds())
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def tdtoko_large(ti: td):  # 1시간 30분 이렇게 시 분 까지는 표시??
    ms, s, d = ti.microseconds, ti.seconds, ti.days
    if d > 365.25:
        return f"{int(d / 365.25)}년"
    if d > 365 / 12:
        return f"{int(d / (365 / 12))}달"
    if d > 0:
        return f"{d}일"
    if s > 3600:
        return f"{int(s / 3600)}시간"
    if s > 60:
        return f"{int(s / 60)}분"
    if s > 0:
        return f"{s}초"
    if ms > 1000:
        return f"{int(ms / 1000)}ms"
    return f"{ms}us"


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


# 스트림 주소 등 정보
"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/24"
# 현재 방솓ㅇ

"https://static.api.kbs.co.kr/mediafactory/v1/schedule/onair_now?rtype=json&local_station_code=00&channel_code=24"
# 모든 방송
"https://static.api.kbs.co.kr/mediafactory/v1/schedule/onair_now?rtype=json&local_station_code=00&channel_code=11,12,14,81,N91,N92,N94,N93,N96,23,25,26,wink11,I92,cctv01,51,52,61,21,22,24"
# 예정
"https://static.api.kbs.co.kr/mediafactory/v1/schedule/weekly?rtype=json&local_station_code=00&channel_code=24&program_planned_date_from=20230129&program_planned_date_to=20230129"


# 모든 채널 리스트


class KBS:
    def __init__(self):
        self.channels_list = self.channels()

    def channels(self):
        channels_info = requests.get("https://cfpwwwapi.kbs.co.kr/api/v1/landing/live").json()[
            "channel"
        ][3]["channel_master"]
        result = {}
        for channel_info in channels_info:
            result[channel_info['item'][0]['channel_id']] = {
                'code': channel_info['channel_code'],
                'title': channel_info['title'],
                "logo": channel_info["image_path_channel_logo"],
                "thumbnail": channel_info["image_path_video_thumbnail"],
            }
        return result

    def channel(self, channel_code='24'):
        url_info = requests.get(
            f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{channel_code}"
        ).json()
        result = {
            "url": url_info["channel_item"][0]["service_url"],
            "bitrate": url_info["channel_item"][0]["bitrate"],  # 비트레이트 적용
            "code": url_info["channel_item"][0]["channel_code"],
            "id": url_info["channel_item"][0]["channel_id"],
            "logo": url_info["channelMaster"]["image_path_channel_logo"],
            "thumbnail": url_info["channelMaster"]["image_path_video_thumbnail"],
            "title": url_info["channelMaster"]["title"],
        }
        return result

    def on_air(self, channel_codes=None):
        if channel_codes is None:
            channel_codes = ["24"]
        else:
            channel_codes = [str(i) for i in channel_codes]
        on_air_info = requests.get(
            f"https://static.api.kbs.co.kr/mediafactory/v1/schedule/onair_now?rtype=json&local_station_code=00&channel_code={','.join(channel_codes)}"
        ).json()
        on_air_data = {
            i["channel_code"]: [self.schedule_parser(i) for i in i["schedules"]]
            for i in on_air_info
        }
        return on_air_data

    def schedules(self, channel_codes=None, start=date.today(), end=date.today()):
        if channel_codes is None:
            channel_codes = ["24"]
        else:
            channel_codes = [str(i) for i in channel_codes]
        schedules_info = requests.get(
            f'https://static.api.kbs.co.kr/mediafactory/v1/schedule/weekly?rtype=json&local_station_code=00&channel_code={",".join(channel_codes)}&program_planned_date_from={dt.strftime(start, "%Y%m%d")}&program_planned_date_to={dt.strftime(end, "%Y%m%d")}'
        ).json()
        schedules_data = defaultdict(dict)
        for schedule in schedules_info:
            schedules_data[schedule["channel_code"]][
                dt.strptime(schedule["program_planned_date"], "%Y%m%d")
            ] = [self.schedule_parser(i) for i in schedule["schedules"]]
        return schedules_data

    def schedule_parser(self, schedule_data):
        result = {
            "title": schedule_data["program_title"],
            "is_live": schedule_data["rerun_classification"],
            "date": dt.strptime(schedule_data["service_date"], "%Y%m%d"),
            "description": schedule_data["program_intention"],
            "staff": schedule_data["program_staff"],
            "actor": schedule_data["program_actor"],
            "genre": schedule_data["program_genre"],
            "thumbnail": schedule_data["image_w"],
            "url": schedule_data["homepage_url"],
            "start": dt.strptime(schedule_data["service_start_time"], "%H%M%S00"),
            "end": dt.strptime(schedule_data["service_end_time"], "%H%M%S00"),
            "duration": td(minutes=int(schedule_data["program_planned_duration_m"])),
            "schedule_id": schedule_data["schedule_unique_id"],
            "id": schedule_data["program_id"],
        }
        return result

    def download(self, id="1fm", record_time=15):
        now = dt.now().strftime("%Y%m%d%H%M%S")
        #now = dt.now().strftime("%Y년%m월%d일%H시%M분%S초")
        code = self.channels_list[id]['code']
        url = self.channel(code)['url']
        program_information = kbs.on_air([code])[code][0]
        today_date = program_information['date'].strftime("%Y%m%d")
        filename = f"{id}_{program_information['title'].replace(' ','_')}_{now}_{tdtoko(record_time)}.{codec[0]}"
        now_downloading[filename] = [dt.now(), False, td(seconds=record_time)]
        Thread(
            target=actual_download,
            args=(
                f'ffmpeg -re -i "{url}" -vn -acodec {codec[1]} -b:a {quality_option} -t {record_time} -metadata title="{program_information["title"]}_{today_date}" -metadata description="{program_information["description"]}" -metadata date="{today_date}" -metadata author="{program_information["actor"]}({program_information["staff"]})" -metadata album="{program_information["title"]}" -metadata track="{today_date}" "{music_directory}{filename}" > "log/{filename}.log" 2>&1',
                filename,
            ),
        ).start()
        return filename


kbs = KBS()


def actual_download(command, filename):
    subprocess.run(command, shell=True)
    now_downloading[filename][1] = dt.now()


for download_event in download_events:
    schedule.every().day.at(download_event[0]).do(kbs.download, download_event[2], download_event[1])
max_bar = 200


@app.get("/", response_class=HTMLResponse)
def index():
    files = os.listdir(music_directory)
    files.sort(reverse=True)
    result = ""
    for file in files:
        channel=file.split('_')[0]
        radio_channel_logo=kbs.channels_list[channel]['logo']
        if file in now_downloading:
            if not now_downloading[file][1]:
                download_information = f"""{tdtoen(dt.now() - now_downloading[file][0])}/{tdtoen(now_downloading[file][2])} ({int((dt.now() - now_downloading[file][0]).total_seconds()/now_downloading[file][2].total_seconds()*100)}%)"""
            else:
                download_information = f"{tdtoko_large(dt.now() - now_downloading[file][0])} 전 다운로드 완료" #, {tdtoko_large(now_downloading[file][1] - now_downloading[file][0])} 동안
        else:
            download_information = ""
        result += f"""<img src='{radio_channel_logo}' height='30'></img>{file} {convert_size(os.path.getsize(f'{music_directory}{file}'))}&emsp;{download_information}
        <br>
        <div class='row col-12 col-md-11 centering centering_text gx-5'>
        <div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='download_file("/music/{file}","{file}")'>다운로드</button></div></div>
    {f'''<div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-danger' onclick='delete_file("{file}")'>삭제</button></div></div>''' if file not in now_downloading or now_downloading[file][1] else ""}
        </div>
        <br><audio controls><source src='/music/{file}' type='audio/mp3'></audio><br><br>"""
    if not files:
        result += "아직 다운로드된 파일이 하나도 없습니다."
    result += f"""<br>예정된 다운로드 이벤트 : {', '.join([f'{i[0]}에 {tdtoko(i[1])} 동안 {i[2]} 채널' for i in download_events])} 다운로드가 예정되어 있습니다."""
    return result

@app.get("/delete", response_class=JSONResponse)
def delete(name: str):
    try:
        # os.remove(f"{music_directory}{name}")
        shutil.move(f"{music_directory}{name}", f"{deleted_directory}{name}")
        return {"content": f"{name} 삭제 성공!"}
    except:
        return {"content": f"{name} 삭제 실패..."}


@app.get("/record", response_class=JSONResponse)
def record(record_time: int = 1, channel='1fm'):
    return {"content": kbs.download(channel, record_time * 60)}


@app.on_event("startup")
@repeat_every(seconds=1)
def every_music() -> None:
    schedule.run_pending()
