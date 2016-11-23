#!/usr/bin/env python3.6
"""Command-line interface to set the desktop wallpaper to a new image
from Danbooru every so often, based on specified tags.

Tags are inputted by the user, and an image is fetched based on these
tags. The image is downloaded and optionally edited before being set as
the Windows desktop wallpaper. After a specified amount of time (via a
timer service), the process starts over.

TODO:
Method or function??
Log in to Danbooru, bypass limit
Platform specific wallpaper settings (e.g. positioning)
Restructure class to only take search as init, and have edited_path
Implement `show c' `show w'

    Copyright (C) 2016  Leo Pham

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

regretfulumbrella@gmail.com
"""

__author__ = "Leo Pham"
__credits__ = []
__date__ = "2016-11-20"
__version__ = "0.1"
__status__ = "Prototype"

import urllib.parse
import urllib.request
import os
import sys
import sched
import time
import configParser
import json
# Platform dependent
if sys.platform == "win32": import ctypes
elif sys.platform == "darwin": import subprocess

import PIL.Image
import PIL.ImageEnhance  # .Color, .Brightness
import PIL.ImageFilter  # .filter


def gram_join(string, splitter=" ", sep=", ", end=" and "):
    """Return a grammatically correct string from a string list."""
    if len(list_) == 1:
        return list_[0]
    string_list = string.split(splitter)
    all_but_last = sep.join(string_list[:-1])
    last = string_list[-1]
    return end.join(all_but_last, last)


def set_wallpaper(wallpaper):
    """Set the desktop wallpaper."""
    if sys.platform == "win32":
        SPI_SETDESKWALLPAPER = 20
        ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0,
            wallpaper.path, 3)
    elif sys.platform == "linux":
        os.system("/usr/bin/gsettings "
            f"set org.gnome.desktop.background picture-uri {wallpaper.path}")
    elif sys.platform == "darwin":
        SCRIPT = "tell application 'Finder' to set desktop picture to POSIX " \
            f"file '{wallpaper.path}'"
        subprocess.Popen(SCRIPT, shell=True)
    else:
        raise NotImplemented

s = sched.scheduler()
s.enterabs(get_next_time, 1, set_wallpaper, DanbooruWallpaper(search))
def get_next_time(duration):
    return time.time() + duration
    # Set service
    # Await time
    # Delete image
    # Get new wallpaper
    # Repeat...
    pass


def edit_wallpaper(wallpaper, blur, grey, dim):
    return DanbooruWallpaper(image.path)


class DanbooruWallpaper:
    """An online image from Danbooru with metadata."""

    def __init__(self, search):
        """Retrieve an image and set metadata.

        Note to self that search may be an id.
        """
        # Might someday be changeable, therefore not constant
        image_board = "https://danbooru.donmai.us"
        posts_list = f"{image_board}/posts.json"
        # Required to handle spaces and other such dangers safely
        query = urllib.parse.urlencode({
            'limit': 1,
            'tags': search,
            'random': "true"
        })
        print("Retrieving image...")
        request = urllib.request.urlopen(f"{posts_list}?{query}")
        data = json.loads(request.read().decode('ascii'))[0]
        # Useful data
        self.id = int(data['id'])
        self.height = int(data['image_height'])
        self.width = int(data['image_width'])
        self.characters = data['tag_string_character'].split()
        self.copyrights = data['tag_string_copyright'].split()
        self.artists = data['tag_string_artist']
        self.tags = data['tag_string_general']
        self.url = f"{image_board}{data['file_url']}"
        self.file_ext = data['file_ext']
        self.title = f"{gram_join(self.characters)} from "
            f"{gram_join(self.copyrights)}, drawn by {gram_join(self.artists)}"
        urllib.request.urlretrieve(self.url, file_name)
        self.path = os.path.join(os.getcwd(), file_name)

    def download(self, file_name=f"{self.title}.{self.file_ext}"):
        """Download an image, set path and return it.
        
        Not to be used for saving edited images, as the Pillow module
        will handle that. Available as a method since downloading may fail.
        """
        print("Downloading image...")
        urllib.request.urlretrieve(self.url, file_name)
        self.path = os.path.join(os.getcwd(), file_name)
        return self.path

    def edit(self, blur, grey, dim):
        """Edit the image for wallpaper suitability and save it."""
        
        self.path
        self.blur
        self.grey
        self.dim
        self.duration # ?

    def view():


def view_image(image):
    """Open the image viewer to view the full image, unedited"""
    pass


def set_wallpaper(image):
    """Get, save, edit and Set an image as the Windows desktop wallpaper"""
    image_url = get_image(search)
    image_path = save_image(image_url)
    wallpaper = edit_image(image_path)
    set_wallpaper(wallpaper)
    set_timer(duration)
    pass


def get_credits(image_url):
    """"""
    pass


# Somewhere, a service is checking for the time and calling set_wallpaper()

print("""
    Booru Wallpaper  Copyright (C) 2016  Leo Pham
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.
    """)

while True:
    print("Danbooru Wallpaper v0.1 - Forgotten Umbrella")
    print("Set your wallpaper to a random image from Danbooru, "
          "based on the provided tags.")
    print()
    print("Actions")
    print("\t1. Set tags\n"
          "\t2. View full image\n"
          "\t3. View credits\n"
          "\t4. Change to next wallpaper\n"
          "\t5. Customise wallpaper\n"
          "\t6. Set rotation interval\n")
    
    while True:
        choice = input("Input your choice (number) >>> ")
        try:
            if int(choice) not in range(1,7):
            # Inclusive min, exclusive max
                raise ValueError
        except ValueError:
            print("Input was not a valid number.")
        else:
            choice = int(choice)
            break
    print()

    if choice == 1:
        while True:
            query = input("Input tags to search on Danbooru (maximum of two) >>> ")
            try:
                image_url = get_image(query)
            except urllib.error.HTTPError:
                print("Too many tags.")
            else:
                break
        set_timer(duration)

