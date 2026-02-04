<!--
  Data Input Step Page

  First step of the georectification wizard.
  Allows users to select DSM, orthophoto, and target image files.
  Displays file information and validates CRS compatibility.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { api, ApiError } from '$lib/services/api';
	import { Button, Card, FileSelect } from '$lib/components/common';
	import { ImagePreview } from '$lib/components/ImageViewer';
	import { wizardStore, isStep1Valid, crsMatch } from '$lib/stores';
	import type { RasterFile, ImageFile } from '$lib/types';

	// Local state for loading indicators
	let loadingDsm = false;
	let loadingOrtho = false;
	let loadingTargetImage = false;
	let lastHydratedDsmPath: string | null = null;
	let lastHydratedOrthoPath: string | null = null;
	let lastHydratedTargetPath: string | null = null;

	// Error messages
	let dsmError: string | null = null;
	let orthoError: string | null = null;
	let targetImageError: string | null = null;

	// Get current state from store
	$: inputData = $wizardStore.inputData;

	async function hydrateRasterPreview(kind: 'dsm' | 'ortho', path: string) {
		try {
			if (kind === 'dsm') {
				loadingDsm = true;
			} else {
				loadingOrtho = true;
			}
			const { info, thumbnail } = await fetchRasterInfo(path);
			if (kind === 'dsm') {
				if (inputData.dsm?.path !== path) return;
				wizardStore.setDsm(info, thumbnail ?? inputData.dsmThumbnail);
			} else {
				if (inputData.ortho?.path !== path) return;
				wizardStore.setOrtho(info, thumbnail ?? inputData.orthoThumbnail);
			}
		} catch (error) {
			console.warn('Failed to hydrate raster preview:', error);
		} finally {
			if (kind === 'dsm') {
				loadingDsm = false;
			} else {
				loadingOrtho = false;
			}
		}
	}

	async function hydrateTargetPreview(path: string) {
		try {
			loadingTargetImage = true;
			const { info, thumbnail } = await fetchImageInfo(path);
			if (inputData.targetImage?.path !== path) return;
			wizardStore.setTargetImage(info, thumbnail || inputData.targetImageThumbnail);
		} catch (error) {
			console.warn('Failed to hydrate target preview:', error);
		} finally {
			loadingTargetImage = false;
		}
	}

	// Hydrate previews and WGS84 bounds when opening existing projects
	$: if (inputData.dsm?.path && inputData.dsm.path !== lastHydratedDsmPath) {
		const needsPreview = !inputData.dsmThumbnail || !inputData.dsm.bounds_wgs84;
		if (needsPreview && !loadingDsm) {
			lastHydratedDsmPath = inputData.dsm.path;
			hydrateRasterPreview('dsm', inputData.dsm.path);
		}
	}

	$: if (inputData.ortho?.path && inputData.ortho.path !== lastHydratedOrthoPath) {
		const needsPreview = !inputData.orthoThumbnail || !inputData.ortho.bounds_wgs84;
		if (needsPreview && !loadingOrtho) {
			lastHydratedOrthoPath = inputData.ortho.path;
			hydrateRasterPreview('ortho', inputData.ortho.path);
		}
	}

	$: if (inputData.targetImage?.path && inputData.targetImage.path !== lastHydratedTargetPath) {
		if (!inputData.targetImageThumbnail && !loadingTargetImage) {
			lastHydratedTargetPath = inputData.targetImage.path;
			hydrateTargetPreview(inputData.targetImage.path);
		}
	}

	function localizeBackendError(errorMessage?: string, detail?: string) {
		if (!errorMessage) {
			return { message: null, includeDetail: true };
		}

		switch (errorMessage) {
			case 'Coordinate reference systems do not match': {
				const match = detail?.match(/DSM CRS: (.*?), Orthophoto CRS: (.*?)(\\.|$)/);
				if (match) {
					return {
						message: t('errors.crs_mismatch', { dsm_crs: match[1], ortho_crs: match[2] }),
						includeDetail: false
					};
				}
				return { message: t('errors.crs_mismatch_simple'), includeDetail: true };
			}
			case 'CRS is not defined':
				return { message: t('errors.crs_not_defined'), includeDetail: true };
			case 'CRS must be a projected coordinate system in meters':
				return { message: t('errors.crs_not_projected'), includeDetail: true };
			case 'CRS unit is undefined':
				return { message: t('errors.crs_unit_undefined'), includeDetail: true };
			case 'CRS unit must be meters':
				return { message: t('errors.crs_unit_not_meters'), includeDetail: true };
			default:
				return { message: errorMessage, includeDetail: true };
		}
	}

	function formatApiError(error: unknown, fallbackMessage: string): string {
		if (error instanceof ApiError) {
			const body = error.body as { error?: string; detail?: string } | null;
			const localized = localizeBackendError(body?.error, body?.detail);
			if (localized.message) {
				if (body?.detail && localized.includeDetail) {
					return `${localized.message}: ${body.detail}`;
				}
				return localized.message;
			}
			if (body?.detail) return body.detail;
			return body?.error || error.statusText || fallbackMessage;
		}
		return fallbackMessage;
	}

	/**
	 * Fetch raster file info and thumbnail
	 */
	async function fetchRasterInfo(
		path: string,
		otherPath?: string | null
	): Promise<{ info: RasterFile; thumbnail: string | null }> {
		// Get file info
		const info = await api.post<RasterFile>('/api/files/raster/info', {
			path,
			other_path: otherPath ?? null
		});

		// Get thumbnail
		let thumbnail: string | null = null;
		try {
			const baseUrl = api.getBaseUrl();
			const response = await fetch(baseUrl + '/api/files/raster/thumbnail', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, max_size: 512 })
			});
			if (response.ok) {
				const blob = await response.blob();
				thumbnail = URL.createObjectURL(blob);
			}
		} catch {
			// Thumbnail is optional, ignore errors
		}

		return { info, thumbnail };
	}

	/**
	 * Fetch image file info
	 */
	async function fetchImageInfo(path: string): Promise<{ info: ImageFile; thumbnail: string }> {
		// Get file info
		const info = await api.post<ImageFile>('/api/files/image/info', { path });

		// For regular images, use the file path directly or create a local URL
		// In Tauri, we can use convertFileSrc or asset protocol
		// For web dev, we'll need the backend to serve the image
		let thumbnail = '';
		try {
			// Try to get thumbnail from backend
			const baseUrl = api.getBaseUrl();
			const response = await fetch(baseUrl + '/api/files/image/thumbnail', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, max_size: 512 })
			});
			if (response.ok) {
				const blob = await response.blob();
				thumbnail = URL.createObjectURL(blob);
			}
		} catch {
			// If no thumbnail endpoint, leave empty
		}

		return { info, thumbnail };
	}

	/**
	 * Handle DSM file selection
	 */
	async function handleDsmSelect(event: CustomEvent<{ path: string }>) {
		const { path } = event.detail;

		console.log('handleDsmSelect called with path:', path);

		if (!path) {
			wizardStore.setDsm(null, null);
			dsmError = null;
			return;
		}

		loadingDsm = true;
		dsmError = null;

		try {
			console.log('Fetching raster info for:', path);
			const { info, thumbnail } = await fetchRasterInfo(path, inputData.ortho?.path);
			console.log('Raster info received:', info);
			wizardStore.setDsm(info, thumbnail);
		} catch (error) {
			console.error('Failed to load DSM info:', error);
			console.error('Error type:', error?.constructor?.name);
			console.error('Full error:', JSON.stringify(error, Object.getOwnPropertyNames(error || {})));
			dsmError = formatApiError(error, t('error.invalidFile'));
			wizardStore.setDsm(null, null);
		} finally {
			loadingDsm = false;
		}
	}

	/**
	 * Handle orthophoto file selection
	 */
	async function handleOrthoSelect(event: CustomEvent<{ path: string }>) {
		const { path } = event.detail;

		if (!path) {
			wizardStore.setOrtho(null, null);
			orthoError = null;
			return;
		}

		loadingOrtho = true;
		orthoError = null;

		try {
			const { info, thumbnail } = await fetchRasterInfo(path, inputData.dsm?.path);
			wizardStore.setOrtho(info, thumbnail);
		} catch (error) {
			console.error('Failed to load orthophoto info:', error);
			orthoError = formatApiError(error, t('error.invalidFile'));
			wizardStore.setOrtho(null, null);
		} finally {
			loadingOrtho = false;
		}
	}

	/**
	 * Handle target image file selection
	 */
	async function handleTargetImageSelect(event: CustomEvent<{ path: string }>) {
		const { path } = event.detail;

		if (!path) {
			wizardStore.setTargetImage(null, null);
			targetImageError = null;
			return;
		}

		loadingTargetImage = true;
		targetImageError = null;

		try {
			const { info, thumbnail } = await fetchImageInfo(path);
			wizardStore.setTargetImage(info, thumbnail);
		} catch (error) {
			console.error('Failed to load target image info:', error);
			targetImageError = formatApiError(error, t('error.invalidFile'));
			wizardStore.setTargetImage(null, null);
		} finally {
			loadingTargetImage = false;
		}
	}

	/**
	 * Format bounds for display
	 */
	function formatBounds(bounds: [number, number, number, number]): string {
		const [xmin, ymin, xmax, ymax] = bounds;
		return '(' + xmin.toFixed(2) + ', ' + ymin.toFixed(2) + ') - (' + xmax.toFixed(2) + ', ' + ymax.toFixed(2) + ')';
	}

	/**
	 * Format resolution for display
	 */
	function formatResolution(resolution: [number, number]): string {
		return resolution[0].toFixed(4) + ' x ' + resolution[1].toFixed(4);
	}

	/**
	 * Format size for display
	 */
	function formatSize(size: [number, number]): string {
		return size[0] + ' x ' + size[1] + ' px';
	}

	/**
	 * Handle next button click
	 */
	async function handleNext() {
		if ($isStep1Valid) {
			// Invalidate subsequent steps (Step 2 onwards) when input data might have changed
			// This ensures camera params and all processing results are cleared when data is modified
			wizardStore.invalidateFromStep(1);

			// Create or update project
			try {
				let projectId = $wizardStore.projectId;

				if (!projectId) {
					// Create new project
					const project = await api.post<{ id: string }>('/api/projects', {
						name: inputData.targetImage?.path?.split('/').pop() ?? 'New Project'
					});
					projectId = project.id;
					wizardStore.setProjectId(projectId);
				}

				// Update project with input data
				await api.put(`/api/projects/${projectId}`, {
					input_data: {
						dsm: inputData.dsm,
						ortho: inputData.ortho,
						target_image: inputData.targetImage
					}
				});
			} catch (error) {
				console.error('Failed to create/update project:', error);
				// Continue anyway - project can be created later
			}

			wizardStore.completeStep(0);
			wizardStore.nextStep();
			// Navigate to camera setup
			goto('/georectify/steps/camera-setup');
		}
	}
