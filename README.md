# Booru Wallpaper
A work-in-progress script that aims to replicate the functionality of the
Mbooru extension for Muzei on Android, on desktop computers.

This program will set the desktop wallpaper (on Linux, Windows and Mac) to a
random image from a Danbooru-like imageboard that fits the specified search
tags.

I like Muzei and the [Muzei
Client](http://forum.xda-developers.com/android/general/windows-muzeiclient-change-windows-t2957586)
by madhacker exists, but it doesn't support Danbooru (or any other sites for
that matter), and so this project came to be. I hope this might be useful for
someone else too. Someday I might make a fork of the client with support for
extensions, but I'll wait and see if the original developer is making any
progress before doing so.

## Requirements
* Python >= 3.6
* Pillow module
* Tk module
* Requests module
* Feh (if using a standalone window manager)

You can install the missing modules with `pip install --user MODULE_NAME`.

## Usage
Call the script from the terminal with the `--help` flag for usage.

Here's an example of how to use the `XD.py` script:

`./XD.py set touhou scenery --imageboard https://danbooru.donmai.us --retries 0
--size 0.5`

This will set the wallpaper to an image tagged with 'touhou' and 'scenery' from
the imageboard located at https://danbooru.donmai.us. It will _not_ retry if it
fails to get an image and the image needs to be at least half the size of the
screen resolution.

To get another image with the same settings as before, do:

`./XD.py --next`

Please note that no scheduling capabilities are available at this stage of
development because I don't know how to get python-crontab working.  

You'll need to set it up yourself using `crontab` with the command `nohup
/path/to/XD.py --next &` on \*NIX, or `pythonw.exe /path/to/XD.py --next` in
the Task Scheduler on Windows.

Also note that Wayland compositors are not supported yet (not until the
protocol matures and something like `feh` comes about).
