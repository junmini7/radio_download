import youtube_dl

ydl = youtube_dl.YoutubeDL(
    {
        "outtmpl": "%(id)s.%(ext)s",
        "format": " bestaudio/best",
        "extractaudio": True,
        "listformats": False,
        "nocheckcertificate": True,
        'download':False
    }
)
#유튜브 썸네일

def mp3(v):
    inf = ydl.extract_info(v, download=False)
    dic = {i["format_id"]: i["url"] for i in inf["formats"]}
    if "140" in dic:
        inf['mp3']= dic["140"]
    else:
        inf['mp3']= dic[
            str(max([int(j) for j in list(set(dic.keys()) & {"249", "250", "251"})]))
        ]
    return inf

def default_link():
    a=['https://www.youtube.com/watch?v=jUmeh5yvy0M','https://www.youtube.com/watch?v=ma8FcJxhZnw','https://www.youtube.com/watch?v=VOmIplFAGeg']
    return [mp3(i) for i in a]