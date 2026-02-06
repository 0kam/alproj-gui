<!--
  CameraParamsForm Component

  A form for editing camera parameters including position and orientation.

  Usage:
    <CameraParamsForm
      value={cameraParams}
      suggestedParams={exifParams}
      on:change={handleChange}
    />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from '$lib/i18n';
	import type { CameraParamsValues } from '$lib/types';

	/** Current camera parameter values */
	export let value: CameraParamsValues;
	/** Suggested parameters from EXIF data */
	export let suggestedParams: Partial<CameraParamsValues> | null = null;
	/** Whether the form is disabled */
	export let disabled: boolean = false;
	/** DSM elevation at the current camera position (for reference) */
	export let dsmElevation: number | null = null;

	const dispatch = createEventDispatcher<{
		change: CameraParamsValues;
	}>();

	// Local copy of values for two-way binding
	let localValue: CameraParamsValues = { ...value };

	// Update local value when prop changes
	$: localValue = { ...value };

	/**
	 * Handle input change and dispatch
	 */
	function handleChange(field: keyof CameraParamsValues, inputValue: string): void {
		const numValue = parseFloat(inputValue);
		if (!isNaN(numValue)) {
			localValue = { ...localValue, [field]: numValue };
			dispatch('change', localValue);
		}
	}

	/**
	 * Apply suggested value for a field
	 */
	function applySuggested(field: keyof CameraParamsValues): void {
		if (suggestedParams && suggestedParams[field] !== undefined) {
			localValue = { ...localValue, [field]: suggestedParams[field] as number };
			dispatch('change', localValue);
		}
	}

	/**
	 * Apply all suggested values
	 */
	function applyAllSuggested(): void {
		if (suggestedParams) {
			localValue = { ...localValue, ...suggestedParams };
			dispatch('change', localValue);
		}
	}

	/**
	 * Check if a suggested value differs from current
	 */
	function hasSuggestion(field: keyof CameraParamsValues): boolean {
		if (!suggestedParams || suggestedParams[field] === undefined) return false;
		return suggestedParams[field] !== localValue[field];
	}

</script>

<div class="camera-params-form">
	<!-- Suggested params banner -->
	{#if suggestedParams && Object.keys(suggestedParams).length > 0}
		<div class="suggested-banner">
			<div class="suggested-banner-content">
				<svg class="suggested-icon" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
						clip-rule="evenodd"
					/>
				</svg>
				<span>{t('advanced.exifSuggestion')}</span>
			</div>
			<button type="button" class="apply-all-btn" on:click={applyAllSuggested} {disabled}>
				{t('advanced.applyAll')}
			</button>
		</div>
	{/if}

	<!-- Position Section -->
	<fieldset class="param-section">
		<legend class="section-title">{t('camera.position')}</legend>
		<div class="param-grid">
			<div class="param-field">
				<label for="param-x">{t('camera.x')}</label>
				<div class="input-wrapper">
					<input
						id="param-x"
						type="number"
						step="0.001"
						value={localValue.x}
						on:input={(e) => handleChange('x', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('x')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.x}"
							on:click={() => applySuggested('x')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="param-field">
				<label for="param-y">{t('camera.y')}</label>
				<div class="input-wrapper">
					<input
						id="param-y"
						type="number"
						step="0.001"
						value={localValue.y}
						on:input={(e) => handleChange('y', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('y')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.y}"
							on:click={() => applySuggested('y')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="param-field">
				<label for="param-z">{t('camera.z')}</label>
				<div class="input-wrapper">
					<input
						id="param-z"
						type="number"
						step="0.1"
						value={localValue.z}
						on:input={(e) => handleChange('z', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('z')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.z}"
							on:click={() => applySuggested('z')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
				{#if dsmElevation !== null}
					<span class="dsm-elevation-hint">DSM: {dsmElevation.toFixed(1)}m (auto: +2m)</span>
				{/if}
			</div>
		</div>
	</fieldset>

	<!-- Orientation Section -->
	<fieldset class="param-section">
		<legend class="section-title">{t('camera.direction')}</legend>
		<div class="param-grid">
			<div class="param-field">
				<label for="param-fov">{t('camera.fov')} (1-180)</label>
				<div class="input-wrapper">
					<input
						id="param-fov"
						type="number"
						min="1"
						max="180"
						step="1"
						value={localValue.fov}
						on:input={(e) => handleChange('fov', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('fov')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.fov}"
							on:click={() => applySuggested('fov')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="param-field">
				<label for="param-pan">{t('advanced.pan')} (0-360)</label>
				<div class="input-wrapper">
					<input
						id="param-pan"
						type="number"
						min="0"
						max="360"
						step="1"
						value={localValue.pan}
						on:input={(e) => handleChange('pan', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('pan')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.pan}"
							on:click={() => applySuggested('pan')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="param-field">
				<label for="param-tilt">{t('camera.tilt')} (-90 to 90)</label>
				<div class="input-wrapper">
					<input
						id="param-tilt"
						type="number"
						min="-90"
						max="90"
						step="1"
						value={localValue.tilt}
						on:input={(e) => handleChange('tilt', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('tilt')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.tilt}"
							on:click={() => applySuggested('tilt')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="param-field">
				<label for="param-roll">{t('camera.roll')} (-180 to 180)</label>
				<div class="input-wrapper">
					<input
						id="param-roll"
						type="number"
						min="-180"
						max="180"
						step="1"
						value={localValue.roll}
						on:input={(e) => handleChange('roll', e.currentTarget.value)}
						{disabled}
					/>
					{#if hasSuggestion('roll')}
						<button
							type="button"
							class="suggestion-btn"
							title="推奨値を適用: {suggestedParams?.roll}"
							on:click={() => applySuggested('roll')}
							{disabled}
						>
							<svg viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</fieldset>

</div>

<style>
	.camera-params-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.suggested-banner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		background-color: #dbeafe;
		border: 1px solid #93c5fd;
		border-radius: 0.5rem;
	}

	.suggested-banner-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #1e40af;
		font-size: 0.875rem;
	}

	.suggested-icon {
		width: 1.25rem;
		height: 1.25rem;
	}

	.apply-all-btn {
		padding: 0.375rem 0.75rem;
		background-color: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background-color 0.2s;
	}

	.apply-all-btn:hover:not(:disabled) {
		background-color: #2563eb;
	}

	.apply-all-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.param-section {
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		padding: 1rem;
		margin: 0;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
		padding: 0 0.5rem;
	}

	.param-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 1rem;
	}

	.param-field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.param-field label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #6b7280;
	}

	.input-wrapper {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.param-field input {
		width: 100%;
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		transition: border-color 0.2s, box-shadow 0.2s;
	}

	.param-field input:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.param-field input:disabled {
		background-color: #f3f4f6;
		cursor: not-allowed;
	}

	.suggestion-btn {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		padding: 0;
		border: none;
		background-color: #dbeafe;
		color: #3b82f6;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: background-color 0.2s;
	}

	.suggestion-btn:hover:not(:disabled) {
		background-color: #bfdbfe;
	}

	.suggestion-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.suggestion-btn svg {
		width: 1rem;
		height: 1rem;
	}

	.dsm-elevation-hint {
		font-size: 0.7rem;
		color: #16a34a;
		font-weight: 500;
		margin-top: 0.125rem;
	}

</style>
