<!--
  FileSelect Component

  A file selection component that supports both Tauri dialog API
  and native file input as fallback.

  Usage:
    <FileSelect
      label="DSM File"
      accept=".tif,.tiff"
      value={filePath}
      on:select={(e) => handleSelect(e.detail.path)}
    />
-->
<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from '$lib/i18n';

	/** Label text for the file input */
	export let label: string;
	/** Accepted file extensions (e.g., ".tif,.tiff") */
	export let accept: string = '*';
	/** Currently selected file path */
	export let value: string | null = null;
	/** Disabled state */
	export let disabled: boolean = false;

	const dispatch = createEventDispatcher<{ select: { path: string } }>();

	// Check if running in Tauri environment
	let isTauri = false;
	let tauriDialog: typeof import('@tauri-apps/plugin-dialog') | null = null;

	onMount(async () => {
		// Check for Tauri environment
		console.log('FileSelect onMount - checking Tauri environment');
		console.log('window.__TAURI__:', typeof window !== 'undefined' ? (window as any).__TAURI__ : 'undefined');

		if (typeof window !== 'undefined' && '__TAURI__' in window) {
			console.log('Tauri detected, importing dialog plugin...');
			try {
				tauriDialog = await import('@tauri-apps/plugin-dialog');
				isTauri = true;
				console.log('Tauri dialog plugin loaded successfully');
			} catch (e) {
				console.error('Failed to load Tauri dialog plugin:', e);
				isTauri = false;
			}
		} else {
			console.log('Not in Tauri environment');
		}
	});

	// Reference to the hidden file input
	let fileInput: HTMLInputElement;

	/**
	 * Extract filename from full path
	 */
	function getFileName(path: string): string {
		return path.split(/[/\\]/).pop() || path;
	}

	/**
	 * Convert accept string to Tauri filters
	 */
	function getFilters(): Array<{ name: string; extensions: string[] }> {
		const extensions = accept
			.split(',')
			.map((ext) => ext.trim().replace(/^\./, ''))
			.filter((ext) => ext !== '*');

		if (extensions.length === 0) {
			return [];
		}

		return [
			{
				name: label,
				extensions
			}
		];
	}

	/**
	 * Handle file selection
	 */
	async function handleClick() {
		if (disabled) return;

		console.log('handleClick called, isTauri:', isTauri, 'tauriDialog:', !!tauriDialog);

		if (isTauri && tauriDialog) {
			// Use Tauri dialog
			try {
				const filters = getFilters();
				console.log('Calling tauriDialog.open with filters:', filters);
				const selected = await tauriDialog.open({
					multiple: false,
					filters: filters.length > 0 ? filters : undefined
				});

				console.log('Tauri dialog result:', selected, 'type:', typeof selected);

				if (selected && typeof selected === 'string') {
					dispatch('select', { path: selected });
				} else if (selected && Array.isArray(selected) && selected.length > 0) {
					// Tauri v2 may return array even for single selection
					dispatch('select', { path: selected[0] });
				}
			} catch (error) {
				console.error('Tauri dialog error:', error);
				console.error('Error details:', JSON.stringify(error, Object.getOwnPropertyNames(error)));
				// Fallback to native input on error
				fileInput?.click();
			}
		} else {
			console.log('Using native file input fallback');
			// Use native file input
			fileInput?.click();
		}
	}

	/**
	 * Handle native file input change
	 */
	function handleFileChange(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];

		if (file) {
			// For web environment, we get the File object
			// Create a fake path using the file name
			// In a real Tauri app, the path would be absolute
			const path = file.name;
			dispatch('select', { path });
		}

		// Reset input so same file can be selected again
		target.value = '';
	}

	/**
	 * Clear selected file
	 */
	function handleClear() {
		dispatch('select', { path: '' });
	}
</script>

<div class="file-select">
	<span class="file-label" role="label">
		<span class="label-text">{label}</span>
	</span>

	<div class="file-input-container">
		<input
			bind:this={fileInput}
			type="file"
			{accept}
			class="hidden-input"
			on:change={handleFileChange}
			{disabled}
		/>

		{#if import.meta.env.DEV && !isTauri}
			<!-- Dev mode: show text input for direct path entry -->
			<input
				type="text"
				class="path-input"
				value={value || ''}
				placeholder="ファイルパスを入力..."
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						dispatch('select', { path: e.currentTarget.value });
					}
				}}
				on:blur={(e) => dispatch('select', { path: e.currentTarget.value })}
				{disabled}
			/>
		{:else}
			<div class="file-display" class:has-value={!!value} class:disabled>
				{#if value}
					<span class="file-name" title={value}>{getFileName(value)}</span>
					<button
						type="button"
						class="clear-button"
						on:click|stopPropagation={handleClear}
						{disabled}
						aria-label="Clear selection"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<line x1="18" y1="6" x2="6" y2="18" />
							<line x1="6" y1="6" x2="18" y2="18" />
						</svg>
					</button>
				{:else}
					<span class="placeholder">{t('dataInput.selectFile')}</span>
				{/if}
			</div>
		{/if}

		<button type="button" class="browse-button" on:click={handleClick} {disabled}>
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
				<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
			</svg>
			<span>{t('dataInput.selectFile')}</span>
		</button>
	</div>
</div>

<style>
	.file-select {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.file-label {
		display: block;
	}

	.label-text {
		font-weight: 500;
		font-size: 0.875rem;
		color: #374151;
	}

	.file-input-container {
		display: flex;
		gap: 0.5rem;
		align-items: stretch;
	}

	.hidden-input {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	.path-input {
		flex: 1;
		padding: 0.5rem 0.75rem;
		background-color: #fff;
		border: 1px solid #6366f1;
		border-radius: 0.375rem;
		min-width: 0;
		font-size: 0.875rem;
		color: #111827;
		transition: all 0.2s ease;
	}

	.path-input:focus {
		outline: none;
		border-color: #4f46e5;
		box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
	}

	.path-input:disabled {
		background-color: #f3f4f6;
		cursor: not-allowed;
		opacity: 0.7;
	}

	.path-input::placeholder {
		color: #9ca3af;
	}

	.file-display {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.75rem;
		background-color: #f9fafb;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		min-width: 0;
		transition: all 0.2s ease;
	}

	.file-display.has-value {
		background-color: #fff;
		border-color: #6366f1;
	}

	.file-display.disabled {
		background-color: #f3f4f6;
		cursor: not-allowed;
		opacity: 0.7;
	}

	.file-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 0.875rem;
		color: #111827;
	}

	.placeholder {
		color: #9ca3af;
		font-size: 0.875rem;
	}

	.clear-button {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.25rem;
		margin-left: 0.5rem;
		background: none;
		border: none;
		border-radius: 0.25rem;
		color: #6b7280;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.clear-button:hover:not(:disabled) {
		color: #ef4444;
		background-color: #fee2e2;
	}

	.clear-button:disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}

	.browse-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background-color: #6366f1;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
		white-space: nowrap;
	}

	.browse-button:hover:not(:disabled) {
		background-color: #4f46e5;
	}

	.browse-button:disabled {
		background-color: #9ca3af;
		cursor: not-allowed;
	}
</style>
