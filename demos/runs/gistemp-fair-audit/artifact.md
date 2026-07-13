# NASA GISTEMP reproducible brief and FAIR evidence audit

## Task and scope

This report parses the **read-unit Markdown returned by the real MCP server**;
it does not read the source CSV directly. The calculation treats `J-D` as the
requested annual field. The captured units preserve that label and its values,
but do not state the anomaly reference baseline, so this report does not infer
one. [G1][G2][G3]

The FAIR table audits only what the captured three-unit GISTEMP pack evidences.
It is not a certification of NASA's complete data stewardship program.

## Reproducible findings

- Parsed years: **147** (1880–2026). [G2][G3]
- Complete `J-D` years: **146**.
- 2024 `J-D`: **1.28 °C**; 2023: **1.17 °C**; difference: **0.11 °C**. [G3]
- Highest complete annual value: **2024 (1.28 °C)**. [G3]
- 2024 is **0.474 °C** above the 2010–2019 mean. [G3]
- 2026 has `J-D = ***` and is excluded from annual comparisons, rather than treated as zero. [G3]

| Period | Mean `J-D` anomaly |
|---|---:|
| 1980-1989 | 0.245 °C |
| 1990-1999 | 0.384 °C |
| 2000-2009 | 0.587 °C |
| 2010-2019 | 0.806 °C |
| 2020-2025 | 1.065 °C |

## FAIR evidence audit

The definitions below come from the captured FAIR Guiding Principles paper.
[F1] `partial` means some pack evidence exists but the full principle is not
established; `not_evidenced` means this closed capture does not support the
claim. Absence of evidence here is not evidence that NASA lacks the property.
Markers beginning with `RUN-` cite this run's step/transport record, not facts
contained in the FAIR paper or GISTEMP pack units.

| Principle | Paper definition | Status | Evidence-scoped rationale |
|---|---|---|---|
| F1 | (meta)data are assigned a globally unique and persistent identifier | `not_evidenced` | A source URL and local unit IDs exist, but global persistence is not established. [G1][G2][G3] |
| F2 | data are described with rich metadata (defined by R1 below) | `partial` | The rows preserve a schema and values; descriptive metadata remains sparse. [G1][G2][G3] |
| F3 | metadata clearly and explicitly include the identifier of the data it describes | `partial` | Read units carry source locators, but no explicit persistent dataset identifier is shown. [G1][G2][G3] |
| F4 | (meta)data are registered or indexed in a searchable resource | `partial` | A recorded search_resource step searched the local MCP pack [RUN-S3]; registration in an external searchable registry is not evidenced. [G1][G2][G3] |
| A1 | (meta)data are retrievable by their identifier using a standardized communications protocol | `partial` | A recorded read_unit step retrieved a captured unit through MCP [RUN-R4]; no globally persistent identifier is evidenced. [G1][G2][G3] |
| A1.1 | the protocol is open, free, and universally implementable | `partial` | A recorded local stdio MCP exchange works with network_access=false [RUN-C1]; the captured pack units do not establish that the protocol is universally implementable. [G1][G2][G3] |
| A1.2 | the protocol allows for an authentication and authorization procedure, where necessary | `not_evidenced` | No authentication or authorization procedure appears in the captured dataset units. [G1][G2][G3] |
| A2 | metadata are accessible, even when the data are no longer available | `not_evidenced` | The snapshot cannot prove metadata survival after source data disappearance. [G1][G2][G3] |
| I1 | (meta)data use a formal, accessible, shared, and broadly applicable language for knowledge representation. | `partial` | A machine-readable table schema is preserved, but no formal knowledge-representation language is declared. [G1][G2][G3] |
| I2 | (meta)data use vocabularies that follow FAIR principles | `not_evidenced` | No FAIR vocabulary is declared in the captured dataset units. [G1][G2][G3] |
| I3 | (meta)data include qualified references to other (meta)data | `not_evidenced` | No qualified references to other metadata objects are captured. [G1][G2][G3] |
| R1 | meta(data) are richly described with a plurality of accurate and relevant attributes | `partial` | Column names and values are present, while richer contextual attributes are limited. [G1][G2][G3] |
| R1.1 | (meta)data are released with a clear and accessible data usage license | `not_evidenced` | No data-usage license appears in the complete three-unit GISTEMP pack. [G1][G2][G3] |
| R1.2 | (meta)data are associated with detailed provenance | `partial` | Source locators and content SHA-256 values provide capture-level provenance. [G1][G2][G3] |
| R1.3 | (meta)data meet domain-relevant community standards | `not_evidenced` | No domain-community metadata standard is declared in the captured units. [G1][G2][G3] |

## Read-before-cite ledger

- [G1] `gistemp/nasa-gistemp-global__001__nasa-gistemp-global-csv-overview` — `overview` — sha256 `f54a1006b28624bf339f660c804e5b673e275014a16237b3f0e37bd825f28db8`
- [G2] `gistemp/nasa-gistemp-global__002__nasa-gistemp-global-csv-rows-1-100` — `rows 1-100` — sha256 `3db6b57975a728bb2d3f891166d1bb3adf26da9b8725e874bd72c226abf3261a`
- [G3] `gistemp/nasa-gistemp-global__003__nasa-gistemp-global-csv-rows-101-147` — `rows 101-147` — sha256 `53cadbd0b342fe928b98bbd74db494c37a553c57aefc7f08d965e89db2d31f8c`
- [F1] `fair-paper/fair-guiding-principles-pmc4792175` — `fair-guiding-principles-pmc4792175.html` — sha256 `049c7896330605fa4f1eb3f540a51770d77004466f3c77a5d1046b130fa8701f`

## Run-evidence ledger

- [RUN-S3] run step 3 `search_resource` — The local MCP search returned the expected GISTEMP overview unit. Source: `run.json` plus the corresponding `raw-events.jsonl` exchange.
- [RUN-R4] run step 4 `read_unit` — The MCP read returned the captured overview unit and its content hash. Source: `run.json` plus the corresponding `raw-events.jsonl` exchange.
- [RUN-C1] run step 1 `initialize + tools/list` — The local stdio MCP session initialized successfully; run metadata records data_access='real stdio MCP subprocess only' and network_access=false. Source: `run.json` plus the corresponding `raw-events.jsonl` exchange.
