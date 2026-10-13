# Plan — Annotation Analytics (per-class counts)

Base: fork of `cvat-ai/cvat`, branch `dev-test01`, cut from `develop` at
`8d35c2953a129a344baff97c611c7c4a2edba0f0`. CVAT has no `main` branch; `develop` is its
default branch, so the PR goes `dev-test01 -> develop` on my fork.

## Environment decision (made before writing code)

My laptop (i5-6300U, 8 GB RAM, 6 GB free disk, no Docker/WSL) cannot run the CVAT stack.
Code is written locally; the stack, the COCO import and **every measurement** run in a GitHub
Codespace on the fork (4-core / 16 GB). Exact CPU/RAM/OS of that machine go in `OBJECTIVES.md`.
The images are built from this branch (`docker compose -f docker-compose.yml -f docker-compose.dev.yml build`),
because the stock `docker compose up` pulls prebuilt images that would not contain my code.

## What "an annotation" means here

Count = top-level `LabeledShape` + `LabeledTrack` + `LabeledImage` (tags) rows, grouped by
`label`, in **annotation jobs only**. Ground-truth and consensus-replica jobs hold copies of the
same objects, so counting them would double count. Skeleton sub-elements (`parent` not null) are
part of one object and are not counted separately. Labels with zero annotations are returned
with `0`, so the graph shows the whole label set.

## Order of work and time budget (8 h)

| # | Step | Budget |
|---|------|--------|
| 0 | Read engine models, IAM/OPA permissions, task routes in `cvat-ui`; write these 3 docs | 1:00 |
| 1 | New Django app `cvat.apps.test`: `GET /api/annotation-stats/tasks/{id}`, counts done in SQL (`GROUP BY label_id`) | 1:00 |
| 5 | Auth: reuse the task **view** OPA rule (no new Rego), so "can see the task" = "can see its stats". 401 without login, 403 without access | 0:30 |
| 2–4 | UI page `/tasks/:tid/annotation-stats` + link in the task Actions menu; bar chart with the `chart.js` already in `cvat-ui`; empty and error states | 1:30 |
| 6 | Speed objective MO-1: measurement script, 5 runs, raw output committed | 1:00 |
| 7 | Grouping: per-class split by shape type (rectangle / polygon / mask / …) | 0:30 |
| 8–9 | Live updates over WebSocket + reconnect with backoff | 1:30 |
| 10 | Decision record, tick Definition of Done with evidence | 1:00 |

Items 1–4 are the floor; I do not start 8 until 4 works in the browser.

## Decided to skip

- Project-level and job-level stats (task only, as asked).
- Caching the counts (Redis). Only if MO-1 is missed; a cache needs invalidation that I would rather not own.
- Frontend unit tests and translating the page. Backend gets a small API test only if time allows.
- Counting `LabeledInterval` (audio/video intervals): not present in the COCO image data.

## Changes to the plan

_(filled in as they happen, with the reason)_
