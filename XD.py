#!/usr/bin/env python3
"""Another version. Features added when I feel like it."""
import sys
import os.path
import subprocess
import getpass
import argparse
import urllib.parse
import urllib.request
import json
import tkinter
import ctypes
import logging

import crontab

logging.basicConfig(format='{levelname}: {message}', style='{', level='INFO')
logger = logging.getLogger(__name__)


def gram_join(string, splitter=' ', joiner=', ', final_joiner=' and '):
    """Return a string joined as specified."""
    string_as_list = string.split(splitter)
    if len(string_as_list) > 1:
        first_section = joiner.join(string_as_list[:-1])
        gram_string = final_joiner.join([first_section, string_as_list[-1]])
    else:
        gram_string = string
    return gram_string


def get_image(tags, imageboard, attempts=1, size=1.0):
    """Retrieve an image and return its data."""
    posts = f'{imageboard}/posts.json'
    query = urllib.parse.urlencode({
        'limit': 1,
        'tags': ' '.join(tags),
        'random': 'true',
    })
    root = tkinter.Tk()
    screen_height = root.winfo_screenheight()
    screen_width = root.winfo_screenwidth()

    for attempt in range(attempts):
        post = f'{posts}?{query}'
        logger.info(f'Attempt {attempt}: Getting image...')
        try:
            with urllib.request.urlopen(post) as request:
                SUCCESS = range(100, 400)
                status = request.getcode()
                logger.debug(f'status = {status}')
                if status in SUCCESS:
                    data = json.loads(request.read().decode('utf-8'))[0]
        except urllib.error.HTTPError as original_error:
            logger.error(original_error)
            raise ValueError('Probably too many tags') from None
        good_fit = (data['image_height'] >= screen_height * size
                    and data['image_width'] >= screen_width * size)
        if data and good_fit:
            break

    else:
        if status not in SUCCESS:
            error = f'{imageboard} returned status {status}'
        elif not good_fit:
            error = "Image wasn't big enough"
        else:
            error = '¯\_(ツ)_/¯'
        raise ValueError(f'Image getting failed. {error}') from None

    return data


def download(url, filename, directory=None):
    """Download a file from a url and return its path."""
    if directory is None:
        directory = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(directory, filename)
    logger.info('Downloading image...')
    urllib.request.urlretrieve(url, path)
    return path


def set_wallpaper(image_path):
    """Set the desktop wallpaper to the image specified."""
    logger.info('Setting wallpaper...')
    if sys.platform == 'win32':
        ctypes.windll.user32.SystemParametersInfoA(20, 0, image_path, 3)
    elif sys.platform == 'linux':
        subprocess.call(
            'gsettings set org.gnome.desktop.background picture-uri '
            'file://{}'.format(image_path), shell=True)
    elif sys.platform == 'darwin':
        subprocess.call(
            "tell application 'Finder' to set desktop picture to POSIX "
            'file {}'.format(image_path), shell=True)
    else:
        raise NotImplementedError


def update_json(file_path, data):
    """Update JSON within file_path."""
    try:
        with open(file_path) as file:
            previous_data = json.load(file)
    except FileNotFoundError:
            logger.error(f'No file at {file_path}')
            previous_data = {}
    if data != previous_data:
        with open(file_path, 'w') as file:
            json.dump(data, file)


