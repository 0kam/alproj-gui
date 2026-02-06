<!--
  SimulationPreview Component

  Displays a simulation image alongside the target image for comparison.
  Calls the simulation API with debouncing to optimize performance.

  Usage:
    <SimulationPreview
      dsmPath="/path/to/dsm.tif"
      orthoPath="/path/to/ortho.tif"
      targetImagePath="/path/to/photo.jpg"
      cameraParams={params}
    />
-->
<script lang="ts">
	import { createEventDispatcher, onDestroy } from 'svelte';
	import { t } from '$lib/i18n';
	import { api } from '$lib/services/api';
	import { Loading } from '$lib/components/common';
	import type { CameraParamsValues, SimulationResponse } from '$lib/types';

	/** Path to DSM file */
	export let dsmPath: string;
	/** Path to orthophoto file */
	export let orthoPath: string;
	/** Path to target image file */
	export let targetImagePath: string;
	/** Camera parameters for simulation */
	export let cameraParams: CameraParamsValues;
	/** Maximum size of the simulation image */
	export let maxSize: number = 800;
	/** Surface distance for rendering (meters) */
	export let surfaceDistance: number = 2000;
	/** Debounce delay in milliseconds */
	export let debounceMs: number = 500;
	/** Stored simulation image to restore (optional) */
	export let initialImage: string | null = null;
	/** Whether simulation has been generated (bindable) */
	export let hasSimulation: boolean = false;

	const dispatch = createEventDispatcher<{
		generated: { image: string };
		cleared: void;
	}>();

	// State
	let simulationImage: string | null = null;
	let targetThumbnail: string | null = null;
	let isLoading = false;
	let error: string | null = null;
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let abortController: AbortController | null = null;

	// Track previous params to detect changes
	let prevParams: string = '';
	let prevTargetPath: string = '';

	/**
	 * Fetch target image thumbnail
	 */
	async function fetchTargetThumbnail(): Promise<void> {
		if (!targetImagePath) {
			targetThumbnail = null;
			return;
		}

		try {
			const response = await fetch(`${api.getBaseUrl()}/api/files/image/thumbnail`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path: targetImagePath, max_size: maxSize })
			});

			if (response.ok) {
				const blob = await response.blob();
				if (targetThumbnail) {
					URL.revokeObjectURL(targetThumbnail);
				}
				targetThumbnail = URL.createObjectURL(blob);
			}
		} catch (err) {
			console.error('Failed to load target thumbnail:', err);
		}
	}

	// Load target thumbnail when path changes
	$: if (targetImagePath !== prevTargetPath) {
		prevTargetPath = targetImagePath;
		fetchTargetThumbnail();
	}

	// Restore stored simulation image if provided
	$: if (initialImage && initialImage !== simulationImage) {
		simulationImage = initialImage;
		hasSimulation = true;
	}

	/**
	 * Fetch simulation image from API
	 */
	async function fetchSimulation(): Promise<void> {
		// Cancel any pending request
		if (abortController) {
			abortController.abort();
		}

		// Validate required paths
		if (!dsmPath || !orthoPath || !targetImagePath) {
			error = 'Required file paths are missing';
			return;
		}

		isLoading = true;
		error = null;
		abortController = new AbortController();

		try {
			const response = await api.post<SimulationResponse>(
				'/api/georectify/simulate',
				{
					dsm_path: dsmPath,
					ortho_path: orthoPath,
					target_image_path: targetImagePath,
					camera_params: cameraParams,
					max_size: maxSize,
					surface_distance: surfaceDistance
				},
				{ signal: abortController.signal }
			);

			simulationImage = `data:image/png;base64,${response.image_base64}`;
			hasSimulation = true;
			dispatch('generated', { image: simulationImage });
		} catch (err) {
			if (err instanceof DOMException && err.name === 'AbortError') {
				// Request was cancelled, ignore
				return;
			}
			console.error('Simulation failed:', err);
			error = err instanceof Error ? err.message : 'Simulation failed';
			simulationImage = null;
			hasSimulation = false;
		} finally {
			isLoading = false;
			abortController = null;
		}
	}

	/**
	 * Debounced simulation fetch
	 */
	function debouncedFetch(): void {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			fetchSimulation();
			debounceTimer = null;
		}, debounceMs);
	}

	/**
	 * Force immediate simulation update
	 */
	export function refresh(): void {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
			debounceTimer = null;
		}
		fetchSimulation();
	}

	// Track parameter changes but do NOT auto-trigger simulation
	// Simulation generation is expensive - only trigger on explicit button click
	$: {
		const currentParams = JSON.stringify({
			dsmPath,
			orthoPath,
			targetImagePath,
			cameraParams,
			surfaceDistance
		});

		if (!prevParams) {
			prevParams = currentParams;
		} else if (currentParams !== prevParams) {
			prevParams = currentParams;
			// Clear previous simulation when parameters change
			// User must click refresh button to generate new simulation
			if (simulationImage) {
				simulationImage = null;
				hasSimulation = false;
				dispatch('cleared');
			}
		}
	}

	onDestroy(() => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		if (abortController) {
			abortController.abort();
		}
		if (targetThumbnail) {
			URL.revokeObjectURL(targetThumbnail);
		}
	});
