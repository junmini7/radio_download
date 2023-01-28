import requests
from bs4 import BeautifulSoup as bs
import subprocess
from datetime import datetime as dt
from datetime import timedelta as td
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    PlainTextResponse,
    FileResponse,
    JSONResponse,

)
from fastapi.middleware.cors import CORSMiddleware
import os
import schedule
from threading import Thread
from fastapi_utils.tasks import repeat_every
import time
import math

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
now_downloading = {}


def tdtoen(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}H{minutes:02}M{seconds:02}S"


def tdtoko(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}시간{minutes}분{seconds}초"


def tdtoko_large(ti: td):
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


size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
music_directory = "/web/music/"


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def download(record_time=15, channel_code=24):
    url = f'http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={channel_code}'
    url2 = f"http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={channel_code}&ch_type=radioList"
    data = bs(requests.get(url).text, 'html.parser').findAll('script')[18].text
    # data_2=bs(requests.get(url2).text,'html.parser').findAll('script')[18].text
    temp = data[data.find('channel_item') + 35:]
    real_url = temp[:temp.index('"') - 1]
    today_date = dt.now().strftime('%Y%m%d')
    now = dt.now().strftime("%Y년%m월%d일%H시%M분%S초")
    print(real_url)
    filename = f"KBS_{now}_{tdtoko(record_time)}.mp3"
    now_downloading[filename] = [dt.now(), False, td(seconds=record_time)]
    Thread(target=actual_download, args=(
        f'ffmpeg -i "{real_url}" -vn -acodec libmp3lame -t {record_time} -metadata title="Every_music_{today_date}" -metadata date="{today_date}" -metadata album="KBS" -metadata track="{today_date}" {music_directory}{filename}',
        filename)).start()
    return filename


def actual_download(command, filename):
    subprocess.run(command, shell=True)
    now_downloading[filename][1] = dt.now()


download_events = [["18:00", 7200], ["01:00", 7200]]
for download_event in download_events:
    schedule.every().day.at(download_event[0]).do(download, download_event[1])


@app.get("/", response_class=HTMLResponse)
def index():
    files = os.listdir(music_directory)
    files.sort(reverse=True)
    result = ""
    for file in files:
        if file in now_downloading:
            if not now_downloading[file][1]:
                introduce=f"{tdtoko_large(dt.now() - now_downloading[file][0])} 전부터 다운로드 중, {tdtoko_large(now_downloading[file][2] - (dt.now() - now_downloading[file][0]))} 후 완료 예정"
            else:
                introduce = f"{tdtoko_large(dt.now() - now_downloading[file][0])}전 {tdtoko_large(now_downloading[file][1] - now_downloading[file][0])} 동안 다운로드 완료"
        else:
            introduce=""
        result += f"""{file} {convert_size(os.path.getsize(f'{music_directory}{file}'))}&emsp;{introduce}
        <br><a href='/music/{file}' download='{file}'>다운로드</a>{f'''&emsp;<a onclick='delete_file("{file}")'>삭제</a>''' if file not in now_downloading or now_downloading[file][1] else ""}<br><audio controls><source src='/music/{file}' type='audio/mp3'></audio><br><br>"""
    if not files:
        result += "아직 다운로드된 파일이 하나도 없습니다."
    result += f"""<br>예정된 다운로드 이벤트 : {', '.join([f'{i[0]}에 {tdtoko(i[1])} 동안' for i in download_events])} 다운로드가 예정되어 있습니다."""
    return result


@app.get("/delete", response_class=JSONResponse)
def delete(name: str):
    try:
        os.remove(f'{music_directory}{name}')
        return {'content': f"{name} 삭제 성공!"}
    except:
        return {'content': f"{name} 삭제 실패..."}


@app.get("/record", response_class=JSONResponse)
def record(time: int = 1):
    return {"content": download(time*60)}


@app.on_event("startup")
@repeat_every(seconds=60)
def every_music() -> None:
    schedule.run_pending()
