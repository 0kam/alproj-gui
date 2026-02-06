<!--
  GeoTIFF Step Page

  Step 5 of the georectification workflow:
  - Export GeoTIFF (background job with progress)
  - Preview output on map
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { Button, Card } from '$lib/components/common';
	import ExportForm from '$lib/components/common/ExportForm.svelte';
	import { MapView, RasterOverlay } from '$lib/components/Map';
	import { api } from '$lib/services/api';
	import { wizardStore } from '$lib/stores';
	import type { ExportRequest, ExportJobResponse, ExportResult, RasterFile } from '$lib/types';
	import type maplibregl from 'maplibre-gl';

	$: projectId = $wizardStore.projectId ?? '';
	let projectCrs = 'EPSG:4326';

	// Export job state
	let isExporting = false;
	let isComplete = false;
	let hasError = false;
	let errorMessage = '';
	let exportedPath = $wizardStore.geotiffPath ?? '';

	// Progress state
	let progress = 0;
	let progressStep = '';
	let progressMessage = '';
	let jobId: string | null = null;
	let ws: WebSocket | null = null;

	// Map preview state
	let map: maplibregl.Map | null = null;
	let mapLoaded = false;
	let previewUrl: string | null = null;
	let previewObjectUrl: string | null = null;
	let previewBounds: [number, number, number, number] | null = null;
	let previewError: string | null = null;
	$: overlayBounds = previewBounds ?? inputData.ortho?.bounds_wgs84 ?? null;

	$: inputData = $wizardStore.inputData;
	$: if (inputData.ortho?.crs) {
		projectCrs = inputData.ortho.crs;
	}
	$: if (exportedPath && !isComplete) {
		isComplete = true;
	}
	$: if (isComplete && exportedPath && !previewUrl && !previewError && !isExporting) {
		void loadPreview(exportedPath);
	}

	function handleMapLoad(event: CustomEvent<{ map: maplibregl.Map }>) {
		map = event.detail.map;
		mapLoaded = true;
	}

	async function loadPreview(path: string): Promise<void> {
		previewError = null;
		previewBounds = null;
		previewUrl = null;

		try {
			const info = await api.post<RasterFile>('/api/files/raster/info', { path });
			previewBounds = info.bounds_wgs84 ?? null;

			const response = await fetch(`${api.getBaseUrl()}/api/files/raster/thumbnail`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, max_size: 1024 })
			});
			if (!response.ok) {
				throw new Error('Failed to fetch GeoTIFF preview');
			}
			const blob = await response.blob();
			if (previewObjectUrl) {
				URL.revokeObjectURL(previewObjectUrl);
			}
			previewObjectUrl = URL.createObjectURL(blob);
			previewUrl = previewObjectUrl;
		} catch (err) {
			console.error('GeoTIFF preview failed:', err);
			previewError = err instanceof Error ? err.message : 'Preview failed';
		}
	}

	function connectWebSocket(id: string): void {
		const wsUrl = api.getBaseUrl().replace(/^http/, 'ws') + `/api/jobs/${id}/ws`;
		ws = new WebSocket(wsUrl);

		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				progress = data.progress ?? 0;
				progressStep = data.step ?? '';
				progressMessage = data.message ?? '';

				if (data.status === 'completed') {
					isExporting = false;
					isComplete = true;
					// Extract path from result
					const result = data.result as ExportResult | null;
					if (result?.path) {
						exportedPath = result.path;
						wizardStore.setGeotiffPath(exportedPath);
						wizardStore.completeStep(4);
						void loadPreview(exportedPath);
					}
					closeWebSocket();
				} else if (data.status === 'failed') {
					isExporting = false;
					hasError = true;
					errorMessage = data.message || data.error || 'Export failed';
					closeWebSocket();
				} else if (data.status === 'cancelled') {
					isExporting = false;
					hasError = true;
					errorMessage = 'Export was cancelled';
					closeWebSocket();
				}
			} catch (err) {
				console.error('WebSocket message parse error:', err);
			}
		};

		ws.onerror = (event) => {
			console.error('WebSocket error:', event);
			// Don't set error here - wait for onclose
		};

		ws.onclose = () => {
			// If still exporting and connection closed, it might be a server issue
			if (isExporting) {
				// Give a small delay then check job status via REST API
				setTimeout(async () => {
					if (isExporting && jobId) {
						try {
							const job = await api.get<{
								status: string;
								result?: ExportResult;
								error?: string;
							}>(`/api/jobs/${jobId}`);
							if (job.status === 'completed' && job.result?.path) {
								isExporting = false;
								isComplete = true;
								exportedPath = job.result.path;
								wizardStore.setGeotiffPath(exportedPath);
								wizardStore.completeStep(4);
								void loadPreview(exportedPath);
							} else if (job.status === 'failed') {
								isExporting = false;
								hasError = true;
								errorMessage = job.error || 'Export failed';
							}
						} catch {
							// Ignore - WebSocket might have closed normally
						}
					}
				}, 1000);
			}
		};
	}

	function closeWebSocket(): void {
		if (ws) {
			ws.close();
			ws = null;
		}
	}

	async function handleExport(event: CustomEvent<ExportRequest>) {
		if (!projectId) {
			hasError = true;
			errorMessage = t('project.notFound');
			return;
		}

		const request: ExportRequest = {
			...event.detail,
			project_id: projectId,
			surface_distance: $wizardStore.matchingParams?.surface_distance ?? event.detail.surface_distance
		};

		isExporting = true;
		hasError = false;
		errorMessage = '';
		progress = 0;
		progressStep = 'starting';
		progressMessage = 'Starting export...';

		try {
			// Submit export job (returns immediately with job ID)
			const response = await api.post<ExportJobResponse>('/api/georectify/export', request);
			jobId = response.id;

			// Connect WebSocket for progress updates
			connectWebSocket(response.id);
		} catch (err) {
			isExporting = false;
			hasError = true;
			errorMessage = err instanceof Error ? err.message : 'Failed to start export';
		}
	}

	function goBack() {
		closeWebSocket();
		wizardStore.prevStep();
		goto('/georectify/steps/result');
	}

	function exportAgain() {
		closeWebSocket();
		isComplete = false;
		exportedPath = '';
		jobId = null;
		progress = 0;
		progressStep = '';
		progressMessage = '';
		wizardStore.setGeotiffPath(null);
		if (previewObjectUrl) {
			URL.revokeObjectURL(previewObjectUrl);
			previewObjectUrl = null;
		}
		previewUrl = null;
		previewBounds = null;
		previewError = null;
	}

	onDestroy(() => {
		closeWebSocket();
		if (previewObjectUrl) {
			URL.revokeObjectURL(previewObjectUrl);
		}
	});

	// Progress display helper
	function getProgressPercent(): number {
		return Math.round(progress * 100);
	}

	function getStepLabel(step: string): string {
		const stepKey = `export.steps.${step}` as const;
		const translated = t(stepKey);
		// If key not found (returns the key itself), fall back to processing
		return translated !== stepKey ? translated : (step || t('common.processing'));
	}
