#!/bin/bash

MOD_NAME=telerembash
PEP8_IGNORE=E221,E501,W504,W391,E241

pycodestyle --ignore=${PEP8_IGNORE} --exclude=tests,.venv -r --show-source tests ${MOD_NAME}

coverage run --source=${MOD_NAME} $(which nosetests) -v --with-doctest tests/ --exclude-dir tests/nonci/
coverage report --show-missing --fail-under=90

python setup.py sdist bdist_wheel
twine check dist/*