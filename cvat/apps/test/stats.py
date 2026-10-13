# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.db.models import Count, QuerySet

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task

# Each row in these tables is one annotated object: a drawn shape, a track, or an image tag.
ANNOTATION_MODELS = (LabeledShape, LabeledTrack, LabeledImage)


def _task_annotations(model, task_id: int) -> QuerySet:
    # Ground truth and consensus replica jobs hold copies of the same objects,
    # so only regular annotation jobs are counted.
    queryset = model.objects.filter(job__segment__task_id=task_id, job__type=JobType.ANNOTATION)
    if model is not LabeledImage:
        # Skeleton points are child rows of one object, not objects of their own.
        queryset = queryset.filter(parent__isnull=True)
    return queryset


def count_annotations_by_label(task: Task) -> list[dict]:
    counts: dict[int, int] = {}
    for model in ANNOTATION_MODELS:
        rows = (
            _task_annotations(model, task.id)
            .values("label_id")
            .annotate(count=Count("id"))
            .order_by()
        )
        for row in rows:
            counts[row["label_id"]] = counts.get(row["label_id"], 0) + row["count"]

    labels = [
        {"id": label.id, "name": label.name, "color": label.color, "count": counts.get(label.id, 0)}
        for label in task.get_labels()
    ]
    return sorted(labels, key=lambda label: (-label["count"], label["name"]))
