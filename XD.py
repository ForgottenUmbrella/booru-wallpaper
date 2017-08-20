#!/usr/bin/env python3
# coding=utf-8
"""Another version. Features added when I feel like it."""
import sys
import os
import os.path
import subprocess
import argparse
import configparser
import json
import textwrap
import ctypes
import logging

import tkinter
import requests
import PIL.Image
import PIL.ImageEnhance
import PIL.ImageFilter

SCRIPT_PATH = os.path.realpath(__file__)
ROOT_DIR = os.path.dirname(SCRIPT_PATH)
DATA_DIR = os.path.join(ROOT_DIR, "data")
IMAGE_DATA_PATH = os.path.join(DATA_DIR, "image_data.json")
DEFAULTS_PATH = os.path.join(DATA_DIR, "defaults.ini")
CONFIG_PATH = os.path.join(DATA_DIR, "prev_config.json")
WALLPAPERS_DIR = os.path.join(ROOT_DIR, "wallpapers")
LOG_PATH = os.path.join(ROOT_DIR, "log.log")

LOGGER = logging.getLogger(__name__)


def wait_warmly():
    """Yield parts of a spinning cursor."""
    chars = r"-\|/"
    while True:
        for c in chars:
            yield c


def gram_join(string, splitter=" ", joiner=", ", final_joiner=" and "):
    """Return a split and (perhaps more grammatical) rejoined string.

    Args:
        string (str): A list as a string to split and rejoin.
        splitter (str): Delimiter used to split `string` into a list.
            Defaults to " ".
        joiner (str): Delimiter used to rejoin the split `string`.
            Defaults to ", ".
        final_joiner (str): Delimiter used to join the last element of
            the split `string`. Defaults to " and ".

    Returns:
        str: The split and rejoined `string`.
    """
    string_as_list = string.split(splitter)
    list_needs_joining = len(string_as_list) > 1
    if list_needs_joining:
        first_section = joiner.join(string_as_list[:-1])
        gram_string = final_joiner.join([first_section, string_as_list[-1]])
    else:
        gram_string = string
    return gram_string


def screen_dimensions():
    """Return a tuple of the screen height and width."""
    root = tkinter.Tk()
    height = root.winfo_screenheight()
    width = root.winfo_screenwidth()
    dimensions = (height, width)
    LOGGER.debug(f"screen dimensions = {height}x{width}")
    return dimensions


def read_json(path):
    """Return a JSON object from a file."""
    with open(path) as file:
        data = json.load(file)
    return data


def write_json(path, data):
    """Store a dictionary as a JSON file."""
    with open(path, "w") as file:
        json.dump(data, file, indent=4)


def download(url, path):
    """Store a copy of a file from the internet."""
    with requests.get(url, stream=True) as response, open(path, "wb") as file:
        chunks = response.iter_content(chunk_size=128)
        spinner = wait_warmly()
        for chunk, cursor in zip(chunks, spinner):
            print(cursor, "Downloading...", end="\r")
            file.write(chunk)
        print()


def get_json(url, params):
    """Make a GET request and return the JSON data as a dict.

    Args:
        url (str): Webpage link to make a request to.
        params (dict): Parameters to pass to URL.

    Returns:
        dict: A JSON object from `url` decoded to a Python dictionary.

    # Raises:
    #     RequestError: If the request is unsuccessful.
    #     ValueError: If no JSON data is available from `url`.
    """
    # success = range(100, 400)
    LOGGER.debug(f"GET url = {url}")
    response = requests.get(url, params=params)
    status = response.status_code
    LOGGER.debug(f"status = {status}")
    # succeeded = status in success
    # if succeeded:
        # try:
    json_data = response.json()
        # except json.JSONDecodeError as original_error:
        #     LOGGER.error(original_error)
        #     raise ValueError(f"{url} does not have JSON data.")
    # else:
        # raise RequestError(f"Response returned code {status}.")
    # if not json_data:
        # raise ValueError(f"No data from {url}.")
    LOGGER.debug(f"json_data = {json_data}")
    return json_data


