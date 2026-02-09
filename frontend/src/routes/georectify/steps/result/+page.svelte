<!--
  Estimation Step Page

  Step 4 of the georectification workflow:
  - Estimate camera parameters (selectable targets)
  - Compare optimized simulation with target image
  - Allow re-run of this step only
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { Button, Card } from '$lib/components/common';
	import ImageCompare from '$lib/components/ImageViewer/ImageCompare.svelte';
	import ProcessLog from '$lib/components/common/ProcessLog.svelte';
	import { api } from '$lib/services/api';
	import { wizardStore } from '$lib/stores';
	import { t } from '$lib/i18n';
	import type { EstimateRequest, EstimateResponse, OptimizerType, EstimationParams } from '$lib/types';

	let isRunning = false;
	let hasError = false;
	let errorMessage = '';

	// Default values
	const defaultOptimizer: OptimizerType = 'cma';
	const defaultTwoStage = true;
	const defaultOptimizePosition = true;
	const defaultOptimizeOrientation = true;
	const defaultOptimizeFov = true;
	const defaultOptimizeDistortion = true;
	const ESTIMATION_TIMEOUT_MS = 600000; // 10 minutes

	// Initialize from store or use defaults
	let optimizer: OptimizerType = $wizardStore.estimationParams?.optimizer ?? defaultOptimizer;
	let twoStage = $wizardStore.estimationParams?.two_stage ?? defaultTwoStage;
	let optimizePosition =
		$wizardStore.estimationParams?.optimize_position ?? defaultOptimizePosition;
	let optimizeOrientation =
		$wizardStore.estimationParams?.optimize_orientation ?? defaultOptimizeOrientation;
	let optimizeFov = $wizardStore.estimationParams?.optimize_fov ?? defaultOptimizeFov;
	let optimizeDistortion =
		$wizardStore.estimationParams?.optimize_distortion ?? defaultOptimizeDistortion;

	let simulationImage: string | null = $wizardStore.estimationSimulation;
	let estimationLog: string[] = $wizardStore.estimationLog;

	let targetImage: string | null = null;
	let targetObjectUrl: string | null = null;
	let lastTargetPath: string | null = null;

	$: inputData = $wizardStore.inputData;
	$: cameraParams = $wizardStore.cameraParams;
	$: matchingParams = $wizardStore.matchingParams;
	$: simulationImage = $wizardStore.estimationSimulation;
	$: estimationLog = $wizardStore.estimationLog;

	// Restore options from store when navigating back to this page
	$: storedEstimationParams = $wizardStore.estimationParams;
	let paramsInitialized = false;
	$: if (storedEstimationParams && !paramsInitialized) {
		optimizer = storedEstimationParams.optimizer;
		twoStage = storedEstimationParams.two_stage ?? defaultTwoStage;
		optimizePosition = storedEstimationParams.optimize_position ?? defaultOptimizePosition;
		optimizeOrientation = storedEstimationParams.optimize_orientation ?? defaultOptimizeOrientation;
		optimizeFov = storedEstimationParams.optimize_fov ?? defaultOptimizeFov;
		optimizeDistortion = storedEstimationParams.optimize_distortion ?? defaultOptimizeDistortion;
		paramsInitialized = true;
	}
	$: if (optimizeDistortion) {
		twoStage = true;
	}

	function resetState() {
		hasError = false;
		errorMessage = '';
	}

	async function fetchTargetImageFull(path: string): Promise<void> {
		try {
			const response = await fetch(`${api.getBaseUrl()}/api/files/image/full`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path })
			});
			if (!response.ok) return;
			const blob = await response.blob();
			if (targetObjectUrl) {
				URL.revokeObjectURL(targetObjectUrl);
			}
			targetObjectUrl = URL.createObjectURL(blob);
			targetImage = targetObjectUrl;
		} catch (err) {
			console.error('Failed to load target image:', err);
		}
	}

	// Always fetch full-size target image for accurate comparison with simulation
	$: {
		const path = inputData.targetImage?.path ?? null;
		if (path && path !== lastTargetPath) {
			lastTargetPath = path;
			targetImage = null;
			void fetchTargetImageFull(path);
		} else if (!path) {
			if (targetObjectUrl) {
				URL.revokeObjectURL(targetObjectUrl);
				targetObjectUrl = null;
			}
			targetImage = null;
			lastTargetPath = null;
		}
	}

	async function runEstimation() {
		resetState();

		if (!inputData.dsm || !inputData.ortho || !inputData.targetImage || !cameraParams) {
			hasError = true;
			errorMessage = t('error.missingData');
			return;
		}

		if (!(optimizePosition || optimizeOrientation || optimizeFov || optimizeDistortion)) {
			hasError = true;
			errorMessage = t('error.noTargetSelected');
			return;
		}

		isRunning = true;
		estimationLog = [];
		simulationImage = null;

		// Invalidate subsequent step (Step 5) when re-running estimation
		wizardStore.invalidateFromStep(4);
		wizardStore.setEstimationResult({ simulation: null, log: [], estimatedParams: null });

		const effectiveTwoStage = twoStage || optimizeDistortion;

		// Save current estimation parameters
		// min_gcp_distance uses simulation_min_distance from matching step
		const currentEstimationParams: EstimationParams = {
			optimizer,
			min_gcp_distance: matchingParams?.simulation_min_distance ?? 100,
			two_stage: effectiveTwoStage,
			optimize_position: optimizePosition,
			optimize_orientation: optimizeOrientation,
			optimize_fov: optimizeFov,
			optimize_distortion: optimizeDistortion
		};

		try {
			// Use matching parameters from Step 3 if available
			// Convert 'none' to undefined for backend compatibility
			const resizeFromMatch = matchingParams?.resize;
			const request: EstimateRequest = {
				dsm_path: inputData.dsm.path,
				ortho_path: inputData.ortho.path,
				target_image_path: inputData.targetImage.path,
				camera_params: cameraParams,
				optimizer: optimizer,
				min_gcp_distance: matchingParams?.simulation_min_distance ?? 100,
				match_id: matchingParams?.match_id,
				two_stage: effectiveTwoStage,
				// Pass matching parameters from Step 3
				matching_method: matchingParams?.matching_method,
				resize: resizeFromMatch === 'none' ? undefined : resizeFromMatch,
				threshold: matchingParams?.threshold,
				outlier_filter: matchingParams?.outlier_filter,
				spatial_thin_grid: matchingParams?.spatial_thin_grid,
				spatial_thin_selection: matchingParams?.spatial_thin_selection,
				surface_distance: matchingParams?.surface_distance,
				simulation_min_distance: matchingParams?.simulation_min_distance,
				optimize_position: optimizePosition,
				optimize_orientation: optimizeOrientation,
				optimize_fov: optimizeFov,
				optimize_distortion: optimizeDistortion
			};

			const response = await api.post<EstimateResponse>('/api/georectify/estimate', request, {
				timeout: ESTIMATION_TIMEOUT_MS
			});

			simulationImage = `data:image/png;base64,${response.simulation_base64}`;
			estimationLog = response.log ?? [];
			wizardStore.setEstimationResult({
				simulation: simulationImage,
				log: estimationLog,
				estimatedParams: response.optimized_params ?? null,
				params: currentEstimationParams
			});

			// Update project with optimized camera parameters
			const projectId = $wizardStore.projectId;
			if (projectId && response.optimized_params) {
				try {
					await api.put(`/api/projects/${projectId}`, {
						camera_params: {
							initial: cameraParams,
							optimized: response.optimized_params
						}
					});
				} catch (updateError) {
					console.error('Failed to update project with optimized params:', updateError);
				}
			}

			wizardStore.completeStep(3);
		} catch (err) {
			hasError = true;
			errorMessage = err instanceof Error ? err.message : t('error.estimationFailed');
		} finally {
			isRunning = false;
		}
	}

	function goBack() {
		wizardStore.prevStep();
		goto('/georectify/steps/processing');
	}

	function goNext() {
		wizardStore.nextStep();
		goto('/georectify/steps/export');
	}

	onDestroy(() => {
		if (targetObjectUrl) {
			URL.revokeObjectURL(targetObjectUrl);
		}
	});
