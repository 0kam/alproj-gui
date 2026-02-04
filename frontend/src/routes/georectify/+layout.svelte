<!--
  Georectify Wizard Layout

  Provides a sidebar with step navigation and a main content area.
  The sidebar displays the wizard steps with visual indicators for
  current, completed, and pending states.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { t } from '$lib/i18n';
	import { Button } from '$lib/components/common';
	import {
		wizardStore,
		steps,
		currentStep,
		progressPercent
	} from '$lib/stores/wizard';
	import { projectStore } from '$lib/stores';

	// Navigate to step path
	function navigateToStep(index: number) {
		const state = wizardStore.getState();
		const step = state.steps[index];

		// Only allow navigation to completed steps or current step
		if (index <= state.currentStep || step.completed) {
			wizardStore.goToStep(index);
			goto(step.path);
		}
	}

	// Handle cancel / return to home
	function handleCancel() {
		projectStore.closeProject();
		goto('/');
	}

	// Reactive step statuses - computed whenever stores change
	$: stepStatuses = $steps.map((step, index) => {
		if (index === $currentStep) return 'current';
		if (step.completed) return 'completed';
		return 'pending';
	}) as ('current' | 'completed' | 'pending')[];

	// Sync step state with route path (e.g. on direct navigation or refresh)
	$: if ($page.url.pathname.startsWith('/georectify/steps/')) {
		const routeIndex = $steps.findIndex((step) => step.path === $page.url.pathname);
		if (routeIndex >= 0 && routeIndex !== $currentStep) {
			wizardStore.goToStep(routeIndex);
		}
	}
</script>

<div class="wizard-container">
	<!-- Sidebar with step list -->
	<aside class="wizard-sidebar">
		<div class="sidebar-header">
			<h2 class="sidebar-title">{t('georectify.title')}</h2>
			<div class="progress-bar">
				<div class="progress-fill" style="width: {$progressPercent}%"></div>
			</div>
		</div>

		<nav class="step-list">
			{#each $steps as step, index (step.id)}
				<button
					class="step-item step-{stepStatuses[index]}"
					class:clickable={index <= $currentStep || step.completed}
					on:click={() => navigateToStep(index)}
					disabled={index > $currentStep && !step.completed}
				>
					<div class="step-indicator">
						{#if stepStatuses[index] === 'completed'}
							<svg
								class="check-icon"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="3"
							>
								<polyline points="20 6 9 17 4 12"></polyline>
							</svg>
						{:else}
							<span class="step-number">{index + 1}</span>
						{/if}
					</div>
					<span class="step-title">{t(step.title)}</span>
				</button>
			{/each}
		</nav>

		<div class="sidebar-footer">
			<Button variant="ghost" size="sm" on:click={handleCancel}>
				{t('common.cancel')}
			</Button>
		</div>
	</aside>

	<!-- Main content area -->
	<div class="wizard-main">
		<div class="wizard-content">
			<slot />
		</div>
	</div>
</div>

<style>
	.wizard-container {
		display: flex;
		height: 100%;
		min-height: calc(100vh - 3.5rem);
	}

	/* Sidebar styles */
	.wizard-sidebar {
		width: 280px;
		background-color: var(--glass-strong);
		border-right: 1px solid var(--line);
		backdrop-filter: blur(10px);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
	}

	.sidebar-header {
		padding: 1.5rem;
		border-bottom: 1px solid var(--line);
	}

	.sidebar-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--brand-700);
		margin: 0 0 1rem 0;
	}

	.progress-bar {
		height: 6px;
		background-color: var(--brand-200);
		border-radius: 3px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, var(--brand-700) 0%, var(--brand-500) 100%);
		transition: width 0.3s ease;
	}

	/* Step list styles */
	.step-list {
		flex: 1;
		padding: 1rem 0;
		overflow-y: auto;
	}

	.step-item {
		display: flex;
		align-items: center;
		width: 100%;
		padding: 0.875rem 1.5rem;
		border: none;
		background: none;
		text-align: left;
		cursor: default;
		transition: background-color 0.2s;
	}

	.step-item.clickable {
		cursor: pointer;
	}

	.step-item.clickable:hover {
		background-color: rgba(11, 35, 51, 0.04);
	}

	.step-item:disabled {
		opacity: 0.6;
	}

	.step-indicator {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-right: 0.75rem;
		font-size: 0.875rem;
		font-weight: 600;
		transition: all 0.2s;
	}

	/* Step status styles */
	.step-pending .step-indicator {
		background-color: var(--brand-200);
		color: var(--brand-700);
	}

	.step-current .step-indicator {
		background-color: var(--brand-700);
		color: #ffffff;
		box-shadow: 0 6px 14px rgba(11, 99, 168, 0.35);
	}

	.step-completed .step-indicator {
		background-color: #f17847;
		color: #ffffff;
		box-shadow: 0 6px 14px rgba(241, 120, 71, 0.3);
	}

	.step-number {
		line-height: 1;
	}

	.check-icon {
		width: 16px;
		height: 16px;
	}

	.step-title {
		font-size: 0.9375rem;
		color: var(--ink-700);
	}

	.step-current .step-title {
		font-weight: 600;
		color: var(--brand-700);
	}

	.step-pending .step-title {
		color: #93a4b7;
	}

	.sidebar-footer {
		padding: 1rem 1.5rem;
		border-top: 1px solid var(--line);
	}

	/* Main content styles */
	.wizard-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		background: transparent;
		overflow: hidden;
	}

	.wizard-content {
		flex: 1;
		padding: 2rem;
		overflow-y: auto;
	}

	.wizard-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 2rem;
		background-color: var(--glass-strong);
		border-top: 1px solid var(--line);
		backdrop-filter: blur(10px);
	}

	.footer-left,
	.footer-right {
		display: flex;
		gap: 0.75rem;
	}

	.nav-arrow {
		display: inline-block;
		margin: 0 0.25rem;
	}
</style>
