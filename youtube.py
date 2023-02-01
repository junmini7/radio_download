import youtube_dl

ydl = youtube_dl.YoutubeDL(
    {
        "outtmpl": "%(id)s.%(ext)s",
        "format": " bestaudio/best",
        "extractaudio": True,
        "listformats": False,
        'nocheckcertificate': True,
    }
)


def mp3(v):
    inf = ydl.extract_info(v, download=False)
    dic = {i["format_id"]: i["url"] for i in inf["formats"]}
    if "140" in dic:
        return dic["140"]
    else:
        return dic[str(max([int(j) for j in list(set(dic.keys()) & {"249", "250", "251"})]))]