</script>

<div class="data-input-page">
	<header class="page-header">
		<h1 class="page-title">{t('dataInput.title')}</h1>
		<p class="page-description">{t('home.description')}</p>
	</header>

	<!-- CRS Mismatch Warning -->
	{#if $crsMatch === false}
		<div class="warning-banner" role="alert">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
				<line x1="12" y1="9" x2="12" y2="13" />
				<line x1="12" y1="17" x2="12.01" y2="17" />
			</svg>
			<span>{t('dataInput.crsMismatchWarning', { dsm_crs: inputData.dsm?.crs ?? '', ortho_crs: inputData.ortho?.crs ?? '' })}</span>
		</div>
	{/if}

	<div class="file-sections">
		<!-- DSM Section -->
		<Card>
			<svelte:fragment slot="header">
				<h2 class="section-title">{t('dataInput.dsm')}</h2>
			</svelte:fragment>

			<div class="file-section-content">
				<FileSelect
					label={t('dataInput.dsm')}
					accept=".tif,.tiff"
					value={inputData.dsm?.path ?? null}
					on:select={handleDsmSelect}
				/>

				<p class="file-description">{t('dataInput.dsmDescription')}</p>

				{#if dsmError}
					<div class="error-message">{dsmError}</div>
				{/if}

				<div class="preview-info-container">
					<ImagePreview
						src={inputData.dsmThumbnail}
						alt={t('dataInput.dsmPreview')}
						loading={loadingDsm}
						maxHeight="180px"
					/>

					{#if inputData.dsm}
						<div class="file-info">
							<h4 class="info-title">{t('dataInput.fileInfo')}</h4>
							<dl class="info-list">
								<dt>{t('dataInput.crs')}</dt>
								<dd>{inputData.dsm.crs}</dd>

								<dt>{t('dataInput.size')}</dt>
								<dd>{formatSize(inputData.dsm.size)}</dd>

								<dt>{t('dataInput.resolution')}</dt>
								<dd>{formatResolution(inputData.dsm.resolution)}</dd>

								<dt>{t('dataInput.bounds')}</dt>
								<dd class="bounds">{formatBounds(inputData.dsm.bounds)}</dd>
							</dl>
						</div>
					{/if}
				</div>
			</div>
		</Card>

		<!-- Orthophoto Section -->
		<Card>
			<svelte:fragment slot="header">
				<h2 class="section-title">{t('dataInput.ortho')}</h2>
			</svelte:fragment>

			<div class="file-section-content">
				<FileSelect
					label={t('dataInput.ortho')}
					accept=".tif,.tiff"
					value={inputData.ortho?.path ?? null}
					on:select={handleOrthoSelect}
				/>

				<p class="file-description">{t('dataInput.orthoDescription')}</p>

				{#if orthoError}
					<div class="error-message">{orthoError}</div>
				{/if}

				<div class="preview-info-container">
					<ImagePreview
						src={inputData.orthoThumbnail}
						alt={t('dataInput.orthoPreview')}
						loading={loadingOrtho}
						maxHeight="180px"
					/>

					{#if inputData.ortho}
						<div class="file-info">
							<h4 class="info-title">{t('dataInput.fileInfo')}</h4>
							<dl class="info-list">
								<dt>{t('dataInput.crs')}</dt>
								<dd>{inputData.ortho.crs}</dd>

								<dt>{t('dataInput.size')}</dt>
								<dd>{formatSize(inputData.ortho.size)}</dd>

								<dt>{t('dataInput.resolution')}</dt>
								<dd>{formatResolution(inputData.ortho.resolution)}</dd>

								<dt>{t('dataInput.bounds')}</dt>
								<dd class="bounds">{formatBounds(inputData.ortho.bounds)}</dd>
							</dl>
						</div>
					{/if}
				</div>
			</div>
		</Card>

		<!-- Target Image Section -->
		<Card>
			<svelte:fragment slot="header">
				<h2 class="section-title">{t('dataInput.photo')}</h2>
			</svelte:fragment>

			<div class="file-section-content">
				<FileSelect
					label={t('dataInput.photo')}
					accept=".jpg,.jpeg,.png,.tif,.tiff"
					value={inputData.targetImage?.path ?? null}
					on:select={handleTargetImageSelect}
				/>

				<p class="file-description">{t('dataInput.photoDescription')}</p>

				{#if targetImageError}
					<div class="error-message">{targetImageError}</div>
				{/if}

				<div class="preview-info-container">
					<ImagePreview
						src={inputData.targetImageThumbnail}
						alt={t('dataInput.targetPreview')}
						loading={loadingTargetImage}
						maxHeight="180px"
					/>

					{#if inputData.targetImage}
						<div class="file-info">
							<h4 class="info-title">{t('dataInput.fileInfo')}</h4>
							<dl class="info-list">
								<dt>{t('dataInput.size')}</dt>
								<dd>{formatSize(inputData.targetImage.size)}</dd>

								{#if inputData.targetImage.exif}
									{#if inputData.targetImage.exif.camera_model}
										<dt>{t('dataInput.camera')}</dt>
										<dd>{inputData.targetImage.exif.camera_model}</dd>
									{/if}

									{#if inputData.targetImage.exif.datetime}
										<dt>{t('dataInput.datetime')}</dt>
										<dd>{inputData.targetImage.exif.datetime}</dd>
									{/if}

									{#if inputData.targetImage.exif.focal_length}
										<dt>{t('dataInput.focalLength')}</dt>
										<dd>{inputData.targetImage.exif.focal_length}mm</dd>
									{/if}

									{#if inputData.targetImage.exif.gps_lat != null && inputData.targetImage.exif.gps_lon != null}
										<dt>GPS</dt>
										<dd>
											{inputData.targetImage.exif.gps_lat.toFixed(6)},
											{inputData.targetImage.exif.gps_lon.toFixed(6)}
											{#if inputData.targetImage.exif.gps_alt != null}
												({inputData.targetImage.exif.gps_alt.toFixed(0)}m)
											{/if}
										</dd>
									{/if}
								{/if}
							</dl>
						</div>
					{/if}
				</div>
			</div>
		</Card>
	</div>

	<!-- Navigation -->
	<footer class="page-footer">
		<div class="nav-spacer"></div>
		<Button variant="primary" disabled={!$isStep1Valid} on:click={handleNext}>
			{t('common.next')}
		</Button>
	</footer>
</div>

<style>
	.data-input-page {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		padding: 1.5rem;
		max-width: 1200px;
		margin: 0 auto;
	}

	.page-header {
		text-align: center;
		margin-bottom: 0.5rem;
	}

	.page-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--ink-900);
		margin: 0 0 0.5rem 0;
	}

	.page-description {
		font-size: 0.95rem;
		color: var(--ink-500);
		margin: 0;
	}

	.warning-banner {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background-color: #fffbeb;
		border: 1px solid #f59e0b;
		border-radius: 0.5rem;
		color: #b45309;
		font-size: 0.875rem;
	}

	.warning-banner svg {
		flex-shrink: 0;
		color: #f59e0b;
	}

	.file-sections {
		display: grid;
		gap: 1.5rem;
	}

	@media (min-width: 1024px) {
		.file-sections {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	.section-title {
		font-size: 1rem;
		font-weight: 600;
		color: var(--ink-900);
		margin: 0;
	}

	.file-section-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.file-description {
		font-size: 0.8rem;
		color: var(--ink-500);
		margin: 0;
	}

	.error-message {
		padding: 0.5rem 0.75rem;
		background-color: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 0.375rem;
		color: #dc2626;
		font-size: 0.8rem;
	}

	.preview-info-container {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.file-info {
		background-color: rgba(255, 255, 255, 0.7);
		border-radius: 0.375rem;
		padding: 0.75rem;
	}

	.info-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--ink-700);
		margin: 0 0 0.5rem 0;
	}

	.info-list {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.25rem 0.75rem;
		margin: 0;
		font-size: 0.8rem;
	}

	.info-list dt {
		color: var(--ink-500);
		font-weight: 500;
	}

	.info-list dd {
		color: var(--ink-900);
		margin: 0;
		word-break: break-word;
	}

	.info-list dd.bounds {
		font-family: monospace;
		font-size: 0.75rem;
	}

	.page-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-top: 1rem;
		border-top: 1px solid var(--line);
	}

	.nav-spacer {
		width: 100px;
	}
</style>