</script>

<svelte:head>
	<title>{t('estimation.title')} - ALPROJ</title>
</svelte:head>

<div class="max-w-5xl mx-auto p-6">
	<h1 class="text-2xl font-bold text-gray-900 mb-6">{t('estimation.title')}</h1>

	<Card title={t('estimation.options')}>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<div>
				<label class="block text-sm font-medium text-gray-700 mb-1">{t('estimation.optimizer')}</label>
				<select
					bind:value={optimizer}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				>
					<option value="cma">{t('optimization.cma.label')}</option>
					<option value="lsq">{t('optimization.lsq.label')}</option>
				</select>
			</div>
			<div class="flex items-center">
				<label class="flex items-center gap-2 text-sm text-gray-700">
					<input
						type="checkbox"
						bind:checked={twoStage}
						disabled={optimizeDistortion}
						class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
					/>
					{t('estimation.twoStage')}
				</label>
				{#if optimizeDistortion}
					<p class="mt-1 text-xs text-gray-500">
						{t('estimation.twoStageAutoEnabled')}
					</p>
				{/if}
			</div>
			<div class="md:col-span-2">
				<label class="block text-sm font-medium text-gray-700 mb-2">
					{t('estimation.optimizeTargets')}
				</label>
				<div class="grid grid-cols-2 gap-3 text-sm text-gray-700">
					<label class="flex items-center gap-2">
						<input
							type="checkbox"
							bind:checked={optimizePosition}
							class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
						/>
						{t('estimation.optimizePosition')}
					</label>
					<label class="flex items-center gap-2">
						<input
							type="checkbox"
							bind:checked={optimizeOrientation}
							class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
						/>
						{t('estimation.optimizeOrientation')}
					</label>
					<label class="flex items-center gap-2">
						<input
							type="checkbox"
							bind:checked={optimizeFov}
							class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
						/>
						{t('estimation.optimizeFov')}
					</label>
					<label class="flex items-center gap-2">
						<input
							type="checkbox"
							bind:checked={optimizeDistortion}
							class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
						/>
						{t('estimation.optimizeDistortion')}
					</label>
				</div>
			</div>
		</div>

		<div class="mt-4 space-y-1 text-xs text-gray-500">
			<p>
				{t('estimation.cmaDescription')}
			</p>
		</div>

		<svelte:fragment slot="footer">
			<div class="flex justify-between">
				<Button variant="secondary" on:click={goBack}>
					{t('common.back')}
				</Button>
				<Button variant="primary" on:click={runEstimation} loading={isRunning}>
					{isRunning ? t('estimation.running') : t('estimation.run')}
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
					<h3 class="text-sm font-medium text-red-800">{t('estimation.error')}</h3>
					<p class="mt-1 text-sm text-red-700">{errorMessage}</p>
				</div>
			</div>
		</div>
	{/if}

	{#if simulationImage}
		<div class="mt-6">
			<Card title={t('estimation.simulationVsTarget')}>
				{#if targetImage}
					<ImageCompare original={targetImage} processed={simulationImage} />
				{:else}
					<p class="text-sm text-gray-500">{t('estimation.targetNotAvailable')}</p>
				{/if}
				{#if estimationLog.length > 0}
					<div class="mt-4">
						<ProcessLog logs={estimationLog} />
					</div>
				{/if}
				<svelte:fragment slot="footer">
					<div class="flex justify-between">
						<Button variant="secondary" on:click={runEstimation} loading={isRunning}>
							{t('estimation.rerun')}
						</Button>
						<Button variant="primary" on:click={goNext}>
							{t('estimation.nextGeotiff')}
						</Button>
					</div>
				</svelte:fragment>
			</Card>
		</div>
	{/if}
</div>