def get_image_data(tags, imageboard, attempts=1, scale=1.0):
    """Return an image's metadata if it matches the requirements.

    Args:
        tags ([str]): Labels the image must match.
        imageboard (str): URL of the website to get images from.
        attempts (int): Number of times to try to get a valid image.
            Defaults to 1.
        scale (float): Relative size of the image in relation to the
            screen. Defaults to 1.0.

    Returns:
        dict: Data stored about the retrieved image.

    Raises:
        ValueError: If none of the images fetched meet all requirements.
    #     ValueError: If there are too many tags, or there were no images
    #         tagged with them all.
    #     OSError: If there was no internet connection available.
    """
    url = f"{imageboard}/posts.json"
    params = {
        "limit": 1,
        "tags": " ".join(tags),
        "random": "true",
        }
    (screen_height, screen_width) = screen_dimensions()
    for attempt in range(attempts):
        # `attempt` is zero-based, but humans aren't.
        real_attempt = attempt + 1
        print(f"Attempt {real_attempt}: Getting image...")
        # try:
        data = get_json(url, params)[0]
        # except urllib.error.HTTPError as original_error:
        #     LOGGER.error(original_error)
        #     raise ValueError("Too many tags.") from None
        # except urllib.error.URLError as original_error:
        #     LOGGER.error(original_error)
        #     raise OSError("No internet connection.") from None
        # except ValueError as original_error:
        #     LOGGER.error(original_error)
        #     raise ValueError("Invalid/conflicting tags.") from None
        good_fit = (
            data["image_height"] >= screen_height * scale and
            data["image_width"] >= screen_width * scale
            )
        if good_fit:
            return data
    raise ValueError("No images were large enough.")


def image_name(image_data):
    """Return the filename of a booru image."""
    return image_data["file_url"].split("/")[-1]


def download_image(tags, imageboard, attempts, scale):
    """Download an image and return its path and data.

    Args:
        tags ([str]): Labels the image must match.
        imageboard (str): URL of website to download from.
        attempts (int): How many times to try to get a good image.
        scale (float): Relative image size in relation to the screen.

    Returns:
        tuple: The path of the image and its metadata.
    """
    data = get_image_data(
        tags, imageboard, attempts=attempts, scale=scale
        )
    url = imageboard + data["file_url"]
    filename = image_name(data)
    path = os.path.join(WALLPAPERS_DIR, filename)
    # print("Downloading image")
    download(url, path)
    return path, data


def sorted_files(directory):
    """Return a sorted list of files  by modified date."""
    files = []
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        files.append(path)
    files.sort(key=os.path.getmtime)
    return files


def remove_old_wallpapers(limit):
    """Delete old wallpapers if there are too many in the folder."""
    wallpapers = sorted_files(WALLPAPERS_DIR)
    num_extra = len(wallpapers) - limit
    if num_extra > 0:
        print("Removing old wallpapers...")
        for wallpaper in wallpapers[:num_extra]:
            os.remove(wallpaper)


def set_linux_wallpaper(path):
    """Set the desktop wallpaper on GNU/Linux."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP").lower()
    if desktop in {"gnome", "x-cinnamon", "unity", "pantheon", "budgie:gnome"}:
        command = (
            "gsettings set org.gnome.desktop.background picture-uri "
            f"file://{path}"
            )
    elif desktop == "mate":
        command = (
            "gsettings set org.mate.background picture-uri "
            f"file://{path}"
            )
    elif desktop == "kde":
        command = (
            "qdbus org.kde.plasmashell /PlasmaShell "
            "org.kde.PlasmaShell.evaluateScript \""
            "var allDesktops = desktops();"
            "for(i = 0; i < allDesktops.length; i++) {"
            "d = allDesktops[i];"
            "d.wallpaperPlugin = 'org.kde.image';"
            "d.currentConfigGroup = Array("
            "'Wallpaper', 'org.kde.image', 'General'"
            ");"
            f"d.writeConfig('Image', 'file://{path}');"
            "}"
            "\""
            )
    elif desktop == "xfce":
        command = (
            "xfconf-query -c xfce4-desktop -p"
            f"$xfce_desktop_prop_prefix/workspace1/last-image -s {path}"
            )
    elif desktop == "enlightenment":
        command = f"enlightenment_remote -desktop-bg-add 0 0 0 0 {path}"
    else:
        command = f"feh --bg-scale {path}"
        print(textwrap.fill(
            "If you're using a standalone WM like i3 or awesome, make sure to "
            "configure it to use feh as the wallpaper source."
            ))
        print(textwrap.fill(
            "For example, if you're using i3, your ~/.config/i3/config should "
            "contain the line, 'exec_always --no-startup-id ~/.fehbg'."
            ))
    subprocess.call(command, shell=True)


def set_windows_wallpaper(path):
    """Set the desktop wallpaper on Windows."""
    spi_setdesktopwallpaper = 20
    spif_sendchange = 2
    irrelevant_param = 0
    ctypes.windll.user32.SystemParametersInfoW(
        spi_setdesktopwallpaper, irrelevant_param, path, spif_sendchange
        )


def set_mac_wallpaper(path):
    """Set the desktop wallpaper on macOS."""
    subprocess.call(
        "tell application 'Finder' to set desktop picture to POSIX "
        f"file {path}", shell=True
        )


def set_wallpaper(path):
    """Set the desktop wallpaper, regardless of operating system.

    Args:
        path (str): Path of image to use as wallpaper.

    Raises:
        NotImplementedError: If the operating system is not yet
            supported.
    """
    print("Setting wallpaper...")
    system = sys.platform
    LOGGER.debug(f"system = {system}")
    if system == "linux":
        set_linux_wallpaper(path)
    elif system == "win32":
        set_windows_wallpaper(path)
    elif system == "darwin":
        set_mac_wallpaper(path)
    else:
        raise NotImplementedError("OS is not yet supported.")


def init_logger(verbose):
    """Initialise the global logger's properties."""
    LOGGER.setLevel(logging.DEBUG)
    debug_handler = logging.FileHandler(LOG_PATH, mode="w")
    debug_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter(
        "{name}:{levelname}: {message}", style="{"
        )
    debug_handler.setFormatter(debug_formatter)
    terminal_handler = logging.StreamHandler()
    if verbose:
        terminal_handler.setLevel(logging.DEBUG)
    else:
        terminal_handler.setLevel(logging.INFO)
    terminal_formatter = logging.Formatter("{levelname}: {message}", style="{")
    terminal_handler.setFormatter(terminal_formatter)
    LOGGER.addHandler(debug_handler)
    LOGGER.addHandler(terminal_handler)


