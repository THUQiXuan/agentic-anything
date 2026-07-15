# CS336 week-1 study plan (evidence-grounded)

## Task

Onboard a new CS336 student for week 1 using only the captured course pack (course page + deep-captured lecture PDFs + the assignment starter repository): (1) say what Assignment 1 is and exactly where to start in the starter repo; (2) point to the lecture slides, with page numbers, for the architecture material the assignment needs; (3) the course page links a PDF handout for Assignment 1 — check whether that link still resolves, and if it does not, locate the handout inside the captured repository instead.

## 1. What Assignment 1 is, and where to start

Assignment 1 is **"Basics"** — the from-scratch foundations assignment of
*CS336: Language Modeling from Scratch*. The course page schedules it and
links the `stanford-cs336/assignment1-basics` starter repository. [C1]

Start in the starter repository, in this order: [C2]

1. `README.md` — scope, environment setup (`uv` managed), and how to run the
   test suite.
2. `cs336_assignment1_basics.pdf` — the full handout (see §3 for why you will
   not reach it from the course page link).
3. `tests/adapters.py` + `tests/` — the graded surface: implement until the
   tests pass.

Note the course's own AI policy before wiring up an assistant: agents in this
course are teaching aids, **not** solution generators. [C3]

## 2. The slides you need for the architecture material

Lecture 3 ("architecture") covers the transformer-architecture decisions the
assignment implements. The RoPE / rotary position embedding material is on
**slides pages 25-32** of the captured deck. [C4]

## 3. Handout link status: dead on the page, alive in the repo

- The course page's Assignment 1 handout link
  `https://github.com/stanford-cs336/assignment1-basics/blob/main/cs336_spring2025_assignment1_basics.pdf`
  failed during capture and is recorded in the pack frontier as
  `attachment_fetch_failed:IngestError` (run step 2; the frontier is part of the
  pack, so any agent can re-check this without leaving the pack).
- The captured repository tree lists `cs336_assignment1_basics.pdf`
  (965,629 bytes) at the repo root — the handout was renamed (the
  `spring2025` prefix was dropped) rather than removed. [C5]
- Practical consequence: open the handout from the repository, not from the
  course page link.

## Citations

[C1] `cs336-course/spring2025` — `/spring2025` — sha256 `2754583fe0977dfb746c0ae40fc19afd82437641d52919e3693d94fcaace9004`
[C2] `cs336-course/stanford-cs336-assignment1-basics__file__readme-md` — `README.md` — sha256 `11bf3402f88f925e27a244b9102656a748d0c1e47f02399f42112faabe52f8fa`
[C3] `cs336-course/stanford-cs336-assignment1-basics__file__agents-md` — `AGENTS.md` — sha256 `005ff2d1c77f92ee2dd3a70d801ced16f63de55b16b7d0e9df29e14d87acd4bc`
[C4] `cs336-course/2025-lecture-3-architecture__004__pages-25-32` — `pages 25-32` — sha256 `3d0925b25bdb496a76b6882054fbfe5e52e4e234204ddd94882500c3a546a4e0`
[C5] `cs336-course/stanford-cs336-assignment1-basics__repo__000__tree` — `tree` — sha256 `85a2471ecbd44dab6978859199a586a30634bdc1c2ac4e8ff76badb4c8771bcb`

## Capture limits

Lecture PDFs beyond the deep-capture budget and all lecture videos are
recorded in the pack frontier rather than captured; code units may be
truncated at the per-file capture limit. Everything cited above was read
inside the pack during this run.