</script>

<div class="simulation-preview">
	<div class="preview-header">
		<h3 class="preview-title">{t('camera.simulation')}</h3>
		<button
			type="button"
			class="generate-btn"
			on:click={refresh}
			disabled={isLoading}
		>
			{#if isLoading}
				<svg
					class="btn-icon spinning"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					/>
				</svg>
				生成中...
			{:else}
				生成
			{/if}
		</button>
	</div>

	<div class="image-comparison">
		<!-- Target Image -->
		<div class="image-panel">
			<div class="panel-header">
				<span class="panel-label">対象画像</span>
			</div>
			<div class="image-container">
				{#if targetThumbnail}
					<img src={targetThumbnail} alt="Target" class="preview-image" />
				{:else if targetImagePath}
					<div class="loading-state">
						<Loading message="対象画像を読み込み中..." />
					</div>
				{:else}
					<div class="placeholder">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
							/>
						</svg>
						<span>画像が選択されていません</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Simulation Image -->
		<div class="image-panel">
			<div class="panel-header">
				<span class="panel-label">シミュレーション</span>
				{#if isLoading}
					<span class="loading-indicator">
						<Loading size="sm" />
					</span>
				{/if}
			</div>
			<div class="image-container">
				{#if error}
					<div class="error-state">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
						<span>{error}</span>
						<button type="button" class="retry-btn" on:click={refresh}>
							{t('common.retry')}
						</button>
					</div>
				{:else if simulationImage}
					<img src={simulationImage} alt="Simulation" class="preview-image" />
				{:else if isLoading}
					<div class="loading-state">
						<Loading message="シミュレーション生成中..." />
					</div>
				{:else}
					<div class="placeholder">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
							/>
						</svg>
						<span>カメラパラメータを調整してシミュレーションを生成してください</span>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.simulation-preview {
		display: flex;
		flex-direction: column;
		height: 100%;
		background-color: white;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.preview-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		background-color: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.preview-title {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
	}

	.generate-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.375rem;
		padding: 0.375rem 0.75rem;
		border: 1px solid #3b82f6;
		background-color: #3b82f6;
		border-radius: 0.375rem;
		cursor: pointer;
		color: white;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.2s;
	}

	.generate-btn:hover:not(:disabled) {
		background-color: #2563eb;
		border-color: #2563eb;
	}

	.generate-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-icon {
		width: 1rem;
		height: 1rem;
	}

	.btn-icon.spinning {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.image-comparison {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1px;
		flex: 1;
		background-color: #e5e7eb;
	}

	.image-panel {
		display: flex;
		flex-direction: column;
		background-color: white;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.75rem;
		background-color: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.panel-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.loading-indicator {
		display: flex;
		align-items: center;
	}

	.image-container {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		background-color: #1f2937;
		overflow: hidden;
	}

	.preview-image {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}

	.placeholder,
	.error-state,
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 2rem;
		text-align: center;
		color: #9ca3af;
	}

	.placeholder svg,
	.error-state svg {
		width: 3rem;
		height: 3rem;
		opacity: 0.5;
	}

	.placeholder span,
	.error-state span {
		font-size: 0.875rem;
	}

	.error-state {
		color: #ef4444;
	}

	.error-state svg {
		color: #ef4444;
	}

	.retry-btn {
		padding: 0.375rem 0.75rem;
		background-color: transparent;
		color: #3b82f6;
		border: 1px solid #3b82f6;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.retry-btn:hover {
		background-color: #3b82f6;
		color: white;
	}
</style>
