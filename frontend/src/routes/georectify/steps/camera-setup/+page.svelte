<!--
  Camera Setup Step Page

  Second step of the georectification wizard.
  Allows users to set camera position and orientation parameters
  with a map view and real-time simulation preview.
-->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { Button, Card, CameraParamsForm } from '$lib/components/common';
	import { MapView, CameraMarker, FovCone, RasterOverlay } from '$lib/components/Map';
	import { SimulationPreview } from '$lib/components/ImageViewer';
	import { api } from '$lib/services/api';
	import { wizardStore } from '$lib/stores';
	import { DEFAULT_CAMERA_PARAMS } from '$lib/types';
	import type { CameraParamsValues, RasterFile, MatchingParams } from '$lib/types';
	import type maplibregl from 'maplibre-gl';

	// Default rendering distance values
	const defaultSurfaceDistance = 3000;
	const defaultSimulationMinDistance = 100;

	// Local state
	let map: maplibregl.Map | null = null;
	let mapLoaded = false;
	let cameraPositionWgs84: [number, number] | null = null;
	let dsmElevation: number | null = null;
	let hasSimulation = false;
	let storedSimulation: string | null = null;
	let lastDsmInfoPath: string | null = null;
	let lastOrthoInfoPath: string | null = null;

	// Rendering distance settings
	let surfaceDistance = $wizardStore.matchingParams?.surface_distance ?? defaultSurfaceDistance;
	let simulationMinDistance = $wizardStore.matchingParams?.simulation_min_distance ?? defaultSimulationMinDistance;

	// Orthophoto overlay state
	let showOrthoOverlay = false;
	let orthoOverlayUrl: string | null = null;
	let orthoOverlayBounds: [number, number, number, number] | null = null;
	let orthoOverlayOpacity = 0.7;
	let lastOrthoOverlayPath: string | null = null;

	// Base layer state
	let baseLayer: 'osm' | 'gsi' = 'osm';

	// Get current state from store
	$: inputData = $wizardStore.inputData;
	$: storedCameraParams = $wizardStore.cameraParams;
	$: storedSimulation = $wizardStore.cameraSimulation;

	async function hydrateRasterInfo(kind: 'dsm' | 'ortho', path: string) {
		try {
			const info = await api.post<RasterFile>('/api/files/raster/info', { path });
			if (kind === 'dsm') {
				if (inputData.dsm?.path !== path) return;
				wizardStore.setDsm(info, inputData.dsmThumbnail);
			} else {
				if (inputData.ortho?.path !== path) return;
				wizardStore.setOrtho(info, inputData.orthoThumbnail);
			}
		} catch (error) {
			console.warn('Failed to hydrate raster info:', error);
		}
	}

	// Ensure bounds_wgs84 is available for map fitting when loading existing projects
	$: if (inputData.dsm?.path && !inputData.dsm.bounds_wgs84 && inputData.dsm.path !== lastDsmInfoPath) {
		lastDsmInfoPath = inputData.dsm.path;
		hydrateRasterInfo('dsm', inputData.dsm.path);
	}

	$: if (
		inputData.ortho?.path &&
		!inputData.ortho.bounds_wgs84 &&
		inputData.ortho.path !== lastOrthoInfoPath
	) {
		lastOrthoInfoPath = inputData.ortho.path;
		hydrateRasterInfo('ortho', inputData.ortho.path);
	}

	// Initialize camera params from store or default
	// Use a flag to track if we've initialized from store to avoid overwriting user edits
	let cameraParams: CameraParamsValues = { ...DEFAULT_CAMERA_PARAMS };
	let initialized = false;

	// Sync from store when component mounts or store changes (only if not yet initialized)
	$: if (storedCameraParams && !initialized) {
		cameraParams = { ...storedCameraParams };
		initialized = true;
	}

	// Camera position for map (lon, lat in WGS84) - computed via transform
	$: cameraPosition = cameraPositionWgs84;

	// Update WGS84 position when camera params change
	$: if (cameraParams.x !== 0 && cameraParams.y !== 0) {
		updateCameraPositionWgs84(cameraParams.x, cameraParams.y);
	} else {
		cameraPositionWgs84 = null;
	}

	/**
	 * Fetch elevation from DSM at the given coordinates
	 * @param autoApply - If true, automatically set z to DSM elevation + 2m
	 */
	async function fetchDsmElevation(x: number, y: number, autoApply: boolean = false) {
		const dsmPath = inputData?.dsm?.path;
		if (!dsmPath) {
			dsmElevation = null;
			return;
		}

		try {
			const response = await fetch(`${api.getBaseUrl()}/api/files/raster/elevation`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					dsm_path: dsmPath,
					x: x,
					y: y
				})
			});

			if (response.ok) {
				const result = await response.json();
				dsmElevation = result.elevation;

				// Auto-apply DSM elevation + 2m if requested
				if (autoApply && dsmElevation !== null) {
					const suggestedZ = dsmElevation + 2;
					cameraParams = {
						...cameraParams,
						z: suggestedZ
					};
					saveCameraParams();
				}
			} else {
				dsmElevation = null;
			}
		} catch (error) {
			console.error('Failed to fetch DSM elevation:', error);
			dsmElevation = null;
		}
	}

	/**
	 * Transform camera position from native CRS to WGS84 for map display
	 */
	async function updateCameraPositionWgs84(x: number, y: number) {
		const dsmCrs = inputData?.dsm?.crs;
		console.log('updateCameraPositionWgs84 called:', { x, y, dsmCrs });

		if (!dsmCrs || dsmCrs === 'EPSG:4326') {
			cameraPositionWgs84 = [x, y];
			console.log('Using coordinates directly as WGS84:', cameraPositionWgs84);
			return;
		}

		try {
			const response = await fetch(`${api.getBaseUrl()}/api/files/transform`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					x: x,
					y: y,
					src_crs: dsmCrs,
					dst_crs: 'EPSG:4326'
				})
			});

			if (response.ok) {
				const result = await response.json();
				cameraPositionWgs84 = [result.x, result.y];
				console.log('Transformed to WGS84 for map display:', cameraPositionWgs84);
			} else {
				console.error('Failed to transform to WGS84, response not ok');
			}
		} catch (error) {
			console.error('Coordinate transform error (DSM CRS -> WGS84):', error);
		}
	}

	// Suggested params from EXIF
	$: suggestedParams = buildSuggestedParams();

	function mergeBounds(
		a: [number, number, number, number] | null,
		b: [number, number, number, number] | null
	): [number, number, number, number] | null {
		if (a && b) {
			return [
				Math.min(a[0], b[0]),
				Math.min(a[1], b[1]),
				Math.max(a[2], b[2]),
				Math.max(a[3], b[3])
			];
		}
		return a ?? b ?? null;
	}

	// Calculate map center from bounds (use WGS84 bounds for map display)
	$: mapBounds = mergeBounds(inputData?.dsm?.bounds_wgs84 ?? null, inputData?.ortho?.bounds_wgs84 ?? null);
	$: mapCenter = calculateMapCenter();

	// Check if we have required data
	$: hasRequiredData = inputData?.dsm && inputData?.ortho && inputData?.targetImage;

	/**
	 * Transform coordinates from WGS84 to DSM's CRS
	 */
	async function transformFromWgs84(lng: number, lat: number): Promise<{ x: number; y: number } | null> {
		const dsmCrs = inputData?.dsm?.crs;
		if (!dsmCrs || dsmCrs === 'EPSG:4326') {
			return { x: lng, y: lat };
		}

		try {
			const response = await fetch(`${api.getBaseUrl()}/api/files/transform`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					x: lng,
					y: lat,
					src_crs: 'EPSG:4326',
					dst_crs: dsmCrs
				})
			});

			if (response.ok) {
				const result = await response.json();
				return { x: result.x, y: result.y };
			}
		} catch (error) {
			console.error('Coordinate transform error (WGS84 -> DSM CRS):', error);
		}
		return null;
	}

	/**
	 * Build suggested params from EXIF data
	 * Note: GPS coordinates are in WGS84 and need to be transformed
	 */
	function buildSuggestedParams(): Partial<CameraParamsValues> | null {
		if (!inputData?.targetImage?.exif) return null;
		const exif = inputData.targetImage.exif;

		const suggested: Partial<CameraParamsValues> = {};

		// Note: GPS coordinates will be transformed separately in applyExifCoordinates
		// Store raw WGS84 values for later transformation
		if (exif.gps_alt !== undefined) suggested.z = exif.gps_alt;

		// Estimate FOV from focal length if available
		if (exif.focal_length) {
			// Assuming 35mm full-frame sensor (36mm width)
			// FOV = 2 * atan(sensor_width / (2 * focal_length))
			const sensorWidth = 36; // mm
			const fovRad = 2 * Math.atan(sensorWidth / (2 * exif.focal_length));
			suggested.fov = Math.round((fovRad * 180) / Math.PI);
		}

		return Object.keys(suggested).length > 0 ? suggested : null;
	}

	/**
	 * Apply EXIF GPS coordinates with proper CRS transformation
	 */
	async function applyExifCoordinates() {
		const exif = inputData?.targetImage?.exif;
		if (!exif || exif.gps_lon === undefined || exif.gps_lat === undefined) return;

		console.log('Applying EXIF GPS coordinates:', exif.gps_lon, exif.gps_lat);
		const transformed = await transformFromWgs84(exif.gps_lon, exif.gps_lat);
		if (transformed) {
			console.log('Transformed to DSM CRS:', transformed.x, transformed.y);
			updateCameraPosition(transformed.x, transformed.y);
		} else {
			console.warn('Failed to transform EXIF coordinates to DSM CRS');
		}
	}

	/**
	 * Calculate map center from DSM bounds (WGS84)
	 */
	function calculateMapCenter(): [number, number] {
		if (mapBounds) {
			const bounds = mapBounds;
			const [xmin, ymin, xmax, ymax] = bounds;
			return [(xmin + xmax) / 2, (ymin + ymax) / 2];
		}
		// Default to Mt. Fuji area
		return [138.7274, 35.3606];
	}

	/**
	 * Handle map load event
	 */
	function handleMapLoad(event: CustomEvent<{ map: maplibregl.Map }>) {
		map = event.detail.map;
		mapLoaded = true;
	}

	/**
	 * Handle map click to set camera position
	 * Transforms WGS84 coordinates to native CRS
	 */
	async function handleMapClick(event: CustomEvent<{ lngLat: maplibregl.LngLat }>) {
		const { lngLat } = event.detail;
		console.log('Map clicked at WGS84:', lngLat.lng, lngLat.lat);

		const transformed = await transformFromWgs84(lngLat.lng, lngLat.lat);
		if (transformed) {
			console.log('Transformed to DSM CRS:', transformed.x, transformed.y);
			updateCameraPosition(transformed.x, transformed.y);
		} else {
			console.error('Failed to transform coordinates - cannot set camera position');
		}
	}

	/**
	 * Handle camera marker drag
	 * Transforms WGS84 coordinates to native CRS
	 */
	async function handleMarkerMove(event: CustomEvent<{ lng: number; lat: number }>) {
		const { lng, lat } = event.detail;
		console.log('Marker moved to WGS84:', lng, lat);

		const transformed = await transformFromWgs84(lng, lat);
		if (transformed) {
			console.log('Transformed to DSM CRS:', transformed.x, transformed.y);
			updateCameraPosition(transformed.x, transformed.y);
		} else {
			console.error('Failed to transform coordinates during marker drag');
		}
	}

	/**
	 * Handle FOV/pan change from map handles
	 */
	function handleFovChange(event: CustomEvent<{ pan: number; fov: number }>) {
		cameraParams = {
			...cameraParams,
			pan: event.detail.pan,
			fov: event.detail.fov
		};
		saveCameraParams();
	}

	/**
	 * Update camera position in params
	 */
	function updateCameraPosition(x: number, y: number) {
		cameraParams = {
			...cameraParams,
			x: x,
			y: y
		};
		saveCameraParams();
		// Fetch elevation from DSM at the new position and auto-apply DSM+2m to z
		fetchDsmElevation(x, y, true);
	}

	/**
	 * Handle params form change
	 */
	function handleParamsChange(event: CustomEvent<CameraParamsValues>) {
		const newParams = event.detail;
		// Check if position changed
		const positionChanged = newParams.x !== cameraParams.x || newParams.y !== cameraParams.y;
		cameraParams = newParams;
		saveCameraParams();
		// Fetch elevation if position changed
		if (positionChanged && newParams.x !== 0 && newParams.y !== 0) {
			fetchDsmElevation(newParams.x, newParams.y);
		}
	}

	/**
	 * Save camera params to store
	 */
	function saveCameraParams() {
		wizardStore.setCameraParams(cameraParams);
	}

	// Reactive validation for camera setup
	$: isValid =
		cameraParams.x !== 0 &&
		cameraParams.y !== 0 &&
		cameraParams.fov > 0 &&
		cameraParams.fov <= 180 &&
		hasSimulation;

	/**
	 * Save rendering distance settings to matchingParams
	 */
	function saveRenderingDistance() {
		// Preserve existing matchingParams and update only rendering distance
		const existingParams = $wizardStore.matchingParams;
		const updatedParams: MatchingParams = {
			matching_method: existingParams?.matching_method ?? 'superpoint-lightglue',
			resize: existingParams?.resize ?? 'none',
			threshold: existingParams?.threshold ?? 30.0,
			outlier_filter: existingParams?.outlier_filter ?? 'fundamental',
			spatial_thin_grid: existingParams?.spatial_thin_grid ?? 50,
			spatial_thin_selection: existingParams?.spatial_thin_selection ?? 'center',
			surface_distance: surfaceDistance,
			simulation_min_distance: simulationMinDistance
		};
		wizardStore.setMatchingResult({ plot: $wizardStore.matchingPlot, params: updatedParams });
	}

	/**
	 * Handle next button click
	 */
	async function handleNext() {
		if (isValid) {
			saveCameraParams();
			saveRenderingDistance();
			// Invalidate subsequent steps (Step 3 onwards) when camera params might have changed
			// This ensures matching and estimation results are cleared when parameters are modified
			wizardStore.invalidateFromStep(2);

			// Update project with camera parameters
			const projectId = $wizardStore.projectId;
			if (projectId) {
				try {
					await api.put(`/api/projects/${projectId}`, {
						camera_params: {
							initial: cameraParams,
							optimized: null
						}
					});
				} catch (error) {
					console.error('Failed to update project camera params:', error);
				}
			}

			wizardStore.completeStep(1);
			wizardStore.nextStep();
			goto('/georectify/steps/processing');
		}
	}

	/**
	 * Handle back button click
	 */
	function handleBack() {
		saveCameraParams();
		wizardStore.prevStep();
		goto('/georectify/steps/data-input');
	}

	function handleSimulationGenerated(event: CustomEvent<{ image: string }>) {
		wizardStore.setCameraSimulation(event.detail.image);
	}

	function handleSimulationCleared() {
		wizardStore.setCameraSimulation(null);
	}

	/**
	 * Fetch orthophoto thumbnail for map overlay
	 */
	async function fetchOrthoOverlay(path: string) {
		if (!path || path === lastOrthoOverlayPath) {
			console.debug('[OrthoOverlay] Skipping fetch, path unchanged:', path);
			return;
		}
		console.debug('[OrthoOverlay] Fetching thumbnail for:', path);
		lastOrthoOverlayPath = path;

		try {
			// Request a larger thumbnail for better map overlay quality
			const response = await fetch(`${api.getBaseUrl()}/api/files/raster/thumbnail`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, max_size: 1024 })
			});

			if (!response.ok) {
				console.warn('[OrthoOverlay] Failed to fetch ortho thumbnail, status:', response.status);
				return;
			}

			const blob = await response.blob();
			console.debug('[OrthoOverlay] Thumbnail fetched, size:', blob.size);
			// Revoke previous URL if exists
			if (orthoOverlayUrl) {
				URL.revokeObjectURL(orthoOverlayUrl);
			}
			orthoOverlayUrl = URL.createObjectURL(blob);
			console.debug('[OrthoOverlay] Object URL created:', orthoOverlayUrl);
		} catch (error) {
			console.error('[OrthoOverlay] Failed to fetch ortho overlay:', error);
		}
	}

	// Fetch ortho overlay thumbnail when ortho path changes
	$: if (inputData.ortho?.path) {
		console.debug('[OrthoOverlay] Ortho path available:', inputData.ortho.path);
		fetchOrthoOverlay(inputData.ortho.path);
	}

	// Update ortho overlay bounds when available (may come from async hydration)
	$: if (inputData.ortho?.bounds_wgs84) {
		console.debug('[OrthoOverlay] Ortho bounds_wgs84 available:', inputData.ortho.bounds_wgs84);
		// Ensure bounds is a proper array
		orthoOverlayBounds = Array.isArray(inputData.ortho.bounds_wgs84)
			? inputData.ortho.bounds_wgs84 as [number, number, number, number]
			: null;
	}

	// Debug log for ortho state
	$: console.debug('[OrthoOverlay] State:', {
		hasOrthoPath: !!inputData.ortho?.path,
		hasBoundsWgs84: !!inputData.ortho?.bounds_wgs84,
		orthoOverlayUrl: !!orthoOverlayUrl,
		orthoOverlayBounds: orthoOverlayBounds,
		showOrthoOverlay
	});

	// Initialize camera params from store or EXIF on mount
	onMount(async () => {
		console.log('Camera setup mounted, inputData:', inputData);
		console.log('DSM bounds_wgs84:', inputData?.dsm?.bounds_wgs84);
		console.log('DSM CRS:', inputData?.dsm?.crs);

		const stored = wizardStore.getState().cameraParams;
		if (stored && stored.x !== 0 && stored.y !== 0) {
			// Restore from store
			console.log('Restoring camera params from store:', stored);
			cameraParams = { ...stored };
			initialized = true;
			// Fetch elevation for existing position
			fetchDsmElevation(cameraParams.x, cameraParams.y);
		} else if (suggestedParams) {
			// Use EXIF suggestions if no stored params (non-coordinate params only)
			console.log('Applying suggested params from EXIF:', suggestedParams);
			cameraParams = {
				...DEFAULT_CAMERA_PARAMS,
				...suggestedParams
			};
			saveCameraParams();
			initialized = true;
			// Apply EXIF coordinates with CRS transformation
			await applyExifCoordinates();
		} else {
			initialized = true;
		}
	});

	onDestroy(() => {
		// Cleanup ortho overlay URL
		if (orthoOverlayUrl) {
			URL.revokeObjectURL(orthoOverlayUrl);
		}
	});
