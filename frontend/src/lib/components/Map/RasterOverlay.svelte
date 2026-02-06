<!--
  RasterOverlay Component

  Adds a raster image overlay to a MapLibre map using an image source.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import maplibregl from 'maplibre-gl';

	/** MapLibre Map instance */
	export let map: maplibregl.Map;
	/** Image URL (object URL or data URL) */
	export let imageUrl: string | null = null;
	/** Bounds in WGS84 [xmin, ymin, xmax, ymax] */
	export let bounds: [number, number, number, number] | null = null;
	/** Overlay opacity */
	export let opacity: number = 0.7;

	const sourceId = `raster-overlay-${Math.random().toString(36).slice(2)}`;
	const layerId = `${sourceId}-layer`;

	// Track if component is destroyed to prevent operations on unmounted component
	let isDestroyed = false;
	// Track pending styledata listener for cleanup
	let pendingStyleListener: (() => void) | null = null;

	function removeOverlay(): void {
		if (!map) return;
		try {
			if (map.getLayer(layerId)) {
				map.removeLayer(layerId);
			}
			if (map.getSource(sourceId)) {
				map.removeSource(sourceId);
			}
		} catch (error) {
			// Map may already be removed, ignore errors
			console.debug('[RasterOverlay] removeOverlay error (map may be destroyed):', error);
		}
	}

	function cleanupStyleListener(): void {
		if (pendingStyleListener && map) {
			try {
				map.off('styledata', pendingStyleListener);
			} catch {
				// Ignore errors if map is already destroyed
			}
			pendingStyleListener = null;
		}
	}

	function addOverlay(): void {
		// Don't proceed if component is destroyed
		if (isDestroyed) {
			console.debug('[RasterOverlay] addOverlay skipped: component destroyed');
			return;
		}

		if (!map || !imageUrl || !bounds) {
			console.debug('[RasterOverlay] addOverlay skipped:', { map: !!map, imageUrl: !!imageUrl, bounds });
			return;
		}

		if (!map.isStyleLoaded()) {
			console.debug('[RasterOverlay] Map style not loaded, waiting...');
			// Clean up any existing listener before adding new one
			cleanupStyleListener();
			// Create a wrapper to track the listener
			pendingStyleListener = () => addOverlay();
			map.once('styledata', pendingStyleListener);
			return;
		}

		// Style is loaded, clear any pending listener
		cleanupStyleListener();

		console.debug('[RasterOverlay] Adding overlay:', { bounds, imageUrl: imageUrl.slice(0, 50) });
		removeOverlay();

		const [minLng, minLat, maxLng, maxLat] = bounds;
		try {
			map.addSource(sourceId, {
				type: 'image',
				url: imageUrl,
				coordinates: [
					[minLng, maxLat],
					[maxLng, maxLat],
					[maxLng, minLat],
					[minLng, minLat]
				]
			});

			map.addLayer({
				id: layerId,
				type: 'raster',
				source: sourceId,
				paint: {
					'raster-opacity': opacity
				}
			});
			console.debug('[RasterOverlay] Overlay added successfully');
		} catch (error) {
			console.error('[RasterOverlay] Failed to add overlay:', error);
		}
	}

	$: {
		if (map && imageUrl && bounds) {
			addOverlay();
		} else if (map) {
			removeOverlay();
		}
	}

	onDestroy(() => {
		isDestroyed = true;
		cleanupStyleListener();
		removeOverlay();
	});
</script>

<!-- This component renders imperatively via MapLibre -->
