#!/usr/bin/env python3
# coding=utf-8
"""Another version. Features added when I feel like it."""
import sys
import os.path
import subprocess
import urllib.parse
import urllib.request
import argparse
import configparser
import json
import ctypes
import logging
import tkinter

import PIL.Image
import PIL.ImageEnhance
import PIL.ImageFilter

SCRIPT_PATH = os.path.realpath(__file__)
ROOT_DIR = os.path.dirname(SCRIPT_PATH)
IMAGE_DATA_DIR = os.path.join(ROOT_DIR, "data")
WALLPAPER_DIR = os.path.join(ROOT_DIR, "wallpapers")

LOGGER = logging.getLogger(__name__)


def init_logger(verbose):
    """Initialise the global logger's properties."""
    LOGGER.setLevel(logging.DEBUG)
    log_path = os.path.join(ROOT_DIR, "log.log")
    debug_handler = logging.FileHandler(log_path, mode="w")
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


def get_json(url):
    """Make a GET request and return the JSON data as a dict.

    Args:
        url (str): Webpage link to make a request to.

    Returns:
        dict: A JSON object from `url` decoded to a Python dictionary.

    # Raises:
    #     RequestError: If the request is unsuccessful.
    #     ValueError: If no JSON data is available from `url`.
    """
    success = range(100, 400)
    LOGGER.debug(f"GET url = {url}")
    with urllib.request.urlopen(url) as response:
        status = response.getcode()
        LOGGER.debug(f"status = {status}")
        succeeded = status in success
        if succeeded:
            raw = response.read()
            encoding = response.headers.get_content_charset()
            LOGGER.debug(f"encoding = {encoding}")
            decoded = raw.decode(encoding)
            # try:
            json_data = json.loads(decoded)
            # except json.JSONDecodeError as original_error:
            #     LOGGER.error(original_error)
            #     raise ValueError(f"{url} does not have JSON data.")
        # else:
            # raise RequestError(f"Response returned code {status}.")
    # if not json_data:
        # raise ValueError(f"No data from {url}.")
    LOGGER.debug(f"json_data = {json_data}")
    return json_data


def get_image_metadata(tags, imageboard):
    """Retrieve an image and return its metadata.

    Args:
        tags ([str]): Labels the image must match.
        imageboard (str): URL of the website to get images from.

    Returns:
        dict: Data stored about the image from the imageboard.

    # Raises:
    #     ValueError: If there are too many tags, or there were no images
    #         tagged with them all.
    #     OSError: If there was no internet connection available.
    """
    posts = f"{imageboard}/posts.json"
    query = urllib.parse.urlencode({
        "limit": 1,
        "tags": " ".join(tags),
        "random": "true",
        })
    post = f"{posts}?{query}"
    # try:
    data = get_json(post)[0]
    # except urllib.error.HTTPError as original_error:
    #     LOGGER.error(original_error)
    #     raise ValueError("Too many tags.") from None
    # except urllib.error.URLError as original_error:
    #     LOGGER.error(original_error)
    #     raise OSError("No internet connection.") from None
    # except ValueError as original_error:
    #     LOGGER.error(original_error)
    #     raise ValueError("Invalid/conflicting tags.") from None
    return data


