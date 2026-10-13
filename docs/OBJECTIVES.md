# Objectives

## Machine

All numbers below come from one GitHub Codespace on the fork, with the stack built from this branch
(`docker compose -f docker-compose.yml -f docker-compose.dev.yml build cvat_server cvat_ui`).
Full `lscpu`, `free -h`, `os-release` and `docker version` output: [`evidence/machine.txt`](evidence/machine.txt).

| | |
|---|---|
| CPU | AMD EPYC 7763, 4 vCPUs (Codespace "4-core") |
| RAM | 15 GiB |
| OS | Ubuntu 24.04.5 LTS (Codespace container), Docker 29.8.0 |
| CVAT commit cloned | `8d35c2953a129a344baff97c611c7c4a2edba0f0` (`develop`) |
| Data | Task 2: all **5,000** COCO val2017 images, 10 jobs of 500, `instances_val2017.json` imported as COCO 1.0 → **41,866** annotations |
| Code written on | Intel i5-6300U, 8 GB RAM, Windows 10 Pro 19045 — not used for any measurement |

## MO-1 — Stats endpoint latency

| Field | Entry |
|---|---|
| What is measured | Wall-clock time of `GET /api/annotation-stats/tasks/{id}` as seen by an HTTP client on the same host: request sent → full JSON body received. Includes auth, the OPA permission check and the SQL. |
| How | [`evidence/measure_stats.py`](evidence/measure_stats.py): log in once with a session cookie (as the browser does), 3 warm-up requests, then 50 sequential requests; the run's value is the **p95** of those 50. Repeated as 5 separate runs. |
| Target | **Median of the 5 run-p95 values ≤ 250 ms**, for task 2 (all 5,000 val2017 images). |
| Conditions | Stack built from this branch in the Codespace above; logged in as the superuser; no import or other request running. |
| Not included | The first request after a container restart, browser rendering time, WebSocket pushes, tasks with GT/consensus jobs. |

**Why 250 ms, and why p95.** The page makes one request and then draws; to feel immediate the whole
thing should land well under 1 s, and the chart itself costs tens of ms. The same query also runs
on every live update (item 8), so it has to stay cheap at the largest task I have. I report p95 rather
than the median per run because a stats page is judged by its slow loads, not its typical one.
I picked the full val2017 set on purpose: with a few hundred images any `GROUP BY` is trivially fast.

### Result: met — 73.8 ms (spread 72.7–76.2 ms)

Raw output: [`evidence/mo1_raw.txt`](evidence/mo1_raw.txt) (every one of the 250 timings is in it).

```
task 2: total=41866 labels=80
run 1: p50=67.8ms p95=74.5ms min=64.2ms max=87.8ms
run 2: p50=66.7ms p95=73.8ms min=64.7ms max=78.7ms
run 3: p50=67.0ms p95=72.7ms min=64.0ms max=75.5ms
run 4: p50=66.5ms p95=76.2ms min=64.6ms max=85.6ms
run 5: p50=67.1ms p95=73.6ms min=65.0ms max=207.1ms
MO-1 median of run p95 = 73.8ms (spread 72.7..76.2ms over 5 runs)
```

**What this tells me.** I cleared the target with no optimisation work, so the honest reading is that
250 ms was set too loose for this data size, not that I made anything fast. Where the time goes:
`EXPLAIN ANALYZE` of the shape `GROUP BY` reports 34 ms execution (index scans on
`engine_segment.task_id` and `engine_labeledshape.job_id`, 10 job loops), so roughly half the request is
SQL and the rest is session auth, the OPA call, three smaller queries and serialisation. The one outlier
(207 ms, run 5) did not move that run's p95.

One finding on the way: the same endpoint called with HTTP Basic auth takes ~300 ms per request,
because Django re-hashes the password on every call. That is why the measurement logs in once with a
session, as the page does; Basic-auth numbers would measure PBKDF2, not this feature.

## MO-2 — Live update latency (added after item 8 was built)

| Field | Entry |
|---|---|
| What is measured | Time from sending an annotation save (`PATCH /api/jobs/{id}/annotations?action=create`) to the open stats page showing the new total. |
| How | [`evidence/measure_live.py`](evidence/measure_live.py): headless Chromium keeps `/tasks/2/annotation-stats` open; each run creates one rectangle, waits for the page text to show total + 1, deletes it, waits for the old total, then pauses a random 0.2–1.2 s. 5 runs. |
| Target | **Median ≤ 1,500 ms.** The server checks once a second, so the design alone allows up to ~1 s plus one recount (MO-1) plus render. |
| Conditions | As MO-1; one browser tab open, nothing else saving. |
| Not included | Saves made inside the annotation editor (they go through the same `PATCH`), many concurrent viewers. |

### Result: met — median 814 ms (spread 140–1,110 ms)

Raw output: [`evidence/mo2_raw.txt`](evidence/mo2_raw.txt)

```
run 1: create -> page 814ms (save request 58ms)
run 2: create -> page 888ms (save request 64ms)
run 3: create -> page 719ms (save request 63ms)
run 4: create -> page 140ms (save request 61ms)
run 5: create -> page 1110ms (save request 64ms)
MO-2 median = 814ms (spread 140..1110ms over 5 runs)
```

The spread is the poll: a save that lands just before a check shows in ~140 ms, one just after waits
nearly a full second. My first trial used a fixed 0.3 s pause and gave 750–757 ms in four of five runs —
the pause had locked every save to the same point of the poll cycle, which made the number look far
more stable than it is. The randomised pause is in the committed script. This latency is the measured
cost of the design choice recorded at the end of `PLAN.md`.
