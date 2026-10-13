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

The code was written with an AI coding assistant (Claude Code), which the brief allows; the commits
carry its co-author line. All decisions and numbers below are from this branch and its evidence.

1. **"An annotation" means a stored shape, not a COCO object.** My first check against task 2 disagreed:
   41,866 from the endpoint, 36,781 annotations in the COCO file. CVAT's COCO importer stores each polygon
   of a multi-part segmentation as its own `LabeledShape` (446 crowd masks + 41,420 polygon parts =
   41,866). I kept the endpoint counting what CVAT stores and shows in the job's object list, and changed
   the check script to derive the shape count from the COCO file, which matches all 80 classes exactly.
   I did not try to merge parts back into objects through `group`: the import puts 8,607 shapes into only
   87 groups, so groups are not one-per-object.
2. **Setup cost more than budgeted (~45 min).** The Codespace has 12 GB free on the workspace disk, so I
   moved Docker's data root to `/tmp` (109 GB) and restarted `dockerd`; that left a stale
   `iptables-legacy` `FORWARD DROP` policy that silently broke container-to-container traffic
   (`cvat_server` waited forever for `cvat_db`). Found by testing a TCP connect from the server
   container, fixed by resetting the policy.
3. **One file outside the planned footprint: `cvat/nginx.conf`.** The in-container nginx spoke HTTP/1.0
   to uvicorn, which drops the WebSocket `Upgrade`. One line (`proxy_http_version 1.1`).
4. **WebSocket rejections accept first, then close.** Closing before accepting reaches the browser as a
   bare HTTP 403 with close code 1006, which the page cannot tell from a network drop, so it would retry
   forever. Accepting first lets it receive 4401/4403/4404 and stop. No data is sent before the check.
5. **MO-2 added after item 8.** I had been quoting single live-update timings; a single number is not a
   measurement, so I defined MO-2 and measured it properly (see `OBJECTIVES.md`, including the
   phase-locking mistake in the first trial).
6. **A layout bug found in my own evidence.** The reconnecting screenshot, taken at 700 px height, showed
   the 80-label chart squeezed into the viewport with half the labels dropped; CVAT's page mixin pins the
   card to viewport height. Fixed (`193bdd5`) and screenshots retaken.
7. **No backend API test.** Planned "if time allows"; I spent that time on the evidence scripts instead.

Actual order matched the table except that item 7 was coded before the item 6 measurement, because
measuring needed the stack and it was not up yet. Wall-clock from first reading to MO-2 was about 2 h,
of which roughly 45 min was image builds and the dataset import — well under the 8 h budget, mostly
because of the assistant.

## Decision record — live updates (item 10)

**Took.** A small ASGI handler (`cvat/apps/test/live.py`) wrapped around the Django application in
`cvat/asgi.py`. It authenticates the session cookie, checks the Origin, applies the same task "view" OPA
rule as the REST endpoint, then once a second reads the task's `updated_date` and pushes a fresh count
when it changes. This works because every annotation create/update/delete goes through
`JobAnnotation._set_updated_date()`, which touches the task.

**Rejected.** Django Channels with a Redis channel layer, pushing from the save path: after an
annotation save, `group_send` to a per-task group and every subscribed socket gets the new count.

**Why.** Channels is a new dependency (`channels`, `channels-redis`) in a pinned requirements set, and it
replaces the ASGI entry point. Worse, there is no clean place to hook the push: annotations are written
with `bulk_create`, which emits no `post_save` signals, so the push would have to live inside
`cvat/apps/dataset_manager/task.py` — core CVAT code — rather than in my app.

**What rejecting it cost** (measured, not estimated):
- *Latency.* Up to one poll interval: MO-2 median 814 ms, spread 140–1,110 ms, where the save itself takes
  ~60 ms. A push would land in roughly the save time.
- *Load that grows with viewers.* Each open page costs one indexed primary-key query per second, and each
  change costs a full recount per open page (MO-1: ~74 ms p95 per recount on 41,866 annotations), where a
  push would count once and fan out. Ten viewers of a busy task means ten recounts per save.
- *Shared thread.* The handler's DB calls run on asgiref's single shared sync thread, so many open
  sockets queue behind each other. Fine for a handful of viewers; not for hundreds.

If this page had many simultaneous viewers, the first change I would make is to compute the count once
per `updated_date` and share it across sockets in the same process, before reaching for Channels.
