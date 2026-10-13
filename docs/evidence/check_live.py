"""
Item 8: WebSocket close codes for rejected connections, then a live update
after creating and deleting one rectangle through the REST API.

    python3 check_live.py TASK_ID   (reads the admin password from /tmp/cvat_admin_pass)
"""

import asyncio, http.cookiejar, json, sys, time, urllib.request

import websockets

base, task = "localhost:8080", int(sys.argv[1])
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
password = open("/tmp/cvat_admin_pass").read().strip()


def api(method, path, body=None):
    csrf = next((c.value for c in jar if c.name == "csrftoken"), "")
    req = urllib.request.Request(
        f"http://{base}/api/{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf, "Referer": f"http://{base}/"},
    )
    with opener.open(req) as r:
        return json.loads(r.read() or "null")


api("POST", "auth/login", {"username": "admin", "password": password})
cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
URL = f"ws://{base}/api/annotation-stats/tasks/{task}/ws"


async def close_code(headers, url=URL):
    async with websockets.connect(url, additional_headers=headers) as ws:
        try:
            await asyncio.wait_for(ws.recv(), 10)
            return "message"
        except websockets.ConnectionClosed as e:
            return e.rcvd.code


async def main():
    print("no cookie           -> close", await close_code({"Origin": f"http://{base}"}))
    print("foreign origin      -> close", await close_code({"Origin": "http://evil.example", "Cookie": cookie}))
    print("missing task 9999   -> close", await close_code({"Origin": f"http://{base}", "Cookie": cookie}, URL.replace(f"/{task}/", "/9999/")))
    async with websockets.connect(URL, additional_headers={"Origin": f"http://{base}", "Cookie": cookie}) as ws:
        first = json.loads(await ws.recv())
        print("snapshot total", first["total"])
        job = api("GET", f"jobs?task_id={task}&page_size=1")["results"][0]
        person = next(l for l in first["labels"] if l["name"] == "person")
        shape = {"type": "rectangle", "frame": job["start_frame"], "label_id": person["id"],
                 "points": [10, 10, 60, 60], "occluded": False, "z_order": 0, "attributes": [], "group": 0}
        body = {"version": 0, "tags": [], "tracks": [], "shapes": [shape]}

        t0 = time.perf_counter()
        created = await asyncio.to_thread(api, "PATCH", f"jobs/{job['id']}/annotations?action=create", body)
        msg = json.loads(await asyncio.wait_for(ws.recv(), 10))
        by_type = next(l for l in msg["labels"] if l["name"] == "person")["by_type"]
        print(f"after create: total {msg['total']} person {by_type} after {(time.perf_counter() - t0) * 1000:.0f} ms")

        body["shapes"] = [{**shape, "id": created["shapes"][0]["id"]}]
        t0 = time.perf_counter()
        await asyncio.to_thread(api, "PATCH", f"jobs/{job['id']}/annotations?action=delete", body)
        msg = json.loads(await asyncio.wait_for(ws.recv(), 10))
        print(f"after delete: total {msg['total']} after {(time.perf_counter() - t0) * 1000:.0f} ms")


asyncio.run(main())
