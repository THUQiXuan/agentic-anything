# tests/test_hooks.py

- page_id: `file__tests--test-hooks-py`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/test_hooks.py
- type: code

## Content

```
import pytest

from requests import hooks


def hook(value):
    return value[1:]


@pytest.mark.parametrize(
    "hooks_list, result",
    (
        (hook, "ata"),
        ([hook, lambda x: None, hook], "ta"),
    ),
)
def test_hooks(hooks_list, result):
    assert hooks.dispatch_hook("response", {"response": hooks_list}, "Data") == result


def test_default_hooks():
    assert hooks.default_hooks() == {"response": []}

```
