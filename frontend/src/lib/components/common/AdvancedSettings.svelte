<!--
  Advanced Settings Panel Component (T063-T065)

  Provides advanced configuration options for georectification:
  - Matching algorithm selection (akaze/sift/superpoint-lightglue/minima-roma)
  - Optimization parameters (optimizer, max_generations, min_gcp_distance)
  - GCP table integration
  - Reprocess button

  Usage:
    <AdvancedSettings
      {gcps}
      {options}
      processing={false}
      on:gcpToggle={handleGcpToggle}
      on:gcpSelect={handleGcpSelect}
      on:optionsChange={handleOptionsChange}
      on:reprocess={handleReprocess}
    />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { GCP, ProcessOptions, MatchingMethod, OptimizerType } from '$lib/types';
	import GcpTable from './GcpTable.svelte';
	import Button from './Button.svelte';
	import { t } from '$lib/i18n';

	/** List of Ground Control Points */
	export let gcps: GCP[] = [];
	/** Current process options */
	export let options: ProcessOptions = {};
	/** Whether reprocessing is in progress */
	export let processing: boolean = false;
	/** Selected GCP ID */
	export let selectedGcpId: number | null = null;
	/** High residual threshold for GCP table */
	export let highResidualThreshold: number = 3;

	const dispatch = createEventDispatcher<{
		gcpToggle: { id: number; enabled: boolean };
		gcpSelect: { id: number };
		optionsChange: { options: ProcessOptions };
		reprocess: void;
	}>();

	// Matching method options (labels and descriptions are retrieved via t() in template)
	const matchingMethods: { value: MatchingMethod; labelKey: string; descriptionKey: string }[] = [
		{
			value: 'akaze',
			labelKey: 'matching.akaze.label',
			descriptionKey: 'matching.akaze.description'
		},
		{
			value: 'sift',
			labelKey: 'matching.sift.label',
			descriptionKey: 'matching.sift.description'
		},
		{
			value: 'superpoint-lightglue',
			labelKey: 'matching.superpoint.label',
			descriptionKey: 'matching.superpoint.description'
		},
		{
			value: 'minima-roma',
			labelKey: 'matching.minima.label',
			descriptionKey: 'matching.minima.description'
		}
	];

	// Optimizer options (labels and descriptions are retrieved via t() in template)
	const optimizers: { value: OptimizerType; labelKey: string; descriptionKey: string }[] = [
		{
			value: 'cma',
			labelKey: 'optimization.cma.label',
			descriptionKey: 'optimization.cma.description'
		},
		{
			value: 'lsq',
			labelKey: 'optimization.lsq.label',
			descriptionKey: 'optimization.lsq.description'
		}
	];

	// Local state bound to inputs
	let matchingMethod: MatchingMethod = options.matching_method ?? 'superpoint-lightglue';
	let optimizer: OptimizerType = options.optimizer ?? 'cma';
	let maxGenerations: number = options.max_generations ?? 100;

	// Section expand states
	let expandedSections = {
		matching: true,
		optimization: false,
		gcps: true
	};

	function toggleSection(section: keyof typeof expandedSections): void {
		expandedSections[section] = !expandedSections[section];
	}

	// Update options when any setting changes
	function updateOptions(): void {
		const newOptions: ProcessOptions = {
			matching_method: matchingMethod,
			optimizer: optimizer,
			max_generations: maxGenerations
		};
		dispatch('optionsChange', { options: newOptions });
	}

	// Watch for changes and emit
	$: {
		matchingMethod;
		optimizer;
		maxGenerations;
		updateOptions();
	}

	function handleGcpToggle(event: CustomEvent<{ id: number; enabled: boolean }>): void {
		dispatch('gcpToggle', event.detail);
	}

	function handleGcpSelect(event: CustomEvent<{ id: number }>): void {
		dispatch('gcpSelect', event.detail);
	}

	function handleReprocess(): void {
		dispatch('reprocess');
	}

	// Calculate enabled/disabled GCP counts
	$: enabledGcpCount = gcps.filter((g) => g.enabled).length;
	$: disabledGcpCount = gcps.length - enabledGcpCount;
	$: hasChanges =
		options.matching_method !== matchingMethod ||
		options.optimizer !== optimizer ||
		options.max_generations !== maxGenerations;
</script>

