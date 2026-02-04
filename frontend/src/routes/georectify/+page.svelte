<!--
  Georectify Wizard Main Page

  Entry point for the georectification wizard.
  Redirects to the first step (data-input) on load.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { wizardStore } from '$lib/stores/wizard';

	onMount(() => {
		// Reset wizard state and redirect to first step
		wizardStore.resetWizard();
		goto('/georectify/steps/data-input', { replaceState: true });
	});
</script>

<div class="loading-container">
	<div class="loading-spinner"></div>
	<p class="loading-text">{t('common.loading')}</p>
</div>

<style>
	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 300px;
		gap: 1rem;
	}

	.loading-spinner {
		width: 40px;
		height: 40px;
		border: 3px solid #e5e7eb;
		border-top-color: #2563eb;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		color: #6b7280;
		font-size: 0.9375rem;
	}
</style>