def init_parser():
    """Return an ArgumentParser with the required arguments."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcommand')
    subparser_set = subparsers.add_parser('set', help='set the wallpaper')
    subparser_set.add_argument(
        'tags', nargs='*',
        help='a space-delimited list of tags the image must match')
    subparser_set.add_argument(
        '-i', '--imageboard', default='https://danbooru.donmai.us',
        help='a URL to source images from (default: https://danbooru.donmai.us')
    subparser_set.add_argument(
        '-r', '--retries', type=int, default=2,
        help='the number of times to retry getting the image (default: 2)')
    subparser_set.add_argument(
        '-s', '--size', type=float, default=0.0,
        help='the minimum relative size of the image in relation to the '
        'screen (default: 0.0)')
    subparser_set.add_argument(
        '-n', '--next', action='store_true', default=False,
        help='set the wallpaper to another image from the previous settings')
    subparser_list = subparsers.add_parser(
        'list', help='list information about the current wallpaper')
    subparser_list.add_argument(
        'list', nargs='*', choices=[
            'all',
            'artist',
            'character',
            'copyright',
            'general',
        ], default=[
            'all',
        ], help='the list to list')
    parser.add_argument(
        '-d', '--duration', type=int, choices=range(1, 25), default=24,
        metavar='{1 ... 24}',
        help='the duration of the wallpaper in hours (default: 24)')
    group_verbosity = parser.add_mutually_exclusive_group()
    group_verbosity.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help='increase verbosity')
    group_verbosity.add_argument(
        '-q', '--quiet', action='store_true', default=False,
        help='decrease verbosity')

    return parser


def main():
    """Set the wallpaper and schedule it to change."""
    script_path = os.path.realpath(__file__)
    this_directory = os.path.dirname(script_path)
    config_path = os.path.join(this_directory, 'config.json')
    data_path = os.path.join(this_directory, 'data.json')
    cron_path = os.path.join(this_directory, 'schedule.tab')

    parser = init_parser()
    args = vars(parser.parse_args())
    if len(sys.argv) == 1:
        parser.parse_args(['--help'])
    # Parse args
    if args['verbose']:
        logger.setLevel(logging.DEBUG)
    elif args['quiet']:
        logger.setLevel(logging.CRITICAL)
    # Nothing is logged to the screen until level is set
    logger.debug(f'args = {args}')

    if 'next' in args:
        try:
            with open(config_path) as config_file:
                config = json.load(config_file)
                logger.debug(f'config = {config}')
        except FileNotFoundError:
            raise ValueError(
                'No previously set tags. Please set some tags before '
                'requesting the next wallpaper') from None
        for key in config:
            if key not in args:
                args[key] = config[key]
        # Falls through

    if args['subcommand'] == 'set' or 'next' in args:
        imageboard = args['imageboard']
        data = get_image(
            args['tags'], imageboard, attempts=args['retries'] + 1,
            size=args['size'])
        partial_url = data['file_url']  # Begins with a forward-slash
        url = f'{imageboard}{partial_url}'
        file_extension = data['file_ext']
        filename = f'wallpaper.{file_extension}'
        path = download(url, filename)
        set_wallpaper(path)

        update_json(data_path, data)
        update_json(config_path, args)

    if args['subcommand'] == 'list':
        if 'all' in args['list']:
            args['list'] = [
                'artist',
                'character',
                'copyright',
                'general',
            ]

        try:
            with open(data_path) as data_file:
                data = json.load(data_file)
                logger.debug(f'data = {data}')
        except FileNotFoundError:
            raise ValueError(
                'Nothing to list. Please set some tags before listing data '
                'about the nonexistent tagged image') from None

        for list_ in args['list']:
            list_name = list_.capitalize()
            gram_list = gram_join(data[f'tag_string_{list_}'])
            print(f'{list_name}: {gram_list}')

    try:
        with open(config_path) as config_file:
            previous_args = json.load(config_file)
    except FileNotFoundError:
        logger.error('No config.json file')
        pass
    else:
        if args['duration'] != previous_args['duration']:
            logger.info('Scheduling next wallpaper change...')
            tab = crontab.CronTab(tabfile=cron_path)
            tab.remove_all()
            command = f'{script_path} set --next'
            cron_job = tab.new(command)
            if args['duration'] == 24:
                cron_job.every().dom()
            else:
                cron_job.every(args['duration']).hours()
            tab.write()
            # user = getpass.getuser()
            # cron_path = f'/var/spool/cron/crontabs/{user}'
            # try:
            #     with open(cron_path) as cron_file:
            #         crontab = cron_file.readlines()
            # except FileNotFoundError:
            #     logger.error('No cron_file')
            #     crontab = []
            #
            # for line_number, line in enumerate(crontab):
            #     if 'booru-wallpaper' in line:
            #         break
            # else:
            #     line_number = len(crontab)
            #
            # if args['duration'] == 24:
            #     duration = '0 * * * *'
            # else:
            #     duration = "0 */{args['duration'] * * *"
            #
            # command = f'{script_path} set --next # booru-wallpaper'
            # crontab[line_number] = f'{duration} {command}\n'
            # logger.debug(f'crontab = {crontab}')
            # with open(cron_path, 'w') as cron_file:
            #     cron_file.writelines(crontab)


if __name__ == '__main__':
    main()
