# Real-source demo snapshots

Every input in this directory comes from a named external publisher. None of
the source prose, code, rows, or book text was written for this demo.

`real-sources.json` records the origin URL, exact version, license, local
snapshot filename, and SHA-256 for every resource. `build_demos.py` refuses to
run if a local snapshot does not match that manifest. This keeps the showcase
both authentic and reproducible even when an upstream webpage or dataset later
changes.

The five resources are:

- Project Gutenberg eBook #11, *Alice's Adventures in Wonderland* (EPUB3);
- the PSF Requests repository at the `v2.34.2` tag;
- the Python 3.13.14 `secrets` documentation page;
- NASA GISS GISTEMP v4 global-mean CSV data, snapshotted 2026-07-11;
- Wilkinson et al.'s FAIR Guiding Principles paper from PubMed Central.

Run `python demos/build_demos.py` from the repository root. Missing snapshots
are downloaded from their manifest URL and verified before use. Existing files
are never silently refreshed.
