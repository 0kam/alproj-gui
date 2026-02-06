/**
 * API Client for ALPROJ GUI Backend
 *
 * Provides a fetch-based HTTP client for communicating with the FastAPI backend.
 * Includes error handling, JSON parsing, and typed request/response methods.
 */

// Default API configuration
const DEFAULT_BASE_URL = 'http://127.0.0.1:8765';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * API Error class for handling HTTP errors
 */
export class ApiError extends Error {
	readonly status: number;
	readonly statusText: string;
	readonly body: unknown;

	constructor(status: number, statusText: string, body: unknown = null) {
		super(`API Error: ${status} ${statusText}`);
		this.name = 'ApiError';
		this.status = status;
		this.statusText = statusText;
		this.body = body;
	}
}

/**
 * Network Error class for connection failures
 */
export class NetworkError extends Error {
	readonly cause: unknown;

	constructor(message: string, cause?: unknown) {
		super(message);
		this.name = 'NetworkError';
		this.cause = cause;
	}
}

/**
 * Timeout Error class
 */
export class TimeoutError extends Error {
	constructor(timeout: number) {
		super(`Request timed out after ${timeout}ms`);
		this.name = 'TimeoutError';
	}
}

/**
 * Request options for API calls
 */
export interface RequestOptions {
	headers?: Record<string, string>;
	timeout?: number;
	signal?: AbortSignal;
}

/**
 * API Client configuration
 */
export interface ApiClientConfig {
	baseUrl?: string;
	defaultTimeout?: number;
	defaultHeaders?: Record<string, string>;
}

/**
 * Create an abort controller with timeout
 */
function createTimeoutController(timeout: number, existingSignal?: AbortSignal): AbortController {
	const controller = new AbortController();

	// Set up timeout
	const timeoutId = setTimeout(() => {
		controller.abort(new TimeoutError(timeout));
	}, timeout);

	// Clean up timeout if aborted by external signal
	if (existingSignal) {
		existingSignal.addEventListener('abort', () => {
			clearTimeout(timeoutId);
			controller.abort(existingSignal.reason);
		});
	}

	// Store timeout ID for cleanup
	(controller as unknown as { timeoutId: ReturnType<typeof setTimeout> }).timeoutId = timeoutId;

	return controller;
}

/**
 * API Client class
 */
class ApiClient {
	private baseUrl: string;
	private defaultTimeout: number;
	private defaultHeaders: Record<string, string>;

	constructor(config: ApiClientConfig = {}) {
		this.baseUrl = config.baseUrl || DEFAULT_BASE_URL;
		this.defaultTimeout = config.defaultTimeout || DEFAULT_TIMEOUT;
		this.defaultHeaders = {
			'Content-Type': 'application/json',
			...config.defaultHeaders
		};
	}

	/**
	 * Build full URL from path
	 */
	private buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
		const url = new URL(path.startsWith('/') ? path : `/${path}`, this.baseUrl);

		if (params) {
			Object.entries(params).forEach(([key, value]) => {
				if (value !== undefined && value !== null) {
					url.searchParams.append(key, String(value));
				}
			});
		}

		return url.toString();
	}

	/**
	 * Execute a fetch request with error handling
	 */
	private async request<T>(
		method: string,
		path: string,
		body?: unknown,
		options: RequestOptions = {}
	): Promise<T> {
		const timeout = options.timeout ?? this.defaultTimeout;
		const controller = createTimeoutController(timeout, options.signal);

		const headers: Record<string, string> = {
			...this.defaultHeaders,
			...options.headers
		};

		// Remove Content-Type for FormData
		if (body instanceof FormData) {
			delete headers['Content-Type'];
		}

		try {
			const response = await fetch(this.buildUrl(path), {
				method,
				headers,
				body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
				signal: controller.signal
			});

			// Clear timeout on response
			const timeoutId = (controller as unknown as { timeoutId: ReturnType<typeof setTimeout> })
				.timeoutId;
			if (timeoutId) {
				clearTimeout(timeoutId);
			}

			// Handle non-OK responses
			if (!response.ok) {
				let errorBody: unknown = null;
				try {
					errorBody = await response.json();
				} catch {
					// Response body might not be JSON
					try {
						errorBody = await response.text();
					} catch {
						// Ignore if we can't read the body
					}
				}
				throw new ApiError(response.status, response.statusText, errorBody);
			}

			// Handle empty responses
			const contentType = response.headers.get('Content-Type');
			if (response.status === 204 || !contentType) {
				return undefined as T;
			}

			// Parse JSON response
			if (contentType.includes('application/json')) {
				return (await response.json()) as T;
			}

			// Return text for other content types
			return (await response.text()) as unknown as T;
		} catch (error) {
			// Re-throw known errors
			if (error instanceof ApiError || error instanceof TimeoutError) {
				throw error;
			}

			// Handle fetch errors (network issues, etc.)
			if (error instanceof TypeError) {
				throw new NetworkError('Failed to connect to the server', error);
			}

			// Handle abort errors
			if (error instanceof DOMException && error.name === 'AbortError') {
				if (controller.signal.reason instanceof TimeoutError) {
					throw controller.signal.reason;
				}
				throw error;
			}

			// Re-throw unknown errors
			throw error;
		}
	}

	/**
	 * GET request
	 */
	async get<T>(
		path: string,
		params?: Record<string, string | number | boolean>,
		options?: RequestOptions
	): Promise<T> {
		const url = params
			? `${path}?${new URLSearchParams(
					Object.entries(params).map(([k, v]) => [k, String(v)])
				).toString()}`
			: path;
		return this.request<T>('GET', url, undefined, options);
	}

	/**
	 * POST request
	 */
	async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
		return this.request<T>('POST', path, body, options);
	}

	/**
	 * PUT request
	 */
	async put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
		return this.request<T>('PUT', path, body, options);
	}

	/**
	 * PATCH request
	 */
	async patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
		return this.request<T>('PATCH', path, body, options);
	}

	/**
	 * DELETE request
	 */
	async delete<T>(path: string, options?: RequestOptions): Promise<T> {
		return this.request<T>('DELETE', path, undefined, options);
	}

	/**
	 * Upload file(s) via POST with FormData
	 */
	async upload<T>(
		path: string,
		files: Record<string, File | File[]>,
		additionalData?: Record<string, string>,
		options?: RequestOptions
	): Promise<T> {
		const formData = new FormData();

		// Add files
		Object.entries(files).forEach(([fieldName, fileOrFiles]) => {
			if (Array.isArray(fileOrFiles)) {
				fileOrFiles.forEach((file) => {
					formData.append(fieldName, file);
				});
			} else {
				formData.append(fieldName, fileOrFiles);
			}
		});

		// Add additional data
		if (additionalData) {
			Object.entries(additionalData).forEach(([key, value]) => {
				formData.append(key, value);
			});
		}

		return this.request<T>('POST', path, formData, options);
	}

	/**
	 * Check if the backend is available
	 */
	async healthCheck(): Promise<boolean> {
		try {
			await this.get('/api/health', undefined, { timeout: 5000 });
			return true;
		} catch {
			return false;
		}
	}

	/**
	 * Update base URL
	 */
	setBaseUrl(url: string): void {
		this.baseUrl = url;
	}

	/**
	 * Get current base URL
	 */
	getBaseUrl(): string {
		return this.baseUrl;
	}
}

// Export singleton instance
export const api = new ApiClient();

// Export class for custom instances
export { ApiClient };
