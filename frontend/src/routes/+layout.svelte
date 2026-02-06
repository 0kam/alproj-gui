<!--
  Root Layout for ALPROJ GUI

  Provides:
  - Application header with logo and save button
  - Keyboard shortcuts (Ctrl+S for save)
  - Main content area
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import '../app.css';
	import { t } from '$lib/i18n';
	import { saveProjectDialog } from '$lib/services/file-dialog';
	import {
		projectStore,
		currentProject,
		currentFilePath,
		hasUnsavedChanges,
		projectSaving,
		wizardStore
	} from '$lib/stores';
	import type { WizardState } from '$lib/stores';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

	// Handle keyboard shortcuts
	function handleKeydown(event: KeyboardEvent) {
		const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
		const modifier = isMac ? event.metaKey : event.ctrlKey;

		if (!modifier) return;

		if (event.key === 's' || event.key === 'S') {
			event.preventDefault();
			handleSave();
		}
	}

	let lastProjectId: string | null = null;
	let lastWizardSnapshot: string | null = null;
	let ignoreWizardChange = false;
	let unsubscribeWizard: (() => void) | null = null;

	function buildWizardSnapshot(state: WizardState): string {
		const snapshot = {
			input_data: {
				dsm: state.inputData.dsm ?? null,
				ortho: state.inputData.ortho ?? null,
				target_image: state.inputData.targetImage ?? null
			},
			camera_simulation: state.cameraSimulation ?? null,
			camera_params: state.cameraParams
				? { initial: state.cameraParams, optimized: state.estimatedParams ?? null }
				: state.estimatedParams
					? { optimized: state.estimatedParams }
					: null,
			process_result: state.processResult ?? null,
			matching_result: {
				match_plot_len: state.matchingPlot?.length ?? 0,
				log: state.matchingLog ?? [],
				match_count: state.matchCount ?? null,
				params: state.matchingParams ?? null
			},
			estimation_result: {
				simulation_len: state.estimationSimulation?.length ?? 0,
				log: state.estimationLog ?? [],
				params: state.estimationParams ?? null,
				optimized_params: state.estimatedParams ?? null
			}
		};

		return JSON.stringify(snapshot);
	}

	onMount(() => {
		unsubscribeWizard = wizardStore.subscribe((state) => {
			const project = get(currentProject);
			if (!project) {
				lastWizardSnapshot = null;
				return;
			}

			const snapshot = buildWizardSnapshot(state);
			if (ignoreWizardChange || lastWizardSnapshot === null) {
				ignoreWizardChange = false;
				lastWizardSnapshot = snapshot;
				return;
			}

			if (snapshot !== lastWizardSnapshot) {
				projectStore.markUnsaved();
				lastWizardSnapshot = snapshot;
			}
		});
		return () => {
			unsubscribeWizard?.();
		};
	});

	$: {
		const project = $currentProject;
		const projectId = project?.id ?? null;
		if (projectId !== lastProjectId) {
			lastProjectId = projectId;
			ignoreWizardChange = true;
			lastWizardSnapshot = project ? buildWizardSnapshot(wizardStore.getState()) : null;
		}
	}

	async function handleSave() {
		if (!$currentProject) return;

		try {
			if ($currentFilePath) {
				// File already exists, overwrite
				await projectStore.saveProject();
			} else {
				// No file path yet, prompt for save location
				const path = await saveProjectDialog($currentProject.name);
				if (path) {
					await projectStore.saveProject(path);
				}
			}
		} catch (error) {
			console.error('Failed to save project:', error);
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="app-container">
	<header class="app-header">
		<div class="header-content">
			<a href="/" class="app-logo">
				<h1 class="app-title">{t('app.name')}</h1>
			</a>
			<nav class="app-nav">
				<!-- Language switcher -->
				<LanguageSwitcher />

				<!-- Project indicator and save button -->
				{#if $currentProject}
					<div class="project-indicator">
						<span class="project-name">{$currentProject.name}</span>
						{#if $hasUnsavedChanges}
							<span class="unsaved-indicator" title={t('project.unsavedChanges')}>*</span>
						{/if}
						{#if $projectSaving}
							<span class="saving-indicator">{t('common.save')}...</span>
						{/if}
					</div>
					<button
						class="save-button"
						on:click={handleSave}
						disabled={$projectSaving}
						title={t('menu.save') + ' (Ctrl+S)'}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
							<polyline points="17 21 17 13 7 13 7 21"></polyline>
							<polyline points="7 3 7 8 15 8"></polyline>
						</svg>
						<span class="save-label">{t('common.save')}</span>
					</button>
				{/if}
			</nav>
		</div>
	</header>

	<main class="main-content">
		<slot />
	</main>
</div>

<style>
	:global(html, body) {
		margin: 0;
		padding: 0;
		height: 100%;
	}

	.app-container {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		position: relative;
		z-index: 1;
	}

	.app-header {
		background: rgba(255, 255, 255, 0.82);
		color: var(--ink-900);
		border-bottom: 1px solid var(--line);
		backdrop-filter: blur(10px);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-content {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 1.5rem;
		height: 3.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.app-logo {
		text-decoration: none;
		color: inherit;
	}

	.app-logo:hover {
		opacity: 0.9;
	}

	.app-title {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0;
		letter-spacing: 0.03em;
		color: var(--brand-700);
	}

	.app-nav {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	/* Project Indicator */
	.project-indicator {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.375rem 0.75rem;
		background-color: rgba(11, 35, 51, 0.05);
		border: 1px solid rgba(11, 35, 51, 0.12);
		border-radius: 0.5rem;
		font-size: 0.875rem;
		max-width: 200px;
	}

	.project-name {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.unsaved-indicator {
		color: #f59f0b;
		font-weight: 700;
		font-size: 1rem;
	}

	.saving-indicator {
		font-size: 0.75rem;
		color: var(--brand-500);
		animation: pulse 1.5s ease-in-out infinite;
	}

	/* Save Button */
	.save-button {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.375rem 0.75rem;
		background-color: rgba(255, 255, 255, 0.85);
		border: 1px solid rgba(11, 35, 51, 0.12);
		border-radius: 0.5rem;
		color: var(--brand-700);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.save-button:hover:not(:disabled) {
		background-color: rgba(255, 255, 255, 1);
		box-shadow: 0 6px 16px rgba(11, 35, 51, 0.1);
	}

	.save-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.save-label {
		display: none;
	}

	@media (min-width: 640px) {
		.save-label {
			display: inline;
		}
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}
</style>
