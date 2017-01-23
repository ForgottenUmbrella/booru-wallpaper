#!/usr/bin/env python3
"""XP version of the project. Features only added when needed."""
import sys
import os.path
import subprocess
import argparse
import urllib.parse
import urllib.request
import json
import tkinter
import ctypes
import logging

logging.basicConfig(
    stream=sys.stdout, filemode='w', format='{levelname}: {message}',
    style='{', level='INFO')


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
        logging.info(f'Attempt {attempt}: Getting image...')
        with urllib.request.urlopen(post) as request:
            SUCCESS = range(100, 400)
            status = request.getcode()
            logging.debug(f'status = {status}')
            if status in SUCCESS:
                data = json.loads(request.read().decode('utf-8'))[0]
        good_fit = (data['image_height'] >= screen_height * size
                    and data['image_width'] >= screen_width * size)
        if data and good_fit:
            break

    else:
        if status not in SUCCESS:
            error = f'{imageboard} returned status {status}.'
        elif not good_fit:
            error = "Image wasn't big enough."
        else:
            error = '¯\_(ツ)_/¯'
        raise ValueError(f'Image getting failed. {error}')

    return data


def download(url, filename, directory=None):
    """Download a file from a url and return its path."""
    if directory is None:
        directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    path = os.path.join(directory, filename)
    logging.info('Downloading image...')
    urllib.request.urlretrieve(url, path)
    return path


def set_wallpaper(image_path):
    """Set the desktop wallpaper to the image specified."""
    logging.info('Setting wallpaper...')
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


def main():
    """Get an image, download it and set it as the wallpaper."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser_set = subparsers.add_parser('set', help='set the wallpaper')
    parser_set.add_argument(
        'tags', nargs='*',
        help='a space-delimited list of tags the image must match')
    parser_set.add_argument(
        '-i', '--imageboard', default='https://danbooru.donmai.us',
        help='a URL to source images from (default: https://danbooru.donmai.us')
    parser_set.add_argument(
        '-r', '--retries', type=int, default=2,
        help='the number of times to retry getting the image (default: 2)')
    parser_set.add_argument(
        '-s', '--size', type=float, default=0.0,
        help='the minimum relative size of the image in relation to the '
        'screen (default: 0.0)')
    parser_set.add_argument(
        '-n', '--next', action='store_true', default=False,
        help='set the wallpaper to another image from the previous settings')
    parser_list = subparsers.add_parser(
        'list', help='list information about the current wallpaper')
    parser_list.add_argument(
        'list', nargs='*',
        choices=['all', 'artists', 'characters', 'copyrights', 'general'],
        default=['all'], help='the list to list')
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help='increase verbosity')

    args = vars(parser.parse_args())
    if 'verbose' in args:
        logging.basicConfig(level='DEBUG')

    if 'next' in args:
        with open('config.json') as config_file:
            try:
                config = json.load(config_file)
            except json.decoder.JSONDecodeError:
                raise ValueError('No previously set tags. Please set some tags '
                'before requesting the next wallpaper.') from None
            logging.debug(f'config = {config}')
        for key in config:
            if key not in args:
                args[key] = config[key]

    if 'tags' in args:
        args['data'] = get_image(
            args['tags'], args['imageboard'], attempts=args['retries'] + 1,
            size=args['size'])
        url = f"{args['imageboard']}{args['data']['file_url']}"
        filename = f"wallpaper.{args['data']['file_ext']}"
        path = download(url, filename)
        set_wallpaper(path)
        with open('config.json', 'r+') as config_file:
            try:
                saved_args = json.load(config_file)
            except json.JSONDecodeError:
                saved_args = None
            if args != saved_args:
                json.dump(args, config_file)

    with open('config.json') as config_file:
        data = json.load(config_file)['data']
        logging.debug(f'data = {data}')
    if 'all' in args.get('list', []):
        args_list = ['artist', 'character', 'copyright', 'general']
    else:
        args_list = args.get('list', [])
    for list_ in args_list:
        list_name = list_.capitalize()
        gram_list = gram_join(data[f'tag_string_{list_}'])
        print(f'{list_name}: {gram_list}')


if __name__ == '__main__':
    main()
