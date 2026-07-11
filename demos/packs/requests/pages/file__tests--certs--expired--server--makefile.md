# tests/certs/expired/server/Makefile

- page_id: `file__tests--certs--expired--server--makefile`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/certs/expired/server/Makefile
- type: code

## Content

```
.PHONY: all clean

server.key:
	openssl genrsa -out $@ 2048

server.csr: server.key
	openssl req -key $< -new -out $@ -config cert.cnf

server.pem: server.csr
	openssl x509 -req -CA ../ca/ca.crt -CAkey ../ca/ca-private.key -in server.csr -outform PEM -out server.pem -days 0 -CAcreateserial
	openssl x509 -in ../ca/ca.crt -outform PEM >> $@

all: server.pem

clean:
	rm -f server.*

```
