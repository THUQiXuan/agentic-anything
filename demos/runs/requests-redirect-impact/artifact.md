# Requests redirect-limit change-impact report

## Task

Assess changing the default redirect ceiling in the pinned Requests v2.34.2
resource from **30 to 10**, without editing upstream code in this run.

## Evidence-backed verdict

The numeric source of truth is `DEFAULT_REDIRECT_LIMIT: int = 30` in
`src/requests/models.py`. [R1] A new `Session` copies that constant into
`self.max_redirects`; `resolve_redirects` raises `TooManyRedirects` when response
history reaches the configured ceiling. [R2] The exception remains a
`RequestException` subtype. [R3]

Changing 30 to 10 therefore needs one direct production-code edit to the
constant. The initialization and guard mechanisms do not need structural
changes. The default regression test currently asserts a history length of 30
and must be updated, while the custom `s.max_redirects = 5` test should remain
unchanged. [R4]

The captured quickstart promises that exceeding the configured maximum raises
`TooManyRedirects`, but its redirect section does not promise a numeric default;
the qualitative documentation remains correct. [R5]

## Impact matrix

| Layer | Current contract | 30 → 10 impact |
|---|---|---|
| Definition | `DEFAULT_REDIRECT_LIMIT = 30` [R1] | Direct edit to `10` |
| Session default | Copies the constant [R2] | New sessions inherit `10`; no structural edit |
| Runtime guard | Compares `len(resp.history)` with `self.max_redirects` [R2] | Same guard trips earlier |
| Exception API | Raises `TooManyRedirects`, a `RequestException` [R2][R3] | No type change |
| Tests | Default expects `30`; custom policy expects `5` [R4] | Update only default expectation |
| Quickstart | Documents configured limit, not numeric value [R5] | No factual numeric edit required |

## Compatibility risk

With no explicit `Session.max_redirects`, redirect chains of length 10 through
29 that previously completed would now raise `TooManyRedirects`. Explicit
per-session policies remain available and are already covered by the custom
value test. [R2][R4]

## Read-before-cite ledger

- [R1] `requests/file__src--requests--models-py` — `src/requests/models.py` — sha256 `95bc0e03bea32cc48ea37aaabbaa48c9f09f1b9138d3ca93d31aa60c3665dbd6`
- [R2] `requests/file__src--requests--sessions-py` — `src/requests/sessions.py` — sha256 `37132aa52850a6d7acaadacc80657cae6bb5c4f34befc45cbdf1ec6930d4447a`
- [R3] `requests/file__src--requests--exceptions-py` — `src/requests/exceptions.py` — sha256 `c5e18f3352454968e337bb3056f0867df2f37c0a0d2c1a77dc05e7e0b3c0411b`
- [R4] `requests/file__tests--test-requests-py` — `tests/test_requests.py` — sha256 `95dd5c40741e00bb8062593e19a2853985f0a65d67eb9eb64046d05841832d87`
- [R5] `requests/file__docs--user--quickstart-rst` — `docs/user/quickstart.rst` — sha256 `0c65d40d6d1cf008eeb66a235029d5da9fa66641bf5ce58599a3e0606138d9c1`
