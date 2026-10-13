// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { Row, Col } from 'antd/lib/grid';
import Button from 'antd/lib/button';
import Empty from 'antd/lib/empty';
import Result from 'antd/lib/result';
import Title from 'antd/lib/typography/Title';
import Text from 'antd/lib/typography/Text';
import {
    Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

import { getCore, ServerError } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

const core = getCore();
const BAR_HEIGHT_PX = 22;

interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
}

interface TaskAnnotationStats {
    task_id: number;
    total: number;
    labels: LabelCount[];
}

function errorMessage(error: unknown): string {
    if (error instanceof ServerError && error.code === 403) {
        return 'You do not have access to this task.';
    }
    if (error instanceof ServerError && error.code === 404) {
        return 'This task does not exist.';
    }
    return error instanceof Error ? error.message : 'Unknown error';
}

function AnnotationStatsChart({ labels }: { labels: LabelCount[] }): JSX.Element {
    return (
        <div style={{ height: labels.length * BAR_HEIGHT_PX + 60 }}>
            <Bar
                data={{
                    labels: labels.map((label) => label.name),
                    datasets: [{
                        label: 'Annotations',
                        data: labels.map((label) => label.count),
                        backgroundColor: labels.map((label) => label.color || '#1890ff'),
                    }],
                }}
                options={{
                    indexAxis: 'y',
                    maintainAspectRatio: false,
                    animation: false,
                    scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
                }}
            />
        </div>
    );
}

function AnnotationStatsPage(): JSX.Element {
    const taskId = +useParams<{ tid: string }>().tid;
    const [stats, setStats] = useState<TaskAnnotationStats | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [fetching, setFetching] = useState(true);

    const fetchStats = useCallback(async (): Promise<void> => {
        setFetching(true);
        setError(null);
        try {
            const response = await core.server.request<{ data: TaskAnnotationStats }>(
                `${core.config.backendAPI}/annotation-stats/tasks/${taskId}`,
                { method: 'GET' },
            );
            setStats(response.data);
        } catch (requestError: unknown) {
            setStats(null);
            setError(errorMessage(requestError));
        } finally {
            setFetching(false);
        }
    }, [taskId]);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    let content: JSX.Element | null = null;
    if (fetching) {
        content = <CVATLoadingSpinner />;
    } else if (error !== null) {
        content = (
            <Result
                className='cvat-annotation-stats-error'
                status='error'
                title='Could not load annotation statistics'
                subTitle={error}
                extra={<Button type='primary' onClick={fetchStats}>Retry</Button>}
            />
        );
    } else if (stats && stats.total === 0) {
        content = (
            <Empty
                className='cvat-annotation-stats-empty'
                description={stats.labels.length ? 'No annotations in this task yet' : 'This task has no labels'}
            />
        );
    } else if (stats) {
        content = (
            <>
                <Text className='cvat-annotation-stats-total'>{`${stats.total} annotations`}</Text>
                <AnnotationStatsChart labels={stats.labels} />
            </>
        );
    }

    return (
        <div className='cvat-annotation-stats-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14} className='cvat-task-top-bar'>
                    <GoBackButton />
                </Col>
            </Row>
            <Row justify='center' className='cvat-annotation-stats-inner-wrapper'>
                <Col span={22} xl={18} xxl={14} className='cvat-annotation-stats-inner'>
                    <Title level={4}>{`Annotations per label — Task #${taskId}`}</Title>
                    {content}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(AnnotationStatsPage);