</script>

<div class="camera-setup-page">
	<header class="page-header">
		<h1 class="page-title">{t('camera.title')}</h1>
		<p class="page-description">
			{t('camera.description')}
		</p>
	</header>

	{#if !hasRequiredData}
		<div class="warning-banner" role="alert">
			<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
				<line x1="12" y1="9" x2="12" y2="13" />
				<line x1="12" y1="17" x2="12.01" y2="17" />
			</svg>
			<span>{t('dataInput.completeFirst')}</span>
			<Button variant="secondary" size="sm" on:click={() => goto('/georectify/steps/data-input')}>
				{t('dataInput.goToDataInput')}
			</Button>
		</div>
	{:else}
		<!-- Top row: Map and Parameters -->
		<div class="top-row">
			<!-- Left: Map -->
			<div class="map-section">
				<Card noPadding>
					<svelte:fragment slot="header">
						<div class="map-header">
							<h2 class="section-title">{t('camera.position')}</h2>
							<div class="map-controls">
								<div class="base-layer-toggle">
									<button
										type="button"
										class="layer-btn"
										class:active={baseLayer === 'osm'}
										on:click={() => (baseLayer = 'osm')}
										title="OpenStreetMap"
									>
										<span class="layer-icon">🗺</span>
										<span class="layer-name">OSM</span>
									</button>
									<button
										type="button"
										class="layer-btn"
										class:active={baseLayer === 'gsi'}
										on:click={() => (baseLayer = 'gsi')}
										title={t('camera.gsiMap')}
									>
										<span class="layer-icon">🏔</span>
										<span class="layer-name">{t('camera.gsiLabel')}</span>
									</button>
								</div>
								{#if orthoOverlayUrl && orthoOverlayBounds}
									<label class="ortho-toggle">
										<input
											type="checkbox"
											bind:checked={showOrthoOverlay}
											class="toggle-checkbox"
										/>
										<span class="toggle-label">{t('camera.aerialPhoto')}</span>
									</label>
								{/if}
							</div>
						</div>
					</svelte:fragment>

					<div class="map-container">
						<MapView
							center={mapCenter}
							zoom={12}
							bounds={mapBounds}
							{baseLayer}
							on:load={handleMapLoad}
							on:click={handleMapClick}
						>
							{#if mapLoaded && map}
								{#if showOrthoOverlay && orthoOverlayUrl && orthoOverlayBounds}
									<RasterOverlay
										{map}
										imageUrl={orthoOverlayUrl}
										bounds={orthoOverlayBounds}
										opacity={orthoOverlayOpacity}
									/>
								{/if}
								{#if cameraPosition}
									<CameraMarker
										{map}
										position={cameraPosition}
										draggable
										on:move={handleMarkerMove}
									/>
									<FovCone
										{map}
										position={cameraPosition}
										pan={cameraParams.pan}
										fov={cameraParams.fov}
										distance={500}
										interactive
										on:change={handleFovChange}
									/>
								{/if}
							{/if}
						</MapView>
					</div>

					{#if cameraPosition}
						<div class="position-display">
							<span class="position-label">{t('camera.positionLabel')}</span>
							<span class="position-value">
								{cameraPosition[0].toFixed(6)}, {cameraPosition[1].toFixed(6)}
							</span>
						</div>
					{/if}
				</Card>
			</div>

			<!-- Right: Camera Parameters Form -->
			<div class="params-section">
				<Card>
					<svelte:fragment slot="header">
						<h2 class="section-title">{t('camera.parameters')}</h2>
					</svelte:fragment>

					<CameraParamsForm
						value={cameraParams}
						{suggestedParams}
						{dsmElevation}
						on:change={handleParamsChange}
					/>
				</Card>

				<!-- Rendering Distance Settings -->
				<Card>
					<svelte:fragment slot="header">
						<h2 class="section-title">{t('rendering.title')}</h2>
					</svelte:fragment>

					<div class="rendering-settings">
						<div class="setting-row">
							<label for="surface-distance" class="setting-label">
								{t('rendering.maxDistance')}
								<span class="setting-hint">{t('rendering.maxDistanceHint')}</span>
							</label>
							<input
								id="surface-distance"
								type="number"
								min="100"
								max="10000"
								step="100"
								bind:value={surfaceDistance}
								class="setting-input"
							/>
						</div>
						<div class="setting-row">
							<label for="min-distance" class="setting-label">
								{t('rendering.minDistance')}
								<span class="setting-hint">{t('rendering.minDistanceHint')}</span>
							</label>
							<input
								id="min-distance"
								type="number"
								min="0"
								max="1000"
								step="10"
								bind:value={simulationMinDistance}
								class="setting-input"
							/>
						</div>
					</div>
				</Card>
			</div>
		</div>

		<!-- Bottom row: Simulation Preview (full width) -->
		<div class="preview-section">
			<Card noPadding>
				<SimulationPreview
					dsmPath={inputData.dsm?.path ?? ''}
					orthoPath={inputData.ortho?.path ?? ''}
					targetImagePath={inputData.targetImage?.path ?? ''}
					{cameraParams}
					{surfaceDistance}
					initialImage={initialized ? storedSimulation : null}
					bind:hasSimulation
					on:generated={handleSimulationGenerated}
					on:cleared={handleSimulationCleared}
				/>
			</Card>
		</div>

		<!-- Navigation -->
		<footer class="page-footer">
			<Button variant="secondary" on:click={handleBack}>
				<span class="nav-arrow">&larr;</span>
				{t('common.back')}
			</Button>
			<Button variant="primary" disabled={!isValid} on:click={handleNext}>
				{t('common.next')}
				<span class="nav-arrow">&rarr;</span>
			</Button>
		</footer>
	{/if}
</div>

<style>
	.camera-setup-page {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		height: 100%;
		padding: 1rem;
	}

	.page-header {
		flex-shrink: 0;
	}

	.page-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--ink-900);
		margin: 0 0 0.25rem 0;
	}

	.page-description {
		font-size: 0.875rem;
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
		width: 20px;
		height: 20px;
		color: #f59e0b;
	}

	.warning-banner span {
		flex: 1;
	}

	.top-row {
		display: grid;
		grid-template-columns: 1fr 400px;
		gap: 1rem;
		min-height: 0;
	}

	.map-section {
		display: flex;
		flex-direction: column;
		min-height: 520px;
	}

	.map-section :global(.bg-white) {
		height: auto;
		display: flex;
		flex-direction: column;
	}

	.map-container {
		flex: 0 0 auto;
		width: 100%;
		aspect-ratio: 1 / 1;
	}

	.position-display {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background-color: rgba(255, 255, 255, 0.6);
		border-top: 1px solid var(--line);
		font-size: 0.875rem;
	}

	.position-label {
		color: var(--ink-500);
		font-weight: 500;
	}

	.position-value {
		font-family: monospace;
		color: var(--ink-900);
	}

	.params-section {
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		gap: 1rem;
	}

	.rendering-settings {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.setting-row {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.setting-label {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--ink-700);
	}

	.setting-hint {
		font-size: 0.75rem;
		font-weight: 400;
		color: var(--ink-400);
	}

	.setting-input {
		width: 100%;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--line);
		border-radius: 0.375rem;
		font-size: 0.875rem;
		color: var(--ink-900);
		background-color: white;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.setting-input:focus {
		outline: none;
		border-color: var(--primary-500);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.preview-section {
		flex-shrink: 0;
		min-height: 350px;
	}

	.preview-section :global(.bg-white) {
		height: 100%;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--ink-700);
		margin: 0;
	}

	.map-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
	}

	.map-controls {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.base-layer-toggle {
		display: flex;
		gap: 0.25rem;
		padding: 0.125rem;
		background: var(--ink-100);
		border-radius: 0.375rem;
	}

	.layer-btn {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.5rem;
		font-size: 0.7rem;
		font-weight: 500;
		background: transparent;
		color: var(--ink-500);
		border: 2px solid transparent;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.layer-btn:hover:not(.active) {
		background: var(--ink-50);
		color: var(--ink-700);
	}

	.layer-btn.active {
		background: white;
		color: var(--primary-700);
		border-color: var(--primary-500);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.layer-icon {
		font-size: 0.875rem;
		line-height: 1;
	}

	.layer-name {
		font-weight: 600;
	}

	.ortho-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-size: 0.75rem;
		color: var(--ink-600);
	}

	.toggle-checkbox {
		width: 1rem;
		height: 1rem;
		accent-color: var(--primary-600);
		cursor: pointer;
	}

	.toggle-label {
		user-select: none;
	}

	.page-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-top: 1rem;
		border-top: 1px solid var(--line);
		flex-shrink: 0;
	}

	.nav-arrow {
		display: inline-block;
		margin: 0 0.25rem;
	}

	/* Responsive layout for smaller screens */
	@media (max-width: 1024px) {
		.top-row {
			grid-template-columns: 1fr;
		}

		.map-section {
			min-height: 360px;
		}

		.map-container {
			min-height: 360px;
		}
	}
</style>
