# cs336_basics/__init__.py

- page_id: `stanford-cs336-assignment1-basics__file__cs336-basics--init-py`
- url: https://github.com/stanford-cs336/assignment1-basics/tree/main
- type: code

## Content

```
import importlib.metadata

try:
    __version__ = importlib.metadata.version("cs336_basics")
except importlib.metadata.PackageNotFoundError:
    pass

```