class XDConfigParser(configparser.ConfigParser):
    """ConfigParser for this program."""
    def __init__(self, path):
        super().__init__()
        self.path = path
        try:
            with open(self.path) as defaults_file:
                self.read_file(defaults_file)
        except FileNotFoundError:
            LOGGER.warning("No defaults.ini file.")
        if not self["DEFAULT"]:
            self._create_defaults()
        LOGGER.debug("config_parser['DEFAULT']:")
        for key, value in self["DEFAULT"].items():
            LOGGER.debug(f"{key} = {repr(value)}")

    def _create_defaults(self):
        self["DEFAULT"] = {
            "imageboard": "https://danbooru.donmai.us",
            "retries": 2,
            "scale": 0.0,
            "next": False,
            "list": "all",
            "blur": 0,
            "grey": 0,
            "dim": 0,
            "duration": 24,
            "keep": 2,
            "verbose": False,
        }
        with open(self.path, "w") as defaults_file:
            self.write(defaults_file)


def init_argparser(defaults):
    """Return an ArgumentParser with appropriate defaults."""
    percentage = range(0, 101)
    percent_meta = "{0 ... 100}"

    # Cast booleans, since configparser doesn't. `parse_args` method has
    # undefined behaviour when both `set_defaults` and the `default`
    # argument are passed, so the defaults need to be modified in-place.
    real_defaults = dict(defaults)
    for key in ("verbose", "next"):
        real_defaults[key] = defaults.getboolean(key)
    defaults = real_defaults

    main_parser = argparse.ArgumentParser(
        description="Utility to regularly set the wallpaper to a random "
        "tagged image from a booru",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    main_parser.set_defaults(**defaults)
    main_parser.add_argument(
        "-d", "--duration", type=int, choices=range(1, 25),
        metavar="{1 ... 24}", help="the duration of the wallpaper in hours"
        )
    main_parser.add_argument(
        "-k", "--keep", type=num_keep_type, metavar="{1 ...}",
        help="the number of wallpapers to keep"
        )
    main_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="increase verbosity"
        )
    subparsers = main_parser.add_subparsers(dest="subcommand")

    subparser_set = subparsers.add_parser(
        "set", help="get an image and set it as the wallpaper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    subparser_set.set_defaults(**defaults)
    subparser_set.add_argument(
        "tags", nargs="*", default=argparse.SUPPRESS,
        help="a space-delimited list of tags the image must match"
        )
    subparser_set.add_argument(
        "-i", "--imageboard", help="a URL to source images from"
        )
    subparser_set.add_argument(
        "-r", "--retries", type=int,
        help="the number of times to retry getting the image"
        )
    subparser_set.add_argument(
        "-s", "--scale", type=float,
        help="the minimum relative size of the image to the screen"
        )
    subparser_set.add_argument(
        "-n", "--next", action="store_true",
        help="get the next wallpaper using the previous settings"
        )

    subparser_list = subparsers.add_parser(
        "list", help="print information about the current wallpaper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    subparser_list.set_defaults(**defaults)
    subparser_list.add_argument(
        "list", nargs="*", choices=[
            "all",
            "artist",
            "character",
            "copyright",
            "general",
        ],
        # XXX: default can't yet be a list (http://bugs.python.org/issue9625)
        # default=[element.strip() for element in defaults["list"].split(",")],
        help="the information to print"
        )

    subparser_edit = subparsers.add_parser(
        "edit", help="modify the current wallpaper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    subparser_edit.set_defaults(**defaults)
    subparser_edit.add_argument(
        "-b", "--blur", type=int, choices=percentage, metavar=percent_meta,
        help="how blurry the image should be, as a percentage"
        )
    subparser_edit.add_argument(
        "-g", "--grey", type=int, choices=percentage, metavar=percent_meta,
        help="how monochrome the image should be, as a percentage"
        )
    subparser_edit.add_argument(
        "-d", "--dim", type=int, choices=percentage, metavar=percent_meta,
        help="how dark the image should be, as a percentage"
        )

    return main_parser


def num_keep_type(x):
    """Return a number if it is natural.

    Used for validating the number of wallpapers to keep.
    """
    x = int(x)
    if x <= 0:
        raise argparse.ArgumentTypeError("Minimum number of wallpapers is 1")
    return x


def get_set_booru_wallpaper(args):
    """Set the wallpaper to an image from a booru and write data."""
    if args["next"]:
        LOGGER.debug("--next called")
        # try:
        args = read_json(CONFIG_PATH)
        LOGGER.debug(f"args = {args}")
        # except (FileNotFoundError, json.JSONDecodeError):
        #     LOGGER.error("No prev_config file.")
        #     raise ValueError(
        #         "Please set some arguments before getting the next"
        #         "wallpaper."
        #         )

    path, data = download_image(
        args["tags"], args["imageboard"], args["retries"] + 1, args["scale"]
        )
    remove_old_wallpapers(args["keep"])
    set_wallpaper(path)

    write_json(IMAGE_DATA_PATH, data)
    write_json(CONFIG_PATH, args)


def list_wallpaper_info(args):
    """Print requested information about the current wallpaper."""
    if "all" in args["list"]:
        args["list"] = [
            "artist",
            "character",
            "copyright",
            "general",
        ]
    # try:
    data = read_json(IMAGE_DATA_PATH)
    LOGGER.debug(f"(list) data = {data}")
    # except FileNotFoundError:
    #     raise ValueError(
    #         "There is no wallpaper to list data about. "
    #         "Please set some tags."
    #         ) from None
    for listed_data in args["list"]:
        section = listed_data.capitalize()
        key = f"tag_string_{listed_data}"
        gram_list = gram_join(data[key])
        print(f"{section}: {gram_list}")


def blur(image, blurriness):
    """Return a blurry PIL image."""
    blur_filter = PIL.ImageFilter.GaussianBlur(blurriness)
    new_image = image.filter(blur_filter)
    return new_image


def grey(image, greyness):
    """Return a grey PIL image."""
    enhancer = PIL.ImageEnhance.Color(image)
    colour = (100 - greyness) / 100
    new_image = enhancer.enhance(colour)
    return new_image


def dim(image, dimness):
    """Return a dimmed PIL image."""
    enhancer = PIL.ImageEnhance.Brightness(image)
    brightness = (100 - dimness) / 100
    new_image = enhancer.enhance(brightness)
    return new_image


def edit_wallpaper(path, blurriness, greyness, dimness):
    """Make the saved wallpaper more/less blurry, grey and dim.

    Args:
        path (str): Location of image to be edited.
        blurriness (int): Percentage of how blurry the image should be.
        greyness (int): Percentage of how monochrome the image should be.
        dimness (int): Percentage of how dim the image should be.
    """
    image = PIL.Image.open(path)
    image = blur(image, blurriness)
    image = grey(image, greyness)
    image = dim(image, dimness)
    image.save(path)


def main(argv=None):
    """Set the wallpaper and schedule it to change.

    Args:
        argv ([str]): Arguments from the command line for the program.

    Raises:
        ValueError: If the user provided an invalid command.
    """
    defaults = XDConfigParser(DEFAULTS_PATH)["DEFAULT"]
    argparser = init_argparser(defaults)
    args = vars(argparser.parse_args(argv))

    init_logger(args["verbose"])
    # Nothing is logged to the terminal until the log level is
    # initialised, so logs can't be performed until now.
    LOGGER.debug(f"argv = {argv}")
    LOGGER.debug(f"args = {args}")

    no_args = (len(sys.argv) == 1)
    if no_args:
        argparser.print_help()
        sys.exit(1)

    if args["subcommand"] == "set":
        get_set_booru_wallpaper(args)
    if args["subcommand"] == "list":
        list_wallpaper_info(args)
    if args["subcommand"] == "edit":
        data = read_json(IMAGE_DATA_PATH)
        filename = image_name(data)
        path = os.path.join(WALLPAPERS_DIR, filename)
        edit_wallpaper(path, args["blur"], args["grey"], args["dim"])
        set_wallpaper(path)


if __name__ == "__main__":
    main()
