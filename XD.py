#!/usr/bin/env python3
"""Another version. Features added when I feel like it."""
import sys
import os.path
import subprocess
# TODO: Useless import??
# import getpass
import urllib.parse
import urllib.request
import argparse
import configparser
import json
import tkinter
import ctypes
import logging

# TODO: Undo comment import
# import crontab

script_path = os.path.realpath(__file__)
this_directory = os.path.dirname(script_path)
config_path = os.path.join(this_directory, 'config.ini')
data_path = os.path.join(this_directory, 'data.json')
cron_path = os.path.join(this_directory, 'schedule.tab')
log_path = os.path.join(this_directory, 'log.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
debug_handler = logging.FileHandler(log_path, mode='w')
debug_handler.setLevel(logging.DEBUG)
debug_formatter = logging.Formatter(
    '{asctime} - {name}:{levelname}: {message}', style='{')
debug_handler.setFormatter(debug_formatter)
terminal_handler = logging.StreamHandler()
terminal_handler.setLevel(logging.INFO)
terminal_formatter = logging.Formatter('{levelname}: {message}', style='{')
terminal_handler.setFormatter(terminal_formatter)
logger.addHandler(debug_handler)
logger.addHandler(terminal_handler)


def gram_join(string, splitter=' ', joiner=', ', final_joiner=' and '):
    """Split a string and return a rejoined (perhaps more grammatical) one."""
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
    SUCCESS = range(100, 400)

    root = tkinter.Tk()
    screen_height = root.winfo_screenheight()
    screen_width = root.winfo_screenwidth()

    for attempt in range(attempts):
        post = f'{posts}?{query}'
        logger.info(f'Attempt {attempt}: Getting image...')
        try:
            with urllib.request.urlopen(post) as request:
                status = request.getcode()
                logger.debug(f'status = {status}')
                if status in SUCCESS:
                    data = json.loads(request.read().decode('utf-8'))[0]
                else:
                    data = {}
        except urllib.error.HTTPError as original_error:
            logger.error(original_error)
            raise ValueError('Probably too many tags') from None
        except urllib.error.URLError as original_error:
            logger.error(original_error)
            raise OSError('Probably no internet connection') from None

        good_fit = (data.get('image_height', 0) >= screen_height * size
                    and data.get('image_width', 0) >= screen_width * size)
        if data and good_fit:
            break

    else:
        if status not in SUCCESS:
            error = f'{imageboard} returned status {status}'
        elif not good_fit:
            error = "Image wasn't big enough"
        else:
            error = '¯\_(ツ)_/¯'
        raise ValueError(f'Image getting failed. {error}')

    return data


def download(url, file_path):
    """Download a file from a url."""
    logger.info('Downloading image...')
    urllib.request.urlretrieve(url, file_path)


def set_wallpaper(image_path):
    """Set the desktop wallpaper to the image specified."""
    logger.info('Setting wallpaper...')
    logger.debug(f'image_path = {image_path}')
    logger.debug(f'sys.platform = {sys.platform}')

    if sys.platform == 'win32':
        SPI_SETDESKTOPWALLPAPER = 20
        SPIF_SENDCHANGE = 2
        IRRELEVANT_PARAM = 0
        # TODO: Remove these comments if they aren't needed (test on win32)
        # Apparently SPIF_SENDWININICHANGE is aliased to SPIF_SENDCHANGE
        # SPIF_SENDWININICHANGE = 3
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKTOPWALLPAPER, IRRELEVANT_PARAM, image_path,
            SPIF_SENDCHANGE)
    elif sys.platform == 'linux':
        subprocess.call(
            'gsettings set org.gnome.desktop.background picture-uri '
            f'file://{image_path}', shell=True)
    elif sys.platform == 'darwin':
        subprocess.call(
            'tell application "Finder" to set desktop picture to POSIX '
            f'file {image_path}', shell=True)
    else:
        raise NotImplementedError('OS is not yet supported')


