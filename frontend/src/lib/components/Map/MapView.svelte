<!--
  MapView Component

  A MapLibre GL JS map component for displaying geographic data.
  Supports custom center, zoom, and bounds.

  Usage:
    <MapView center={[139.6917, 35.6895]} zoom={10} />
    <MapView center={center} zoom={zoom} bounds={[xmin, ymin, xmax, ymax]} />
-->
<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';

	/** Center coordinates [longitude, latitude] */
	export let center: [number, number] = [138.7274, 35.3606]; // Mt. Fuji area default
	/** Zoom level (0-22) */
	export let zoom: number = 10;
	/** Bounds to fit [xmin, ymin, xmax, ymax] (WGS84) */
	export let bounds: [number, number, number, number] | null = null;
	/** Map style URL - defaults to GSI (Geospatial Information Authority of Japan) tiles */
	export let styleUrl: string | undefined = undefined;
	/** Whether to show attribution control */
	export let showAttribution: boolean = true;
	/** Whether to show navigation control */
	export let showNavigation: boolean = true;
	/** Base layer type */
	export let baseLayer: 'osm' | 'gsi' = 'osm';

	const dispatch = createEventDispatcher<{
		load: { map: maplibregl.Map };
		click: { lngLat: maplibregl.LngLat; point: maplibregl.Point };
		moveend: { center: maplibregl.LngLat; zoom: number };
	}>();

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map | null = null;
	let mapLoaded = false;
	let resizeObserver: ResizeObserver | null = null;
	let lastCenter: [number, number] | null = null;
	let lastZoom: number | null = null;
	let lastBounds: [number, number, number, number] | null = null;
	let pendingBounds: [number, number, number, number] | null = null;

	function centerChanged(next: [number, number]): boolean {
		if (!lastCenter) return true;
		return Math.abs(lastCenter[0] - next[0]) > 1e-7 || Math.abs(lastCenter[1] - next[1]) > 1e-7;
	}

	function zoomChanged(next: number): boolean {
		if (lastZoom === null) return true;
		return Math.abs(lastZoom - next) > 1e-6;
	}

	function boundsChanged(next: [number, number, number, number]): boolean {
		if (!lastBounds) return true;
		return (
			lastBounds[0] !== next[0] ||
			lastBounds[1] !== next[1] ||
			lastBounds[2] !== next[2] ||
			lastBounds[3] !== next[3]
		);
	}

	// Default style with both OSM and GSI sources
	const defaultStyle: maplibregl.StyleSpecification = {
		version: 8,
		sources: {
			osm: {
				type: 'raster',
				tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
				tileSize: 256,
				attribution:
					'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
			},
			gsi: {
				type: 'raster',
				tiles: ['https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png'],
				tileSize: 256,
				maxzoom: 18,
				attribution:
					'<a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
			}
		},
		layers: [
			{
				id: 'osm-layer',
				type: 'raster',
				source: 'osm',
				minzoom: 0,
				maxzoom: 22,
				layout: {
					visibility: 'visible'
				}
			},
			{
				id: 'gsi-layer',
				type: 'raster',
				source: 'gsi',
				minzoom: 0,
				maxzoom: 18,
				layout: {
					visibility: 'none'
				}
			}
		]
	};

	/**
	 * Switch base layer visibility
	 */
	function switchBaseLayer(layer: 'osm' | 'gsi'): void {
		if (!map || !map.isStyleLoaded()) return;

		const osmVisibility = layer === 'osm' ? 'visible' : 'none';
		const gsiVisibility = layer === 'gsi' ? 'visible' : 'none';

		if (map.getLayer('osm-layer')) {
			map.setLayoutProperty('osm-layer', 'visibility', osmVisibility);
		}
		if (map.getLayer('gsi-layer')) {
			map.setLayoutProperty('gsi-layer', 'visibility', gsiVisibility);
		}
	}

	// Expose map instance for parent components
	export function getMap(): maplibregl.Map | null {
		return map;
	}

	// Fit map to bounds
	export function fitBounds(
		boundsArray: [number, number, number, number],
		options?: maplibregl.FitBoundsOptions
	): void {
		if (!map) return;
		const lngLatBounds = new maplibregl.LngLatBounds(
			[boundsArray[0], boundsArray[1]],
			[boundsArray[2], boundsArray[3]]
		);
		map.fitBounds(lngLatBounds, { padding: 50, ...options });
	}

	// Fly to location
	export function flyTo(lng: number, lat: number, zoomLevel?: number): void {
		if (!map) return;
		map.flyTo({
			center: [lng, lat],
			zoom: zoomLevel ?? map.getZoom()
		});
	}

	onMount(() => {
		// Initialize map
		map = new maplibregl.Map({
			container: mapContainer,
			style: styleUrl || defaultStyle,
			center: center,
			zoom: zoom,
			attributionControl: showAttribution ? {} : false
		});

		// Add navigation control
		if (showNavigation) {
			map.addControl(new maplibregl.NavigationControl(), 'top-right');
		}

		// Handle map load
		map.on('load', () => {
			if (map) {
				mapLoaded = true;
				dispatch('load', { map });

				// Fit to bounds if provided (either from prop or pending from reactive statement)
				const boundsToFit = pendingBounds ?? bounds;
				if (boundsToFit) {
					fitBounds(boundsToFit);
					lastBounds = [...boundsToFit];
					pendingBounds = null;
				}
			}
		});

		// Handle map click
		map.on('click', (e) => {
			dispatch('click', {
				lngLat: e.lngLat,
				point: e.point
			});
		});

		// Handle move end
		map.on('moveend', () => {
			if (map) {
				dispatch('moveend', {
					center: map.getCenter(),
					zoom: map.getZoom()
				});
			}
		});

		// Set up resize observer for responsive behavior
		resizeObserver = new ResizeObserver(() => {
			if (map) {
				map.resize();
			}
		});
		resizeObserver.observe(mapContainer);
	});

	onDestroy(() => {
		if (resizeObserver) {
			resizeObserver.disconnect();
			resizeObserver = null;
		}
		if (map) {
			map.remove();
			map = null;
		}
	});

	// React to center changes
	$: if (map && center) {
		if (centerChanged(center)) {
			map.setCenter(center);
			lastCenter = [...center];
		}
	}

	// React to zoom changes
	$: if (map && zoom !== undefined) {
		if (zoomChanged(zoom)) {
			map.setZoom(zoom);
			lastZoom = zoom;
		}
	}

	// React to bounds changes
	$: if (map && bounds) {
		if (boundsChanged(bounds)) {
			if (mapLoaded) {
				fitBounds(bounds);
				lastBounds = [...bounds];
			} else {
				// Map not yet loaded, store bounds and fit when load completes
				pendingBounds = [...bounds];
			}
		}
	}

	// React to base layer changes
	$: if (map) {
		switchBaseLayer(baseLayer);
	}
</script>

<div class="map-container" bind:this={mapContainer}>
	<slot />
</div>

<style>
	.map-container {
		width: 100%;
		height: 100%;
		min-height: 300px;
	}

	.map-container :global(.maplibregl-map) {
		width: 100%;
		height: 100%;
	}
</style>
