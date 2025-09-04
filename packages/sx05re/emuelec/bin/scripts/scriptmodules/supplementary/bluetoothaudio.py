#!/usr/bin/env python

# simple curses menu to manage bluetooth audio devices
# based on bluetoothcontroller.py

import os
import sys
import curses
from curses import panel
from bluetool import Bluetooth

AUDIO_ICONS = ["audio-card", "audio-headset", "audio-video"]


class Menu(object):
    def __init__(self, items, stdscreen):
        self.window = stdscreen.subwin(0, 0)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()

        self.position = 0
        self.items = items
        self.items.append(("Back / Exit", "exit"))

    def navigate(self, n):
        self.position += n
        if self.position < 0:
            self.position = 0
        elif self.position >= len(self.items):
            self.position = len(self.items) - 1

    def display(self):
        self.panel.top()
        self.panel.show()
        self.window.clear()

        while True:
            self.window.refresh()
            curses.doupdate()
            for index, item in enumerate(self.items):
                if index == self.position:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL

                msg = "%d. %s" % (index, item[0])
                self.window.addstr(1 + index, 1, msg, mode)

            key = self.window.getch()

            if key in [curses.KEY_ENTER, ord("\n")]:
                if self.position == len(self.items) - 1:
                    break
                else:
                    self.items[self.position][1]()

            elif key == curses.KEY_UP:
                self.navigate(-1)

            elif key == curses.KEY_DOWN:
                self.navigate(1)

        self.window.clear()
        self.panel.hide()
        panel.update_panels()
        curses.doupdate()


class BluetoothAudio(object):
    def __init__(self, stdscreen):
        self.scan_timeout = 90
        self.bt = Bluetooth()
        self.bt.start_scanning(self.scan_timeout)

        self.screen = stdscreen
        curses.curs_set(0)
        mainMenu = [
            ("Rescan devices\t\t(scans for {} seconds in background)".format(self.scan_timeout), self.rescan_devices),
            ("Trust device\t\t(shows only untrusted audio devices)", self.trust_device_menu),
            ("Pair device\t\t(shows only unpaired audio devices)", self.pair_device_menu),
            ("Connect device\t(shows only paired and trusted audio devices)", self.connect_device_menu),
        ]
        self.make_menu(mainMenu)
        self.menu.display()

    def make_menu(self, menulist):
        self.menu = Menu(menulist, self.screen)

    def get_selected_device(self):
        return self.menu.items[self.menu.position][0].split("\t")[0]

    def navigate_to_back(self):
        self.menu.navigate(len(self.menu.items) - 1)

    def rescan_devices(self):
        self.bt.start_scanning(self.scan_timeout)
        self.navigate_to_back()

    def trust_device_menu(self):
        properties = ["Icon", "RSSI", "Trusted"]
        menu = []
        for device in self.bt.get_available_devices():
            mac_address = device["mac_address"].decode("utf-8")
            for prop in properties:
                device[prop] = self.bt.get_device_property(mac_address, prop)
            if (device["Icon"] in AUDIO_ICONS) and (device["Trusted"] == 0):
                menu.append(("{}\t{}\tRSSI: {}".format(mac_address, device["name"].decode("utf-8"), device["RSSI"]), self.trust_device))
        self.make_menu(menu)
        self.menu.display()

    def trust_device(self):
        mac = self.get_selected_device()
        self.bt.trust(mac)
        if self.bt.get_device_property(mac, "Trusted") == 1:
            self.menu.items[self.menu.position] = ("{} trusted!".format(mac), self.navigate_to_back)
        else:
            self.menu.items[self.menu.position] = ("Error trusting {}".format(mac), self.navigate_to_back)

    def pair_device_menu(self):
        properties = ["Icon", "Paired", "Trusted"]
        menu = []
        for device in self.bt.get_devices_to_pair():
            mac_address = device["mac_address"].decode("utf-8")
            for prop in properties:
                device[prop] = self.bt.get_device_property(mac_address, prop)
            if (device["Icon"] in AUDIO_ICONS) and (device["Trusted"] == 1) and (device["Paired"] == 0):
                menu.append(("{}\t{}".format(mac_address, device["name"].decode("utf-8")), self.pair_device))
        self.make_menu(menu)
        self.menu.display()

    def pair_device(self):
        mac = self.get_selected_device()
        self.bt.pair(mac)
        if self.bt.get_device_property(mac, "Paired") == 1:
            self.menu.items[self.menu.position] = ("{} paired!".format(mac), self.navigate_to_back)
        else:
            self.menu.items[self.menu.position] = ("Error pairing {}".format(mac), self.navigate_to_back)

    def connect_device_menu(self):
        properties = ["Icon", "Connected", "Paired", "Trusted"]
        menu = []
        for device in self.bt.get_available_devices():
            mac_address = device["mac_address"].decode("utf-8")
            for prop in properties:
                device[prop] = self.bt.get_device_property(mac_address, prop)
            if (device["Icon"] in AUDIO_ICONS) and (device["Paired"] == 1) and (device["Trusted"] == 1) and (device["Connected"] == 0):
                menu.append(("{}\t{}".format(mac_address, device["name"].decode("utf-8")), self.connect_device))
        self.make_menu(menu)
        self.menu.display()

    def connect_device(self):
        mac = self.get_selected_device()
        self.bt.connect(mac)
        if self.bt.get_device_property(mac, "Connected") == 1:
            mac_underscore = mac.replace(":", "_")
            os.system("pactl set-default-sink bluez_sink.{}".format(mac_underscore))
            os.system("/emuelec/bin/rr_audio.sh pulseaudio")
            self.menu.items[self.menu.position] = ("{} connected!".format(mac), self.navigate_to_back)
        else:
            self.menu.items[self.menu.position] = ("Error connecting {}".format(mac), self.navigate_to_back)


def autoconnect():
    bt = Bluetooth()
    for device in bt.get_available_devices():
        mac = device["mac_address"].decode("utf-8")
        icon = bt.get_device_property(mac, "Icon")
        paired = bt.get_device_property(mac, "Paired")
        trusted = bt.get_device_property(mac, "Trusted")
        connected = bt.get_device_property(mac, "Connected")
        if (icon in AUDIO_ICONS) and (paired == 1) and (trusted == 1) and (connected == 0):
            bt.connect(mac)
            mac_underscore = mac.replace(":", "_")
            os.system("pactl set-default-sink bluez_sink.{}".format(mac_underscore))
            os.system("/emuelec/bin/rr_audio.sh pulseaudio")
            break


def main(stdscreen):
    BluetoothAudio(stdscreen)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reconnect":
        autoconnect()
    else:
        curses.wrapper(main)
