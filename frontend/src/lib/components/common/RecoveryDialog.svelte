<!--
  RecoveryDialog Component

  Displays a modal dialog for recovering unsaved projects.
  Shows at startup when recovery files are detected.

  Features:
  - List of recoverable files with timestamps
  - Recover or discard options for each file
  - Recover all or discard all bulk actions

  Usage:
    <RecoveryDialog
      recoveryFiles={files}
      open={showDialog}
      on:recover={handleRecover}
      on:discard={handleDiscard}
      on:close={handleClose}
    />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from '$lib/i18n';
	import { Button } from '$lib/components/common';
	import type { RecoveryFile } from '$lib/stores/project';

	/** List of recovery files */
	export let recoveryFiles: RecoveryFile[] = [];
	/** Whether the dialog is open */
	export let open: boolean = false;
	/** Whether recovery is in progress */
	export let loading: boolean = false;

	const dispatch = createEventDispatcher<{
		recover: RecoveryFile;
		discard: RecoveryFile;
		recoverAll: void;
		discardAll: void;
		close: void;
	}>();

	/**
	 * Format date for display
	 */
	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return date.toLocaleString('ja-JP', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit'
			});
		} catch {
			return dateStr;
		}
	}

	/**
	 * Handle backdrop click to close
	 */
	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			dispatch('close');
		}
	}

	/**
	 * Handle escape key to close
	 */
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && !loading) {
			dispatch('close');
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<div
		class="dialog-backdrop"
		role="dialog"
		aria-modal="true"
		aria-labelledby="recovery-title"
		on:click={handleBackdropClick}
		on:keydown={handleKeydown}
	>
		<div class="dialog-container">
			<div class="dialog-header">
				<div class="header-icon">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-6 w-6"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
						/>
					</svg>
				</div>
				<div>
					<h2 id="recovery-title" class="dialog-title">{t('recovery.title')}</h2>
					<p class="dialog-subtitle">{t('recovery.description')}</p>
				</div>
			</div>

			<div class="dialog-body">
				{#if recoveryFiles.length === 0}
					<p class="no-files">{t('recovery.noFiles')}</p>
				{:else}
					<ul class="recovery-list">
						{#each recoveryFiles as file (file.path)}
							<li class="recovery-item">
								<div class="file-info">
									<span class="file-name">{file.projectName}</span>
									<span class="file-date">
										{t('recovery.savedAt')}: {formatDate(file.savedAt)}
									</span>
								</div>
								<div class="file-actions">
									<Button
										variant="primary"
										size="sm"
										disabled={loading}
										on:click={() => dispatch('recover', file)}
									>
										{t('recovery.recover')}
									</Button>
									<Button
										variant="ghost"
										size="sm"
										disabled={loading}
										on:click={() => dispatch('discard', file)}
									>
										{t('recovery.discard')}
									</Button>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="dialog-footer">
				{#if recoveryFiles.length > 1}
					<div class="bulk-actions">
						<Button
							variant="primary"
							size="sm"
							disabled={loading}
							on:click={() => dispatch('recoverAll')}
						>
							{t('recovery.recoverAll')}
						</Button>
						<Button
							variant="ghost"
							size="sm"
							disabled={loading}
							on:click={() => dispatch('discardAll')}
						>
							{t('recovery.discardAll')}
						</Button>
					</div>
				{/if}
				<div class="close-action">
					<Button variant="secondary" disabled={loading} on:click={() => dispatch('close')}>
						{t('common.close')}
					</Button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.dialog-backdrop {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}

	.dialog-container {
		background-color: white;
		border-radius: 0.5rem;
		box-shadow:
			0 20px 25px -5px rgba(0, 0, 0, 0.1),
			0 10px 10px -5px rgba(0, 0, 0, 0.04);
		max-width: 32rem;
		width: 100%;
		max-height: calc(100vh - 4rem);
		display: flex;
		flex-direction: column;
	}

	.dialog-header {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1.5rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.header-icon {
		flex-shrink: 0;
		width: 2.5rem;
		height: 2.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: #fef3c7;
		border-radius: 9999px;
		color: #d97706;
	}

	.dialog-title {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
	}

	.dialog-subtitle {
		margin: 0.25rem 0 0;
		font-size: 0.875rem;
		color: #6b7280;
	}

	.dialog-body {
		flex: 1;
		overflow-y: auto;
		padding: 0;
	}

	.no-files {
		padding: 2rem;
		text-align: center;
		color: #6b7280;
	}

	.recovery-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.recovery-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid #e5e7eb;
		gap: 1rem;
	}

	.recovery-item:last-child {
		border-bottom: none;
	}

	.file-info {
		flex: 1;
		min-width: 0;
	}

	.file-name {
		display: block;
		font-weight: 500;
		color: #111827;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.file-date {
		display: block;
		font-size: 0.75rem;
		color: #6b7280;
		margin-top: 0.125rem;
	}

	.file-actions {
		display: flex;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.dialog-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.5rem;
		border-top: 1px solid #e5e7eb;
		background-color: #f9fafb;
	}

	.bulk-actions {
		display: flex;
		gap: 0.5rem;
	}

	.close-action {
		margin-left: auto;
	}
</style>
