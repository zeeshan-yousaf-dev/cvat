# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from rest_framework import routers

from .views import TaskAnnotationStatsViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register("annotation-stats/tasks", TaskAnnotationStatsViewSet, basename="annotation-stats")

urlpatterns = router.urls
