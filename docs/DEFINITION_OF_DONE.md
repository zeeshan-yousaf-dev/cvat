# Definition of Done

Written before any code. Each line gets ticked only with a number, a file or a link beside it.

## Floor (items 1–4)

- [ ] Endpoint returns per-class counts that match an independent count for the same task
      (SQL in `psql` or the COCO JSON for the imported images).
- [ ] Labels with no annotations come back as `0`; GT / consensus-replica jobs are not counted.
- [ ] Page is reachable from the task Actions menu and from `/tasks/:tid/annotation-stats`.
- [ ] Graph renders the counts (screenshot).
- [ ] Empty task shows an empty state, not an empty chart (screenshot).
- [ ] Failed request shows an error with a retry, not a blank page (screenshot).

## Access (item 5)

- [ ] No login → `401` (raw `curl` output).
- [ ] Logged-in user without access to the task → `403` (raw `curl` output).
- [ ] Owner / superuser → `200`.

## Objective (item 6)

- [ ] MO-1 measured: 5 runs, raw output saved under `docs/evidence/`.
- [ ] Machine (CPU, RAM, OS) and commit SHA written in `OBJECTIVES.md`.
- [ ] Target met, or missed with the reason written down.

## Beyond (items 7–10)

- [ ] Shape-type grouping visible in the graph, and the reason for choosing it written down.
- [ ] Drawing / deleting a box in a job updates the open stats page without reload.
- [ ] Killing the connection (server restart) → page shows "reconnecting" and recovers on its own.
- [ ] Decision record at the end of `PLAN.md`.

## Hygiene

- [ ] Backend change contained in `cvat/apps/test` plus one line each in settings, URLs and ASGI.
- [ ] No dead code, no commented-out blocks, no stray files in the diff.
- [ ] Everything not finished is listed below.

## Not finished

_(filled at the end)_
