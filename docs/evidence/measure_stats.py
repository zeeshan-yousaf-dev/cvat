"""
MO-1: latency of GET /api/annotation-stats/tasks/{id} (see docs/OBJECTIVES.md).

Logs in once with a session cookie, like the browser does, then per run sends
3 warm-up requests and 50 timed sequential requests. Prints every timing.

    python3 measure_stats.py --task 1 --user admin --password ... | tee mo1_raw.txt
"""

import argparse
import http.cookiejar
import json
import platform
import statistics
import time
import urllib.request


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q / 100 * (len(ordered) - 1)))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--task", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=3)
    args = parser.parse_args()

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    login = urllib.request.Request(
        f"{args.host}/api/auth/login",
        data=json.dumps({"username": args.user, "password": args.password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    opener.open(login).read()

    url = f"{args.host}/api/annotation-stats/tasks/{args.task}"

    def timed_get():
        start = time.perf_counter()
        with opener.open(url) as response:
            body = response.read()
        return (time.perf_counter() - start) * 1000, body

    _, body = timed_get()
    stats = json.loads(body)
    print(f"python {platform.python_version()} | {url}")
    print(f"task {stats['task_id']}: total={stats['total']} labels={len(stats['labels'])}")

    run_p95 = []
    for run in range(1, args.runs + 1):
        for _ in range(args.warmup):
            timed_get()
        timings = [timed_get()[0] for _ in range(args.requests)]
        p95 = percentile(timings, 95)
        run_p95.append(p95)
        print(
            f"run {run}: p50={statistics.median(timings):.1f}ms p95={p95:.1f}ms "
            f"min={min(timings):.1f}ms max={max(timings):.1f}ms"
        )
        print("  raw ms: " + " ".join(f"{t:.1f}" for t in timings))

    print(
        f"MO-1 median of run p95 = {statistics.median(run_p95):.1f}ms "
        f"(spread {min(run_p95):.1f}..{max(run_p95):.1f}ms over {args.runs} runs)"
    )


if __name__ == "__main__":
    main()
