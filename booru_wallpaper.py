#!/usr/bin/env python3.6
"""Command-line interface to set the desktop wallpaper to a new image
from Danbooru every so often, based on specified tags.

Tags are inputted by the user, and an image is fetched based on these
tags. The image is downloaded and optionally edited before being set as
the Windows desktop wallpaper. After a specified amount of time (via a
timer service), the process starts over.

##TODO:
add everything again...
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

__author__ = 'Leo Pham'
__credits__ = []
__date__ = '2016-11-20'
__version__ = '0.1'
__status__ = 'Prototype'

import os
import sys
import getpass
import argparse
import urllib.parse
import urllib.request
import configparser
import json
# Platform dependent
if sys.platform == 'win32': import ctypes
elif sys.platform == 'darwin': import subprocess
##disabled because py3.6 can't
# import PIL.Image
# import PIL.ImageEnhance  # .Color, .Brightness
# import PIL.ImageFilter  # .filter

DISCLAIMER = f'''
    Booru Wallpaper  Copyright (C) {__date__[:3]}  {__author__}
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.
'''
CONDITIONS = '''
    5. Conveying Modified Source Versions.

    You may convey a work based on the Program, or the modifications to produce
    it from the Program, in the form of source code under the terms of
    section 4, provided that you also meet all of these conditions:

    a) The work must carry prominent notices stating that you modified it, and
       giving a relevant date.
    b) The work must carry prominent notices stating that it is released under
       this License and any conditions added under section 7. This requirement
       modifies the requirement in section 4 to “keep intact all notices”.
    c) You must license the entire work, as a whole, under this License to
       anyone who comes into possession of a copy. This License will therefore
       apply, along with any applicable section 7 additional terms, to the whole
       of the work, and all its parts, regardless of how they are packaged.
       This License gives no permission to license the work in any other way,
       but it does not invalidate such permission if you have separately
       received it.
    d) If the work has interactive user interfaces, each must display
       Appropriate Legal Notices; however, if the Program has interactive
       interfaces that do not display Appropriate Legal Notices, your work need
       not make them do so.
'''
WARRANTY = '''
    15. Disclaimer of Warranty.

    THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE
    LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR
    OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND,
    EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
    ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.
    SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY
    SERVICING, REPAIR OR CORRECTION.
'''


def main(argv):
    parser = argparse.ArgumentParser(description='Set the wallpaper to a '
        'random image from a booru-based imageboard every now and then.')
    subparsers = parser.add_subparsers()
    # Set
    parser_set = subparsers.add_parser('set', help='set the tags, imageboard '
        'and duration of images')
    parser_set.add_argument('-t', '--tags', nargs='+', help='a space-delimited '
        'list of tags to search; only two tags allowed for unregistered '
        'Danbooru users')
    parser_set.add_argument('-s', '--source', choices=['danbooru', 'safebooru',
        'moebooru', 'gelbooru'], help='an imageboard to source images from')
        ##default='danbooru' if first-time else confparser.source
    parser_set.add_argument('-d', '--duration', type=int, help='an integer '
        'for how many hours an image will be used as the wallpaper before it '
        'is changed')
        ##default=same idea as above
    # Edit
    PERCENTAGE = list(range(100)) + [100]
    parser_edit = subparsers.add_parser('edit', help='edit the wallpaper\'s '
        'appearance - the amount of blurriness, greyness and dimness to apply')
    parser_edit.add_argument('-b', '--blur', type=int, choices=PERCENTAGE,
        help='an integer for the wallpaper\'s blurriness')
        ##default=same
    parser_edit.add_argument('-g', '--grey', '--gray', type=int,
        choices=PERCENTAGE, help='an integer, from 0 to 100 inclusive, for the '
        'wallpaper\'s greyness (yes that\'s a word, probably)')
        ##default=same
    parser_edit.add_argument('-d', '--dim', type=int, choices=PERCENTAGE,
        help='an integer for the wallpaper\'s dimness')
        ##default=same
    # View
    parser_view = subparsers.add_parser('view', help='view the image, its '
        'tags (artist, characters, copyright, other), webpage or source')
    parser_view.add_argument('view_choice', choices=['image', 'tags', 'page',
        'source'], help='what to view - will be opened in the relevant apps')
    # Login
    parser_login = subparsers.add_parser('login', help='log in to the selected '
        'imageboard, to bypass its limits on the number of tags and '
        'censorship, you dead animal-f*cking pedophile')
    parser_login.add_argument('user', help='the account name to log in to; '
        'a secure password prompt will appear after inputting this')
    # Everything else
    parser.add_argument('-n', '--next', action='store_true', help='change the '
        'wallpaper')
    parser.add_argument('-s', '--stop', action='store_true', help='begone '
        'unholy spirit, begone! (kill the daemon service running in the '
        'background)')
    parser.add_argument('-v', '--version', action='version',
        version='%(prog)s '+__version__, help='display the version')
    ##will use fstrings when py3.6 available

    if len(sys.argv) == 1:
        argv = interactive_main()
        
    args = vars(parser.parse_args(argv))

    ##os.system('cron or schtask command to call booru_wallpaper.py -n
    ##every now and then if not already started on first run')


def interactive_main():
    ##Convert input into argv
    print(DISCLAIMER)
    while (True):
        print('Actions')
        print('\t1. Set tags\n'
                'set source'
                'blur'
                'grey'
                'dim'
                'login'
                'return to reality'
              '\t2. View full image\n'
              '\t3. View credits\n'
              '\t4. Change to next wallpaper\n'
              '\t5. Customise wallpaper\n'
              '\t6. Set rotation interval\n')
        ##don't use numbers, so can prompt "show c" "show w"
        action = input('Input action: ')
        if action == 'show c': print(CONDITIONS)
        elif action == 'show w': print(WARRANTY)
        # elif action == ...
        else: print('no.')


if __name__ == '__main__':
    main(sys.argv[1:])
