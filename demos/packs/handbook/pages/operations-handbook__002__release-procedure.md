# Release procedure

- page_id: `operations-handbook__002__release-procedure`
- url: https://github.com/THUQiXuan/agentic-anything/blob/main/demos/sources/operations-handbook.md
- type: section

## Content

### Release procedure

Production releases happen on Tuesdays at 14:00 UTC. The release owner must
verify the canary dashboard for ten minutes before promoting traffic.

The emergency rollback command is `aurora rollback --release CURRENT`.
Rollback approval code **ORBIT-17** is required in the incident record.
