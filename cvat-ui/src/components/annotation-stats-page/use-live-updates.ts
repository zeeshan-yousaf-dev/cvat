// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState } from 'react';

export type LiveStatus = 'connecting' | 'live' | 'reconnecting' | 'unavailable';

// Close codes the server sends when retrying cannot help (see cvat/apps/test/live.py)
const FINAL_CLOSE_CODES = [4401, 4403, 4404];
const MAX_RETRY_DELAY_MS = 10000;

// Keeps a WebSocket open to `path` on the current host, reconnecting with exponential backoff
// after any drop. The server sends a full snapshot on every connect, so nothing missed while
// disconnected has to be replayed.
export function useLiveUpdates<T>(path: string, onMessage: (data: T) => void): LiveStatus {
    const [status, setStatus] = useState<LiveStatus>('connecting');
    const onMessageRef = useRef(onMessage);
    onMessageRef.current = onMessage;

    useEffect(() => {
        let socket: WebSocket | null = null;
        let retryTimer: ReturnType<typeof setTimeout> | undefined;
        let attempt = 0;
        let disposed = false;

        const connect = (): void => {
            const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
            socket = new WebSocket(`${scheme}://${window.location.host}${path}`);
            socket.onmessage = (event: MessageEvent<string>) => {
                attempt = 0;
                setStatus('live');
                onMessageRef.current(JSON.parse(event.data));
            };
            socket.onclose = (event: CloseEvent) => {
                if (disposed) {
                    return;
                }
                if (FINAL_CLOSE_CODES.includes(event.code)) {
                    setStatus('unavailable');
                    return;
                }
                setStatus('reconnecting');
                retryTimer = setTimeout(connect, Math.min(1000 * 2 ** attempt, MAX_RETRY_DELAY_MS));
                attempt += 1;
            };
        };

        connect();
        return () => {
            disposed = true;
            clearTimeout(retryTimer);
            socket?.close();
        };
    }, [path]);

    return status;
}