</script>

<svelte:head>
	<title>{t('export.pageTitle')}</title>
</svelte:head>

<div class="max-w-5xl mx-auto p-6">
	<h1 class="text-2xl font-bold text-gray-900 mb-6">{t('export.heading')}</h1>

	{#if !isComplete}
		<Card title={t('export.heading')}>
			{#if isExporting}
				<!-- Loading display during export -->
				<div class="space-y-4 py-8 text-center">
					<div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
					<p class="text-sm text-gray-700 font-medium">{t('export.exporting')}</p>
					<p class="text-xs text-gray-400">
						{t('export.exportNote')}
					</p>
				</div>
			{:else}
				<ExportForm
					{projectId}
					defaultCrs={projectCrs}
					templatePath={inputData.ortho?.path ?? null}
					targetImagePath={inputData.targetImage?.path ?? null}
					submitting={isExporting}
					on:export={handleExport}
				/>
			{/if}

			{#if hasError}
				<div class="mt-4 bg-red-50 border border-red-200 rounded-md p-4">
					<div class="flex items-start">
						<svg class="h-5 w-5 text-red-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
								clip-rule="evenodd"
							/>
						</svg>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">{t('export.error')}</h3>
							<p class="mt-1 text-sm text-red-700">{errorMessage}</p>
						</div>
					</div>
				</div>
			{/if}

			<svelte:fragment slot="footer">
				<Button variant="secondary" on:click={goBack} disabled={isExporting}>
					{t('common.back')}
				</Button>
			</svelte:fragment>
		</Card>
	{:else}
		<Card title={t('export.mapPreview')}>
			<div class="space-y-4">
				<div class="text-sm text-gray-600">
					{t('export.output')} <span class="font-mono text-xs">{exportedPath}</span>
				</div>
				<div class="h-96 border rounded-lg overflow-hidden">
					<MapView
						bounds={overlayBounds}
						on:load={handleMapLoad}
					>
						{#if mapLoaded && map && previewUrl && overlayBounds}
							<RasterOverlay {map} imageUrl={previewUrl} bounds={overlayBounds} />
						{/if}
					</MapView>
				</div>
				{#if previewError}
					<p class="text-sm text-red-600">{previewError}</p>
				{/if}
			</div>
			<svelte:fragment slot="footer">
				<div class="flex justify-between">
					<Button variant="secondary" on:click={exportAgain}>
						{t('export.reexport')}
					</Button>
					<Button variant="secondary" on:click={goBack}>
						{t('common.back')}
					</Button>
				</div>
			</svelte:fragment>
		</Card>
	{/if}
</div>
