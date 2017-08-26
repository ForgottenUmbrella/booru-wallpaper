#!/usr/bin/env python3
# coding=utf-8
"""Another version. Features added when I feel like it."""
import sys
import os
import os.path
import subprocess
import argparse
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
CONFIG_PATH = os.path.join(DATA_DIR, "prev_config.json")
WALLPAPERS_DIR = os.path.join(ROOT_DIR, "wallpapers")
LOG_PATH = os.path.join(ROOT_DIR, "log")

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
_DEBUG_HANDLER = logging.FileHandler(LOG_PATH, mode="w")
_DEBUG_HANDLER.setLevel(logging.DEBUG)
_DEBUG_FORMATTER = logging.Formatter(
    "{name}:{levelname}: {message}", style="{"
)
_DEBUG_HANDLER.setFormatter(_DEBUG_FORMATTER)
_TERMINAL_HANDLER = logging.StreamHandler()
_TERMINAL_HANDLER.setLevel(logging.INFO)
_TERMINAL_FORMATTER = logging.Formatter("{levelname}: {message}", style="{")
_TERMINAL_HANDLER.setFormatter(_TERMINAL_FORMATTER)
LOGGER.addHandler(_DEBUG_HANDLER)
LOGGER.addHandler(_TERMINAL_HANDLER)

INITIAL_CONFIG = {
    "tags": [],
    "imageboard": "https://danbooru.donmai.us",
    "attempts": 1,
    "scale": 0.0,
    "keep": 1,
    "rotation": 0,
    "blur": 0.0,
    "grey": 0.0,
    "dim": 0.0,
}


def sorted_files(directory):
    """Return a sorted list of files by modified date."""
    files = []
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        files.append(path)
    files.sort(key=os.path.getmtime)
    return files


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
    spinner = wait_warmly()
    with requests.get(url, stream=True) as response, open(path, "wb") as file:
        chunks = response.iter_content(chunk_size=128)
        for cursor, chunk in zip(spinner, chunks):
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
    json_data = response.json()
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
        scale (float): Relative image in relation to the screen.
            Defaults to 1.0.

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
        # except urllib.error.HTTPError as ex:
        #     LOGGER.error(ex)
        #     raise ValueError("Too many tags.") from None
        # except urllib.error.URLError as ex:
        #     LOGGER.error(ex)
        #     raise OSError("No internet connection.") from None
        # except json.JSONDecodeError as ex:
        #     LOGGER.error(ex)
        #     raise ValueError(f"{url} does not have JSON data.")
        # except ValueError as ex:
        #     LOGGER.error(ex)
        #     raise ValueError("Invalid/conflicting tags.") from None
        good_fit = (
            data["image_height"] >= screen_height * scale and
            data["image_width"] >= screen_width * scale
        )
        if good_fit:
            return data
    raise ValueError("No images were large enough.")


def booru_image_name(image_data):
    """Return the filename of a booru image."""
    return image_data["file_url"].split("/")[-1]


def download_booru_image(
        tags, imageboard, attempts=1, scale=1.0, directory=WALLPAPERS_DIR):
    """Download an image and return its path and data.

    Args:
        tags ([str]): Labels the image must match.
        imageboard (str): URL of website to download from.
        attempts (int): Number of times to try to get a valid image.
            Defaults to 1.
        scale (float): Relative image size in relation to the screen.
            Defaults to 1.0.
        directory (str): Path of folder to download to.
            Defaults to the `WALLPAPERS_DIR` constant.

    Returns:
        tuple: The path of the image and its metadata.
    """
    data = get_image_data(
        tags, imageboard, attempts=attempts, scale=scale
    )
    url = imageboard + data["file_url"]
    filename = booru_image_name(data)
    path = os.path.join(directory, filename)
    download(url, path)
    return path, data


def remove_old_wallpapers(limit, directory=WALLPAPERS_DIR):
    """Delete old wallpapers if there are too many in the folder."""
    wallpapers = sorted_files(directory)
    num_extra = len(wallpapers) - limit
    if num_extra > 0:
        print("Removing old wallpapers...")
        for wallpaper in wallpapers[:num_extra]:
            os.remove(wallpaper)


