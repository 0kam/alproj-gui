/**
 * WebSocket Service for Job Progress Tracking
 *
 * Provides a WebSocket connection manager for real-time job progress updates.
 * Handles connection lifecycle, reconnection, and message parsing.
 */

import type { ProcessResult } from '$lib/types';

// WebSocket configuration
const WS_BASE_URL = 'ws://localhost:8765';
const RECONNECT_DELAY = 1000; // ms
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * WebSocket message types from server
 */
interface ProgressMessage {
	type: 'progress';
	progress: number;
	step: string;
	message?: string;
}

interface CompleteMessage {
	type: 'complete';
	result: ProcessResult;
}

interface ErrorMessage {
	type: 'error';
	error: string;
}

type TypedWebSocketMessage = ProgressMessage | CompleteMessage | ErrorMessage;

type BackendStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

interface BackendWebSocketMessage {
	progress?: number;
	step?: string;
	message?: string;
	status?: BackendStatus | string;
	result?: ProcessResult | null;
	error?: string;
}

/**
 * Callbacks for WebSocket events
 */
export interface WebSocketCallbacks {
	onProgress: (progress: number, step: string, message: string) => void;
	onComplete: (result: ProcessResult) => void;
	onError: (error: string) => void;
	onConnectionChange?: (connected: boolean) => void;
}

/**
 * WebSocket connection state
 */
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

/**
 * Connect to job progress WebSocket
 *
 * @param jobId - The job ID to monitor
 * @param callbacks - Event callbacks for progress, completion, and errors
 * @returns Cleanup function to close the connection
 */
export function connectJobWebSocket(jobId: string, callbacks: WebSocketCallbacks): () => void {
	let ws: WebSocket | null = null;
	let reconnectAttempts = 0;
	let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
	let isCleanedUp = false;

	function connect() {
		if (isCleanedUp) return;

		const url = `${WS_BASE_URL}/api/jobs/${jobId}/ws`;
		ws = new WebSocket(url);

		ws.onopen = () => {
			console.log(`WebSocket connected for job ${jobId}`);
			reconnectAttempts = 0;
			callbacks.onConnectionChange?.(true);
		};

		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data) as unknown;
				handleMessage(data);
			} catch (err) {
				console.error('Failed to parse WebSocket message:', err);
			}
		};

		ws.onerror = (event) => {
			console.error('WebSocket error:', event);
		};

		ws.onclose = (event) => {
			console.log(`WebSocket closed for job ${jobId}:`, event.code, event.reason);
			callbacks.onConnectionChange?.(false);

			// Don't reconnect if intentionally closed or max attempts reached
			if (isCleanedUp || event.code === 1000) {
				return;
			}

			// Attempt reconnection
			if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
				reconnectAttempts++;
				const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1);
				console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`);
				reconnectTimeout = setTimeout(connect, delay);
			} else {
				callbacks.onError('Connection lost. Max reconnection attempts reached.');
			}
		};
	}

	function handleMessage(message: unknown) {
		if (!message || typeof message !== 'object') {
			console.warn('Unknown WebSocket message payload:', message);
			return;
		}

		if ('type' in message) {
			const typedMessage = message as TypedWebSocketMessage;
			switch (typedMessage.type) {
				case 'progress':
					callbacks.onProgress(
						typedMessage.progress,
						typedMessage.step,
						typedMessage.message || ''
					);
					return;
				case 'complete':
					callbacks.onComplete(typedMessage.result);
					return;
				case 'error':
					callbacks.onError(typedMessage.error);
					return;
				default:
					console.warn('Unknown WebSocket message type:', typedMessage);
					return;
			}
		}

		const backendMessage = message as BackendWebSocketMessage;
		if (backendMessage.error) {
			callbacks.onError(backendMessage.error);
			return;
		}

		if (backendMessage.status) {
			if (backendMessage.status === 'completed') {
				if (backendMessage.result) {
					callbacks.onComplete(backendMessage.result);
				} else {
					callbacks.onError(backendMessage.message || 'Job completed without result.');
				}
				return;
			}
			if (backendMessage.status === 'failed' || backendMessage.status === 'cancelled') {
				callbacks.onError(backendMessage.message || 'Job failed.');
				return;
			}
		}

		if (typeof backendMessage.progress === 'number') {
			callbacks.onProgress(
				backendMessage.progress,
				backendMessage.step || '',
				backendMessage.message || ''
			);
			return;
		}

		console.warn('Unknown WebSocket message payload:', backendMessage);
	}

	// Start connection
	connect();

	// Return cleanup function
	return () => {
		isCleanedUp = true;
		if (reconnectTimeout) {
			clearTimeout(reconnectTimeout);
		}
		if (ws) {
			ws.close(1000, 'Client closed connection');
			ws = null;
		}
	};
}

/**
 * Create a mock WebSocket connection for testing/development
 *
 * @param callbacks - Event callbacks
 * @param duration - Total duration of the mock process in ms
 * @returns Cleanup function
 */
export function createMockWebSocket(callbacks: WebSocketCallbacks, duration: number = 5000): () => void {
	let cancelled = false;
	const steps = [
		'Initializing...',
		'Loading images...',
		'Matching features...',
		'Optimizing parameters...',
		'Generating GeoTIFF...',
		'Finalizing...'
	];

	const stepDuration = duration / steps.length;

	callbacks.onConnectionChange?.(true);

	steps.forEach((step, index) => {
		if (cancelled) return;

		setTimeout(() => {
			if (cancelled) return;

			const progress = (index + 1) / steps.length;
			callbacks.onProgress(progress, step, `Processing step ${index + 1} of ${steps.length}`);

			// Complete on last step
			if (index === steps.length - 1) {
				setTimeout(() => {
					if (cancelled) return;
					callbacks.onComplete({
						metrics: {
							rmse: 2.5,
							gcp_count: 15,
							gcp_total: 20,
							residual_mean: 1.8,
							residual_std: 0.7,
							residual_max: 4.2
						},
						geotiff_path: '/tmp/output.tif',
						log: steps.map((s, i) => `[${new Date().toISOString()}] ${s}`)
					});
				}, 500);
			}
		}, stepDuration * (index + 1));
	});

	return () => {
		cancelled = true;
		callbacks.onConnectionChange?.(false);
	};
}
