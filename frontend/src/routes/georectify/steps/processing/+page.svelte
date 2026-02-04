<!--
  Matching Step Page

  Step 3 of the georectification workflow:
  - Select image matching method
  - Run matching to generate a match plot
  - Allow re-run if result is not good
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { Button, Card } from '$lib/components/common';
	import ProcessLog from '$lib/components/common/ProcessLog.svelte';
	import { api } from '$lib/services/api';
	import { wizardStore } from '$lib/stores';
	import type { MatchRequest, MatchResponse, MatchingMethod, MatchingParams } from '$lib/types';

	let isRunning = false;
	let hasError = false;
	let errorMessage = '';

	// Default values
	const defaultMatchingMethod: MatchingMethod = 'superpoint-lightglue';
	const defaultSpatialThinGrid: number | null = 50;
	const defaultThreshold = 30.0;
	const defaultSurfaceDistance = 3000;
	const defaultSimulationMinDistance = 100;
	const fixedOutlierFilter = 'fundamental';
	const fixedSpatialThinSelection = 'center';

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
				timeout: 300000
			});

			matchPlot = `data:image/png;base64,${response.match_plot_base64}`;
			matchLog = response.log ?? [];
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
					<label class="block text-sm font-medium text-gray-700 mb-1">{t('matching.resize')}</label>
					<div class="flex items-center gap-2">
						<input
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
