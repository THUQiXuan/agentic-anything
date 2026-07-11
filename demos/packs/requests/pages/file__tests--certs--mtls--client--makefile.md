# tests/certs/mtls/client/Makefile

- page_id: `file__tests--certs--mtls--client--makefile`
- url: https://github.com/psf/requests/tree/v2.34.2/tests/certs/mtls/client/Makefile
- type: code

## Content

```
.PHONY: all clean

client.key:
	openssl genrsa -out $@ 2048

client.csr: client.key
	openssl req -key $< -new -out $@ -config cert.cnf

client.pem: client.csr
	openssl x509 -req -CA ./ca/ca.crt -CAkey ./ca/ca-private.key -in client.csr -outform PEM -out client.pem -days 730 -CAcreateserial
	openssl x509 -in ./ca/ca.crt -outform PEM >> $@

all: client.pem

clean:
	rm -f client.*

```
