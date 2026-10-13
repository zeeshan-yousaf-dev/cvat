# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from collections import Counter, defaultdict

from django.db.models import Count, QuerySet

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task


def _task_annotations(model, task_id: int) -> QuerySet:
    # Ground truth and consensus replica jobs hold copies of the same objects,
    # so only regular annotation jobs are counted.
    queryset = model.objects.filter(job__segment__task_id=task_id, job__type=JobType.ANNOTATION)
    if model is not LabeledImage:
        # Skeleton points are child rows of one object, not objects of their own.
        queryset = queryset.filter(parent__isnull=True)
    return queryset


def count_annotations_by_label(task: Task) -> list[dict]:
    """
    Counts annotated objects per label, split by kind: the shape type for drawn
    shapes (rectangle, polygon, mask, ...), "track" for tracks and "tag" for tags.
    Every count is a GROUP BY in the database; no annotation rows are loaded.
    """
    by_label: defaultdict[int, Counter] = defaultdict(Counter)

    shape_rows = (
        _task_annotations(LabeledShape, task.id)
        .values("label_id", "type")
        .annotate(count=Count("id"))
        .order_by()
    )
    for row in shape_rows:
        by_label[row["label_id"]][row["type"]] += row["count"]

    for model, kind in ((LabeledTrack, "track"), (LabeledImage, "tag")):
        rows = _task_annotations(model, task.id).values("label_id").annotate(count=Count("id")).order_by()
        for row in rows:
            by_label[row["label_id"]][kind] += row["count"]

    labels = [
        {
            "id": label.id,
            "name": label.name,
            "color": label.color,
            "count": sum(by_label[label.id].values()),
            "by_type": dict(by_label[label.id]),
        }
        for label in task.get_labels()
    ]
    return sorted(labels, key=lambda label: (-label["count"], label["name"]))
