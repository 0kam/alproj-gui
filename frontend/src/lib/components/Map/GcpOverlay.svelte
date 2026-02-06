<!--
  GCP Overlay Component (T062)

  Displays GCP markers on a MapLibre GL map.
  - Enabled GCPs: green markers
  - Disabled GCPs: red markers
  - Selected GCP: enlarged marker

  Usage:
    <GcpOverlay {map} {gcps} selectedId={1} on:select={handleSelect} />
-->
<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import type { GCP } from '$lib/types';

	/** MapLibre Map instance */
	export let map: maplibregl.Map;
	/** List of Ground Control Points */
	export let gcps: GCP[] = [];
	/** Currently selected GCP ID */
	export let selectedId: number | null = null;
	/** Whether to show disabled GCPs */
	export let showDisabled: boolean = true;

	const dispatch = createEventDispatcher<{
		select: { id: number };
	}>();

	// Store marker instances for cleanup
	let markers: Map<number, maplibregl.Marker> = new Map();

	// Marker sizes
	const MARKER_SIZE = 14;
	const SELECTED_MARKER_SIZE = 22;

	// Colors
	const ENABLED_COLOR = '#22c55e'; // green-500
	const DISABLED_COLOR = '#ef4444'; // red-500
	const SELECTED_BORDER = '#2563eb'; // blue-600

	function createMarkerElement(gcp: GCP, isSelected: boolean): HTMLDivElement {
		const size = isSelected ? SELECTED_MARKER_SIZE : MARKER_SIZE;
		const color = gcp.enabled ? ENABLED_COLOR : DISABLED_COLOR;

		const container = document.createElement('div');
		container.className = 'gcp-marker';
		container.style.cssText = `
			width: ${size}px;
			height: ${size}px;
			cursor: pointer;
			transition: transform 0.15s ease;
		`;

		// Create SVG marker
		container.innerHTML = `
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}">
				<circle cx="12" cy="12" r="10" fill="${color}" stroke="${isSelected ? SELECTED_BORDER : 'white'}" stroke-width="${isSelected ? 3 : 2}" />
				<text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">${gcp.id}</text>
			</svg>
		`;

		// Add tooltip
		container.title = `GCP ${gcp.id}\nImage: (${gcp.image_x.toFixed(1)}, ${gcp.image_y.toFixed(1)})\nGeo: (${gcp.geo_x.toFixed(6)}, ${gcp.geo_y.toFixed(6)})\n${gcp.residual !== undefined ? `Residual: ${gcp.residual.toFixed(2)} px` : ''}\nStatus: ${gcp.enabled ? 'Enabled' : 'Disabled'}`;

		return container;
	}

	function updateMarkers(): void {
		if (!map) return;

		// Remove markers that are no longer in the GCP list or should be hidden
		const gcpIds = new Set(gcps.filter((g) => showDisabled || g.enabled).map((g) => g.id));
		for (const [id, marker] of markers) {
			if (!gcpIds.has(id)) {
				marker.remove();
				markers.delete(id);
			}
		}

		// Add or update markers
		for (const gcp of gcps) {
			if (!showDisabled && !gcp.enabled) continue;

			const isSelected = selectedId === gcp.id;
			const existingMarker = markers.get(gcp.id);

			if (existingMarker) {
				// Update existing marker
				const currentElement = existingMarker.getElement();
				const newElement = createMarkerElement(gcp, isSelected);

				// Replace element content
				currentElement.innerHTML = newElement.innerHTML;
				currentElement.style.width = newElement.style.width;
				currentElement.style.height = newElement.style.height;
				currentElement.title = newElement.title;

				// Update position if changed
				const currentPos = existingMarker.getLngLat();
				if (currentPos.lng !== gcp.geo_x || currentPos.lat !== gcp.geo_y) {
					existingMarker.setLngLat([gcp.geo_x, gcp.geo_y]);
				}
			} else {
				// Create new marker
				const element = createMarkerElement(gcp, isSelected);

				const marker = new maplibregl.Marker({
					element,
					anchor: 'center'
				})
					.setLngLat([gcp.geo_x, gcp.geo_y])
					.addTo(map);

				// Click handler
				element.addEventListener('click', (e) => {
					e.stopPropagation();
					dispatch('select', { id: gcp.id });
				});

				// Hover effect
				element.addEventListener('mouseenter', () => {
					element.style.transform = 'scale(1.2)';
				});
				element.addEventListener('mouseleave', () => {
					element.style.transform = 'scale(1)';
				});

				markers.set(gcp.id, marker);
			}
		}
	}

	// Fly to selected GCP
	export function flyToSelected(): void {
		if (!map || selectedId === null) return;

		const gcp = gcps.find((g) => g.id === selectedId);
		if (gcp) {
			map.flyTo({
				center: [gcp.geo_x, gcp.geo_y],
				zoom: Math.max(map.getZoom(), 14)
			});
		}
	}

	// Fit map to show all GCPs
	export function fitToGcps(): void {
		if (!map || gcps.length === 0) return;

		const enabledGcps = gcps.filter((g) => g.enabled);
		const targetGcps = enabledGcps.length > 0 ? enabledGcps : gcps;

		if (targetGcps.length === 0) return;

		const bounds = new maplibregl.LngLatBounds();
		for (const gcp of targetGcps) {
			bounds.extend([gcp.geo_x, gcp.geo_y]);
		}

		map.fitBounds(bounds, { padding: 50 });
	}

	onMount(() => {
		if (map) {
			// Wait for map to be ready
			if (map.loaded()) {
				updateMarkers();
			} else {
				map.on('load', updateMarkers);
			}
		}
	});

	onDestroy(() => {
		// Cleanup all markers
		for (const marker of markers.values()) {
			marker.remove();
		}
		markers.clear();
	});

	// React to changes
	$: if (map) {
		updateMarkers();
	}

	// React to gcps changes
	$: gcps, updateMarkers();

	// React to selectedId changes
	$: selectedId, updateMarkers();

	// React to showDisabled changes
	$: showDisabled, updateMarkers();
</script>

<!-- This component renders markers imperatively via MapLibre -->
