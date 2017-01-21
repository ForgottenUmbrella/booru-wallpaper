#!/usr/bin/env python3.6
"""XP version of the project. Features only added when needed."""
# TODO: screen size, install new os
import os
import os.path
import subprocess
import argparse
import urllib.parse
import urllib.request
import json
import tkinter
import ctypes
import logging

logging.basicConfig(filename='log.log', filemode='w',
                    format='{levelname}: {message}', style='{',
                    level='DEBUG')


def get_image(tags, imageboard, retries=3, fit_screen=False, variance=1.0):
    """Retrieve an image and return its data."""
    posts = f'{imageboard}/posts.json'
    query = urllib.parse.urlencode({
        'limit': 1,
        'tags': ' '.join(tags),
        'random': 'true',
    })
    post = f'{posts}?{query}'
    root = tkinter.Tk()
    screen_height = root.getscreenheight()
    screen_width = root.getscreenwidth()
    for attempt in range(retries):
        with urllib.request.urlopen(post) as request:
            SUCCESS = range(100, 400)
            status = request.getcode()
            if status in SUCCESS:
                data = json.loads(request.read().decode('utf-8'))[0]
        good_fit = (data['image_height'] >= screen_height * variance
                    and data['image_width'] >= screen_width * variance)
        if data and (good_fit or not fit_screen):
            break
    else:
        if status not in SUCCESS:
            error = f'{imageboard} returned status {status}.'
        elif not good_fit:
            error = "Image wasn't big enough."
        else:
            error = 'No images.'
        raise ValueError(f'Image getting failed. {error}'

    return data
    while True:
        logging.info('Retrieving image...')
        logging.debug('tags = {!r}'.format(tags))
        logging.debug('imageboard_url = {!r}'.format(imageboard))
        # Apparently you should use a context manager
        with urllib.request.urlopen(post) as request:
        # request = urllib.request.urlopen('{}?{}'.format(posts, query))
            try:
                metadata = json.loads(request.read().decode('utf-8'))[0]
            except IndexError:
                if emergency_brake:
                    raise ValueError('Query returned nothing. ¯\_(ツ)_/¯')
                query = urllib.parse.urlencode({
                    'limit': 1,
                    'tags': ' '.join(tags),
                })
                emergency_brake = True
            else:
                break
    return metadata
