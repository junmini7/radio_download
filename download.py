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
print(real_url)
process = subprocess.Popen(f'mplayer {real_url} -ao pcm:file=test.flv -vc dummy -vo null', shell=True, preexec_fn=os.setsid)
time.sleep(15)
os.killpg(os.getpgid(process.pid), signal.SIGTERM)

def __change_meta_data(file_name):
    file_path = "./data/" + file_name + ".mp3"
    try:
        meta = EasyID3(file_path)
    except mutagen.id3.ID3NoHeaderError:
        meta = mutagen.File(file_path, easy=True)
        meta.add_tags()
    today_date = dt.now().strftime('%Y%m%d')
    meta['title'] = str(dt.now())
    meta["artist"] = today_date + "_KBS"
    meta["genre"] = today_date + "_RADIO"
    meta["album"] = today_date + "_ALBUM"
    meta.save()
    print("META", str(meta))


def __flv_to_mp3(absolute_path):
    try:
        subprocess.run("ffmpeg -i " + str(absolute_path) + ".flv -acodec mp3 " + absolute_path + ".mp3",
                       stdout=subprocess.PIPE, shell=True)
    except subprocess.CalledProcessError as sub_exception:
        print("ERROR With RTMP:", sub_exception)


def his():
    file_name = str(dt.now()) + "FILE_KBS"
    absolute_path = "./data/" + file_name
    print("CHECK", absolute_path)


    __flv_to_mp3(absolute_path)
    __change_meta_data(absolute_path, file_name)



