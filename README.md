# Booru Wallpaper
A work-in-progress script that aims to replicate the functionality of the Mbooru extension for Muzei on Android, on desktop computers.

This program will set the desktop wallpaper (in Windows, Mac and Linux) to a random image from a Danbooru-like imageboard that fits the specified search tags. After a specified amount of time has passed, it will fetch another image.

I like Muzei and the [Muzei Client](http://forum.xda-developers.com/android/general/windows-muzeiclient-change-windows-t2957586) by madhacker exists, but it doesn't support Danbooru (or any other sites for that matter), and so this project came to be. I hope this might be useful for someone else too. Someday I might make a fork of the client with support for extensions, but I'll wait and see if the original developer is making any progress before doing so.

## Dependencies
* Python 3.6
* Pillow module
* Cronjob module

**Please note that nothing but the `XD.py` script works right now.**

## Usage
Call the script from the terminal with the `--help` flag for usage.

Here's an example of how to use the `XD.py` script:  
`./XD.py touhou scenery --imageboard https://danbooru.donmai.us --retries 0 --size 0.5`
This will set the wallpaper to an image tagged with 'touhou' and 'scenery' from the imageboard located at https://danbooru.donmai.us. It will _not_ retry if it fails to get an image and the image needs to be at least half the size of the screen resolution.

To get another image with the same settings as before, do:  
`./XD.py --next`

Please note that no scheduling capabilities are available at this stage of development.
