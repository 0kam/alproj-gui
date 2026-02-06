<!--
  ImagePreview Component

  Displays an image preview with loading and error states.
  Supports both URL and Base64 image sources.

  Usage:
    <ImagePreview
      src={imageUrl}
      alt="Preview image"
      loading={isLoading}
    />
-->
<script lang="ts">
	import { t } from '$lib/i18n';

	/** Image source URL or Base64 data URI */
	export let src: string | null = null;
	/** Alternative text for the image */
	export let alt: string = 'Preview';
	/** Loading state */
	export let loading: boolean = false;
	/** Maximum height of the preview container */
	export let maxHeight: string = '200px';
	/** Aspect ratio (e.g., "16/9", "4/3", "1") */
	export let aspectRatio: string | null = null;

	// Error state for image loading
	let hasError = false;

	/**
	 * Handle image load error
	 */
	function handleError() {
		hasError = true;
	}

	/**
	 * Handle successful image load
	 */
	function handleLoad() {
		hasError = false;
	}

	// Reset error state when src changes
	$: if (src) {
		hasError = false;
	}
</script>

<div
	class="image-preview"
	style:max-height={maxHeight}
	style:aspect-ratio={aspectRatio}
	class:loading
	class:has-error={hasError}
	class:empty={!src && !loading}
>
	{#if loading}
		<div class="loading-container">
			<div class="spinner" aria-hidden="true">
				<svg
					class="animate-spin"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
			</div>
			<span class="loading-text">{t('common.loading')}</span>
		</div>
	{:else if hasError}
		<div class="error-container">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="48"
				height="48"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
				<circle cx="8.5" cy="8.5" r="1.5" />
				<polyline points="21 15 16 10 5 21" />
				<line x1="4" y1="4" x2="20" y2="20" class="error-line" />
			</svg>
			<span class="error-text">{t('common.error')}</span>
		</div>
	{:else if src}
		<img {src} {alt} class="preview-image" on:error={handleError} on:load={handleLoad} />
	{:else}
		<div class="empty-container">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="48"
				height="48"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
				<circle cx="8.5" cy="8.5" r="1.5" />
				<polyline points="21 15 16 10 5 21" />
			</svg>
			<span class="empty-text">No image</span>
		</div>
	{/if}
</div>

<style>
	.image-preview {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		overflow: hidden;
		position: relative;
	}

	.image-preview.loading {
		background-color: #f9fafb;
	}

	.image-preview.has-error {
		background-color: #fef2f2;
		border-color: #fecaca;
	}

	.image-preview.empty {
		background-color: #f9fafb;
		min-height: 120px;
	}

	.preview-image {
		width: 100%;
		height: 100%;
		object-fit: contain;
		display: block;
	}

	.loading-container,
	.error-container,
	.empty-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 1.5rem;
		color: #6b7280;
	}

	.spinner {
		width: 2rem;
		height: 2rem;
		color: #6366f1;
	}

	.spinner svg {
		width: 100%;
		height: 100%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text,
	.error-text,
	.empty-text {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.error-container {
		color: #dc2626;
	}

	.error-container svg {
		color: #f87171;
	}

	.error-line {
		stroke: #ef4444;
		stroke-width: 2;
	}

	.empty-container svg {
		color: #d1d5db;
	}

	.empty-text {
		color: #9ca3af;
	}
</style>
