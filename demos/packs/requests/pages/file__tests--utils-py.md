# tests/utils.py

- page_id: `file__tests--utils-py`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/utils.py
- type: code

## Content

```
import contextlib
import os


@contextlib.contextmanager
def override_environ(**kwargs):
    save_env = dict(os.environ)
    for key, value in kwargs.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(save_env)

```
