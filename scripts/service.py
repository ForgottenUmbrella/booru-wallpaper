#!/usr/bin/env python3
"""Daemon: ability to the extent of changing wallpapers."""
# XXX: just use nohup service.py &
# XXX: just use nohup XD.py --next &
import os
import time
import json

import XD

with open(XD.config_path) as config_file:
    config = json.load(config_file)

while True:
    time.sleep(config['duration'])
    XD.main(['--next'])
