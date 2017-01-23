#!/usr/bin/env python3.6
"""Command-line interface and script to set the desktop wallpaper to a
new image from an imageboard every so often.

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

Contact at regretfulumbrella@gmail.com

TODO: See list below
    start argument for first-time (set up crontab)
    size check
    write a class that represents a Rotation, so the Wallpaper class
        isn't God
    os.system('cron or schtask actions to call booru_wallpaper.py -n
        every now and then if not already started on first run')
    finish interactive_main
    Platform specific wallpaper settings (e.g. positioning) - use
    gsettings for linux, and import winreg for windows
    python 2 support? lol no update to python 3
"""

import sys
import os
import os.path
import subprocess
import argparse
import configparser
import urllib.parse
import urllib.request
import xml.dom.minidom
import json
import textwrap
import re
import getpass
import random
import tkinter
import logging
# Platform dependent (scheduling)
if sys.platform == 'win32':
    import ctypes
    import winreg
import PIL.Image
import PIL.ImageEnhance  # .Color, .Brightness
import PIL.ImageFilter  # .filter

logging.basicConfig(filename='log.log', filemode='w',
                    format='{levelname}: {message}', style='{',
                    level='DEBUG')

__author__ = 'Leo Pham'
__credits__ = []
# Don't update this
__date__ = '2016-11-20'
__version__ = '0.0.1'
__status__ = 'Prototype'

