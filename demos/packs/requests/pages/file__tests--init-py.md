# tests/__init__.py

- page_id: `file__tests--init-py`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/__init__.py
- type: code

## Content

```
"""Requests test package initialisation."""

import warnings

try:
    from urllib3.exceptions import SNIMissingWarning

    # urllib3 1.x sets SNIMissingWarning to only go off once,
    # while this test suite requires it to always fire
    # so that it occurs during test_requests.test_https_warnings
    warnings.simplefilter("always", SNIMissingWarning)
except ImportError:
    # urllib3 2.0 removed that warning and errors out instead
    SNIMissingWarning = None

```
