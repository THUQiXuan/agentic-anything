# tests/certs/valid/server/Makefile

- page_id: `file__tests--certs--valid--server--makefile`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/certs/valid/server/Makefile
- type: code

## Content

```
.PHONY: all clean

server.key:
	openssl genrsa -out $@ 2048

server.csr: server.key
	openssl req -key $< -config cert.cnf -new -out $@

server.pem: server.csr
	openssl x509 -req -CA ../ca/ca.crt -CAkey ../ca/ca-private.key -in server.csr -outform PEM -out server.pem -extfile cert.cnf -extensions v3_ca -days 7200 -CAcreateserial
	openssl x509 -in ../ca/ca.crt -outform PEM >> $@

all: server.pem

clean:
	rm -f server.*

```
