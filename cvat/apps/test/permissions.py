# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from cvat.apps.engine.permissions import TaskPermission


class TaskAnnotationStatsPermission:
    """
    Annotation stats add no access rules of their own: whoever may view a task
    may see its counts. PolicyEnforcer only calls `create`, which returns the
    existing task "view" check, so the decision is made by the tasks Rego policy.
    """

    @classmethod
    def create(cls, request, view, obj, iam_context):
        return [TaskPermission.create_scope_view(request, obj, iam_context)]
