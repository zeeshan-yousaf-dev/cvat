"""
MO-2: time from saving an annotation to the open stats page showing the new count
(see docs/OBJECTIVES.md). Headless Chromium keeps /tasks/{id}/annotation-stats open;
each run creates one rectangle through the REST API, waits until the page text shows
the new total, then deletes the rectangle and waits for the old total again.

    python measure_live.py --task 2   (needs playwright; reads /tmp/cvat_admin_pass)
"""

import argparse
import random
import statistics
import time

from playwright.sync_api import sync_playwright

TOTAL_JS = "parseInt(document.querySelector('.cvat-annotation-stats-toolbar').innerText)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--task", type=int, required=True)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    base = args.host

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        password = open("/tmp/cvat_admin_pass").read().strip()
        page.request.post(f"{base}/api/auth/login", data={"username": "admin", "password": password})
        csrf = next(c["value"] for c in page.context.cookies() if c["name"] == "csrftoken")
        headers = {"X-CSRFToken": csrf, "Referer": f"{base}/"}

        page.goto(f"{base}/tasks/{args.task}/annotation-stats")
        page.wait_for_selector(".cvat-annotation-stats-live >> text=Live", timeout=60000)
        before = page.evaluate(TOTAL_JS)

        job = page.request.get(f"{base}/api/jobs?task_id={args.task}&page_size=1").json()["results"][0]
        label = page.request.get(f"{base}/api/labels?task_id={args.task}").json()["results"][0]
        shape = {"type": "rectangle", "frame": job["start_frame"], "label_id": label["id"],
                 "points": [10, 10, 60, 60], "occluded": False, "z_order": 0, "attributes": [], "group": 0}
        annotations_url = f"{base}/api/jobs/{job['id']}/annotations"

        def save_and_wait(action, shapes, expected_total):
            start = time.perf_counter()
            response = page.request.patch(
                f"{annotations_url}?action={action}",
                data={"version": 0, "tags": [], "tracks": [], "shapes": shapes}, headers=headers,
            )
            saved = time.perf_counter()
            page.wait_for_function(f"{TOTAL_JS} === {expected_total}", timeout=15000, polling=10)
            shown = time.perf_counter()
            return response.json(), (shown - start) * 1000, (saved - start) * 1000

        print(f"task {args.task}: {before} annotations, label '{label['name']}', job {job['id']}")
        results = []
        for run in range(1, args.runs + 1):
            created, total_ms, save_ms = save_and_wait("create", [shape], before + 1)
            results.append(total_ms)
            print(f"run {run}: create -> page {total_ms:.0f}ms (save request {save_ms:.0f}ms)")
            shape_id = created["shapes"][0]["id"]
            save_and_wait("delete", [{**shape, "id": shape_id}], before)
            # A random pause so saves land at different points of the 1 s server poll;
            # a fixed pause phase-locks to the poll and hides the real spread.
            time.sleep(random.uniform(0.2, 1.2))

        print(
            f"MO-2 median = {statistics.median(results):.0f}ms "
            f"(spread {min(results):.0f}..{max(results):.0f}ms over {args.runs} runs)"
        )
        browser.close()


if __name__ == "__main__":
    main()
