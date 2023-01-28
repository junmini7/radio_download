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


def tdtoko(ti: td):
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
    now = dt.now().strftime("%Y%m%d%H%M%S")
    print(real_url)
    filename = f"everymusic_{now}_{record_time}s.mp3"
    now_downloading[filename] = [dt.now(), False]
    Thread(target=actual_download, args=(
    f'ffmpeg -i "{real_url}" -vn -acodec libmp3lame -t {record_time} -metadata title="Every_music_{today_date}" -metadata date="{today_date}" -metadata album="KBS" -metadata track="{today_date}" /web/music/{filename}',
    filename)).start()
    return filename


def actual_download(command, filename):
    subprocess.run(command,  shell=True)
    now_downloading[filename][1] = dt.now()


schedule.every().day.at("18:00").do(download, 7200)
schedule.every().day.at("01:00").do(download, 7200)


os.path.getsize
@app.get("/", response_class=HTMLResponse)
def index():
    files = os.listdir('/web/music')
    files.sort(reverse=True)
    result = "".join([
                         f"<p>{k} : {tdtoko(dt.now() - v[0])}전부터 다운로드 시작, {f'{tdtoko(dt.now() - v[1])}전에 다운로드 완료' if v[1] else '아직 다운로드 중'}</p>"
                         for k, v in now_downloading.items()])
    for file in files:
        result += f"<a href='/music/{file}' download='{file}'>{file} {convert_size(os.path.getsize(f'/web/music/{file}'))}</a><br><audio controls><source src='/music/{file}' type='audio/mp3'></audio><br><br>"
    if result:
        return result
    else:
        return "nothing"


@app.get("/record", response_class=JSONResponse)
def record(time: int = 15):
    return {"content": download(time)}


@app.on_event("startup")
@repeat_every(seconds=60)
def every_music() -> None:
    schedule.run_pending()
