#Booru Wallpaper
A work-in-progress console application that aims to basically be the
Mbooru extension for Muzei on Android, on PC.

This program will set the desktop wallpaper (in Windows, Mac and Linux)
to a random image from a booru that fits the specified search tags.
After a specified amount of time has passed, another image will be fetched.

I like Muzei and a Muzei Client exists, but it doesn't support Danbooru,
and so this project came to be. I don't intend to replace the [Muzei Client](http://forum.xda-developers.com/android/general/windows-muzeiclient-change-windows-t2957586) by madhacker, only to have something that
works for me. I hope this might just be useful for someone else too.
Maybe someday I'll make a fork of the client with support for extensions,
but I'll wait and see if any progress is being made by the original developer
before doing so.

##Dependencies
* Python 3.6 (currently in beta)
* Pillow module

##To Do
1. Get the backbone of the program finished.
2. Add all the features (including the undocumented tag rotation feature).
3. Make it compatible with the interactive shell, as opposed to just the
   shell script.
