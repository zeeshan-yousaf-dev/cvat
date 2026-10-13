"""
Items 8 and 9 in a real browser (headless Chromium): the page updates without a reload
when a shape is created, shows the reconnecting state while cvat_server is stopped,
and recovers on its own when it is started again.

    python check_live_browser.py OUTPUT_DIR   (needs playwright; reads /tmp/cvat_admin_pass)
"""

import json, subprocess, sys, time
from playwright.sync_api import sync_playwright

out, base = sys.argv[1], "http://localhost:8080"
password = open("/tmp/cvat_admin_pass").read().strip()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 700})
    page.request.post(f"{base}/api/auth/login", data={"username": "admin", "password": password})
    csrf = next(c["value"] for c in page.context.cookies() if c["name"] == "csrftoken")
    headers = {"X-CSRFToken": csrf, "Referer": f"{base}/"}

    def total_text():
        return page.locator(".cvat-annotation-stats-toolbar").inner_text().split("\n")[0]

    def badge():
        return page.locator(".cvat-annotation-stats-live").inner_text()

    page.goto(f"{base}/tasks/2/annotation-stats")
    page.wait_for_selector("text=Live", timeout=60000)
    print("loaded:", total_text(), "|", badge())
    page.screenshot(path=f"{out}/05_live_before.png")

    job = page.request.get(f"{base}/api/jobs?task_id=2&page_size=1").json()["results"][0]
    labels = page.request.get(f"{base}/api/labels?task_id=2&name=person").json()["results"]
    shape = {"type": "rectangle", "frame": job["start_frame"], "label_id": labels[0]["id"],
             "points": [10, 10, 60, 60], "occluded": False, "z_order": 0, "attributes": [], "group": 0}
    body = {"version": 0, "tags": [], "tracks": [], "shapes": [shape]}
    t0 = time.perf_counter()
    created = page.request.patch(f"{base}/api/jobs/{job['id']}/annotations?action=create", data=body, headers=headers).json()
    page.wait_for_function("document.querySelector('.cvat-annotation-stats-toolbar').innerText.startsWith('41867')", timeout=15000)
    print(f"after create, page shows: {total_text()} ({(time.perf_counter() - t0) * 1000:.0f} ms, no reload)")
    page.screenshot(path=f"{out}/06_live_after_create.png")

    subprocess.run(["docker", "stop", "cvat_server"], check=True, capture_output=True)
    page.wait_for_selector("text=reconnecting", timeout=30000)
    print("server stopped, page shows:", badge(), "|", total_text())
    page.screenshot(path=f"{out}/07_reconnecting.png")

    subprocess.run(["docker", "start", "cvat_server"], check=True, capture_output=True)
    t0 = time.perf_counter()
    page.wait_for_selector(".cvat-annotation-stats-live >> text=Live", timeout=180000)
    print(f"server started, page back to: {badge()} after {time.perf_counter() - t0:.0f} s")

    body["shapes"] = [{**shape, "id": created["shapes"][0]["id"]}]
    page.request.patch(f"{base}/api/jobs/{job['id']}/annotations?action=delete", data=body, headers=headers)
    page.wait_for_function("document.querySelector('.cvat-annotation-stats-toolbar').innerText.startsWith('41866')", timeout=15000)
    print("after delete on the new connection, page shows:", total_text(), "|", badge())
    page.screenshot(path=f"{out}/08_recovered_after_delete.png")
    browser.close()
