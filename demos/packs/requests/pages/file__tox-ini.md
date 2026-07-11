# tox.ini

- page_id: `file__tox-ini`
- url: https://github.com/psf/requests/tree/v2.34.2/tox.ini
- type: code

## Content

```
[tox]
envlist = py{310,311,312,313,314}-{default, use_chardet_on_py3}

[testenv]
deps = -rrequirements-dev.txt
extras =
    security
    socks
commands =
    pytest {posargs:tests}

[testenv:default]

[testenv:use_chardet_on_py3]
extras =
    security
    socks
    use_chardet_on_py3

```
