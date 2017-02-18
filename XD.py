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
import configparser
import tkinter
import ctypes
import logging

# XXX: Undo comment
# import crontab

script_path = os.path.realpath(__file__)
this_directory = os.path.dirname(script_path)
# config_path = os.path.join(this_directory, 'config.json')
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
            raise ValueError('Probably too many tags') from original_error
        except urllib.error.URLError as original_error:
            logger.error(original_error)
            raise SystemError('No internet connection') from original_error
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
        # Apparently SPIF_SENDWININICHANGE is aliased to SPIF_SENDCHANGE
        # SPIF_SENDWININICHANGE = 3
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKTOPWALLPAPER, 0, image_path, SPIF_SENDCHANGE)
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


def update_data(file_path, data):
    """Update data within file_path."""
    filetype = os.path.splitext(file_path)[1]
    logger.debug(f'filetype = {filetype}')
    if 'tags' in data:
        logger.debug(f'data = {data}')
    else:
        logger.debug(f'data["id"] = {data["id"]}')

    try:
        with open(file_path) as file:
            if filetype == '.json':
                previous_data = json.load(file)
            elif filetype == '.ini':
                previous_data = configparser.ConfigParser()
                previous_data.read(file)
            else:
                raise ValueError('Not a compatible filetype')

            if 'tags' in data:
                logger.debug(f'(update) previous_data = {previous_data}')
            else:
                logger.debug(f'(update) previous_data["id"] = '
                             f'{previous_data["id"]}')
    except (FileNotFoundError, json.JSONDecodeError):
            logger.error(f'Empty or missing file at {file_path}')
            previous_data = {}

    if data != previous_data:
        with open(file_path, 'w') as file:
            if filetype == '.json':
                json.dump(data, file, indent=4, separators=(', ', ': '))
            elif filetype == '.ini':
                previous_data.write(file)


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


def init_config(path=config_path):
    config_parser = configparser.ConfigParser()
    with open(path) as config_file:
        config_parser.read(config_file)
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
        with open(path, 'w') as config_file:
            config_parser.write(config_file)
    return config_parser


def main(argv=sys.argv[1:]):
    """Set the wallpaper and schedule it to change."""
    config_parser = init_config()
    default_args = config_parser['DEFAULT']
    parser = init_parser(default_args)
    args = vars(parser.parse_args(argv))
    if len(sys.argv) == 1:
        parser.parse_args(['--help'])
    # Parse args
    if args['verbose']:
        terminal_handler.setLevel(logging.DEBUG)
    elif args['quiet']:
        terminal_handler.setLevel(logging.CRITICAL)
    # Nothing is logged to the screen until level is set
    logger.debug(f'args = {args}')

    if args['subcommand'] == 'set':
        if args['next']:
            logger.debug('--next called')
            try:
                with open(config_path) as config_file:
                    # TODO: config -> config_parser, no try-except, config['args']
                    config = json.load(config_file)
                    logger.debug(f'config = {config}')
            except (FileNotFoundError, json.JSONDecodeError) as original_error:
                raise ValueError(
                    'No previously set tags. Please set some tags before '
                    'requesting the next wallpaper') from original_error
            for key in config:
                logger.debug(f'key = {key}')
                if key not in args:
                    args[key] = config[key]
            logger.debug(f'args = {args}')

        imageboard = args['imageboard']
        data = get_image(
            args['tags'], imageboard, attempts=args['retries'] + 1,
            size=args['size'])
        partial_url = data['file_url']  # Begins with a forward-slash
        url = f'{imageboard}{partial_url}'
        file_extension = data['file_ext']
        filename = f'wallpaper.{file_extension}'
        path = os.path.join(this_directory, filename)
        download(url, path)
        set_wallpaper(path)

        update_data(data_path, data)
        update_data(config_path, args)

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
        except (FileNotFoundError, json.JSONDecodeError) as original_error:
            raise ValueError(
                'Nothing to list. Please set some tags before listing data '
                'about the nonexistent tagged image') from original_error

        for list_ in args['list']:
            list_name = list_.capitalize()
            gram_list = gram_join(data[f'tag_string_{list_}'])
            print(f'{list_name}: {gram_list}')

    try:
        with open(config_path) as config_file:
            previous_args = config_parser.read(config_file)
            logger.debug(f'(sched) previous_args = {previous_args}')
    except FileNotFoundError:
        logger.error('No config.ini file')
        pass
    else:
        # XXX: remove `or True`/`and False`
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
