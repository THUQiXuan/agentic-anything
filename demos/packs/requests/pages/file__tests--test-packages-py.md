# tests/test_packages.py

- page_id: `file__tests--test-packages-py`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/test_packages.py
- type: code

## Content

```
import requests


def test_can_access_urllib3_attribute():
    requests.packages.urllib3


def test_can_access_idna_attribute():
    requests.packages.idna


def test_can_access_chardet_attribute():
    requests.packages.chardet

```
