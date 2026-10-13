// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { Row, Col } from 'antd/lib/grid';
import Button from 'antd/lib/button';
import Radio from 'antd/lib/radio';
import Empty from 'antd/lib/empty';
import Result from 'antd/lib/result';
import Title from 'antd/lib/typography/Title';
import Text from 'antd/lib/typography/Text';
import {
    Chart as ChartJS, BarElement, CategoryScale, Legend, LinearScale, Tooltip, type ChartDataset,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

import { getCore, ServerError } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';

ChartJS.register(BarElement, CategoryScale, Legend, LinearScale, Tooltip);

const core = getCore();
const BAR_HEIGHT_PX = 22;

// Fixed colours so a kind keeps its colour whichever kinds a task happens to contain.
const KIND_COLORS: Record<string, string> = {
    rectangle: '#1890ff',
    polygon: '#52c41a',
    mask: '#fa8c16',
    polyline: '#13c2c2',
    points: '#eb2f96',
    ellipse: '#722ed1',
    cuboid: '#a0d911',
    skeleton: '#faad14',
    track: '#2f54eb',
    tag: '#8c8c8c',
};

type ChartMode = 'total' | 'by_type';

interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
    by_type: Record<string, number>;
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

function chartDatasets(labels: LabelCount[], mode: ChartMode): ChartDataset<'bar', number[]>[] {
    if (mode === 'total') {
        return [{
            label: 'Annotations',
            data: labels.map((label) => label.count),
            backgroundColor: labels.map((label) => label.color || KIND_COLORS.rectangle),
        }];
    }

    const kinds = Array.from(new Set(labels.flatMap((label) => Object.keys(label.by_type)))).sort();
    return kinds.map((kind) => ({
        label: kind,
        data: labels.map((label) => label.by_type[kind] ?? 0),
        backgroundColor: KIND_COLORS[kind] ?? '#bfbfbf',
    }));
}

function AnnotationStatsChart({ labels, mode }: { labels: LabelCount[], mode: ChartMode }): JSX.Element {
    return (
        <div style={{ height: labels.length * BAR_HEIGHT_PX + 60 }}>
            <Bar
                data={{
                    labels: labels.map((label) => label.name),
                    datasets: chartDatasets(labels, mode),
                }}
                options={{
                    indexAxis: 'y',
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: { legend: { display: mode === 'by_type' } },
                    scales: {
                        x: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
                        y: { stacked: true },
                    },
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
    const [mode, setMode] = useState<ChartMode>('total');

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
                <div className='cvat-annotation-stats-toolbar'>
                    <Text>{`${stats.total} annotations`}</Text>
                    <Radio.Group
                        value={mode}
                        optionType='button'
                        onChange={(event) => setMode(event.target.value)}
                        options={[
                            { label: 'Total', value: 'total' },
                            { label: 'By shape type', value: 'by_type' },
                        ]}
                    />
                </div>
                <AnnotationStatsChart labels={stats.labels} mode={mode} />
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
