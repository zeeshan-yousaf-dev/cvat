# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

"""
Live annotation stats over WebSocket: /api/annotation-stats/tasks/{id}/ws

CVAT has no channel layer, so this is a plain ASGI handler placed in front of the
Django application. It authenticates the browser session cookie, applies the same
task "view" rule as the REST endpoint, sends the current counts, and then sends them
again whenever the task's updated_date changes. Every annotation save in CVAT goes
through JobAnnotation._set_updated_date(), which touches the task.
"""

import asyncio
import io
import json
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user
from django.core.handlers.asgi import ASGIRequest
from django.db import close_old_connections
from django.utils.module_loading import import_string

from cvat.apps.engine.models import Task
from cvat.apps.engine.permissions import TaskPermission
from cvat.apps.iam.middleware import get_organization

from .stats import count_annotations_by_label

PATH = re.compile(r"^/api/annotation-stats/tasks/(?P<task_id>\d+)/ws$")
POLL_INTERVAL_SECONDS = 1.0

# Application close codes; the page does not retry on these.
CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404


def _authorize(scope, task_id: int) -> int | None:
    """Returns None when the connection may proceed, otherwise a close code."""
    close_old_connections()
    request = ASGIRequest({**scope, "method": "GET"}, io.BytesIO())

    # The session cookie is sent cross-site too, so only accept same-origin pages.
    origin = request.headers.get("Origin")
    if origin is None or urlsplit(origin).netloc != request.get_host():
        return CLOSE_FORBIDDEN

    session_store = import_string(settings.SESSION_ENGINE).SessionStore
    request.session = session_store(request.COOKIES.get(settings.SESSION_COOKIE_NAME))
    request.user = get_user(SimpleNamespace(session=request.session))
    if not request.user.is_authenticated:
        return CLOSE_UNAUTHENTICATED

    try:
        task = Task.objects.select_related("organization", "project").get(id=task_id)
    except Task.DoesNotExist:
        return CLOSE_NOT_FOUND

    request.iam_context = get_organization(request)
    if not TaskPermission.create_scope_view(request, task).check_access().allow:
        return CLOSE_FORBIDDEN
    return None


def _updated_date(task_id: int):
    close_old_connections()
    return Task.objects.filter(id=task_id).values_list("updated_date", flat=True).first()


def _snapshot(task_id: int) -> str:
    close_old_connections()
    task = Task.objects.get(id=task_id)
    labels = count_annotations_by_label(task)
    return json.dumps(
        {"task_id": task.id, "total": sum(label["count"] for label in labels), "labels": labels}
    )


async def _serve(scope, receive, send, task_id: int) -> None:
    if (await receive())["type"] != "websocket.connect":
        return

    close_code = await sync_to_async(_authorize)(scope, task_id)
    # Closing before accepting turns into a bare HTTP 403 for the browser; accept first
    # so the page receives the close code and knows not to retry.
    await send({"type": "websocket.accept"})
    if close_code is not None:
        await send({"type": "websocket.close", "code": close_code})
        return

    disconnected = asyncio.Event()

    async def wait_for_disconnect():
        while (await receive())["type"] != "websocket.disconnect":
            pass
        disconnected.set()

    watcher = asyncio.create_task(wait_for_disconnect())
    last_seen = object()
    try:
        while not disconnected.is_set():
            updated_date = await sync_to_async(_updated_date)(task_id)
            if updated_date is None:
                await send({"type": "websocket.close", "code": CLOSE_NOT_FOUND})
                return
            if updated_date != last_seen:
                last_seen = updated_date
                text = await sync_to_async(_snapshot)(task_id)
                await send({"type": "websocket.send", "text": text})
            try:
                await asyncio.wait_for(disconnected.wait(), POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
    except OSError:
        # The client went away between the poll and the send.
        pass
    finally:
        watcher.cancel()


def with_annotation_stats_websocket(django_application):
    """Wraps the ASGI application, taking over only the stats WebSocket path."""

    async def application(scope, receive, send):
        if scope["type"] == "websocket" and (match := PATH.match(scope["path"])):
            await _serve(scope, receive, send, int(match["task_id"]))
        else:
            await django_application(scope, receive, send)

    return application
