import requests
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
from threading import Thread
from fastapi_utils.tasks import repeat_every
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
download_events = [["18:00", 7200, "1fm"], ["01:00", 7200, "1fm"]]
codecs = [["mp3", "libmp3lame"], ["m4a", "aac"]]
codec = codecs[0]
id_to_ko_name = {
    "1fm": "Classic FM",
    "2fm": "Cool FM",
    "worldradio": "KBS WORLD Radio CH2",
    "wink11": "KBS WORLD Radio CH1",
    "hanminjokradio": "한민족방송",
}
record_channel_ids = ["1fm"]
now_recording = defaultdict(lambda: False)


def tdtoko(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}시간{minutes}분{seconds}초"


def tdtoen(time_diff: td):
    s = int(time_diff.total_seconds())
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
        self.record_schedules = None
        self.channels_list = self.channels()
        self.codes = [i["code"] for i in self.channels_list.values()]
        self.update_schedules()

    def update_schedules(self):
        self.record_schedules = self.schedules([self.id_to_code(id) for id in record_channel_ids])

    def channels(self):
        channels_info = requests.get(
            "https://cfpwwwapi.kbs.co.kr/api/v1/landing/live"
        ).json()["channel"][3]["channel_master"]
        result = {}
        for channel_info in channels_info:
            result[channel_info["item"][0]["channel_id"]] = {
                "code": channel_info["channel_code"],
                "title": channel_info["title"],
                "logo": channel_info["image_path_channel_logo"],
                "thumbnail": channel_info["image_path_video_thumbnail"],
            }
        return result

    def channel(self, channel_code="24"):
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

    def bitrate_parser(self, bitrate):
        return bitrate.replace("Kbps", "k")

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

    def schedules(
            self,
            channel_codes=None,
            start=date.today() - td(days=1),
            end=date.today() + td(days=1),
    ):
        if channel_codes is None:
            channel_codes = ["24"]
        else:
            channel_codes = [str(i) for i in channel_codes]
        schedules_info = requests.get(
            f'https://static.api.kbs.co.kr/mediafactory/v1/schedule/weekly?rtype=json&local_station_code=00&channel_code={",".join(channel_codes)}&program_planned_date_from={dt.strftime(start, "%Y%m%d")}&program_planned_date_to={dt.strftime(end, "%Y%m%d")}'
        ).json()
        schedules_data = defaultdict(list)
        for day_schedule in schedules_info:
            schedules_data[day_schedule["channel_code"]] += [
                self.schedule_parser(i) for i in day_schedule["schedules"]
            ]
        return schedules_data

    def schedule_parser(self, schedule_data):
        start = dt.strptime(
            schedule_data["service_date"] + schedule_data["service_start_time"],
            "%Y%m%d%H%M%S00",
        )  # actual datetime
        end = dt.strptime(
            schedule_data["service_date"] + schedule_data["service_end_time"],
            "%Y%m%d%H%M%S00",
        )
        if end < start:
            end += td(days=1)
        result = {
            "title": schedule_data["program_title"],
            "is_live": schedule_data["rerun_classification"],
            "date": dt.strptime(
                schedule_data["service_date"], "%Y%m%d"
            ),  # actual date, planned date has no meaning
            "description": schedule_data["program_intention"],
            "staff": schedule_data["program_staff"],
            "actor": schedule_data["program_actor"],
            "genre": schedule_data["program_genre"],
            "thumbnail": schedule_data["image_w"],
            "url": schedule_data["homepage_url"],
            "start": start,
            "end": end,
            "duration": td(minutes=int(schedule_data["program_planned_duration_m"])),
            "schedule_id": schedule_data["schedule_unique_id"],
            "id": schedule_data["program_id"],
        }
        return result

    def id_to_code(self, id):
        return self.channels_list[id]["code"]

    def download(self, id="1fm", record_time=15, program_information=None):
        now = dt.now().strftime("%Y%m%d%H%M%S")
        # now = dt.now().strftime("%Y년%m월%d일%H시%M분%S초")
        code = self.id_to_code(id)
        url_info = self.channel(code)
        if program_information is None:
            program_information = self.on_air([code])[code][0]
        filename = f"{now}_{id}_{program_information['title'].replace(' ', '_')}_{program_information['is_live']}_{tdtoko(record_time)}.{codec[0]}"
        now_downloading[filename] = [dt.now(), False, td(seconds=record_time)]
        file_path = f"{music_directory}{filename}"
        today_date = program_information["date"].strftime("%Y%m%d")
        thumbnail_url = program_information["thumbnail"]
        thumbnail_filename = self.download_image(
            program_information["id"] + ".jpg", thumbnail_url
        )
        download_command = (
            f'ffmpeg -re -i "{url_info["url"]}" -vn -acodec {codec[1]} -b:a {self.bitrate_parser(url_info["bitrate"])} -t {record_time} -metadata title="{program_information["title"]}_{today_date}" -metadata description="{program_information["description"]}" -metadata date="{today_date}" -metadata author="{program_information["actor"]}({program_information["staff"]})" -metadata album="{program_information["title"]}" -metadata track="{today_date}" -f {codec[0]} - | ffmpeg -i /dev/stdin -i "{thumbnail_filename}" -map 0:0 -map 1:0 -c copy -id3v2_version 3 "{file_path}"',
            # > "log/{filename}.log" 2>&1',
        )
        subprocess.run(download_command, shell=True)
        now_downloading[filename][1] = dt.now()
        """ffmpeg -i in.mp3 -i test.png -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" out.mp3"""

    def record_download(self, id, program_schedule):
        now_recording[id] = True
        self.download(
            id, (program_schedule["end"] - dt.now()).total_seconds(), program_schedule
        )
        now_recording[id] = False

    def download_image(self, filename, url):
        path = os.path.join("img", filename)
        if not os.path.exists(path):
            try:
                r = requests.get(url, stream=True)
            except:
                print(url)
                # raise FileNotFoundError
            else:
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        for chunk in r:
                            f.write(chunk)
        return path

    def actual_download(self, url_info, record_time, program_information, filename):
        now = dt.now().strftime("%Y%m%d%H%M%S")


