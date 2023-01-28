import requests
from bs4 import BeautifulSoup as bs
import subprocess
from datetime import datetime as dt
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

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI()


def download(record_time=15, channel_code=24):
    url = f'http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={channel_code}'
    url2 = f"http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code={channel_code}&ch_type=radioList"
    data = bs(requests.get(url).text, 'html.parser').findAll('script')[18].text
    # data_2=bs(requests.get(url2).text,'html.parser').findAll('script')[18].text
    temp = data[data.find('channel_item') + 35:]
    real_url = temp[:temp.index('"') - 1]
    today_date = dt.now().strftime('%Y%m%d')
    print(real_url)
    subprocess.Popen(
        f'ffmpeg -i "{real_url}" -vn -acodec libmp3lame -t {record_time} -metadata title="Every_music_{today_date}" -metadata date="{today_date}" -metadata album="KBS" -metadata track="{today_date}" /web/music/everymusic_{today_date}.mp3',
        shell=True)


@app.get("/", response_class=HTMLResponse)
def index():
    files = os.listdir('/web/music')
    result = ""
    for file in files:
        result += f"<a href='/music/{file}' download='{file}'>{file}</a><br>"
    return result
