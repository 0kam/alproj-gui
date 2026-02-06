<!--
  CameraMarker Component

  A draggable marker representing camera position on the map.
  Displays a camera icon and emits position change events.

  Usage:
    <CameraMarker {map} position={[139.6917, 35.6895]} draggable on:move={handleMove} />
-->
<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import maplibregl from 'maplibre-gl';

	/** MapLibre Map instance */
	export let map: maplibregl.Map;
	/** Camera position [longitude, latitude] */
	export let position: [number, number];
	/** Whether the marker is draggable */
	export let draggable: boolean = true;
	/** Marker color */
	export let color: string = '#3b82f6'; // blue-500

	const dispatch = createEventDispatcher<{
		move: { lng: number; lat: number };
		dragstart: void;
		dragend: { lng: number; lat: number };
	}>();

	let marker: maplibregl.Marker | null = null;
	let markerElement: HTMLDivElement;

	// Create camera icon SVG
	function createCameraIcon(): HTMLDivElement {
		const container = document.createElement('div');
		container.className = 'camera-marker';
		container.innerHTML = `
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="32" height="32">
				<path d="M12 10.9c-.61 0-1.1.49-1.1 1.1s.49 1.1 1.1 1.1c.61 0 1.1-.49 1.1-1.1s-.49-1.1-1.1-1.1zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-1.24.29-2.41.78-3.47l1.93 1.93c-.13.39-.21.8-.21 1.24 0 1.93 1.57 3.5 3.5 3.5 1.93 0 3.5-1.57 3.5-3.5s-1.57-3.5-3.5-3.5c-.44 0-.85.08-1.24.21L6.83 5.57C8.09 4.57 9.97 4 12 4c4.41 0 8 3.59 8 8s-3.59 8-8 8z"/>
				<circle cx="12" cy="12" r="2" fill="${color}"/>
			</svg>
		`;
		// Add styles
		container.style.cssText = `
			cursor: ${draggable ? 'grab' : 'default'};
			transition: transform 0.1s ease;
		`;
		return container;
	}

	// Update marker position
	export function setPosition(lng: number, lat: number): void {
		if (marker) {
			marker.setLngLat([lng, lat]);
		}
	}

	onMount(() => {
		if (!map) return;

		// Create custom marker element
		markerElement = createCameraIcon();

		// Create marker
		marker = new maplibregl.Marker({
			element: markerElement,
			draggable: draggable,
			anchor: 'center'
		})
			.setLngLat(position)
			.addTo(map);

		// Handle drag events
		if (draggable) {
			marker.on('dragstart', () => {
				if (markerElement) {
					markerElement.style.cursor = 'grabbing';
					markerElement.style.transform = 'scale(1.1)';
				}
				dispatch('dragstart');
			});

			marker.on('drag', () => {
				const lngLat = marker?.getLngLat();
				if (lngLat) {
					dispatch('move', { lng: lngLat.lng, lat: lngLat.lat });
				}
			});

			marker.on('dragend', () => {
				if (markerElement) {
					markerElement.style.cursor = 'grab';
					markerElement.style.transform = 'scale(1)';
				}
				const lngLat = marker?.getLngLat();
				if (lngLat) {
					dispatch('dragend', { lng: lngLat.lng, lat: lngLat.lat });
				}
			});
		}
	});

	onDestroy(() => {
		if (marker) {
			marker.remove();
			marker = null;
		}
	});

	// React to position changes from parent
	$: if (marker && position) {
		const currentPos = marker.getLngLat();
		if (currentPos.lng !== position[0] || currentPos.lat !== position[1]) {
			marker.setLngLat(position);
		}
	}

	// React to draggable changes
	$: if (marker) {
		marker.setDraggable(draggable);
		if (markerElement) {
			markerElement.style.cursor = draggable ? 'grab' : 'default';
		}
	}
</script>
