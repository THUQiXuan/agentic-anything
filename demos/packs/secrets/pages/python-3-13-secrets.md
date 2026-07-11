# secrets — Generate secure random numbers for managing secrets — Python 3.13.14 documentation

- page_id: `python-3-13-secrets`
- url: https://docs.python.org/3.13/library/python-3.13-secrets.html
- type: docs
- description: Source code: Lib/secrets.py The secrets module is used for generating cryptographically strong random numbers suitable for managing data such as passwords, account authentication, security tokens, ...

## Content

#### Table of Contents

- secrets — Generate secure random numbers for managing secrets

- Random numbers

- Generating tokens

- How many bytes should tokens use?

- Other functions

- Recipes and best practices

##### Previous topic

hmac — Keyed-Hashing for Message Authentication

##### Next topic

Generic Operating System Services

#### This page

- Report a bug

- Show source

#### Navigation

- index

- modules |

- next |

- previous |

- Python »

- 3.13.14 Documentation »

- The Python Standard Library »

- Cryptographic Services »

- secrets — Generate secure random numbers for managing secrets

- Theme Auto Light Dark |

## secrets — Generate secure random numbers for managing secrets¶

Added in version 3.6.

Source code: Lib/secrets.py

The secrets module is used for generating cryptographically strong random numbers suitable for managing data such as passwords, account authentication, security tokens, and related secrets.

In particular, secrets should be used in preference to the default pseudo-random number generator in the random module, which is designed for modelling and simulation, not security or cryptography.

See also

PEP 506

### Random numbers¶

The secrets module provides access to the most secure source of randomness that your operating system provides.

class secrets.SystemRandom¶

A class for generating random numbers using the highest-quality sources provided by the operating system. See random.SystemRandom for additional details.

secrets.choice(seq)¶

Return a randomly chosen element from a non-empty sequence.

secrets.randbelow(exclusive_upper_bound)¶

Return a random int in the range [0, exclusive_upper_bound).

secrets.randbits(k)¶

Return a non-negative int with k random bits.

### Generating tokens¶

The secrets module provides functions for generating secure tokens, suitable for applications such as password resets, hard-to-guess URLs, and similar.

secrets.token_bytes(nbytes=None)¶

Return a random byte string containing nbytes number of bytes.

If nbytes is not specified or None, DEFAULT_ENTROPY is used instead.

```
>>> token_bytes(16) b'\xebr\x17D*t\xae\xd4\xe3S\xb6\xe2\xebP1\x8b'
```

secrets.token_hex(nbytes=None)¶

Return a random text string, in hexadecimal. The string has nbytes random bytes, each byte converted to two hex digits.

If nbytes is not specified or None, DEFAULT_ENTROPY is used instead.

```
>>> token_hex(16) 'f9bf78b9a18ce6d46a0cd2b0b86df9da'
```

secrets.token_urlsafe(nbytes=None)¶

Return a random URL-safe text string, containing nbytes random bytes. The text is Base64 encoded, so on average each byte results in approximately 1.3 characters.

If nbytes is not specified or None, DEFAULT_ENTROPY is used instead.

```
>>> token_urlsafe(16) 'Drmhze6EPcv0fN_81Bj-nA'
```

#### How many bytes should tokens use?¶

To be secure against brute-force attacks, tokens need to have sufficient randomness. Unfortunately, what is considered sufficient will necessarily increase as computers get more powerful and able to make more guesses in a shorter period. As of 2015, it is believed that 32 bytes (256 bits) of randomness is sufficient for the typical use-case expected for the secrets module.

For those who want to manage their own token length, you can explicitly specify how much randomness is used for tokens by giving an int argument to the various token_* functions. That argument is taken as the number of bytes of randomness to use.

Otherwise, if no argument is provided, or if the argument is None, the token_* functions use DEFAULT_ENTROPY instead.

secrets.DEFAULT_ENTROPY¶

Default number of bytes of randomness used by the token_* functions.

The exact value is subject to change at any time, including during maintenance releases.

### Other functions¶

secrets.compare_digest(a, b)¶

Return True if strings or bytes-like objects a and b are equal, otherwise False, using a “constant-time compare” to reduce the risk of timing attacks. See hmac.compare_digest() for additional details.

### Recipes and best practices¶

This section shows recipes and best practices for using secrets to manage a basic level of security.

Generate an eight-character alphanumeric password:

```
import string import secrets alphabet = string.ascii_letters + string.digits password = ''.join(secrets.choice(alphabet) for i in range(8))
```