kbs = KBS()

# for download_event in download_events:
#     schedule.every().day.at(download_event[0]).do(
#         kbs.download, download_event[2], download_event[1]
#     )
max_bar = 200


@app.get("/", response_class=HTMLResponse)
def index():
    files = os.listdir(music_directory)
    files.sort(reverse=True)
    result = ""
    for file in files:
        channel = file.split("_")[1]
        radio_channel_logo = kbs.channels_list[channel]["logo"]
        if file in now_downloading:
            if not now_downloading[file][1]:
                download_information = f"""{tdtoen(dt.now() - now_downloading[file][0])}/{tdtoen(now_downloading[file][2])} ({int((dt.now() - now_downloading[file][0]).total_seconds() / now_downloading[file][2].total_seconds() * 100)}%)"""
            else:
                download_information = f"{tdtoko_large(dt.now() - now_downloading[file][0])} 전 다운로드 완료"  # , {tdtoko_large(now_downloading[file][1] - now_downloading[file][0])} 동안
        else:
            download_information = ""
        result += f"""<img src='{radio_channel_logo}' height='30'></img>{file} {convert_size(os.path.getsize(f'{music_directory}{file}'))}&emsp;{download_information}<br>"""
        if file not in now_downloading or now_downloading[file][1]:
            result += f"""<div class='row col-12 col-md-11 centering centering_text gx-5'>
        <div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-primary' onclick='download_file("/music/{file}","{file}")'>다운로드</button></div></div><div class="col-12 col-md-5 col-xl-3 centering" style="margin-bottom:10px"><div class="row">
    <button class='btn btn-danger' onclick='delete_file("{file}")'>삭제</button></div></div></div><br><audio controls><source src='/music/{file}' type='audio/mp3'></audio><br>"""
        result += "<br>"

    if not files:
        result += "아직 다운로드된 파일이 하나도 없습니다."
    result += f"""<br>예정된 다운로드 이벤트 : {', '.join([f'{i[0]}에 {tdtoko(i[1])} 동안 {i[2]} 채널' for i in download_events])} 다운로드가 예정되어 있습니다."""
    return result


@app.get("/delete", response_class=JSONResponse)
def delete(name: str, request: Request):
    ip = str(request.client.host)
    if ip.startswith("192.168"):
        try:
            # os.remove(f"{music_directory}{name}")
            shutil.move(f"{music_directory}{name}", f"{deleted_directory}{name}")
            return {"content": f"{name} 삭제 성공!"}
        except:
            return {"content": f"{name} 삭제 실패..."}
    else:
        return {"content": "로컬 네트워크에서만 삭제가 가능합니다."}


@app.get("/record", response_class=JSONResponse)
def record(record_time: int = 1, channel="1fm"):
    # if now_recording[channel]:
    #     return {'content':f'현재 {channel} 채널로 다운로드 중이므로 끝난 후 이용해주세요.'}
    Thread(target=kbs.download, args=(channel, record_time * 60)).start()
    return {"content": f"{channel}채널에서 {record_time}분간 다운로드를 시작했습니다!"}



@app.get("/schedules", response_class=JSONResponse)
def recordschedules():
    return kbs.record_schedules


@app.get("/now_recording", response_class=JSONResponse)
def nowrecording():
    return now_recording


@app.get("/now_downloading", response_class=JSONResponse)
def nowdown():
    return now_downloading


@app.on_event("startup")
@repeat_every(seconds=300)
def schedule_update():
    kbs.update_schedules()


@app.on_event("startup")
@repeat_every(seconds=1)
def schedule_check() -> None:
    for id in record_channel_ids:
        schedules = kbs.record_schedules[kbs.id_to_code(id)]
        for program_schedule in schedules:
            if (
                    program_schedule["start"] - td(seconds=10)
                    <= dt.now()
                    < program_schedule["end"]
                    and not now_recording[id]
            ):  # 10초전 시작
                Thread(target=kbs.record_download, args=(id, program_schedule)).start()
