# Objectives

## MO-1 — Stats endpoint latency

| Field | Entry |
|---|---|
| What is measured | Wall-clock time of `GET /api/annotation-stats/tasks/{id}` as seen by an HTTP client on the same host: request sent → full JSON body received. Includes auth, the OPA permission check and the SQL. |
| How | `docs/evidence/measure_stats.py`: 3 warm-up requests, then 50 sequential requests; the run's value is the **p95** of those 50. Repeated as 5 separate runs. |
| Target | **Median of the 5 run-p95 values ≤ 250 ms**, for a task holding all 5,000 COCO val2017 images and their imported annotations. |
| Conditions | Local Docker stack built from this branch, inside the Codespace described below; logged in as the superuser via token; no other requests or imports running; the task fully imported before the first run. |
| Not included | The first request after a container restart, browser rendering time, WebSocket pushes, tasks inside projects with GT/consensus jobs. |

**Why 250 ms, and why p95.** The page makes one request and then draws; to feel immediate the whole
thing should land well under 1 s, and the chart itself costs tens of ms. The same query also runs
on every live update (item 8), so it has to stay cheap at the largest task I have. I report p95 rather
than the median per run because a stats page is judged by its slow loads, not its typical one.
I picked the full val2017 set on purpose: with a few hundred images any `GROUP BY` is trivially fast and
the target would say nothing.

## Machine

_(filled from the Codespace with `lscpu`, `free -h`, `cat /etc/os-release`, `docker version`)_

- CVAT commit cloned: `8d35c2953a129a344baff97c611c7c4a2edba0f0`
- Code written on: Intel i5-6300U, 8 GB RAM, Windows 10 Pro 19045 (not used for any measurement)
- Measured on: _TBD_
- Images imported: _TBD_ — annotations in DB: _TBD_

## Results

_(raw output pasted from the measurement runs; median and spread; met or missed and why)_
