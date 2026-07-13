# Maintainer Impact Brief: Change Default Redirect Ceiling from 30 to 20 in Requests Library

## Summary:
This proposed change reduces the library-wide default maximum number of HTTP redirects allowed from 30 to 20, while preserving the ability for users to override this limit on a per-Session basis. The change affects the constant DEFAULT_REDIRECT_LIMIT, the Session class initialization, runtime enforcement of redirect limits, the exception raised on exceeding the limit, relevant tests, and user documentation.

## Evidence and Trace:

1. Constant Definition:
- In `src/requests/models.py`, the constant `DEFAULT_REDIRECT_LIMIT` is defined as 30.
- This constant is imported and re-exposed in `src/requests/sessions.py` for backward compatibility.

2. Session Initialization:
- In `src/requests/sessions.py`, the `Session` class has an attribute `max_redirects` initialized to `DEFAULT_REDIRECT_LIMIT` (30).
- This attribute can be overridden per Session instance by setting `s.max_redirects`.

3. Runtime Enforcement:
- In the `SessionRedirectMixin.resolve_redirects` method (`src/requests/sessions.py`), the number of redirects followed is tracked.
- If the number of redirects exceeds `self.max_redirects`, a `TooManyRedirects` exception is raised.
- The exception class `TooManyRedirects` is defined in `src/requests/exceptions.py`.

4. Exception Type:
- `TooManyRedirects` inherits from `RequestException`, which is a subclass of `IOError`.
- This exception is raised with a message indicating the exceeded redirect limit.

5. Tests:
- In `tests/test_requests.py`, there are tests verifying the default redirect limit behavior:
  - `test_HTTP_302_TOO_MANY_REDIRECTS` tests that a redirect chain exceeding 30 raises `TooManyRedirects`.
  - `test_HTTP_302_TOO_MANY_REDIRECTS_WITH_PARAMS` tests that a custom `max_redirects` (e.g., 5) set on a Session instance is respected.
- These tests confirm both the default limit and per-Session override functionality.

6. User Documentation:
- In `docs/user/quickstart.rst`, the redirection behavior is documented, including the use of the `allow_redirects` parameter and the `Response.history` property.
- The same captured unit states that exceeding the configured maximum raises `TooManyRedirects`.
- The captured user documentation does not explicitly state the numeric default, so the pack does not support claiming that “30” is part of the documented public contract.

## Recommended Changes:
- Change the value of `DEFAULT_REDIRECT_LIMIT` in `src/requests/models.py` from 30 to 20.
- This will automatically update the default `max_redirects` in Session instances.
- No changes are needed in the Session class code since it uses the constant.
- No changes are needed in the exception class or runtime enforcement logic.
- If maintainers want the numeric default to become part of the documented contract, add a note to `docs/user/quickstart.rst`; its current qualitative statement remains correct without an edit.
- No changes are needed in tests for the custom per-Session override behavior.
- Update the test `test_HTTP_302_TOO_MANY_REDIRECTS` in `tests/test_requests.py` to expect 20 redirects instead of 30 for the default limit.

## What Should Not Change:
- The per-Session override mechanism for `max_redirects` should remain unchanged.
- The exception type `TooManyRedirects` and its usage should remain unchanged.
- The runtime enforcement logic in `resolve_redirects` should remain unchanged except for the new default limit.
- Other redirect-related behaviors and status codes should remain unchanged.

## Claim-Evidence Matrix:

| Claim                                                      | Evidence Source (file, unit)               |
|------------------------------------------------------------|--------------------------------------------|
| DEFAULT_REDIRECT_LIMIT is defined as 30                    | src/requests/models.py                      |
| Session.max_redirects initialized to DEFAULT_REDIRECT_LIMIT| src/requests/sessions.py                    |
| Redirect limit enforced in resolve_redirects method        | src/requests/sessions.py                    |
| TooManyRedirects exception raised on exceeding redirects   | src/requests/sessions.py, src/requests/exceptions.py |
| Tests verify default limit of 30 and per-Session override  | tests/test_requests.py                       |
| User docs state that exceeding the configured maximum raises TooManyRedirects | docs/user/quickstart.rst |

## Limitations:
- The user documentation does not explicitly state the numeric default redirect limit; the change should add or clarify this.
- The source code excerpts were truncated in some files, but the key elements for this change were found.
- No evidence was found of other places defining or overriding the default redirect limit outside the traced files.

## Summary:
Changing the `DEFAULT_REDIRECT_LIMIT` constant from 30 to 20 is the minimal and correct source change to update the library-wide default redirect ceiling. The per-Session override remains intact. Tests for the default limit should be updated accordingly, and user documentation should be clarified to reflect the new default. No other code or exception changes are necessary.

---
