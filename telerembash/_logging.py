# coding=utf-8
#
# created by kpe on 16.10.2020 at 10:04 PM
#

from __future__ import division, absolute_import, print_function

import os
import sys
import yaml
import logging
import logging.config
import coloredlogs


def setup_logging(default_path='logging.yaml', default_level=logging.INFO, env_key='LOG_CFG'):

    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
            except Exception as e:
                print(e)
                print('Error in Logging Configuration. Using default configs')
                logging.basicConfig(level=default_level)
                coloredlogs.install(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        coloredlogs.install(level=default_level)
        print(f"Failed to load logging configuration:[{path}]. Using default configs", file=sys.stderr)
