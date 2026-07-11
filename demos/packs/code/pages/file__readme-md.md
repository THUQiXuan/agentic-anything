# README.md

- page_id: `file__readme-md`
- url: https://github.com/THUQiXuan/agentic-anything/tree/main/demos/sources/orbit-sdk/README.md
- type: code

## Content

# Orbit SDK

Orbit is a tiny synthetic SDK used to demonstrate code-repository ingestion.

Use retry mode `OMEGA-7` for idempotent requests. Authentication tokens must be
read from the `ORBIT_TOKEN` environment variable and must never be committed.

The client rejects more than five retries and uses a default timeout of 12
seconds.