Note

Applications should not store passwords in a recoverable format, whether plain text or encrypted. They should be salted and hashed using a cryptographically strong one-way (irreversible) hash function.

Generate a ten-character alphanumeric password with at least one lowercase character, at least one uppercase character, and at least three digits:

```
import string import secrets alphabet = string.ascii_letters + string.digits while True: password = ''.join(secrets.choice(alphabet) for i in range(10)) if (any(c.islower() for c in password) and any(c.isupper() for c in password) and sum(c.isdigit() for c in password) >= 3): break
```

Generate an XKCD-style passphrase:

```
import secrets # On standard Linux systems, use a convenient dictionary file. # Other platforms may need to provide their own word-list. with open('/usr/share/dict/words') as f: words = [word.strip() for word in f] password = ' '.join(secrets.choice(words) for i in range(4))
```

Generate a hard-to-guess temporary URL containing a security token suitable for password recovery applications:

```
import secrets url = 'https://example.com/reset=' + secrets.token_urlsafe()
```

#### Table of Contents

- secrets — Generate secure random numbers for managing secrets

- Random numbers

- Generating tokens

- How many bytes should tokens use?

- Other functions

- Recipes and best practices

##### Previous topic

hmac — Keyed-Hashing for Message Authentication

##### Next topic

Generic Operating System Services

#### This page

- Report a bug

- Show source

#### Navigation

- index

- modules |

- next |

- previous |

- Python »

- 3.13.14 Documentation »

- The Python Standard Library »

- Cryptographic Services »

- secrets — Generate secure random numbers for managing secrets

- Theme Auto Light Dark |

© 2001-2026, Python Software Foundation. This page is licensed under the Python Software Foundation License Version 2. Examples, recipes, and other code in the documentation are additionally licensed under the Zero Clause BSD License. See for more information. The Python Software Foundation is a non-profit corporation. Last updated on Jul 11, 2026 (12:49 UTC). ? Created using 8.2.3.

## Links

