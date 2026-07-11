# tests/certs/expired/Makefile

- page_id: `file__tests--certs--expired--makefile`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/certs/expired/Makefile
- type: code

## Content

```
.PHONY: all clean ca server

ca:
	make -C $@ all

server:
	make -C $@ all

all: ca server

clean:
	make -C ca clean
	make -C server clean

```
