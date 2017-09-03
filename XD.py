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
import contextlib

import tkinter
import requests
import PIL.Image
import PIL.ImageEnhance
import PIL.ImageFilter

SCRIPT_PATH = os.path.realpath(__file__)
ROOT_DIR = os.path.dirname(SCRIPT_PATH)
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


def sorted_files(directory):
    """Return a list of files sorted by modified date."""
    files = []
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        files.append(path)
    files.sort(key=os.path.getmtime)
    return files


def makedirs(directories):
    """Create directories if they are missing."""
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


@contextlib.contextmanager
def spinner():
    """Context manager for a spinning cursor so it prints neatly."""
    yield wait_warmly()
    print("\bDone.")


def wait_warmly():
    """Yield parts of a spinning cursor."""
    chars = r"-\|/"
    while True:
        for char in chars:
            yield char


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
    with requests.get(url, stream=True) as response, open(path, "wb") as file,\
            spinner() as cursors:
        chunks = response.iter_content(chunk_size=128)
        for cursor, chunk in zip(cursors, chunks):
            print("\rDownloading...", cursor, end="")
            file.write(chunk)


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
    # XXX: Is this needed?
    # success = range(100, 400)
    try:
        response = requests.get(url, params=params)
    except requests.exceptions.ConnectionError:
        print("No internet connection. Please connect to the internet.")
        sys.exit(126)
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
        # except json.JSONDecodeError as ex:
        #     LOGGER.error(ex)
        #     raise ValueError(f"{url} does not have JSON data.")
        # except ValueError as ex:
        #     LOGGER.error(ex)
        #     raise ValueError("Invalid/conflicting tags.") from None
        good_size = (
            data["image_height"] >= screen_height * scale and
            data["image_width"] >= screen_width * scale
        )
        if good_size:
            return data
    raise ValueError("No images were large enough.")


def booru_image_path(image_data, wallpapers_dir):
    """Return the path of a booru image."""
    filename = os.path.basename(image_data["file_url"])
    return os.path.join(wallpapers_dir, filename)