def get_valid_image_metadata(tags, imageboard, attempts=1, scale=1.0):
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
    """
    (screen_height, screen_width) = screen_dimensions()
    for attempt in range(attempts):
        # `attempt` is zero-based, but humans aren't.
        real_attempt = attempt + 1
        print(f"Attempt {real_attempt}: Getting image...")
        data = get_image_metadata(tags, imageboard)
        good_fit = (
            data["image_height"] >= screen_height * scale and
            data["image_width"] >= screen_width * scale
            )
        if good_fit:
            return data
    raise ValueError("No images were large enough.")


def read_json(path):
    """Return a JSON object from a file."""
    with open(path) as file:
        data = json.load(file)
    return data


def download(url, file_path):
    """Store a copy of a file from the internet."""
    print("Downloading image...")
    urllib.request.urlretrieve(url, file_path)


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
    data = get_valid_image_metadata(
        tags, imageboard, attempts=attempts, scale=scale
        )
    url = imageboard + data["file_url"]
    extension = data["file_ext"]
    # TODO: Use default name. /wallpaper.
    filename = f"wallpaper.{extension}"
    path = os.path.join(WALLPAPER_DIR, filename)
    download(url, path)
    return path, data


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
            "verbose": False,
        }
        with open(self.path, "w") as defaults_file:
            self.write(defaults_file)


def init_argparser(defaults):
    """Return an ArgumentParser with appropriate defaults."""
    percentage = range(0, 101)
    percent_meta = "{0 ... 100}"
    argparser = argparse.ArgumentParser(
        description="Utility to regularly set the wallpaper to a random "
        "tagged image from a booru"
        )
    subparsers = argparser.add_subparsers(dest="subcommand")

    subparser_set = subparsers.add_parser(
        "set", help="get an image and set it as the wallpaper"
        )
    subparser_set.add_argument(
        "tags", nargs="*",
        help="a space-delimited list of tags the image must match"
        )
    subparser_set.add_argument(
        "-i", "--imageboard", default=defaults["imageboard"],
        help="a URL to source images from (default: %(default)s)"
        )
    subparser_set.add_argument(
        "-r", "--retries", type=int, default=int(defaults["retries"]),
        help="the number of times to retry getting the image "
        "(default: %(default)s)"
        )
    subparser_set.add_argument(
        "-s", "--scale", type=float, default=float(defaults["scale"]),
        help="the minimum relative size of the image to the screen "
        "(default: %(default)s)"
        )
    # TODO: move out of subparser
    subparser_set.add_argument(
        "-n", "--next", action="store_true",
        default=defaults.getboolean("next"),
        help="get the next wallpaper using the previous settings"
        )

    subparser_list = subparsers.add_parser(
        "list", help="print information about the current wallpaper"
        )
    subparser_list.add_argument(
        "list", nargs="*", choices=[
            "all",
            "artist",
            "character",
            "copyright",
            "general",
            # XXX: default can't yet be a list (http://bugs.python.org/issue9625)
            # ], default=[element.strip() for element in defaults["list"].split(",")],
        ], default="all",
        help="the list to list (default: %(default)s)"
        )

    subparser_edit = subparsers.add_parser(
        "edit", help="modify the current wallpaper"
        )
    subparser_edit.add_argument(
        "-b", "--blur", type=int, choices=percentage,
        default=int(defaults["blur"]), metavar=percent_meta,
        help="how blurry the image should be, as a percentage "
        "(default: %(default)s)"
        )
    subparser_edit.add_argument(
        "-g", "--grey", type=int, choices=percentage,
        default=int(defaults["grey"]), metavar=percent_meta,
        help="how monochrome the image should be, as a percentage "
        "(default: %(default)s)"
        )
    subparser_edit.add_argument(
        "-d", "--dim", type=int, choices=percentage,
        default=int(defaults["dim"]), metavar=percent_meta,
        help="how dark the image should be, as a percentage "
        "(default: %(default)s)"
        )

    argparser.add_argument(
        "-d", "--duration", type=int, choices=range(1, 25),
        default=int(defaults["duration"]), metavar="{1 ... 24}",
        help="the duration of the wallpaper in hours (default: %(default)s)"
        )
    argparser.add_argument(
        "-v", "--verbose", action="store_true",
        default=defaults.getboolean("verbose"), help="increase verbosity"
        )

    return argparser


def get_previous_args(config_path):
    """Return previous arguments supplied from a path.

    Args:
        config_path (str): Path where previous arguments are
            stored.

    Returns:
        dict: The previous arguments passed as key-value pairs.

    Raises:
        ValueError: If no previous arguments are available.
    """
    # try:
    with open(config_path) as config_file:
        previous_args = json.load(config_file)
    # except (FileNotFoundError, json.JSONDecodeError):
    #     LOGGER.error("No prev_config file.")
    #     raise ValueError("No previous arguments.")
    return previous_args


def set_booru_wallpaper(args, image_data_path):
    """Set the wallpaper to an image from a booru and write data."""
    config_path = os.path.join(IMAGE_DATA_DIR, "prev_config.json")
    if args["next"]:
        LOGGER.debug("--next called")
        # try:
        args = get_previous_args(config_path)
        # except ValueError as original_error:
        #     LOGGER.error(original_error)
        #     raise ValueError(
        #         "Please set some arguments before getting the next"
        #         "wallpaper."
        #         )

    path, data = download_image(
        args["tags"], args["imageboard"], args["retries"] + 1, args["scale"]
        )
    set_wallpaper(path)

    with open(image_data_path, "w") as data_file:
        json.dump(data, data_file, indent=4, separators=(", ", ": "))
    with open(config_path, "w") as config_file:
        json.dump(args, config_file, indent=4, separators=(", ", ": "))


def list_wallpaper_info(args, image_data_path):
    """Print requested information about the current wallpaper."""
    if "all" in args["list"]:
        args["list"] = [
            "artist",
            "character",
            "copyright",
            "general",
        ]
    # try:
    with open(image_data_path) as data_file:
        data = json.load(data_file)
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
    defaults_path = os.path.join(IMAGE_DATA_DIR, "defaults.ini")
    defaults = XDConfigParser(defaults_path)["DEFAULT"]
    argparser = init_argparser(defaults)
    args = vars(argparser.parse_args(argv))
    image_data_path = os.path.join(IMAGE_DATA_DIR, "image_data.json")

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
        set_booru_wallpaper(args, image_data_path)
    if args["subcommand"] == "list":
        list_wallpaper_info(args, image_data_path)
    if args["subcommand"] == "edit":
        data = read_json(image_data_path)
        path = os.path.join(WALLPAPER_DIR, f"wallpaper.{data['file_ext']}")
        edit_wallpaper(path, args["blur"], args["grey"], args["dim"])
        set_wallpaper(path)

    # XXX: Why is this here? FIXME: scheduling
    # if args["duration"] != previous_args["duration"]:
    #     print("Scheduling next wallpaper change...")
    #     cron_path = os.path.join(IMAGE_DATA_DIR, "schedule.tab")
    #     tab = crontab.CronTab(tabfile=cron_path)
    #     tab.remove_all()
    #     command = f"{SCRIPT_PATH} set --next"
    #     cron_job = tab.new(command)
    #     if args["duration"] == 24:
    #         cron_job.every().dom()
    #     else:
    #         cron_job.every(args["duration"]).hours()
    #     tab.write()
    #     tab_view = tab.render()
    #     LOGGER.debug(f"cron_job = {tab_view}")
        # user = getpass.getuser()
        # cron_path = f"/var/spool/cron/crontabs/{user}"
        # try:
        #     with open(cron_path) as cron_file:
        #         crontab = cron_file.readlines()
        # except FileNotFoundError:
        #     LOGGER.error("No cron_file.")
        #     crontab = []
        #
        # for line_number, line in enumerate(crontab):
        #     if "booru-wallpaper" in line:
        #         break
        # else:
        #     line_number = len(crontab)
        #
        # if args["duration"] == 24:
        #     duration = "0 * * * *"
        # else:
        #     duration = "0 */{args["duration"] * * *"
        #
        # command = f"{SCRIPT_PATH} set --next # booru-wallpaper"
        # CRONTAB[LINE_NUMBER] = F"{DURATION} {COMMAND}\N"
        # LOGGER.debug(f"crontab = {crontab}")
        # with open(cron_path, "w") as cron_file:
        #     cron_file.writelines(crontab)


if __name__ == "__main__":
    main()