DISCLAIMER = '''
    Booru Wallpaper  Copyright (C) 2016  Leo Pham
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
       apply, along with any applicable section 7 additional terms, to the
       whole of the work, and all its parts, regardless of how they are
       packaged.
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


class BooruWallpaper:
    """An image from a Danbooru-like imageboard for use as a wallpaper."""
    def __init__(self, options=None):
        """Initialise some attributes.

        options = {
            tags -> list,
            imageboard -> string,
            duration -> int,
            blur -> int,
            grey -> int,
            dim -> int,
            user -> string,
            password -> string,
        }

        data = {
            has_large -> string,
            bit_flags -> string,
            up_score -> string,
            tag_count_copyright -> string,
            created_at -> string,
            updated_at -> string,
            file_size -> string,
            is_note_locked -> string,
            last_comment_bumped_at -> string,
            source -> string,  # 404 Forbidden
            large_file_url -> string,  # Not large
            tag_count_general -> string,
            md5 -> string,
            file_url -> string,                         ***
            has_children -> string,
            score -> string,
            children_ids -> string,
            tag_string_character -> string,             ***
            image_height -> string,                     ***
            down_score -> string,
            pixiv_id -> string,
            tag_string -> string,
            has_active_children -> string,
            tag_string_copyright -> string,             ***
            rating -> string,
            fav_string -> string,
            is_deleted -> string,
            fav_count -> string,
            last_noted_at -> string,
            preview_file_url -> string,
            is_rating_locked -> string,
            image_width -> string,                      ***
            is_banned -> string,
            tag_string_artist -> string,                ***
            is_status_locked -> string,
            tag_count -> string,
            file_ext -> string,                         ***
            parent_id -> string,
            is_pending -> string,
            pool_string -> string,
            tag_count_artist -> string,
            last_commented_at -> string,
            approver_id -> string,
            tag_string_general -> string,               ***
            has_visible_children -> string,
            tag_count_character -> string,
            uploader_name -> string,
            uploader_id -> string,
            id -> string,                               ***
            is_flagged -> string,
        }

        """
        self.reset(options)

    def reset(options=None):
        """(Re)initialise the attributes from the options."""
        if options is None:
            options = {}
        self.rotation = options.get('rotation', 1)
        self.all_config = init_config()
        self.config = all_config['Rotation {}'.format(self.rotation)]
        # Values of None don't cause get method to return default
        self.tags = options.get('tags') or self.config['tags'].split()
        self.imageboard = options.get('imageboard') or self.config['imageboard']
        self.duration = int(options.get('duration') or self.config['duration'])
        self.edits = {
            'blur': int(options.get('blur') or self.config['blur']),
            'grey': int(options.get('grey') or self.config['grey']),
            'dim': int(options.get('dim') or self.config['dim']),
        }
        self.login = {
            'username': options.get('username') or self.config['username'],
            # todo: 'password': ???
        }
        if self.imageboard == 'danbooru':
            self.imageboard_url = 'https://danbooru.donmai.us'
        else:
            # TODO: implement other imageboards
            raise NotImplemented
        # if (self.tags != self.config['tags'].split()
        #     or self.imageboard != self.config['imageboard']
        #     or options['next']):
        #     # Cases where a new image should be retrieved
        #     self.get_image(self.tags, self.imageboard)
        #     self.download()
        #
        # metadata = self._get_image()
        # # All values of metadata are strings, and most are useless;
        # # cherry-pick the good ones and give them nice names
        # self.metadata = {
        #     'id': int(metadata['id']),
        #     'height': int(metadata['image_height']),
        #     'width': int(metadata['image_width']),
        #     'characters': metadata['tag_string_character'].split(),
        #     'copyrights': metadata['tag_string_copyright'].split(),
        #     'artists': metadata['tag_string_artist'].split(),
        #     'general_tags': metadata['tag_string_general'].split(),
        #     'url': '{}{}'.format(self.imageboard_url, metadata['file_url']),
        #     'file_extension': metadata['file_ext'],
        # }
        # self.metadata.update({
        #     'page': '{}/posts/{}'.format(
        #         self.imageboard_url, self.metadata['id']),
        #     'title': '{} from {}, drawn by {}'.format(
        #         gram_join(self.metadata['characters']),
        #         gram_join(self.metadata['copyrights']),
        #         gram_join(self.metadata['artists'])),
        #     'filename': '{}.{}'.format(
        #         self.title, self.metadata['file_extension']),
        #     'path': self._download()
        # })

    def get_image(self, tags=self.tags, imageboard=self.imageboard_url):
        """Retrieve an image and return its data."""
        # TODO: login support??
        # TODO: size check
        posts = '{}/posts.json'.format(imageboard)
        query = urllib.parse.urlencode({
            'limit': 1,
            'tags': ' '.join(tags),
            'random': 'true',
        })
        post = '{}?{}'.format(posts, query)
        # To raise an error if request returns nothing twice in a row
        emergency_brake = False
        while True:
            logging.info('Retrieving image...')
            logging.debug('tags = {!r}'.format(tags))
            logging.debug('imageboard_url = {!r}'.format(imageboard))
            # Apparently you should use a context manager
            with urllib.request.urlopen(post) as request:
            # request = urllib.request.urlopen('{}?{}'.format(posts, query))
                try:
                    metadata = json.loads(request.read().decode('utf-8'))[0]
                except IndexError:
                    if emergency_brake:
                        raise ValueError('Query returned nothing. ¯\_(ツ)_/¯')
                    query = urllib.parse.urlencode({
                        'limit': 1,
                        'tags': ' '.join(tags),
                    })
                    emergency_brake = True
                else:
                    break
        return metadata

    def download(self, url=self.metadata['url'],
                 file=self.metadata['filename']):
        """Download an image and return its path on the filesystem."""
        urllib.request.urlretrieve(url, file)
        path = os.path.join(os.getcwd(), file)
        return path

    def get_source_page(self, page=self.metadata['page']):
        """Return the human-viewable source page URL."""
        with urllib.request.urlopen(page) as request:
            html = request.read().decode('utf-8')
        html = html.replace('doctype', 'DOCTYPE')
        html = re.sub('(<script.*?>)', '\\1<![CDATA[', html)
        html = re.sub('(</script.*?>)', ']]>\\1', html)
        html = re.sub('(<meta.*?)[^/]>', '\\1/>', html)
        html = re.sub('(<link.*?)[^/]>', '\\1/>', html)
        dom = xml.dom.minidom.parseString(html)

    def edit_image(self, edits=self.edits):
        """Edit the image for suitability as a wallpaper."""
        image = PIL.Image.open(self.path)
        blur_filter = PIL.ImageFilter.GaussianBlur(edits['blur'])
        new_image = image.filter(blur_filter)
        grey_maker = PIL.ImageEnhance.Color(image)
        new_image = grey_maker.enhance((100-edits['grey']) / 100)
        dimmer = PIL.ImageEnhance.Brightness(image)
        new_image = dimmer.enhance((100-edits['dim']) / 100)
        new_image.save('wallpaper.{}'.format(self.metadata['file_extension']))

    def get_wallpaper(self):
        """Get an image, download it, edit it and save it."""
        self.get_image()
        self.edit_image()
        # TODO: self.save_wallpaper()

    def set_wallpaper(self):
        """Set the desktop wallpaper as the (edited) image."""
        if sys.platform == 'win32':
            ctypes.windll.user32.SystemParametersInfoA(20, 0, self.path, 3)
        elif sys.platform == 'linux':
            subprocess.call(
                'gsettings set org.gnome.desktop.background picture-uri '
                'file://{}'.format(self.path), shell=True)
        elif sys.platform == 'darwin':
            subprocess.call(
                "tell application 'Finder' to set desktop picture to POSIX "
                'file {}'.format(self.path), shell=True)
        else:
            raise NotImplementedError

    def next_wallpaper(self, old_options):
        """Get new wallpaper and return new rotation."""
        num_rotations = len([section for section in self.all_config.sections
                             if section.startswith('Rotation')])
        if self.config['Global']['order'] == 'random':
            next_rotation = random.randrange(0, num_rotations)
        elif self.rotation < num_rotations - 1:
            next_rotation = self.all_config['Global']['current'] + 1
        else:
            next_rotation = self.all_config['Global']['current']
        new_options = {
            **old_options,
            'rotation': next_rotation,
            }
        # old self.all_config is obscured after reset, so save it first
        self.finalise_config()
        self.reset(new_options)
        self.get_wallpaper()
        self.set_wallpaper()
        return next_rotation

    def handle_options(options):
        """Call the relevant methods based on the options provided."""
        # Using self.tags instead of options['tags'] because it defaults
        # to config if None
        if (self.tags != self.config['tags']
            or self.imageboard != self.config['imageboard']
            and self.rotation == int(self.config['Global']['current'])):
            self.get_wallpaper()
            self.set_wallpaper()
        elif options['next']:
            self.all_config['Global']['current'] = self.next_wallpaper(options)
        elif not any(self.edits.values):
            self.edit_image()
            self.set_wallpaper()
        elif options['order'] != self.config['Global']['order']:
            self.config['Global']['order'] = options['order']
        elif options['disable'] not in self.config['Global']['disabled'].split():
            self.config['Global']['disabled'] += str(options['disable'])
        elif options['view-choice']:
            # TODO: launch some apps
            pass
        elif self.duration != self.config['duration']:
            # TODO: some cron thingo and writing
            pass
        elif options['stop']:
            # TODO: cron stuff
            pass
        else:
            raise ValueError('Nothing happened.')

    def finalise_config(self):
        """Write the new config to its file."""
        # TODO: write metadata as well
        self.config['imageboard'] = self.imageboard
        self.config['duration'] = str(self.duration)
        self.config['blur'] = str(self.edits['blur'])
        self.config['grey'] = str(self.edits['grey'])
        self.config['dim'] = str(self.edits['dim'])
        with open('wallpaper.ini', 'w') as config_file:
            self.config.write(config_file)


def init_parser():
    """Return an argparser with the necessary arguments."""
    PERCENTAGE = range(101)
    PERCENTAGE_META = '{0 ... 100}'

    parser = argparse.ArgumentParser(
        description='set the wallpaper to a random image from a booru-based '
        'imageboard every now and then')
    subparsers = parser.add_subparsers()
    # Set
    parser_set = subparsers.add_parser(
        'set', help='set the tags, imageboard, duration, blurriness, greyness '
        'and dimness')
    parser_set.add_argument(
        '-r', '--rotation', type=int, default=0, help='an integer for which '
        'set of settings to modify, in order to support a rotation of tags. '
        'Defaults to 0.')
    parser_set.add_argument(
        '-t', '--tags', nargs='+', help='a space-delimited list of tags to '
        'search; only two tags allowed for unregistered Danbooru users; '
        'exclusions that usually use a single hyphen must use two instead due '
        'to how the parser works')
    parser_set.add_argument(
        '-i', '--imageboard',
        choices=['danbooru', 'safebooru', 'moebooru', 'gelbooru'],
        help='an imageboard to source images from')
    parser_set.add_argument(
        '-d', '--duration', type=int, help='an integer for the interval (in '
        'hours) between wallpaper changes')
    parser_set.add_argument(
        '--blur', type=int, choices=PERCENTAGE, help='a percentage for '
        'how blurry the wallpaper will be', metavar=PERCENTAGE_META)
    parser_set.add_argument(
        '--grey', '--gray', type=int, choices=PERCENTAGE,
        help='a percentage for how grey the wallpaper will be',
        metavar=PERCENTAGE_META)
    parser_set.add_argument(
        '--dim', type=int, choices=PERCENTAGE, help='a percentage for how dim '
        'the wallpaper will be', metavar=PERCENTAGE_META)
    parser_set.add_argument(
        '-u', '--username', help='a username for the selected imageboard to '
        'bypass tag restrictions; a secure password prompt will appear '
        'afterward')
    # View
    parser_view = subparsers.add_parser(
        'view', help='view the image, its tags (artist, characters, '
        'copyright, other), webpage or source')
    # Don't use built-in mutual exclusivity feature, since it's ugly
    parser_view.add_argument(
        'view-choice', choices=['image', 'tags', 'page', 'source'],
        help='what to view - will be opened in the relevant apps')
    # Everything else
    parser.add_argument(
        '-o', '--order', choices=['random', 'sequential'], help='set the order '
        'in which to cycle through the rotation of tags')
    parser.add_argument(
        '-d', '--disable', type=int, help='disable a rotation of tags')
    parser.add_argument(
        '-n', '--next', action='store_true', help='change the wallpaper')
    parser.add_argument(
        '-s', '--stop', action='store_true', help='stop the background service')
    parser.add_argument(
        '-version', action='version', version='%(prog)s {}'.format(__version__),
        help='display the version')
    return parser


def init_config():
    """Create or read the config file and return its parser."""
    # TODO: Move into BooruWallpaper??
    config_parser = configparser.ConfigParser()
    filename = 'wallpaper.ini'
    if not os.path.isfile(filename):
        config_parser['DEFAULT'] = {
            'imageboard': 'danbooru',
            'duration': '1',
            'blur': '0',
            'grey': '0',
            'dim': '0',
        }
        config_parser['self.rotation_config'] = {
            'order': 'random',
            'disabled': '',
            'current': '1',
        }
        with open(filename, 'w') as config_file:
            config_parser.write(config_file)
    config_parser.read(filename)
    return config_parser


def gram_join(string, splitter=' ', joiner=', ', final_joiner=', and '):
    """Join a string as specified."""
    string_as_list = string.split(splitter)
    first_section = joiner.join(string_as_list[:-1])
    return final_joiner.join([first_section, string_as_list[-1]])


def main(args=sys.argv[1:]):
    """Handle the program input and output."""
    if not args:
        # If no args were passed through the terminal, then it is
        # assumed that the user wishes to run in interactive mode
        interactive_main()
    else:
        arg_parser = init_parser()
        options = vars(arg_parser.parse_args(args))
        wallpaper = BooruWallpaper()
        try:
            wallpaper.handle_options(options)
        except ValueError:
            arg_parser.parse_args(args + ['--help'])
        else:
            wallpaper.finalise_config()

def interactive_main():
    """Provide a command-line interface for setting the program."""
    print(DISCLAIMER)
    wallpaper = BooruWallpaper()
    action = True
    while action:
        options = {}
        # TODO: Organise this
        print('ACTIONS')
        print('Rotation management')
        print('\tSelect rotation to set\n'
              '\tDisable a rotation\n'
              '\tSet order for rotations\n')
        print('Image sourcing')
        print('\tSet tags to search for\n'
              '\tSet source for images\n'
              '\tLog in to your account for the source\n')
        print('Wallpaper customisation')
        print('\tSet blurriness\n'
              '\tSet greyness\n'
              '\tSet dimness\n')
        print('Information on the current wallpaper')
        print('\tView image\n'
              '\tView webpage\n'
              '\tView tagging data\n'
              '\tView original source\n')
        print('Program management')
        print('\tNext wallpaper\n'
              '\tStop the service\n'
              '\tShow conditions\n'
              '\tShow warranty\n'
              '\tReturn to reality\n')
        action = input('Input action: ')
        if 'rotation' in action:
            pass
        elif 'order' in action:
            pass
        elif 'set' in action and 'tags' in action:
            pass
        elif 'set' in action and 'source' in action:
            pass
        elif 'log in' in action:
            pass
        elif 'blur' in action:
            pass
        elif 'grey' in action or 'gray' in action:
            pass
        elif 'dim' in action:
            pass
        elif 'image' in action:
            pass
        elif 'artist' in action:
            pass
        elif 'web' in action or 'page' in action:
            pass
        elif 'view' in action and 'tags' in action:
            pass
        elif 'view' in action and 'source' in action:
            # Up to here
            pass
        if action == 'show c' or 'conditions' in action:
            print(CONDITIONS)
        elif action == 'show w' or 'warranty' in action:
            print(WARRANTY)
        # TODO: elif action == ...
        elif action == 'exit':
            sys.exit()
        # Otherwise, options remain empty
        # TODO: Construct options from input in each branch
        try:
            wallpaper.handle_options(options)
        except ValueError:
            print('Invalid action: {!r}'.format(action))
        except TypeError:
            print('{} requires an integer.'.format(action))
        except urllib.error.HTMLError:
            if action == 'source':
                # TODO: name pending
                print('Probably too many tags entered.')
            elif action == 'tags':
                # TODO: name pending
                print(textwrap.fill(
                    'You do not have the privilege for that.'
                    'Either too many or banned tags for your user level. '
                    'See https://danbooru.donmai.us/wiki_pages/43574 for '
                    'more information.'))


if __name__ == '__main__':
    main()