def init_parser(defaults):
    """Return an ArgumentParser with the required arguments."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcommand')

    subparser_set = subparsers.add_parser('set', help='set the wallpaper')
    subparser_set.add_argument(
        'tags', nargs='*',
        help='a space-delimited list of tags the image must match')
    subparser_set.add_argument(
        '-i', '--imageboard', default=defaults['imageboard'],
        help=f'a URL to source images from (default: {defaults["imageboard"]})')
    subparser_set.add_argument(
        '-r', '--retries', type=int, default=int(defaults['retries']),
        help='the number of times to retry getting the image (default: '
        f'{defaults["retries"]})')
    subparser_set.add_argument(
        '-s', '--size', type=float, default=float(defaults['size']),
        help='the minimum relative size of the image in relation to the '
        f'screen (default: {defaults["size"]})')
    subparser_set.add_argument(
        '-n', '--next', action='store_true',
        default=defaults.getboolean('next'),
        help='get the next wallpaper from the previous settings '
        '(which can be overloaded)')

    subparser_list = subparsers.add_parser(
        'list', help='list information about the current wallpaper')
    subparser_list.add_argument(
        'list', nargs='*', choices=[
            'all',
            'artist',
            'character',
            'copyright',
            'general',
        ], default=[element.strip() for element in defaults['list'].split(',')],
        help=f'the list to list (default: {defaults["list"]})')

    parser.add_argument(
        '-d', '--duration', type=int, choices=range(1, 25),
        default=int(defaults['duration']), metavar='{1 ... 24}',
        help='the duration of the wallpaper in hours (default: '
        f'{defaults["duration"]})')

    group_verbosity = parser.add_mutually_exclusive_group()
    group_verbosity.add_argument(
        '-v', '--verbose', action='store_true',
        default=defaults.getboolean('verbose'), help='increase verbosity')
    group_verbosity.add_argument(
        '-q', '--quiet', action='store_true',
        default=defaults.getboolean('quiet'), help='decrease verbosity')

    return parser


def init_config(path):
    config_parser = configparser.ConfigParser()
    try:
        with open(path) as config_file:
            config_parser.read(config_file)
    except FileNotFoundError:
        logger.error('No config.ini file')

    # 'DEFAULT' is always in the parser, but it might be Falsy
    if not config_parser['DEFAULT']:
        config_parser['DEFAULT'] = {
            'imageboard': 'https://danbooru.donmai.us',
            'retries': 2,
            'size': 0.0,
            'next': False,
            'list': 'all',
            'duration': 24,
            'verbose': False,
            'quiet': False
        }
    # Custom sections aren't always in the parser
    if 'SETTINGS' not in config_parser:
        config_parser['SETTINGS'] = {}

    with open(path, 'w') as config_file:
        config_parser.write(config_file)
    return config_parser


def main(argv=sys.argv[1:]):
    """Set the wallpaper and schedule it to change."""
    config_parser = init_config(config_path)
    previous_args = config_parser['SETTINGS']
    default_args = config_parser['DEFAULT']
    parser = init_parser(default_args)
    args = vars(parser.parse_args(argv))

    if len(sys.argv) == 1:
        parser.parse_args(['--help'])
        # Explicit implicit return

    if args['verbose']:
        terminal_handler.setLevel(logging.DEBUG)
    elif args['quiet']:
        terminal_handler.setLevel(logging.CRITICAL)

    # Nothing is logged to the screen until level is set
    logger.debug(f'args = {args}')

    if args['subcommand'] == 'set':
        if args['next']:
            logger.debug('--next called')
            if 'tags' not in previous_args:
                raise ValueError(
                    'No previously set tags. Please set some before '
                    'requesting the next wallpaper')

            for arg in previous_args:
                logger.debug(f'arg = {arg}')
                if arg not in args:
                    args[arg] = previous_args[arg]
            logger.debug(f'args = {args}')

        imageboard = args['imageboard']
        max_attempts = args['retries'] + 1
        data = get_image(
            args['tags'], imageboard, attempts=max_attempts,
            size=args['size'])
        # data['file_url'] begins with a forward-slash
        partial_url = data['file_url']
        url = f'{imageboard}{partial_url}'
        file_extension = data['file_ext']
        filename = f'wallpaper.{file_extension}'
        path = os.path.join(this_directory, filename)

        download(url, path)
        set_wallpaper(path)

        with open(data_path, 'w') as data_file:
            json.dump(data, data_file, indent=4, separators=(', ', ': '))

        config_parser['SETTINGS'] = args
        with open(config_path, 'w') as config_file:
            config_parser.write(config_file)

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
                'There is no wallpaper to list data about. '
                'Please set some tags') from None

        for listed_data in args['list']:
            list_name = listed_data.capitalize()
            gram_list = gram_join(data[f'tag_string_{listed_data}'])
            print(f'{list_name}: {gram_list}')

    # TODO: remove `or True`/`and False`
    if args['duration'] != previous_args['duration'] and False:
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
        logger.debug(f'cron_job = {tab.render()}')
        # FIXME: scheduling
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
