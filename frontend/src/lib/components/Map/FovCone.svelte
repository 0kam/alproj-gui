<!--
  FovCone Component

  Draws a field-of-view cone (sector) on the map representing
  the camera's viewing angle and direction.

  Usage:
    <FovCone {map} position={[139.6917, 35.6895]} pan={45} fov={60} distance={1000} />
-->
<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import maplibregl from 'maplibre-gl';

	/** MapLibre Map instance */
	export let map: maplibregl.Map;
	/** Camera position [longitude, latitude] */
	export let position: [number, number];
	/** Pan angle (bearing/azimuth) in degrees (0-360, 0=North) */
	export let pan: number = 0;
	/** Field of view angle in degrees */
	export let fov: number = 60;
	/** Distance of the cone in meters */
	export let distance: number = 500;
	/** Whether the cone handles are interactive */
	export let interactive: boolean = false;
	/** Distance of interactive handles in meters */
	export let handleDistance: number | null = null;
	/** Minimum FOV angle */
	export let minFov: number = 1;
	/** Maximum FOV angle */
	export let maxFov: number = 180;
	/** Fill color of the cone */
	export let fillColor: string = 'rgba(59, 130, 246, 0.3)'; // blue-500 with opacity
	/** Stroke color of the cone */
	export let strokeColor: string = '#3b82f6'; // blue-500
	/** Number of segments for smooth arc */
	export let segments: number = 32;

	const dispatch = createEventDispatcher<{
		change: { pan: number; fov: number };
	}>();

	const sourceId = `fov-cone-source-${Math.random().toString(36).substring(7)}`;
	const fillLayerId = `fov-cone-fill-${Math.random().toString(36).substring(7)}`;
	const lineLayerId = `fov-cone-line-${Math.random().toString(36).substring(7)}`;

	let isInitialized = false;
	let handlesInitialized = false;
	let panMarker: maplibregl.Marker | null = null;
	let fovMarker: maplibregl.Marker | null = null;
	let panMarkerElement: HTMLDivElement | null = null;
	let fovMarkerElement: HTMLDivElement | null = null;

	/**
	 * Calculate destination point given start point, bearing, and distance
	 * Uses Haversine formula
	 */
	function destinationPoint(
		lng: number,
		lat: number,
		bearing: number,
		dist: number
	): [number, number] {
		const R = 6371000; // Earth's radius in meters
		const d = dist / R; // Angular distance in radians
		const bearingRad = (bearing * Math.PI) / 180;
		const lat1 = (lat * Math.PI) / 180;
		const lng1 = (lng * Math.PI) / 180;

		const lat2 = Math.asin(
			Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(bearingRad)
		);
		const lng2 =
			lng1 +
			Math.atan2(
				Math.sin(bearingRad) * Math.sin(d) * Math.cos(lat1),
				Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
			);

		return [(lng2 * 180) / Math.PI, (lat2 * 180) / Math.PI];
	}

	function normalizeAngle(angle: number): number {
		return ((angle % 360) + 360) % 360;
	}

	function bearingBetween(
		fromLng: number,
		fromLat: number,
		toLng: number,
		toLat: number
	): number {
		const φ1 = (fromLat * Math.PI) / 180;
		const φ2 = (toLat * Math.PI) / 180;
		const Δλ = ((toLng - fromLng) * Math.PI) / 180;

		const y = Math.sin(Δλ) * Math.cos(φ2);
		const x =
			Math.cos(φ1) * Math.sin(φ2) -
			Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);

		const θ = Math.atan2(y, x);
		return normalizeAngle((θ * 180) / Math.PI);
	}

	function angleDiff(a: number, b: number): number {
		const diff = Math.abs(a - b) % 360;
		return diff > 180 ? 360 - diff : diff;
	}

	function clampFov(nextFov: number): number {
		return Math.min(maxFov, Math.max(minFov, nextFov));
	}

	function getHandleDistance(): number {
		if (handleDistance && handleDistance > 0) return handleDistance;
		return Math.max(distance * 0.7, 50);
	}

	function createHandleElement(kind: 'pan' | 'fov'): HTMLDivElement {
		const element = document.createElement('div');
		const color = kind === 'pan' ? '#2563eb' : '#f59e0b';
		element.className = `fov-handle fov-handle-${kind}`;
		element.title = kind === 'pan' ? 'Pan' : 'FOV';
		element.style.cssText = `
			width: 14px;
			height: 14px;
			border-radius: 999px;
			background: ${color};
			border: 2px solid #ffffff;
			box-shadow: 0 1px 4px rgba(0,0,0,0.3);
			cursor: grab;
		`;
		return element;
	}

	function updateHandlePositions(): void {
		if (!panMarker || !fovMarker) return;
		const handleDist = getHandleDistance();
		const panPos = destinationPoint(position[0], position[1], pan, handleDist);
		const fovBearing = normalizeAngle(pan + fov / 2);
		const fovPos = destinationPoint(position[0], position[1], fovBearing, handleDist);
		panMarker.setLngLat(panPos);
		fovMarker.setLngLat(fovPos);
	}

	function initializeHandles(): void {
		if (!map || handlesInitialized || !interactive) return;

		panMarkerElement = createHandleElement('pan');
		fovMarkerElement = createHandleElement('fov');

		panMarker = new maplibregl.Marker({
			element: panMarkerElement,
			draggable: true,
			anchor: 'center'
		})
			.setLngLat(position)
			.addTo(map);

		fovMarker = new maplibregl.Marker({
			element: fovMarkerElement,
			draggable: true,
			anchor: 'center'
		})
			.setLngLat(position)
			.addTo(map);

		panMarker.on('drag', () => {
			const lngLat = panMarker?.getLngLat();
			if (!lngLat) return;
			const nextPan = bearingBetween(position[0], position[1], lngLat.lng, lngLat.lat);
			dispatch('change', { pan: nextPan, fov });
		});

		fovMarker.on('drag', () => {
			const lngLat = fovMarker?.getLngLat();
			if (!lngLat) return;
			const handleBearing = bearingBetween(position[0], position[1], lngLat.lng, lngLat.lat);
			const nextFov = clampFov(2 * angleDiff(handleBearing, pan));
			dispatch('change', { pan, fov: nextFov });
		});

		updateHandlePositions();
		handlesInitialized = true;
	}

	function cleanupHandles(): void {
		if (panMarker) {
			panMarker.remove();
			panMarker = null;
		}
		if (fovMarker) {
			fovMarker.remove();
			fovMarker = null;
		}
		panMarkerElement = null;
		fovMarkerElement = null;
		handlesInitialized = false;
	}

	/**
	 * Generate GeoJSON polygon for the FOV cone
	 */
	function generateConeGeometry(): GeoJSON.Feature<GeoJSON.Polygon> {
		const coordinates: [number, number][] = [];

		// Start from camera position
		coordinates.push(position);

		// Calculate start and end bearings
		const startBearing = (pan - fov / 2 + 360) % 360;
		const endBearing = (pan + fov / 2 + 360) % 360;

		// Generate arc points
		for (let i = 0; i <= segments; i++) {
			let bearing: number;
			if (startBearing <= endBearing) {
				bearing = startBearing + (i / segments) * fov;
			} else {
				// Handle wrap-around (e.g., from 350 to 10 degrees)
				const totalAngle = fov;
				bearing = (startBearing + (i / segments) * totalAngle) % 360;
			}
			const point = destinationPoint(position[0], position[1], bearing, distance);
			coordinates.push(point);
		}

		// Close the polygon
		coordinates.push(position);

		return {
			type: 'Feature',
			properties: {},
			geometry: {
				type: 'Polygon',
				coordinates: [coordinates]
			}
		};
	}

	/**
	 * Update the cone geometry on the map
	 */
	function updateCone(): void {
		if (!map || !isInitialized) return;

		const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
		if (source) {
			source.setData(generateConeGeometry());
		}
	}

	/**
	 * Initialize the cone layers on the map
	 */
	function initializeCone(): void {
		if (!map) return;

		// Check if map is loaded
		if (!map.isStyleLoaded()) {
			map.once('load', initializeCone);
			return;
		}

		// Add source
		if (!map.getSource(sourceId)) {
			map.addSource(sourceId, {
				type: 'geojson',
				data: generateConeGeometry()
			});
		}

		// Add fill layer
		if (!map.getLayer(fillLayerId)) {
			map.addLayer({
				id: fillLayerId,
				type: 'fill',
				source: sourceId,
				paint: {
					'fill-color': fillColor,
					'fill-opacity': 1
				}
			});
		}

		// Add line layer for outline
		if (!map.getLayer(lineLayerId)) {
			map.addLayer({
				id: lineLayerId,
				type: 'line',
				source: sourceId,
				paint: {
					'line-color': strokeColor,
					'line-width': 2,
					'line-opacity': 0.8
				}
			});
		}

		isInitialized = true;
	}

	/**
	 * Clean up the cone layers
	 */
	function cleanup(): void {
		if (!map) return;

		try {
			if (map.getLayer(lineLayerId)) {
				map.removeLayer(lineLayerId);
			}
			if (map.getLayer(fillLayerId)) {
				map.removeLayer(fillLayerId);
			}
			if (map.getSource(sourceId)) {
				map.removeSource(sourceId);
			}
		} catch (e) {
			// Map might already be destroyed
		}

		isInitialized = false;
	}

	onMount(() => {
		if (map) {
			initializeCone();
			initializeHandles();
		}
	});

	onDestroy(() => {
		cleanup();
		cleanupHandles();
	});

	// React to position changes
	$: if (isInitialized && position) {
		updateCone();
	}

	// React to pan changes
	$: if (isInitialized && pan !== undefined) {
		updateCone();
	}

	// React to fov changes
	$: if (isInitialized && fov) {
		updateCone();
	}

	// React to distance changes
	$: if (isInitialized && distance) {
		updateCone();
	}

	// React to interactive toggle
	$: if (map && interactive) {
		initializeHandles();
		updateHandlePositions();
	}

	$: if (!interactive && handlesInitialized) {
		cleanupHandles();
	}

	// React to handle updates
	$: if (
		handlesInitialized &&
		position &&
		pan !== undefined &&
		fov !== undefined &&
		distance !== undefined &&
		handleDistance !== undefined
	) {
		updateHandlePositions();
	}

	// React to color changes
	$: if (isInitialized && map && fillColor) {
		try {
			if (map.getLayer(fillLayerId)) {
				map.setPaintProperty(fillLayerId, 'fill-color', fillColor);
			}
		} catch (e) {
			// Ignore if layer doesn't exist
		}
	}

	$: if (isInitialized && map && strokeColor) {
		try {
			if (map.getLayer(lineLayerId)) {
				map.setPaintProperty(lineLayerId, 'line-color', strokeColor);
			}
		} catch (e) {
			// Ignore if layer doesn't exist
		}
	}
</script>
