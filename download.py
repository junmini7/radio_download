import requests
from bs4 import BeautifulSoup as bs
import signal
import os
import subprocess
from datetime import datetime as dt
from datetime import date
import time
import mutagen
import mutagen.mp3
from mutagen.easyid3 import EasyID3

url = 'http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=24'
url2 = "http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=24&ch_type=radioList"
data = bs(requests.get(url).text, 'html.parser').findAll('script')[18].text
# data_2=bs(requests.get(url2).text,'html.parser').findAll('script')[18].text
temp = data[data.find('channel_item') + 35:]
real_url = temp[:temp.index('"') - 1]
today_date = dt.now().strftime('%Y%m%d')
print(real_url)
subprocess.Popen(f'ffmpeg -i "{real_url}" -vn -acodec libmp3lame -t 15 -metadata title="Every_music_{today_date}" -metadata date="{today_date}" -metadata album="KBS" -metadata track="{today_date}" ./data/everymusic_{today_date}.mp3',shell=True)


