# HISTORY.md

- page_id: `file__history-md`
- url: https://github.com/psf/requests/tree/v2.34.2/HISTORY.md
- type: code

## Content

Release History
===============

dev
---

- \[Short description of non-trivial change.\]

2.34.2 (2026-05-14)
-------------------
- Moved `headers` input type back to `Mapping` to avoid invariance issues
  with `MutableMapping` and inferred dict types. Users calling
  `Request.headers.update()` may need to narrow typing in their code. (#7441)

2.34.1 (2026-05-13)
-------------------

**Bugfixes**
- Widened `json` input type from `dict` and `list` to `Mapping`
  and `Sequence`. (#7436)
- Changed `headers` input type to MutableMapping and removed `None` from
  `Request.headers` typing to improve handling for users. (#7431)
- `Response.reason` moved from `str | None` to `str` to improve handling
  for users. (#7437)
- Fixed a bug where some bodies with custom `__getattr__` implementations
  weren't being properly detected as Iterables. (#7433)

2.34.0 (2026-05-11)
-------------------

**Announcements**
- Requests 2.34.0 introduces inline types, replacing those provided by
  typeshed. Public API types should be fully compatible with mypy, pyright,
  and ty. We believe types are comprehensive but if you find issues, please
  report them to the pinned tracking issue.

Special thanks to @bastimeyer, @cthoyt, @edgarrmondragon, and @srittau for
  helping review and test the types ahead of the release. (#7272)

**Improvements**
- Digest Auth hashing algorithms have added `usedforsecurity=False` to clarify
  security considerations. (#7310)
- Requests added support for Python 3.15 based on beta1. Downstream projects
  should be able to start testing prior to its release in October. (#7422)
- Requests added support for Python 3.14t. (#7419)

**Bugfixes**
- ``Response.history`` no longer contains a reference to itself, preventing
  accidental looping when traversing the history list. (#7328)
- Requests no longer performs greedy matching on no_proxy domains. The
  proxy_bypass implementation has been updated with CPython's fix from
  bpo-39057. (#7427)
- Requests no longer incorrectly strips duplicate leading slashes in
  URI paths. This should address user issues with specific presigned
  URLs. Note the full fix requires urllib3 2.7.0+. (#7315)

2.33.1 (2026-03-30)
-------------------

**Bugfixes**
- Fixed test cleanup for CVE-2026-25645 to avoid leaving unnecessary
  files in the tmp directory. (#7305)
- Fixed Content-Type header parsing for malformed values. (#7309)
- Improved error consistency for malformed header values. (#7308)

2.33.0 (2026-03-25)
-------------------

**Announcements**
- 📣 Requests is adding inline types. If you have a typed code base that
uses Requests, please take a look at #7271. Give it a try, and report
any gaps or feedback you may have in the issue. 📣

**Security**
- CVE-2026-25645 ``requests.utils.extract_zipped_paths`` now extracts
  contents to a non-deterministic location to prevent malicious file
  replacement. This does not affect default usage of Requests, only
  applications calling the utility function directly.

**Improvements**
- Migrated to a PEP 517 build system using setuptools. (#7012)

**Bugfixes**
- Fixed an issue where an empty netrc entry could cause
  malformed authentication to be applied to Requests on
  Python 3.11+. (#7205)

**Deprecations**
- Dropped support for Python 3.9 following its end of support. (#7196)

**Documentation**
- Various typo fixes and doc improvements.

2.32.5 (2025-08-18)
-------------------

**Bugfixes**

- The SSLContext caching feature originally introduced in 2.32.0 has created
  a new class of issues in Requests that have had negative impact across a number
  of use cases. The Requests team has decided to revert this feature as long term
  maintenance of it is proving to be unsustainable in its current iteration.

**Deprecations**
- Added support for Python 3.14.
- Dropped support for Python 3.8 following its end of support.

2.32.4 (2025-06-10)
-------------------

**Security**
- CVE-2024-47081 Fixed an issue where a maliciously crafted URL and trusted
  environment will retrieve credentials for the wrong hostname/machine from a
  netrc file.

**Improvements**
- Numerous documentation improvements

**Deprecations**
- Added support for pypy 3.11 for Linux and macOS.
- Dropped support for pypy 3.9 following its end of support.

2.32.3 (2024-05-29)
-------------------

**Bugfixes**
- Fixed bug breaking the ability to specify custom SSLContexts in sub-classes of
  HTTPAdapter. (#6716)
- Fixed issue where Requests started failing to run on Python versions compiled
  without the `ssl` module. (#6724)

2.32.2 (2024-05-21)
-------------------

**Deprecations**
- To provide a more stable migration for custom HTTPAdapters impacted
  by the CVE changes in 2.32.0, we've renamed `_get_connection` to
  a new public API, `get_connection_with_tls_context`. Existing custom
  HTTPAdapters will need to migrate their code to use this new API.
  `get_connection` is considered deprecated in all versions of Requests>=2.32.0.

A minimal (2-line) example has been provided in the linked PR to ease
  migration, but we strongly urge users to evaluate if their custom adapter
  is subject to the same issue described in CVE-2024-35195. (#6710)

2.32.1 (2024-05-20)
-------------------

**Bugfixes**
- Add missing test certs to the sdist distributed on PyPI.

2.32.0 (2024-05-20)
-------------------

**Security**
- Fixed an issue where setting `verify=False` on the first request from a
  Session will cause subsequent requests to the _same origin_ to also ignore
  cert verification, regardless of the value of `verify`.
  (https://github.com/psf/requests/security/advisories/GHSA-9wx4-h78v-vm56)

**Improvements**
- `verify=True` now reuses a global SSLContext which should improve
  request time variance between first and subsequent requests. It should
  also minimize certificate load time on Windows systems when using a Python
  version built with OpenSSL 3.x. (#6667)
- Requests now supports optional use of character detection
  (`chardet` or `charset_normalizer`) when repackaged or vendored.
  This enables `pip` and other projects to minimize their vendoring
  surface area. The `Response.text()` and `apparent_encoding` APIs
  will default to `utf-8` if neither library is present. (#6702)

**Bugfixes**
- Fixed bug in length detection where emoji length was incorrectly
  calculated in the request content-length. (#6589)
- Fixed deserialization bug in JSONDecodeError. (#6629)
- Fixed bug where an extra leading `/` (path separator) could lead
  urllib3 to unnecessarily reparse the request URI. (#6644)

**Deprecations**

- Requests has officially added support for CPython 3.12 (#6503)
- Requests has officially added support for PyPy 3.9 and 3.10 (#6641)
- Requests has officially dropped support for CPython 3.7 (#6642)
- Requests has officially dropped support for PyPy 3.7 and 3.8 (#6641)

**Documentation**
- Various typo fixes and doc improvements.

**Packaging**
- Requests has started adopting some modern packaging practices.
  The source files for the projects (formerly `requests`) is now located
  in `src/requests` in the Requests sdist. (#6506)
- Starting in Requests 2.33.0, Requests will migrate to a PEP 517 build system
  using `hatchling`. This should not impact the average user, but extremely old
  versions of packaging utilities may have issues with the new packaging format.

2.31.0 (2023-05-22)
-------------------

**Security**
- Versions of Requests between v2.3.0 and v2.30.0 are vulnerable to potential
  forwarding of `Proxy-Authorization` headers to destination servers when
  following HTTPS redirects.

When proxies are defined with user info (`https://user:pass@proxy:8080`), Requests
  will construct a `Proxy-Authorization` header that is attached to the request to
  authenticate with the proxy.

In cases where Requests receives a redirect response, it previously reattached
  the `Proxy-Authorization` header incorrectly, resulting in the value being
  sent through the tunneled connection to the destination server. Users who rely on
  defining their proxy credentials in the URL are *strongly* encouraged to upgrade
  to Requests 2.31.0+ to prevent unintentional leakage and rotate their proxy
  credentials once the change has been fully deployed.

Users who do not use a proxy or do not supply their proxy credentials through
  the user information portion of their proxy URL are not subject to this
  vulnerability.

Full details can be read in our [Github Security Advisory](https://github.com/psf/requests/security/advisories/GHSA-j8r2-6x86-q33q)
  and [CVE-2023-32681](https://nvd.nist.gov/vuln/detail/CVE-2023-32681).

2.30.0 (2023-05-03)
-------------------

**Dependencies**
- ⚠️ Added support for urllib3 2.0. ⚠️

This may contain minor breaking changes so we advise careful testing and
  reviewing https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html
  prior to upgrading.

Users who wish to stay on urllib3 1.x can pin to `urllib3<2`.

2.29.0 (2023-04-26)
-------------------

**Improvements**

- Requests now defers chunked requests to the urllib3 implementation to improve
  standardization. (#6226)
- Requests relaxes header component requirements to support bytes/str subclasses. (#6356)

2.28.2 (2023-01-12)
-------------------

**Dependencies**

- Requests now supports charset\_normalizer 3.x. (#6261)

**Bugfixes**

- Updated MissingSchema exception to suggest https scheme rather than http. (#6188)

2.28.1 (2022-06-29)
-------------------

**Improvements**

- Speed optimization in `iter_content` with transition to `yield from`. (#6170)

**Dependencies**

- Added support for chardet 5.0.0 (#6179)
- Added support for charset-normalizer 2.1.0 (#6169)

2.28.0 (2022-06-09)
-------------------

**Deprecations**

- ⚠️ Requests has officially dropped support for Python 2.7. ⚠️ (#6091)
- Requests has officially dropped support for Python 3.6 (including pypy3.6). (#6091)

**Improvements**

- Wrap JSON parsing issues in Request's JSONDecodeError for payloads without
  an encoding to make `json()` API consistent. (#6097)
- Parse header components consistently, raising an InvalidHeader error in
  all invalid cases. (#6154)
- Added provisional 3.11 support with current beta build. (#6155)
- Requests got a makeover and we decided to paint it black. (#6095)

**Bugfixes**

- Fixed bug where setting `CURL_CA_BUNDLE` to an empty string would disable
  cert verification. All Requests 2.x versions before 2.28.0 are affected. (#6074)
- Fixed urllib3 exception leak, wrapping `urllib3.exceptions.SSLError` with
  `requests.exceptions.SSLError` for `content` and `iter_content`. (#6057)
- Fixed issue where invalid Windows registry entries caused proxy resolution
  to raise an exception rather than ignoring the entry. (#6149)
- Fixed issue where entire payload could be included in the error message for
  JSONDecodeError. (#6036)

2.27.1 (2022-01-05)
-------------------

**Bugfixes**

- Fixed parsing issue that resulted in the `auth` component being
  dropped from proxy URLs. (#6028)

2.27.0 (2022-01-03)
-------------------

**Improvements**

- Officially added support for Python 3.10. (#5928)

- Added a `requests.exceptions.JSONDecodeError` to unify JSON exceptions between
  Python 2 and 3. This gets raised in the `response.json()` method, and is
  backwards compatible as it inherits from previously thrown exceptions.
  Can be caught from `requests.exceptions.RequestException` as well. (#5856)

- Improved error text for misnamed `InvalidSchema` and `MissingSchema`
  exceptions. This is a temporary fix until exceptions can be renamed
  (Schema->Scheme). (#6017)

- Improved proxy parsing for proxy URLs missing a scheme. This will address
  recent changes to `urlparse` in Python 3.9+. (#5917)

**Bugfixes**

- Fixed defect in `extract_zipped_paths` which could result in an infinite loop
  for some paths. (#5851)

- Fixed handling for `AttributeError` when calculating length of files obtained
  by `Tarfile.extractfile()`. (#5239)

- Fixed urllib3 exception leak, wrapping `urllib3.exceptions.InvalidHeader` with
  `requests.exceptions.InvalidHeader`. (#5914)

- Fixed bug where two Host headers were sent for chunked requests. (#5391)

- Fixed regression in Requests 2.26.0 where `Proxy-Authorization` was
  incorrectly stripped from all requests sent with `Session.send`. (#5924)

- Fixed performance regression in 2.26.0 for hosts with a large number of
  proxies available in the environment. (#5924)

- Fixed idna exception leak, wrapping `UnicodeError` with
  `requests.exceptions.InvalidURL` for URLs with a leading dot (.) in the
  domain. (#5414)

**Deprecations**

- Requests support for Python 2.7 and 3.6 will be ending in 2022. While we
  don't have exact dates, Requests 2.27.x is likely to be the last release
  series providing support.

2.26.0 (2021-07-13)
-------------------

**Improvements**

- Requests now supports Brotli compression, if either the `brotli` or
  `brotlicffi` package is installed. (#5783)

- `Session.send` now correctly resolves proxy configurations from both
  the Session and Request. Behavior now matches `Session.request`. (#5681)

**Bugfixes**

- Fixed a race condition in zip extraction when using Requests in parallel
  from zip archive. (#5707)

**Dependencies**

- Instead of `chardet`, use the MIT-licensed `charset_normalizer` for Python3
  to remove license ambiguity for projects bundling requests. If `chardet`
  is already installed on your machine it will be used instead of `charset_normalizer`
  to keep backwards compatibility. (#5797)

You can also install `chardet` while installing requests by
  specifying `[use_chardet_on_py3]` extra as follows:

```shell
    pip install "requests[use_chardet_on_py3]"
    ```

Python2 still depends upon the `chardet` module.

- Requests now supports `idna` 3.x on Python 3. `idna` 2.x will continue to
  be used on Python 2 installations. (#5711)

**Deprecations**

- The `requests[security]` extra has been converted to a no-op install.
  PyOpenSSL is no longer the recommended secure option for Requests. (#5867)

- Requests has officially dropped support for Python 3.5. (#5867)

2.25.1 (2020-12-16)
-------------------

**Bugfixes**

- Requests now treats `application/json` as `utf8` by default. Resolving
  inconsistencies between `r.text` and `r.json` output. (#5673)

**Dependencies**

- Requests now supports chardet v4.x.

2.25.0 (2020-11-11)
-------------------

**Improvements**

- Added support for NETRC environment variable. (#5643)

**Dependencies**

- Requests now supports urllib3 v1.26.

**Deprecations**

- Requests v2.25.x will be the last release series with support for Python 3.5.
- The `requests[security]` extra is officially deprecated and will be removed
  in Requests v2.26.0.

2.24.0 (2020-06-17)
-------------------

**Improvements**

- pyOpenSSL TLS implementation is now only used if Python
  either doesn't have an `ssl` module or doesn't support
  SNI. Previously pyOpenSSL was unconditionally used if available.
  This applies even if pyOpenSSL is installed via the
  `requests[security]` extra (#5443)

- Redirect resolution should now only occur when
  `allow_redirects` is True. (#5492)

- No longer perform unnecessary Content-Length calculation for
  requests that won't use it. (#5496)

2.23.0 (2020-02-19)
-------------------

**Improvements**

- Remove defunct reference to `prefetch` in Session `__attrs__` (#5110)

**Bugfixes**

- Requests no longer outputs password in basic auth usage warning. (#5099)

**Dependencies**

- Pinning for `chardet` and `idna` now uses major version instead of minor.
  This hopefully reduces the need for releases every time a dependency is updated.

2.22.0 (2019-05-15)
-------------------

**Dependencies**

- Requests now supports urllib3 v1.25.2.
  (note: 1.25.0 and 1.25.1 are incompatible)

**Deprecations**

- Requests has officially stopped support for Python 3.4.

2.21.0 (2018-12-10)
-------------------

**Dependencies**

- Requests now supports idna v2.8.

2.20.1 (2018-11-08)
-------------------

**Bugfixes**

- Fixed bug with unintended Authorization header stripping for
  redirects using default ports (http/80, https/443).

2.20.0 (2018-10-18)
-------------------

**Bugfixes**

-   Content-Type header parsing is now case-insensitive (e.g.
    charset=utf8 v Charset=utf8).
-   Fixed exception leak where certain redirect urls would raise
    uncaught urllib3 exceptions.
-   Requests removes Authorization header from requests redirected
    from https to http on the same hostname. (CVE-2018-18074)
-   `should_bypass_proxies` now handles URIs without hostnames (e.g.
    files).

**Dependencies**

- Requests now supports urllib3 v1.24.

**Deprecations**

- Requests has officially stopped support for Python 2.6.

2.19.1 (2018-06-14)
-------------------

**Bugfixes**

-   Fixed issue where status\_codes.py's `init` function failed trying
    to append to a `__doc__` value of `None`.

2.19.0 (2018-06-12)
-------------------

**Improvements**

-   Warn user about possible slowdown when using cryptography version
    &lt; 1.3.4
-   Check for invalid host in proxy URL, before forwarding request to
    adapter.
-   Fragments are now properly maintained across redirects. (RFC7231
    7.1.2)
-   Removed use of cgi module to expedite library load time.
-   Added support for SHA-256 and SHA-512 digest auth algorithms.
-   Minor performance improvement to `Request.content`.
-   Migrate to using collections.abc for 3.7 compatibility.

**Bugfixes**

-   Parsing empty `Link` headers with `parse_header_links()` no longer
    return one bogus entry.
-   Fixed issue where loading the default certificate bundle from a zip
    archive would raise an `IOError`.
-   Fixed issue with unexpected `ImportError` on windows system which do
    not support `winreg` module.
-   DNS resolution in proxy bypass no longer includes the username and
    password in the request. This also fixes the issue of DNS queries
    failing on macOS.
-   Properly normalize adapter prefixes for url comparison.
-   Passing `None` as a file pointer to the `files` param no longer
    raises an exception.
-   Calling `copy` on a `RequestsCookieJar` will now preserve the cookie
    policy correctly.

**Dependencies**

-   We now support idna v2.7.
-   We now support urllib3 v1.23.

2.18.4 (2017-08-15)
-------------------

**Improvements**

-   Error messages for invalid headers now include the header name for
    easier debugging

**Dependencies**

-   We now support idna v2.6.

2.18.3 (2017-08-02)
-------------------

**Improvements**

-   Running `$ python -m requests.help` now includes the installed
    version of idna.

**Bugfixes**

-   Fixed issue where Requests would raise `ConnectionError` instead of
    `SSLError` when encountering SSL problems when using urllib3 v1.22.

2.18.2 (2017-07-25)
-------------------

**Bugfixes**

-   `requests.help` no longer fails on Python 2.6 due to the absence of
    `ssl.OPENSSL_VERSION_NUMBER`.

**Dependencies**

-   We now support urllib3 v1.22.

2.18.1 (2017-06-14)
-------------------

**Bugfixes**

-   Fix an error in the packaging whereby the `*.whl` contained
    incorrect data that regressed the fix in v2.17.3.

2.18.0 (2017-06-14)
-------------------

**Improvements**

-   `Response` is now a context manager, so can be used directly in a
    `with` statement without first having to be wrapped by
    `contextlib.closing()`.

**Bugfixes**

-   Resolve installation failure if multiprocessing is not available
-   Resolve tests crash if multiprocessing is not able to determine the
    number of CPU cores
-   Resolve error swallowing in utils set\_environ generator

2.17.3 (2017-05-29)
-------------------

**Improvements**

-   Improved `packages` namespace identity support, for monkeypatching
    libraries.

2.17.2 (2017-05-29)
-------------------

**Improvements**

-   Improved `packages` namespace identity support, for monkeypatching
    libraries.

2.17.1 (2017-05-2

(truncated at 20000 chars)
