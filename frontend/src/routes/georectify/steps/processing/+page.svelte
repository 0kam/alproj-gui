<!--
  Matching Step Page

  Step 3 of the georectification workflow:
  - Select image matching method
  - Run matching to generate a match plot
  - Allow re-run if result is not good
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { Button, Card } from '$lib/components/common';
	import ProcessLog from '$lib/components/common/ProcessLog.svelte';
	import { api } from '$lib/services/api';
	import { wizardStore } from '$lib/stores';
	import type { MatchRequest, MatchResponse, MatchingMethod, MatchingParams } from '$lib/types';

	type BackendLogChunk = {
		next_offset: number;
		text: string;
	};

	type IntervalId = ReturnType<typeof globalThis.setInterval>;

	let isRunning = false;
	let hasError = false;
	let errorMessage = '';
	let showModelDownloadProgress = false;
	let modelDownloadProgress = 0;
	let hasModelDownloadPercent = false;
	let modelLogPollTimer: IntervalId | null = null;
	let modelLogPollInFlight = false;
	let backendLogOffset = 0;

	// Default values
	const defaultMatchingMethod: MatchingMethod = 'superpoint-lightglue';
	const defaultSpatialThinGrid: number | null = 50;
	const defaultThreshold = 30.0;
	const defaultSurfaceDistance = 3000;
	const defaultSimulationMinDistance = 100;
	const fixedOutlierFilter = 'fundamental';
	const fixedSpatialThinSelection = 'center';
	const MATCH_TIMEOUT_MS = 1200000; // 20 minutes

	function getDefaultResize(method: MatchingMethod): number | 'none' {
		return method === 'minima-roma' ? 800 : 'none';
	}

	// Initialize from store or use defaults
	let matchingMethod: MatchingMethod = $wizardStore.matchingParams?.matching_method ?? defaultMatchingMethod;
	let spatialThinGrid: number | null = $wizardStore.matchingParams?.spatial_thin_grid ?? defaultSpatialThinGrid;
	let resize: number | 'none' =
		$wizardStore.matchingParams?.resize ?? getDefaultResize(matchingMethod);
	let threshold = $wizardStore.matchingParams?.threshold ?? defaultThreshold;
	let surfaceDistance = $wizardStore.matchingParams?.surface_distance ?? defaultSurfaceDistance;
	let simulationMinDistance =
		$wizardStore.matchingParams?.simulation_min_distance ?? defaultSimulationMinDistance;
	let resizeEnabled = resize !== 'none';
	let resizeValue = typeof resize === 'number' ? resize : 800;

	let matchPlot: string | null = $wizardStore.matchingPlot;
	let matchLog: string[] = $wizardStore.matchingLog;
	let matchCount: number | null = $wizardStore.matchCount;

	$: inputData = $wizardStore.inputData;
	$: cameraParams = $wizardStore.cameraParams;
	$: matchPlot = $wizardStore.matchingPlot;
	$: matchLog = $wizardStore.matchingLog;
	$: matchCount = $wizardStore.matchCount;

	// Restore options from store when navigating back to this page
	$: storedMatchingParams = $wizardStore.matchingParams;
	let paramsInitialized = false;
	$: if (storedMatchingParams && !paramsInitialized) {
		matchingMethod = storedMatchingParams.matching_method;
		spatialThinGrid = storedMatchingParams.spatial_thin_grid ?? defaultSpatialThinGrid;
		resize = storedMatchingParams.resize ?? getDefaultResize(matchingMethod);
		threshold = storedMatchingParams.threshold ?? defaultThreshold;
		surfaceDistance = storedMatchingParams.surface_distance ?? defaultSurfaceDistance;
		simulationMinDistance =
			storedMatchingParams.simulation_min_distance ?? defaultSimulationMinDistance;
		resizeEnabled = resize !== 'none';
		resizeValue = typeof resize === 'number' ? resize : 800;
		paramsInitialized = true;
	}

	let lastMethod: MatchingMethod = matchingMethod;
	$: if (matchingMethod !== lastMethod) {
		const recommended = getDefaultResize(matchingMethod);
		if (recommended === 'none') {
			resizeEnabled = false;
			resizeValue = 800;
		} else {
			resizeEnabled = true;
			resizeValue = recommended;
		}
		lastMethod = matchingMethod;
	}

	$: resize = resizeEnabled ? resizeValue : 'none';

	function resetState() {
		hasError = false;
		errorMessage = '';
	}

	function isTauri(): boolean {
		const runtime = globalThis as typeof globalThis & {
			__TAURI__?: unknown;
			__TAURI_INTERNALS__?: unknown;
		};
		return (
			typeof runtime !== 'undefined' &&
			('__TAURI__' in runtime || '__TAURI_INTERNALS__' in runtime)
		);
	}

	function appendMatchLogs(lines: string[]): void {
		if (lines.length === 0) return;
		matchLog = [...matchLog, ...lines].slice(-500);
	}

	function parseLogLines(rawText: string): string[] {
		if (!rawText) return [];
		return rawText
			.split(/\r\n|\n|\r/g)
			.map((line) => line.trim())
			.filter((line) => line.length > 0);
	}

	function hasDownloadSignals(lines: string[]): boolean {
		return lines.some((line) => {
			const lower = line.toLowerCase();
			return (
				lower.includes('downloading:') ||
				lower.includes('download') ||
				lower.includes('fetching') ||
				lower.includes('.partial') ||
				/\d{1,3}%\|/.test(line)
			);
		});
	}

	function extractPercentFromLines(lines: string[]): number | null {
		let latest: number | null = null;
		for (const line of lines) {
			const matches = [...line.matchAll(/(\d{1,3})%/g)];
			if (matches.length === 0) continue;
			const raw = matches[matches.length - 1]?.[1];
			if (!raw) continue;
			const value = Number(raw);
			if (Number.isNaN(value) || value < 0 || value > 100) continue;
			latest = value;
		}
		return latest;
	}

	async function getBackendLogCursor(): Promise<number> {
		if (!isTauri()) return 0;
		const { invoke } = await import('@tauri-apps/api/core');
		return await invoke<number>('get_backend_log_cursor');
	}

	async function readBackendLogChunk(offset: number): Promise<BackendLogChunk> {
		if (!isTauri()) {
			return { next_offset: offset, text: '' };
		}
		const { invoke } = await import('@tauri-apps/api/core');
		return await invoke<BackendLogChunk>('read_backend_log_chunk', {
			offset,
			maxBytes: 128 * 1024
		});
	}

	async function pollModelDownloadLogOnce(): Promise<void> {
		if (!isRunning || modelLogPollInFlight) return;

		modelLogPollInFlight = true;
		try {
			const chunk = await readBackendLogChunk(backendLogOffset);
			backendLogOffset = chunk.next_offset;
			const lines = parseLogLines(chunk.text);
			if (lines.length === 0) return;

			appendMatchLogs(lines);
			if (!showModelDownloadProgress && hasDownloadSignals(lines)) {
				showModelDownloadProgress = true;
			}
			const percent = extractPercentFromLines(lines);
			if (percent !== null) {
				hasModelDownloadPercent = true;
				modelDownloadProgress = Math.max(modelDownloadProgress, percent);
			}
		} catch (error) {
			void error;
		} finally {
			modelLogPollInFlight = false;
		}
	}

	async function startModelDownloadProgress(): Promise<void> {
		stopModelDownloadProgress();
		showModelDownloadProgress = false;
		modelDownloadProgress = 0;
		hasModelDownloadPercent = false;
		backendLogOffset = 0;

		try {
			backendLogOffset = await getBackendLogCursor();
		} catch (error) {
			void error;
		}

		if (!isTauri()) return;

		modelLogPollTimer = globalThis.setInterval(() => {
			void pollModelDownloadLogOnce();
		}, 1000);

		await pollModelDownloadLogOnce();
	}

	function stopModelDownloadProgress() {
		if (modelLogPollTimer) {
			globalThis.clearInterval(modelLogPollTimer);
			modelLogPollTimer = null;
		}
	}

	onDestroy(() => {
		stopModelDownloadProgress();
	});

	async function runMatching() {
		resetState();

		if (!inputData.dsm || !inputData.ortho || !inputData.targetImage || !cameraParams) {
			hasError = true;
			errorMessage = t('error.missingData');
			return;
		}

		isRunning = true;
		matchLog = [];
		matchPlot = null;
		matchCount = null;
		await startModelDownloadProgress();

		// Invalidate subsequent steps (Step 4 onwards) when re-running matching
		wizardStore.invalidateFromStep(3);
		wizardStore.setMatchingResult({
			plot: null,
			log: [],
			count: null,
			params: {
				matching_method: matchingMethod,
				resize,
				threshold,
				outlier_filter: fixedOutlierFilter,
				spatial_thin_grid: spatialThinGrid,
				spatial_thin_selection: fixedSpatialThinSelection,
				surface_distance: surfaceDistance,
				simulation_min_distance: simulationMinDistance,
				match_id: null
			}
		});

		try {
			const request: MatchRequest = {
				dsm_path: inputData.dsm.path,
				ortho_path: inputData.ortho.path,
				target_image_path: inputData.targetImage.path,
				camera_params: cameraParams,
				matching_method: matchingMethod,
				resize: resizeEnabled ? resizeValue : undefined,
				threshold,
				outlier_filter: fixedOutlierFilter,
				spatial_thin_grid: spatialThinGrid,
				spatial_thin_selection: fixedSpatialThinSelection,
				surface_distance: surfaceDistance,
				simulation_min_distance: simulationMinDistance
			};

			const response = await api.post<MatchResponse>('/api/georectify/match', request, {
				timeout: MATCH_TIMEOUT_MS
			});

			matchPlot = `data:image/png;base64,${response.match_plot_base64}`;
			appendMatchLogs(response.log ?? []);
			matchCount = response.match_count ?? null;
			const matchId = response.match_id ?? null;

			// Save matching parameters for use in estimation step
			const currentMatchingParams: MatchingParams = {
				matching_method: matchingMethod,
				resize,
				threshold,
				outlier_filter: fixedOutlierFilter,
				spatial_thin_grid: spatialThinGrid,
				spatial_thin_selection: fixedSpatialThinSelection,
				surface_distance: surfaceDistance,
				simulation_min_distance: simulationMinDistance,
				match_id: matchId
			};

			wizardStore.setMatchingResult({
				plot: matchPlot,
				log: matchLog,
				count: matchCount,
				params: currentMatchingParams
			});
			wizardStore.completeStep(2);
		} catch (err) {
			hasError = true;
			errorMessage = err instanceof Error ? err.message : t('matching.failed');
		} finally {
			await pollModelDownloadLogOnce();
			modelDownloadProgress = 100;
			stopModelDownloadProgress();
			isRunning = false;
		}
	}

	function goBack() {
		wizardStore.prevStep();
		goto('/georectify/steps/camera-setup');
	}

	function goNext() {
		wizardStore.nextStep();
		goto('/georectify/steps/result');
	}
