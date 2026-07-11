# tests/test_adapters.py

- page_id: `file__tests--test-adapters-py`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/test_adapters.py
- type: code

## Content

```
import requests.adapters


def test_request_url_handles_leading_path_separators():
    """See also https://github.com/psf/requests/issues/6643."""
    a = requests.adapters.HTTPAdapter()
    p = requests.Request(method="GET", url="http://127.0.0.1:10000//v:h").prepare()
    assert "//v:h" == a.request_url(p, {})

```