<div class="advanced-settings space-y-4">
	<!-- Matching Algorithm Section -->
	<div class="border border-gray-200 rounded-lg overflow-hidden">
		<button
			type="button"
			class="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex justify-between items-center text-left transition-colors"
			on:click={() => toggleSection('matching')}
		>
			<span class="font-medium text-gray-900">{t('matching.method')}</span>
			<svg
				class="w-5 h-5 text-gray-500 transform transition-transform duration-200
					{expandedSections.matching ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		{#if expandedSections.matching}
			<div class="p-4 space-y-3">
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					{#each matchingMethods as method}
						<label
							class="relative flex cursor-pointer rounded-lg border p-4 transition-all
								{matchingMethod === method.value
								? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
								: 'border-gray-200 hover:border-gray-300'}"
						>
							<input
								type="radio"
								name="matchingMethod"
								value={method.value}
								bind:group={matchingMethod}
								class="sr-only"
							/>
							<div class="flex flex-col">
								<span class="font-medium text-gray-900">{t(method.labelKey)}</span>
								<span class="text-xs text-gray-500 mt-1">{t(method.descriptionKey)}</span>
							</div>
							{#if matchingMethod === method.value}
								<svg
									class="absolute top-2 right-2 h-5 w-5 text-primary-600"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</label>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- Optimization Parameters Section -->
	<div class="border border-gray-200 rounded-lg overflow-hidden">
		<button
			type="button"
			class="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex justify-between items-center text-left transition-colors"
			on:click={() => toggleSection('optimization')}
		>
			<span class="font-medium text-gray-900">{t('optimization.title')}</span>
			<svg
				class="w-5 h-5 text-gray-500 transform transition-transform duration-200
					{expandedSections.optimization ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		{#if expandedSections.optimization}
			<div class="p-4 space-y-4">
				<!-- Optimizer Selection -->
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-2">{t('estimation.optimizer')}</label>
					<div class="grid grid-cols-2 gap-3">
						{#each optimizers as opt}
							<label
								class="relative flex cursor-pointer rounded-lg border p-3 transition-all
									{optimizer === opt.value
									? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
									: 'border-gray-200 hover:border-gray-300'}"
							>
								<input
									type="radio"
									name="optimizer"
									value={opt.value}
									bind:group={optimizer}
									class="sr-only"
								/>
								<div class="flex flex-col">
									<span class="font-medium text-gray-900 text-sm">{t(opt.labelKey)}</span>
									<span class="text-xs text-gray-500">{t(opt.descriptionKey)}</span>
								</div>
							</label>
						{/each}
					</div>
				</div>

				<!-- Max Generations (only for CMA-ES) -->
				{#if optimizer === 'cma'}
					<div>
						<label for="maxGenerations" class="block text-sm font-medium text-gray-700 mb-1">
							{t('estimation.maxGenerations')}
							<span class="text-gray-400 font-normal">({maxGenerations})</span>
						</label>
						<input
							type="range"
							id="maxGenerations"
							min="10"
							max="500"
							step="10"
							bind:value={maxGenerations}
							class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
						/>
						<div class="flex justify-between text-xs text-gray-400 mt-1">
							<span>10 ({t('optimization.maxGenerationsSlider.fast')})</span>
							<span>500 ({t('optimization.maxGenerationsSlider.precise')})</span>
						</div>
					</div>
				{/if}

			</div>
		{/if}
	</div>

	<!-- GCP Table Section -->
	<div class="border border-gray-200 rounded-lg overflow-hidden">
		<button
			type="button"
			class="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex justify-between items-center text-left transition-colors"
			on:click={() => toggleSection('gcps')}
		>
			<span class="font-medium text-gray-900">
				{t('gcp.title')}
				<span class="text-gray-500 font-normal">({enabledGcpCount} / {gcps.length})</span>
			</span>
			<svg
				class="w-5 h-5 text-gray-500 transform transition-transform duration-200
					{expandedSections.gcps ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		{#if expandedSections.gcps}
			<div class="p-4">
				{#if gcps.length > 0}
					<GcpTable
						{gcps}
						editable={!processing}
						selectedId={selectedGcpId}
						{highResidualThreshold}
						on:toggle={handleGcpToggle}
						on:select={handleGcpSelect}
					/>
				{:else}
					<div class="py-8 text-center text-gray-500">
						{t('gcp.noData')}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Reprocess Button -->
	<div class="flex justify-end pt-2">
		<Button
			variant="primary"
			loading={processing}
			disabled={enabledGcpCount < 4}
			on:click={handleReprocess}
		>
			{#if processing}
				{t('advanced.reprocessing')}
			{:else}
				{t('advanced.reprocess')}
			{/if}
		</Button>
	</div>

	{#if enabledGcpCount < 4}
		<p class="text-sm text-red-600 text-right">
			{t('gcp.required')}
		</p>
	{/if}
</div>