</script>

<svelte:head>
	<title>{t('matching.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto p-6">
	<h1 class="text-2xl font-bold text-gray-900 mb-6">{t('matching.title')}</h1>

	<Card title={t('matching.options')}>
		<div class="space-y-4">
			<div>
				<label for="matching-method" class="block text-sm font-medium text-gray-700 mb-1">
					{t('matching.method')}
				</label>
				<select
					id="matching-method"
					bind:value={matchingMethod}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				>
					<option value="akaze">{t('matching.akaze.label')}</option>
					<option value="sift">{t('matching.sift.label')}</option>
					<option value="superpoint-lightglue">{t('matching.superpoint.label')}</option>
					<option value="minima-roma">{t('matching.minima.label')}</option>
				</select>
				<div class="mt-2 space-y-1 text-xs text-gray-500">
					<p>
						{t('matching.akazeSiftNote')}
					</p>
					<p>
						{t('matching.minimaNote')}
					</p>
				</div>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="spatial-thin-grid" class="block text-sm font-medium text-gray-700 mb-1">
						{t('matching.spatialThinGrid')}
					</label>
					<input
						id="spatial-thin-grid"
						type="number"
						min="1"
						bind:value={spatialThinGrid}
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
					/>
					<p class="mt-1 text-xs text-gray-500">{t('matching.spatialThinGridHelp')}</p>
				</div>
				<div>
					<label for="matching-resize-enabled" class="block text-sm font-medium text-gray-700 mb-1"
						>{t('matching.resize')}</label
					>
					<div class="flex items-center gap-2">
						<input
							id="matching-resize-enabled"
							type="checkbox"
							bind:checked={resizeEnabled}
							class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
						/>
						<input
							type="number"
							min="100"
							max="4096"
							disabled={!resizeEnabled}
							bind:value={resizeValue}
							class="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
						/>
						<span class="text-sm text-gray-500">px</span>
					</div>
				</div>
				<div>
					<label for="matching-threshold" class="block text-sm font-medium text-gray-700 mb-1">
						{t('matching.threshold')}
					</label>
					<input
						id="matching-threshold"
						type="number"
						min="0"
						step="0.1"
						bind:value={threshold}
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
					/>
					<p class="mt-1 text-xs text-gray-500">{t('matching.thresholdHelp')}</p>
				</div>
			</div>
		</div>

		<svelte:fragment slot="footer">
			<div class="flex justify-between">
				<Button variant="secondary" on:click={goBack}>
					{t('common.back')}
				</Button>
				<Button variant="primary" on:click={runMatching} loading={isRunning}>
					{isRunning ? t('matching.running') : t('matching.run')}
				</Button>
			</div>
		</svelte:fragment>
	</Card>

	{#if isRunning && showModelDownloadProgress}
		<div class="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 space-y-2">
			<div class="flex items-center justify-between">
				<span>{t('matching.modelDownloadNotice')}</span>
				<span>
					{#if hasModelDownloadPercent}
						{Math.max(1, Math.round(modelDownloadProgress))}%
					{:else}
						{t('matching.modelDownloadPreparing')}
					{/if}
				</span>
			</div>
			<div class="h-2 w-full overflow-hidden rounded bg-blue-100">
				{#if hasModelDownloadPercent}
					<div
						class="h-full bg-blue-500 transition-[width] duration-500 ease-out"
						style={`width: ${Math.max(2, modelDownloadProgress)}%`}
					></div>
				{:else}
					<div class="h-full model-download-indeterminate"></div>
				{/if}
			</div>
		</div>
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
					<h3 class="text-sm font-medium text-red-800">{t('matching.error')}</h3>
					<p class="mt-1 text-sm text-red-700">{errorMessage}</p>
				</div>
			</div>
		</div>
	{/if}

	{#if matchPlot}
		<div class="mt-6">
			<Card title={t('matching.result')}>
				<div class="space-y-4">
					<img src={matchPlot} alt={t('matching.resultAlt')} class="w-full rounded-lg border" />
					{#if matchCount !== null}
						<p class="text-sm text-gray-600">{t('matching.matchCount', { count: matchCount })}</p>
					{/if}
					{#if matchLog.length > 0}
						<ProcessLog logs={matchLog} />
					{/if}
				</div>
				<svelte:fragment slot="footer">
					<div class="flex justify-between">
						<Button variant="secondary" on:click={runMatching} loading={isRunning}>
							{t('common.rerun')}
						</Button>
						<Button variant="primary" on:click={goNext}>
							{t('matching.nextEstimation')}
						</Button>
					</div>
				</svelte:fragment>
			</Card>
		</div>
	{/if}
</div>

<style>
	@keyframes model-download-indeterminate-slide {
		0% {
			transform: translateX(-120%);
		}
		100% {
			transform: translateX(320%);
		}
	}

	.model-download-indeterminate {
		width: 28%;
		background: linear-gradient(90deg, #60a5fa 0%, #2563eb 55%, #60a5fa 100%);
		animation: model-download-indeterminate-slide 1s ease-in-out infinite;
	}
</style>
