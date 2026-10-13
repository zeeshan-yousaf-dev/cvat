# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from cvat.apps.engine.models import Task

from .permissions import TaskAnnotationStatsPermission
from .serializers import TaskAnnotationStatsSerializer
from .stats import count_annotations_by_label


@extend_schema(tags=["annotation-stats"])
class TaskAnnotationStatsViewSet(viewsets.GenericViewSet):
    queryset = Task.objects.select_related("organization", "project")
    iam_permission_class = TaskAnnotationStatsPermission
    # A single task is looked up by id; list filters and organization filtering do not apply.
    filter_backends = []

    @extend_schema(
        summary="Get the number of annotations per label in a task",
        responses=TaskAnnotationStatsSerializer,
    )
    def retrieve(self, request, pk=None):
        task = self.get_object()
        labels = count_annotations_by_label(task)
        serializer = TaskAnnotationStatsSerializer(
            {
                "task_id": task.id,
                "total": sum(label["count"] for label in labels),
                "labels": labels,
            }
        )
        return Response(serializer.data)