def set_linux_wallpaper(path):
    """Set the desktop wallpaper on GNU/Linux."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP").lower()
    if desktop in ("gnome", "x-cinnamon", "unity", "pantheon", "budgie:gnome"):
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


def init_argparser():
    """Return an ArgumentParser specialised for this script."""
    percentage = range(0, 101)
    percent_meta = "{0 ... 100}"

    main_parser = argparse.ArgumentParser(
        description="Utility to periodically set the wallpaper to a random "
        "tagged image from a booru",
    )
    main_parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase verbosity"
    )
    subparsers = main_parser.add_subparsers(dest="subcommand")

    args = {
        "tags": ("-t", "--tags"),
        "imageboard": ("-i", "--imageboard"),
        "attempts": ("-a", "--attempts"),
        "scale": ("-s", "--scale"),
        "keep": ("-k", "--keep"),
        "rotation": ("-r", "--rotation"),
        "blur": ("-b", "--blur"),
        "grey": ("-g", "--grey"),
        "dim": ("-d", "--dim"),
    }
    kwargs = {
        "tags": {
            "help": "list of labels images should match",
        },
        "imageboard": {
            "help": "Danbooru-like site to get images from",
        },
        "attempts": {
            "help": "number of times to try to get an image",
        },
        "scale": {
            "help": "minimum image size ratio relative to the screen",
        },
        "keep": {
            "help": "number of wallpapers to store",
        },
        "rotation": {
            "help": "hours to wait before changing wallpapers",
        },
        "blur": {
            "help": "percentage of blurriness",
        },
        "grey": {
            "help": "percentage of loss in colour",
        },
        "dim": {
            "help": "percentage of darkness",
        },
    }
    set_subparser = subparsers.add_parser(
        "set", help="change settings for getting an image, wallpaper "
        "appearance, the schedule and the number of images to store",
    )
    set_subparser.add_argument(
        *args["tags"], **kwargs["tags"], nargs="*"
    )
    set_subparser.add_argument(
        *args["imageboard"], **kwargs["imageboard"]
    )
    set_subparser.add_argument(
        *args["attempts"], **kwargs["attempts"], type=int
    )
    set_subparser.add_argument(
        *args["scale"], **kwargs["scale"], type=float
    )
    set_subparser.add_argument(
        *args["keep"], **kwargs["keep"], type=wallpaper_num, metavar="{1 ...}"
    )
    set_subparser.add_argument(
        *args["rotation"], **kwargs["rotation"], type=int,
        choices=range(0, 25), metavar="{1 ... 24}"
    )
    edit_group = set_subparser.add_argument_group(
        "wallpaper edit arguments",
        "immediately change the wallpaper's appearance"
    )
    edit_group.add_argument(
        *args["blur"], **kwargs["blur"], type=int, choices=percentage,
        metavar=percent_meta
    )
    edit_group.add_argument(
        *args["grey"], **kwargs["grey"], type=int, choices=percentage,
        metavar=percent_meta
    )
    edit_group.add_argument(
        *args["dim"], **kwargs["dim"], type=int, choices=percentage,
        metavar=percent_meta
    )

    parent_subparser = argparse.ArgumentParser(add_help=False)
    for arg in args:
        parent_subparser.add_argument(
            *args[arg], **kwargs[arg], action="store_true"
        )
    subparsers.add_parser(
        "get", help="view configuration values", parents=[parent_subparser]
    )
    subparsers.add_parser(
        "reset", help="set configuration back to its initial values",
        parents=[parent_subparser]
    )

    subparsers.add_parser(
        "info", help="view information about the current wallpaper",
        add_help=False
    )
    subparsers.add_parser(
        "next", help="get another wallpaper",
        add_help=False
    )
    return main_parser


def wallpaper_num(x):
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
        try:
            args = read_json(CONFIG_PATH)
        except FileNotFoundError:
            print(textwrap.fill(
                "There are no previous arguments to get another wallpaper. "
                "Please set some arguments."
            ))
            sys.exit(1)
        # except json.JSONDecodeError:
        #     os.remove(CONFIG_PATH)
        #     print(textwrap.fill(
        #         "Previous arguments were corrupt. Please set new arguments."
        #     ))
        #     sys.exit(1)
        LOGGER.debug(f"args = {args}")

    path, data = download_booru_image(
        args["tags"], args["imageboard"], attempts=args["attempts"],
        scale=args["scale"]
    )
    remove_old_wallpapers(args["keep"])
    set_wallpaper(path)

    write_json(IMAGE_DATA_PATH, data)
    write_json(CONFIG_PATH, args)


def booru_wallpaper_info():
    """Print information about the current wallpaper."""
    try:
        data = read_json(IMAGE_DATA_PATH)
    except FileNotFoundError:
        print(textwrap.fill(
            "There is no wallpaper to list data about. "
            "Please set some arguments."
        ))
        sys.exit(1)
    # except json.JSONDecodeError:
    #     os.remove(IMAGE_DATA_PATH)
    #     print(textwrap.fill(
    #         "The image data was corrupted. Please get a new wallpaper."
    #     ))
    #     sys.exit(1)
    LOGGER.debug(f"(list) data = {data}")
    for info in ("artist", "character", "copyright"):
        section = info.capitalize()
        key = f"tag_string_{info}"
        info_list = gram_join(str(data[key]), final_joiner=", ")
        print(textwrap.fill(
            f"{section}: {info_list}",
            subsequent_indent=" " * len(section + ": ")
        ))
    # TODO: add a domain key
    url = data["domain"] + data["file_url"]
    print(f"URL: {url}")


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
    argparser = init_argparser()
    args = vars(argparser.parse_args(argv))

    if args["verbose"]:
        _TERMINAL_HANDLER.setLevel(logging.DEBUG)
    else:
        _TERMINAL_HANDLER.setLevel(logging.INFO)
    # No debug messages are displayed until the level is set, so no logs
    # can be performed until now.
    LOGGER.debug(f"argv = {argv}")
    LOGGER.debug(f"args = {args}")

    no_args = (len(sys.argv) == 1)
    if no_args:
        argparser.print_help()
        sys.exit(1)

    if args["subcommand"] == "set":
        get_set_booru_wallpaper(args)
    if args["subcommand"] == "list":
        booru_wallpaper_info()
    if args["subcommand"] == "edit":
        data = read_json(IMAGE_DATA_PATH)
        filename = booru_image_name(data)
        path = os.path.join(WALLPAPERS_DIR, filename)
        edit_wallpaper(path, args["blur"], args["grey"], args["dim"])
        set_wallpaper(path)


if __name__ == "__main__":
    main()
