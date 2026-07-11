# setup.py

- page_id: `file__setup-py`
- url: https://github.com/psf/requests/tree/v2.34.2/setup.py
- type: code

## Content

```
import sys

if sys.version_info < (3, 10):  # noqa: UP036
    sys.stderr.write("Requests requires Python 3.10 or later.\n")
    sys.exit(1)

from setuptools import setup

setup()

```
