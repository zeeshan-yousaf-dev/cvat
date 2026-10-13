# Definition of Done

Written before any code (`879409d`). Each line is ticked only with a number, a file or a link beside it.
All evidence lives in [`evidence/`](evidence/) and comes from the Codespace described in `OBJECTIVES.md`.

## Floor (items 1–4)

- [x] Endpoint returns per-class counts that match an independent count for the same task.
      Task 2: 80 of 80 classes identical, total **41,866** —
      [`counts_endpoint.txt`](evidence/counts_endpoint.txt) vs the `shapes` column of
      [`counts_coco.txt`](evidence/counts_coco.txt), produced by [`coco_counts.py`](evidence/coco_counts.py)
      straight from `instances_val2017.json`. (It does *not* match the 36,781 COCO objects; why is change 1 in `PLAN.md`.)
- [x] Labels with no annotations come back as `0`: task 3 returns all 80 labels at 0 →
      [`counts_empty_task.txt`](evidence/counts_empty_task.txt).
      GT / consensus-replica jobs are excluded by `job__type=JobType.ANNOTATION` in `cvat/apps/test/stats.py`;
      **not demonstrated** — no task here has such jobs.
- [x] Page reachable from the task Actions menu → [`00_task_actions_menu.png`](evidence/00_task_actions_menu.png),
      and at `/tasks/:tid/annotation-stats`.
- [x] Graph renders the counts → [`01_task2_total.png`](evidence/01_task2_total.png).
- [x] Empty task shows an empty state, not an empty chart → [`03_empty_task.png`](evidence/03_empty_task.png).
- [x] Failed request shows an error with a retry → [`04_error_missing_task.png`](evidence/04_error_missing_task.png)
      (task 9999, 404). A page opened while the server is down recovers once the WebSocket reconnects.

## Access (item 5)

- [x] No login → `401` — [`access.txt`](evidence/access.txt).
- [x] Logged-in user without access to the task → `403` — [`access.txt`](evidence/access.txt) (user `outsider`, registered by the script).
- [x] Owner / superuser → `200` — [`access.txt`](evidence/access.txt).

## Objective (item 6)

- [x] MO-1 measured: 5 runs × 50 requests, raw output [`mo1_raw.txt`](evidence/mo1_raw.txt).
- [x] Machine (CPU, RAM, OS) and commit SHA in `OBJECTIVES.md`; full output [`machine.txt`](evidence/machine.txt).
- [x] Target met: **73.8 ms** median of run p95 (72.7–76.2 ms) vs ≤ 250 ms. Noted in `OBJECTIVES.md` that it was met without optimisation work.

## Beyond (items 7–10)

- [x] Shape-type grouping visible in the graph → [`02_task2_by_shape_type.png`](evidence/02_task2_by_shape_type.png)
      (446 masks, 41,420 polygons). Chosen because on this data one class count hides different work:
      COCO import yields polygons for ordinary objects and masks for crowd regions, and someone
      planning review wants to know which is which. It costs nothing extra: same `GROUP BY`, one more column.
- [x] Creating / deleting a shape updates the open page without reload:
      41,866 → 41,867 → 41,866 — [`live_browser.txt`](evidence/live_browser.txt), [`05`](evidence/05_live_before.png),
      [`06`](evidence/06_live_after_create.png), [`08`](evidence/08_recovered_after_delete.png);
      socket-level check incl. close codes 4401/4403/4404 in [`live_ws.txt`](evidence/live_ws.txt);
      MO-2 median **814 ms** (140–1,110 ms) in [`mo2_raw.txt`](evidence/mo2_raw.txt).
      Shapes were saved through the REST API the editor uses, not by drawing in the editor.
- [x] Stopping `cvat_server` → page shows "Connection lost, reconnecting…" ([`07_reconnecting.png`](evidence/07_reconnecting.png))
      and is live again **24 s** after it is started, with no reload ([`live_browser.txt`](evidence/live_browser.txt)).
      One run only; the 24 s is mostly server boot plus the 10 s backoff cap.
- [x] Decision record at the end of `PLAN.md`.

## Hygiene

- [x] Backend change contained in `cvat/apps/test` plus 1 line in `cvat/settings/base.py`, 3 in `cvat/urls.py`,
      5 in `cvat/asgi.py` and 1 in `cvat/nginx.conf` (the last one was not planned; change 3 in `PLAN.md`).
      UI change contained in `cvat-ui/src/components/annotation-stats-page` plus 2 lines in `cvat-app.tsx` and 6 in
      `tasks-page/actions-menu-items.tsx`. `git diff --stat 8d35c29 -- . ':!docs'`: 17 files, 614 insertions, 0 deletions.
- [x] No dead code, no commented-out blocks; the only files outside the feature are the evidence under `docs/evidence/`.
- [x] Everything not finished is listed below.

## Not finished

- **No automated tests.** No Django API test for the endpoint or the socket, no UI test. The evidence scripts are
  manual checks, not a suite.
- **`cvat/schema.yml` not regenerated.** The endpoint has `extend_schema`, but CVAT's committed OpenAPI file was not
  updated, so CVAT's schema check in CI would flag it. No `changelog.d` fragment either.
- **GT / consensus exclusion untested** (see the floor section).
- **No 403 shown through the page or the socket** for a real outsider: the REST 403 is shown with `curl`, and the
  socket's 4403 is shown for a foreign Origin, not for a logged-in user without access (same `TaskPermission` call).
- **Live updates do not scale with viewers** (one poll and one recount per open page; see the decision record).
- **Reconnect measured once**, not five times.
- **Project- and job-level stats** were out of scope from the start.
