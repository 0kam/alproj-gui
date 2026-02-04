<!--
  Home Page for ALPROJ GUI

  Displays a welcome message and provides quick actions:
  - Create a new georectification project
  - Open an existing project file

  Backend connection status is shown at the bottom.
  Recovery dialog appears when unsaved projects are detected.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { api } from '$lib/services/api';
	import { openProjectDialog } from '$lib/services/file-dialog';
	import { Button, Card, RecoveryDialog } from '$lib/components/common';
	import { projectStore, recoveryFiles, type RecoveryFile } from '$lib/stores';

	// Backend connection state
	let backendConnected = false;
	let checkingConnection = true;
	let initialConnectionAttempts = 0;
	const MAX_INITIAL_ATTEMPTS = 30; // Try for up to 60 seconds (30 * 2s interval)

	// Recovery dialog state
	let showRecoveryDialog = false;
	let recoveryLoading = false;

	// Check backend connection and recovery files on mount
	onMount(() => {
		// Initial connection check with retry logic for startup
		checkInitialConnection();

		return () => {
			// Cleanup handled by interval clearing in checkInitialConnection
		};
	});

	async function checkInitialConnection() {
		checkingConnection = true;
		initialConnectionAttempts = 0;

		// Retry with 2 second intervals until connected or max attempts reached
		const retryInterval = setInterval(async () => {
			initialConnectionAttempts++;

			try {
				backendConnected = await api.healthCheck();
				if (backendConnected) {
					// Connected! Stop retrying
					clearInterval(retryInterval);
					checkingConnection = false;
					checkRecoveryFiles();

					// Set up periodic health check for subsequent monitoring
					const monitorInterval = setInterval(async () => {
						try {
							backendConnected = await api.healthCheck();
						} catch {
							backendConnected = false;
						}
					}, 10000);

					// Store cleanup function (handled by component destroy)
					return () => clearInterval(monitorInterval);
				}
			} catch {
				backendConnected = false;
			}

			// Check if we've exceeded max attempts
			if (initialConnectionAttempts >= MAX_INITIAL_ATTEMPTS) {
				clearInterval(retryInterval);
				checkingConnection = false;
			}
		}, 2000);

		// Do an immediate first check
		try {
			backendConnected = await api.healthCheck();
			if (backendConnected) {
				clearInterval(retryInterval);
				checkingConnection = false;
				checkRecoveryFiles();

				// Set up periodic health check
				setInterval(async () => {
					try {
						backendConnected = await api.healthCheck();
					} catch {
						backendConnected = false;
					}
				}, 10000);
			}
		} catch {
			// First attempt failed, continue with retry interval
		}
	}

	async function checkRecoveryFiles() {
		const files = await projectStore.checkRecoveryFiles();
		if (files.length > 0) {
			showRecoveryDialog = true;
		}
	}

	async function handleNewProject() {
		try {
			const project = await projectStore.createProject('Untitled Project');
			// Navigate to the wizard
			goto('/georectify/steps/data-input');
		} catch (error) {
			console.error('Failed to create project:', error);
		}
	}

	async function handleOpenProject() {
		try {
			const path = await openProjectDialog();
			if (path) {
				await projectStore.openProjectFile(path);
				// Navigate to the wizard
				goto('/georectify/steps/data-input');
			}
		} catch (error) {
			console.error('Failed to open project:', error);
		}
	}

	async function handleRecover(event: CustomEvent<RecoveryFile>) {
		const file = event.detail;
		recoveryLoading = true;
		try {
			await projectStore.recoverProject(file.path);
			showRecoveryDialog = false;
			goto('/georectify/steps/data-input');
		} catch (error) {
			console.error('Failed to recover project:', error);
		} finally {
			recoveryLoading = false;
		}
	}

	async function handleDiscard(event: CustomEvent<RecoveryFile>) {
		const file = event.detail;
		await projectStore.discardRecovery(file.path);
		if ($recoveryFiles.length === 0) {
			showRecoveryDialog = false;
		}
	}

	async function handleRecoverAll() {
		// Recover the first file and close dialog
		if ($recoveryFiles.length > 0) {
			await handleRecover({ detail: $recoveryFiles[0] } as CustomEvent<RecoveryFile>);
		}
	}

	async function handleDiscardAll() {
		for (const file of $recoveryFiles) {
			await projectStore.discardRecovery(file.path);
		}
		showRecoveryDialog = false;
	}

	function handleCloseRecoveryDialog() {
		showRecoveryDialog = false;
	}
