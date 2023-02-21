
rpi_music = MusicPlayer()
@app.get("/home", response_class=JSONResponse)
def home_status(request: Request):
    ip = str(request.client.host)
    # {'url': inf['mp3'], 'title': inf['title'], 'artist': inf['uploader'], 'thumbnail': inf['thumbnail'],
    # 'description': inf['description'], 'real_url': f"https://youtu.be/{inf['id']}"})
    result = {
        "ip": ip, "volume": rpi_music.volume, 'playlist': rpi_music.playlist,
                    'is_playing': rpi_music.is_playing(),
        'playlist_html': "".join([playlist_template.render(real_url=i['real_url'], thumbnail=i['thumbnail'],
                                                           description=i['description'], artist=i['artist'],
                                                           title=i['title']) for i in rpi_music.playlist])}
    now_index = rpi_music.now_index()
    result['now_index'] = now_index
    if now_index != -1:
        result['now_playing'] = rpi_music.playlist[now_index]
    else:
        result['now_playing'] = False
    return {'content':result}


@app.get("/home/play", response_class=JSONResponse)
def play(request: Request):
    ip = str(request.client.host)
    rpi_music.play()
    return {"content": {"ip": ip}}


@app.get("/home/pause", response_class=JSONResponse)
def pause(request: Request):
    ip = str(request.client.host)
    rpi_music.pause()
    return {"content": {"ip": ip}}


@app.get("/home/next", response_class=JSONResponse)
def pause(request: Request):
    ip = str(request.client.host)
    rpi_music.next()
    return {"content": {"ip": ip}}


@app.get("/home/previous", response_class=JSONResponse)
def pause(request: Request):
    ip = str(request.client.host)
    rpi_music.previous()
    return {"content": {"ip": ip}}


@app.get("/home/set_volume", response_class=JSONResponse)
def set_volume(request: Request, value=100):
    ip = str(request.client.host)
    rpi_music.set_volume(value)
    return {"content": {"ip": ip, 'volume': value}}


@app.get("/home/get_volume", response_class=JSONResponse)
def get_volume(request: Request):
    ip = str(request.client.host)
    return {"content": {"ip": ip, 'volume': rpi_music.volume}}


@app.get("/home/change_volume", response_class=JSONResponse)
def change_volume(request: Request, value=10):
    ip = str(request.client.host)
    rpi_music.change_volume(value)
    return {"content": {"ip": ip, 'volume': rpi_music.volume}}


class music_info(BaseModel):
    link: Union[str, None] = None
    youtube: Union[str, None] = None
    radio: Union[str, None] = None
    time: int = 10800
    repeat: bool = True
    play: bool = True


@app.post("/home/append", response_class=JSONResponse)
def append(request: Request, data: music_info):
    ip = str(request.client.host)
    if data.youtube:
        try:
            inf = mp3(data.youtube)
        except:
            return {'error': '유튜브 주소가 올바르지 않습니다!'}
        rpi_music.append(
            {'url': inf['mp3'], 'title': inf['title'], 'artist': inf['uploader'], 'thumbnail': inf['thumbnail'],
             'description': inf['description'], 'real_url': f"https://youtu.be/{inf['id']}"})
        rpi_music.play()
    if data.radio:
        code = kbs.id_to_code(data.radio)
        url_information = kbs.channel(code)
        program_information = kbs.on_air([code])[code][0]
        rpi_music.set_playlist([
            {'url': url_information['url'], 'title': program_information['title'],
             'artist': f'{program_information["actor"]}({program_information["staff"]})',
             'thumbnail': program_information['thumbnail'], 'description': program_information['description'],
             'real_url': program_information['url']}]
        )
        rpi_music.play()
    return {"content": {"ip": ip, 'success': f"성공했습니다!"}}
