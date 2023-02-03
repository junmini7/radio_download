from vlc import Instance
from urllib.request import url2pathname
from urllib.parse import urlparse
import os
import vlc
from vlc import Media, MediaList, MediaListPlayer
from datetime import datetime as dt
from datetime import timedelta as td


def after_print(method):
    def decorated(self, *args, **kwargs):
        # before the method call
        # if self.busy:
        #     return None
        # self.busy = True

        # the actual method call
        result = method(self, *args, **kwargs)

        # after the method call
        print(self)
        return result

    return decorated


class Player(object):
    def __init__(self, urls=None, mode=1):
        if urls is None:
            urls = []
        self.player = MediaListPlayer()
        self.player.set_playback_mode(vlc.PlaybackMode(mode))  # default, loop, repeat
        self.volume = 100
        self.set_playlist(urls)
        # self.busy = False

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, idx):
        return self.playlist[idx].get_mrl()

    def __len__(self):
        return len(self.playlist)

    def __bool__(self):
        return self.is_playing()

    def __repr__(self):
        now_i = self.now_index()
        return '\n'.join(
            [f' *** {media.get_mrl()}' if i == now_i else f' --- {media.get_mrl()}' for i, media in
             enumerate(self.playlist)])

    def set_playlist_local(self, path):
        self.playlist = MediaList()
        for file in os.listdir(path):
            if file.endswith('.mp3'):
                song = os.path.join(path, file)
                self.playlist.add_media(song)
        self.player.set_media_list(self.playlist)

    def set_playlist(self, urls):
        self.playlist = MediaList(urls)
        self.player.set_media_list(self.playlist)

    def get_playlist(self):
        return [i.get_mrl() for i in self.playlist]

    @after_print
    def append(self, url):
        self.playlist.add_media(url)

    @after_print
    def appends(self, urls):
        for url in urls:
            self.playlist.add_media(url)

    @after_print
    def insert(self, url, idx):
        self.playlist.insert_media(Media(url), idx)

    @after_print
    def remove(self, idx):
        self.playlist.remove_index(idx)

    def now_index(self):
        item = self.now_media()
        if item:
            return self.playlist.index_of_item(item)
        else:
            return -1

    def now_playing(self):
        now = self.now_media()
        if now:
            return now.get_mrl()
        else:
            return "Not playing"

    def now_media(self):
        return self.player.get_media_player().get_media()

    def now_length(self):
        return self.player.get_media_player().get_length() #td(milliseconds=self.player.get_media_player().get_length())

    @after_print
    def play(self):
        self.player.play()

    @after_print
    def play_index(self, idx):
        self.player.play_item_at_index(idx)  # self.player[idx]

    @after_print
    def play_item(self, url):
        self.player.play_item(Media(url))

    @after_print
    def pause(self):
        self.player.pause()

    @after_print
    def set_pause(self, do_pause: bool):
        self.player.set_pause(int(do_pause))

    @after_print
    def stop(self):
        self.player.stop()

    @after_print
    def next(self):
        self.player.next()

    @after_print
    def previous(self):
        self.player.previous()

    def set_volume(self, volume=100):
        self.volume = volume
        self.player.get_media_player().audio_set_volume(volume)
        return self.volume

    def get_volume(self):
        self.volume = self.player.get_media_player().audio_get_volume()
        return self.volume

    def change_volume(self, diff=10):
        self.set_volume(self.volume + diff)
        self.volume+=diff

    def is_playing(self):
        return bool(self.player.is_playing())
        #
        # def state(self):
        #     return self.player.get_state()

    def player_state(self):
        return self.player.get_media_player().get_state()
