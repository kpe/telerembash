# coding=utf-8
#
# created by kpe on 09.01.2021 at 2:22 PM
#

from __future__ import division, absolute_import, print_function

from .version import __version__
from ._logging import setup_logging

import os
setup_logging(default_path=os.path.normpath(os.path.join(os.getcwd(), "logging.config.yaml")))