- [Python logo](https://www.python.org/) (nav)
- [Table of Contents](https://docs.python.org/3.13/library/contents.html) (nav)
- [secrets — Generate secure random numbers for managing secrets](https://docs.python.org/3.13/library/python-3.13-secrets.html) → `python-3-13-secrets` (nav)
- [Random numbers](https://docs.python.org/3.13/library/python-3.13-secrets.html#random-numbers) → `python-3-13-secrets` (nav)
- [Generating tokens](https://docs.python.org/3.13/library/python-3.13-secrets.html#generating-tokens) → `python-3-13-secrets` (nav)
- [How many bytes should tokens use?](https://docs.python.org/3.13/library/python-3.13-secrets.html#how-many-bytes-should-tokens-use) → `python-3-13-secrets` (nav)
- [Other functions](https://docs.python.org/3.13/library/python-3.13-secrets.html#other-functions) → `python-3-13-secrets` (nav)
- [Recipes and best practices](https://docs.python.org/3.13/library/python-3.13-secrets.html#recipes-and-best-practices) → `python-3-13-secrets` (nav)
- [hmac — Keyed-Hashing for Message Authentication](https://docs.python.org/3.13/library/hmac.html) (nav)
- [Generic Operating System Services](https://docs.python.org/3.13/library/allos.html) (nav)
- [Report a bug](https://docs.python.org/3.13/library/bugs.html) (nav)
- [Show source](https://github.com/python/cpython/blob/main/Doc/library/secrets.rst?plain=1) (nav)
- [index](https://docs.python.org/3.13/library/genindex.html)
- [modules](https://docs.python.org/3.13/library/py-modindex.html)
- [next](https://docs.python.org/3.13/library/allos.html)
- [previous](https://docs.python.org/3.13/library/hmac.html)
- [Python](https://www.python.org/)
- [3.13.14 Documentation](https://docs.python.org/3.13/library/index.html)
- [The Python Standard Library](https://docs.python.org/3.13/library/index.html)
- [Cryptographic Services](https://docs.python.org/3.13/library/crypto.html)
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#module-secrets) → `python-3-13-secrets`
- [Lib/secrets.py](https://github.com/python/cpython/tree/3.13/Lib/secrets.py)
- [random](https://docs.python.org/3.13/library/random.html#module-random)
- [PEP 506](https://peps.python.org/pep-0506/)
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#random-numbers) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.SystemRandom) → `python-3-13-secrets`
- [random.SystemRandom](https://docs.python.org/3.13/library/random.html#random.SystemRandom)
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.choice) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.randbelow) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.randbits) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#generating-tokens) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.token_bytes) → `python-3-13-secrets`
- [DEFAULT_ENTROPY](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.DEFAULT_ENTROPY) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.token_hex) → `python-3-13-secrets`
- [DEFAULT_ENTROPY](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.DEFAULT_ENTROPY) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.token_urlsafe) → `python-3-13-secrets`
- [DEFAULT_ENTROPY](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.DEFAULT_ENTROPY) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#how-many-bytes-should-tokens-use) → `python-3-13-secrets`
- [brute-force attacks](https://en.wikipedia.org/wiki/Brute-force_attack)
- [int](https://docs.python.org/3.13/library/functions.html#int)
- [DEFAULT_ENTROPY](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.DEFAULT_ENTROPY) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.DEFAULT_ENTROPY) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#other-functions) → `python-3-13-secrets`
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#secrets.compare_digest) → `python-3-13-secrets`
- [bytes-like objects](https://docs.python.org/3.13/library/glossary.html#term-bytes-like-object)
- [timing attacks](https://codahale.com/a-lesson-in-timing-attacks/)
- [hmac.compare_digest()](https://docs.python.org/3.13/library/hmac.html#hmac.compare_digest)
- [¶](https://docs.python.org/3.13/library/python-3.13-secrets.html#recipes-and-best-practices) → `python-3-13-secrets`
- [store passwords in a recoverable format](https://cwe.mitre.org/data/definitions/257.html)
- [XKCD-style passphrase](https://xkcd.com/936/)
- [Table of Contents](https://docs.python.org/3.13/library/contents.html)
- [secrets — Generate secure random numbers for managing secrets](https://docs.python.org/3.13/library/python-3.13-secrets.html) → `python-3-13-secrets`
- [Random numbers](https://docs.python.org/3.13/library/python-3.13-secrets.html#random-numbers) → `python-3-13-secrets`
- [Generating tokens](https://docs.python.org/3.13/library/python-3.13-secrets.html#generating-tokens) → `python-3-13-secrets`
- [How many bytes should tokens use?](https://docs.python.org/3.13/library/python-3.13-secrets.html#how-many-bytes-should-tokens-use) → `python-3-13-secrets`
- [Other functions](https://docs.python.org/3.13/library/python-3.13-secrets.html#other-functions) → `python-3-13-secrets`
- [Recipes and best practices](https://docs.python.org/3.13/library/python-3.13-secrets.html#recipes-and-best-practices) → `python-3-13-secrets`
- [hmac — Keyed-Hashing for Message Authentication](https://docs.python.org/3.13/library/hmac.html)
- [Generic Operating System Services](https://docs.python.org/3.13/library/allos.html)
- [Report a bug](https://docs.python.org/3.13/library/bugs.html)
- [Show source](https://github.com/python/cpython/blob/main/Doc/library/secrets.rst?plain=1)
- [index](https://docs.python.org/3.13/library/genindex.html)
- [modules](https://docs.python.org/3.13/library/py-modindex.html)
- [next](https://docs.python.org/3.13/library/allos.html)
- [previous](https://docs.python.org/3.13/library/hmac.html)
- [Python](https://www.python.org/)
- [3.13.14 Documentation](https://docs.python.org/3.13/library/index.html)
- [The Python Standard Library](https://docs.python.org/3.13/library/index.html)
- [Cryptographic Services](https://docs.python.org/3.13/library/crypto.html)
- [Copyright](https://docs.python.org/3.13/library/copyright.html)
- [History and License](https://docs.python.org/3.13/library/license.html)
- [Please donate.](https://www.python.org/psf/donations/)
- [Found a bug](https://docs.python.org/3.13/library/bugs.html)
- [Sphinx](https://www.sphinx-doc.org/)

## Forms

### `form-1` — GET https://docs.python.org/3.13/library/search.html

- `q` · search
- submit: Go

### `form-2` — GET https://docs.python.org/3.13/library/search.html

- `q` · search
- submit: Go

### `form-3` — GET https://docs.python.org/3.13/library/search.html

- `q` · search
- submit: Go

## Images

- Python logo: https://docs.python.org/3.13/library/_static/py.svg
- Python logo: https://docs.python.org/3.13/library/_static/py.svg
- Python logo: https://docs.python.org/3.13/library/_static/py.svg
