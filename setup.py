#!/usr/bin/env python3

#
# created by kpe on 09.01.2021 at 2:20 PM
#

import pathlib
import sys

from setuptools import setup, find_packages, convert_path


WORK_DIR = pathlib.Path(__file__).parent
MOD_NAME = "telerembash"


# Check python version
MINIMAL_PY_VERSION = (3, 7)
if sys.version_info < MINIMAL_PY_VERSION:
    raise RuntimeError(f"{MOD_NAME} works only with Python {{}}+".format('.'.join(map(str, MINIMAL_PY_VERSION))))


def _version():
    ns = {}
    with open(convert_path(f"{MOD_NAME}/version.py"), "r") as fh:
        exec(fh.read(), ns)
    return ns['__version__']


__version__ = _version()


with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as reader:
    install_requires = list(map(lambda x: x.strip(), reader.readlines()))


setup(name=f"{MOD_NAME}",
      version=__version__,
      url="https://github.com/kpe/telerembash/",
      description="A Telegram Remote Shell Bot with HOTP authentication.",
      long_description=long_description,
      long_description_content_type="text/x-rst",
      keywords="telegram totp hotp authentication bot",
      license="MIT",

      author="kpe",
      author_email="kpe.git@gmailbox.org",
      packages=find_packages(exclude=["tests"]),
      package_data={"": ["*.txt", "*.rst"],
                    "telerembash": ["artifacts/*.yaml", "artifacts/*.template"]},
      entry_points={
          'console_scripts': ['telerem=telerembash.cli:main']
      },

      zip_safe=True,
      install_requires=install_requires,
      python_requires=">=3.5",
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: Implementation :: CPython",
          "Programming Language :: Python :: Implementation :: PyPy"])

