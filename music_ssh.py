import paramiko
import re
import atexit


class MusicPlayer:
    def __init__(self, host="192.168.123.105", username="pi", password="wnsalsl7!"):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password)
        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile("wb")
        self.stdout = channel.makefile("r")
        self.in_history = []
        self.out_history = []
        self.init()
        self.set_volume(40)
        self.print()
        self.playlist = []
        # atexit.register(self.__del__)

    def __del__(self):
        self.ssh.close()

    def init(self):
        for command in [
            "python",
            "from player import *",
            "P=Player()"
        ]:
            self.execute(command)

    def execute(self, cmd):
        self.in_history.append(cmd)
        self.stdin.write(cmd + "\n")

    def print(self, lines=1):
        for line in self.stdout:
            lined = line.strip()
            print(lined)
            self.out_history.append(lined)
            if self.in_history[-1] in lined:
                next_one = self.stdout.__next__().strip()
                print(next_one)
                self.out_history.append(next_one)
                return next_one

    def set_playlist(self, informations):
        self.execute(f'P.set_playlist({str([i["url"] for i in informations])})')
        self.playlist = informations

    def append(self, information):
        self.execute(f'P.append("{information["url"]}")')
        self.playlist.append(information)

    def appends(self, informations):
        self.execute(f'P.appends({str([i["url"] for i in informations])})')
        self.playlist += informations

    def insert(self, information, idx):
        self.execute(f'P.insert("{information["url"]}",{idx})')
        self.playlist.insert(information, idx)

    def remove(self, idx):
        self.execute(f'P.remove({idx})')
        del self.playlist[idx]

    def now_index(self):
        self.execute(f'P.now_index()')
        return int(self.print())

    def now_playing(self):
        self.execute('P.now_playing()')
        return self.print()

    def now_length(self):
        self.execute(f'P.now_length()')
        return int(self.print())

    def play(self):
        self.execute("P.play()")

    def play_index(self, idx):
        self.execute(f'P.play_index({idx})')

    def pause(self):
        self.execute("P.pause()")

    def set_pause(self, do_pause=bool):
        self.execute(f"P.set_pause({do_pause})")

    def stop(self):
        self.execute("P.stop()")

    def next(self):
        self.execute("P.next()")

    def next(self):
        self.execute("P.previous()")

    def set_volume(self, volume=100):
        self.execute(f"P.set_volume({volume})")
        self.volume = volume

    def change_volume(self, diff=10):
        self.execute(f"P.change_volume({diff})")
        self.volume += diff

    def get_volume(self):
        self.execute("P.get_volume()")
        self.volume = int(self.print())
        return self.volume

    def is_playing(self):
        self.execute("P.is_playing()")
        return "True" == self.print()

    def create_screen(self, name="pi"):
        self.execute(f"screen -S {name}")

    def delete_screen(self):
        self.execute("\x04")


if __name__ == "__main__":
    a = MusicPlayer()