def remove_old_wallpapers(limit, directories):
    """Delete old wallpapers if there are too many in the folders."""
    print("Removing old wallpapers...")
    for directory in directories:
        wallpapers = sorted_files(directory)
        num_extra = len(wallpapers) - limit
        if num_extra > 0:
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
            "Make sure to configure your window manager/desktop environment "
            "to use `feh` as the wallpaper source."
        ))
        print(textwrap.fill(
            "For example, if you're using i3, your ~/.config/i3/config should "
            "contain: 'exec_always --no-startup-id ~/.fehbg'."
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


def natural(num):
    """Return a number if it is natural, else raise an error."""
    # Will raise an error if num is a (string) float.
    num = int(num)
    if num <= 0:
        raise ValueError("Number must be whole and greater than 0.")
    return num


def percentage(num):
    """Return a number if between 0 and 1, else raise an error."""
    num = float(num)
    if num < 0 or num > 1:
        raise ValueError("Number must be between 0 and 1.")
    return num


def nonnegative(num):
    """Return a number if it isn't negative, else raise an error."""
    num = float(num)
    if num < 0:
        raise ValueError("Number must be greater than or equal to 0.")
    return num


def init_argparser():
    """Return an ArgumentParser specialised for this script."""
    percent_meta = "{0.0,...,1.0}"
    natural_meta = "{1,2,3,...}"
    nonnegative_int_meta = "{0,1,2,...}"
    nonnegative_float_meta = "{0.0,...}"

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
        "period": ("-p", "--period"),
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
        "period": {
            "help":
                "hours to wait before changing wallpapers (a value of 0 means "
                "it will never change)",
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
        *args["attempts"], **kwargs["attempts"], type=natural,
        metavar=natural_meta
    )
    set_subparser.add_argument(
        *args["scale"], **kwargs["scale"], type=nonnegative,
        metavar=nonnegative_float_meta
    )
    set_subparser.add_argument(
        *args["keep"], **kwargs["keep"], type=natural,
        metavar=natural_meta
    )
    set_subparser.add_argument(
        *args["period"], **kwargs["period"], type=nonnegative,
        metavar=nonnegative_int_meta
        # XXX: Can scheduling handle more than 24 hours?
        # choices=range(0, 25), metavar="{1 ... 24}"
    )
    edit_group = set_subparser.add_argument_group(
        "wallpaper edit arguments",
        "immediately change the wallpaper's appearance"
    )
    edit_group.add_argument(
        *args["blur"], **kwargs["blur"], type=percentage, metavar=percent_meta
    )
    edit_group.add_argument(
        *args["grey"], **kwargs["grey"], type=percentage, metavar=percent_meta
    )
    edit_group.add_argument(
        *args["dim"], **kwargs["dim"], type=percentage, metavar=percent_meta
    )

    parent_subparser = argparse.ArgumentParser(add_help=False)
    for arg in args:
        parent_subparser.add_argument(
            *args[arg], **kwargs[arg], action="store_true"
        )
    subparsers.add_parser(
        "get", parents=[parent_subparser], help="view configuration values",
        epilog="if no options are specified, show all"
    )
    subparsers.add_parser(
        "reset", parents=[parent_subparser],
        help="set configuration back to its initial values",
        epilog="if no options are specified, reset all"
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


def next_wallpaper(config, image_data_path, wallpapers_dir, edits_dir):
    """Set the next wallpaper, and write its image data."""
    data = get_image_data(
        config["tags"], config["imageboard"], attempts=config["attempts"],
        scale=config["scale"]
    )
    # Patch so info subcommand can display source.
    data["post_url"] = os.path.join(
        config["imageboard"], "posts", str(data["id"])
    )
    url = config["imageboard"] + data["file_url"]
    path = booru_image_path(data, wallpapers_dir)
    download(url, path)
    remove_old_wallpapers(config["keep"], (wallpapers_dir, edits_dir))
    if any(config[edit] != 0 for edit in ("blur", "grey", "dim")):
        path = edit_booru_wallpaper(config, path, edits_dir)
    set_wallpaper(path)
    write_json(image_data_path, data)


def wallpaper_info(image_data_path):
    """Return information about the current wallpaper."""
    try:
        data = read_json(image_data_path)
    except FileNotFoundError:
        print(textwrap.fill(
            "There is no information on the wallpaper, as it was not set "
            "through this program."
        ))
        sys.exit(2)
    LOGGER.debug(f"data = {data}")
    info = []
    for key in ("artist", "character", "copyright"):
        real_key = f"tag_string_{key}"
        info_list = gram_join(str(data[real_key]), final_joiner=", ")
        info.extend(textwrap.wrap(
            f"{key}: {info_list}",
            subsequent_indent=" " * len(key+ ": ")
        ))
    info.append(f"url: {data['post_url']}")
    return "\n".join(info)


def blur_image(image, blur_ratio):
    """Return a blurry PIL image."""
    width = max(image.size)
    # Divide by two, otherwise we get a diameter.
    blur_radius = blur_ratio * width / 2
    blur_filter = PIL.ImageFilter.GaussianBlur(blur_radius)
    new_image = image.filter(blur_filter)
    return new_image


def grey_image(image, grey_ratio):
    """Return a grey PIL image."""
    enhancer = PIL.ImageEnhance.Color(image)
    colour_ratio = 1 - grey_ratio
    new_image = enhancer.enhance(colour_ratio)
    return new_image


def dim_image(image, dim_ratio):
    """Return a dimmed PIL image."""
    enhancer = PIL.ImageEnhance.Brightness(image)
    bright_ratio = 1 - dim_ratio
    new_image = enhancer.enhance(bright_ratio)
    return new_image


def edit_image(in_path, out_path=None, blurriness=0, greyness=0, dimness=0):
    """Make an image more/less blurry, grey and dim.

    Args:
        in_path (str): Location of image to be edited.
        out_path (str): Location of where to save the edited image.
            Defaults to the same as `in_path`.
        blurriness (float): How blurry it should be, from 0 to 1.
            Defaults to 0.
        greyness (float): How colourless it should be, from 0 to 1.
            Defaults to 0.
        dimness (float): How dim it should be, from 0 to 1.
            Defaults to 0.
    """
    if out_path is None:
        out_path = in_path
    image = PIL.Image.open(in_path)
    image = blur_image(image, blurriness)
    image = grey_image(image, greyness)
    image = dim_image(image, dimness)
    image.save(out_path)


def get_config(path, initial_config):
    """Return a stored config dict or a newly created one if missing."""
    try:
        config = read_json(path)
    except FileNotFoundError:
        LOGGER.info("Missing config")
        config = initial_config
        write_json(path, config)
    return config


def update_config(config_path, config, args):
    """Update the config options if they've changed."""
    for arg in config:
        if args[arg] is not None:
            config[arg] = args[arg]
    write_json(config_path, config)


def reset_config(path, config, initial_config, args):
    """Restore some config options to initial values."""
    none_specified = not any(args[arg] for arg in initial_config)
    for arg in initial_config:
        if args[arg] or none_specified:
            config[arg] = initial_config[arg]
    write_json(path, config)


def config_info(config, args):
    """Return some config options."""
    options = []
    none_specified = not any(args[arg] for arg in config)
    for arg in config:
        if args[arg] or none_specified:
            options.append(f"{arg}: {config[arg]}")
    return "\n".join(options)


def edit_booru_wallpaper(config, path, edits_dir):
    """Modify the wallpaper in place and return its new path."""
    blur = config["blur"] or 0
    grey = config["grey"] or 0
    dim = config["dim"] or 0
    filename = os.path.basename(path)
    new_path = os.path.join(edits_dir, filename)
    print("Editing wallpaper...")
    edit_image(path, new_path, blur, grey, dim)
    return new_path


def update_and_edit(
        config_path, image_data_path, wallpapers_dir, edits_dir, args):
    """Update the config and edit the wallpaper if necessary."""
    config = read_json(config_path)
    update_config(config_path, config, args)
    if any(config[edit] is not None for edit in ("blur", "grey", "dim")):
        image_data = read_json(image_data_path)
        image_path = booru_image_path(image_data, wallpapers_dir)
        new_path = edit_booru_wallpaper(args, image_path, edits_dir)
        set_wallpaper(new_path)


def main(argv=None):
    """Set the wallpaper and schedule it to change.

    Args:
        argv ([str]): Arguments from the command line for the program.

    Raises:
        ValueError: If the user provided an invalid command.
    """
    argparser = init_argparser()
    args = vars(argparser.parse_args(argv))
    initial_config = {
        "tags": [],
        "imageboard": "https://danbooru.donmai.us",
        "attempts": 1,
        "scale": 0.0,
        "keep": 1,
        "period": 0,
        "blur": 0.0,
        "grey": 0.0,
        "dim": 0.0,
    }
    data_dir = os.path.join(ROOT_DIR, "data")
    image_data_path = os.path.join(data_dir, "image_data.json")
    config_path = os.path.join(data_dir, "config.json")
    wallpapers_dir = os.path.join(ROOT_DIR, "wallpapers")
    edits_dir = os.path.join(ROOT_DIR, "edits")
    makedirs((data_dir, wallpapers_dir, edits_dir))
    config = get_config(config_path, initial_config)

    if args["verbose"]:
        _TERMINAL_HANDLER.setLevel(logging.DEBUG)
    else:
        _TERMINAL_HANDLER.setLevel(logging.INFO)
    # No debug messages are displayed until the level is set, so no logs
    # can be performed until now.
    LOGGER.debug(f"args = {args}")
    LOGGER.debug(f"config = {config}")

    no_args = (len(sys.argv) == 1)
    if no_args:
        argparser.print_help()
        sys.exit(2)

    subcommand = args["subcommand"]
    if subcommand == "set":
        update_and_edit(
            config_path, image_data_path, wallpapers_dir, edits_dir,
            args
        )
    if subcommand == "get":
        print(config_info(config, args))
    if subcommand == "reset":
        reset_config(config_path, config, initial_config, args)
    if subcommand == "next":
        next_wallpaper(config, image_data_path, wallpapers_dir, edits_dir)
    if subcommand == "info":
        print(wallpaper_info(image_data_path))


if __name__ == "__main__":
    main()