</script>

<div class="home-container">
	<section class="hero">
		<h1 class="hero-title">{t('home.welcome')}</h1>
		<p class="hero-subtitle">{t('home.description')}</p>
	</section>

	<section class="actions">
		<Card>
			<svelte:fragment slot="header">
				<h2 class="card-title">{t('home.newProject')}</h2>
			</svelte:fragment>

			<p class="card-description">
				{t('dataInput.dsmDescription')}
			</p>

			<svelte:fragment slot="footer">
				<Button
					variant="primary"
					fullWidth
					disabled={!backendConnected}
					on:click={handleNewProject}
				>
					{t('home.newProject')}
				</Button>
			</svelte:fragment>
		</Card>

		<Card>
			<svelte:fragment slot="header">
				<h2 class="card-title">{t('home.openProject')}</h2>
			</svelte:fragment>

			<p class="card-description">
				{t('project.open')}
			</p>

			<svelte:fragment slot="footer">
				<Button
					variant="secondary"
					fullWidth
					disabled={!backendConnected}
					on:click={handleOpenProject}
				>
					{t('dataInput.selectFile')}
				</Button>
			</svelte:fragment>
		</Card>
	</section>

	<footer class="status-footer">
		<div class="status-item">
			<span class="status-label">{t('status.backend')}:</span>
			{#if checkingConnection}
				<span class="status-indicator connecting">{t('status.connecting')}</span>
			{:else if backendConnected}
				<span class="status-indicator online">{t('status.connected')}</span>
			{:else}
				<span class="status-indicator offline">{t('status.disconnected')}</span>
			{/if}
		</div>
	</footer>
</div>

<!-- Recovery Dialog -->
<RecoveryDialog
	recoveryFiles={$recoveryFiles}
	open={showRecoveryDialog}
	loading={recoveryLoading}
	on:recover={handleRecover}
	on:discard={handleDiscard}
	on:recoverAll={handleRecoverAll}
	on:discardAll={handleDiscardAll}
	on:close={handleCloseRecoveryDialog}
/>

<style>
	.home-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 2rem;
		gap: 2rem;
		min-height: calc(100vh - 3.5rem);
	}

	.hero {
		text-align: center;
		padding: 2.5rem 2rem;
		max-width: 600px;
		background: var(--glass);
		border: 1px solid var(--line);
		border-radius: 1.25rem;
		box-shadow: var(--shadow-soft);
		backdrop-filter: blur(8px);
	}

	.hero-title {
		font-size: 2rem;
		color: var(--brand-700);
		margin: 0 0 0.75rem 0;
		font-weight: 700;
	}

	.hero-subtitle {
		color: var(--ink-500);
		font-size: 1.1rem;
		margin: 0;
		line-height: 1.5;
	}

	.actions {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.5rem;
		max-width: 700px;
		width: 100%;
	}

	.card-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--ink-900);
		margin: 0;
	}

	.card-description {
		color: var(--ink-500);
		font-size: 0.9rem;
		line-height: 1.6;
		margin: 0;
	}

	.status-footer {
		margin-top: auto;
		padding: 1.5rem;
	}

	.status-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.status-label {
		color: var(--ink-500);
	}

	.status-indicator {
		padding: 0.25rem 0.75rem;
		border-radius: 9999px;
		font-weight: 500;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-indicator.online {
		background-color: #e3f4ea;
		color: #1d6b4f;
	}

	.status-indicator.offline {
		background-color: #fbe7e9;
		color: #b4232c;
	}

	.status-indicator.connecting {
		background-color: #e3eef8;
		color: var(--brand-700);
	}
</style>
