<!--
  GCP Table Component (T061)

  Displays a table of Ground Control Points with:
  - ID, image coordinates, geographic coordinates, residual, enabled toggle
  - Sortable by residual
  - High residual highlighting
  - Toggle and select events

  Usage:
    <GcpTable {gcps} editable on:toggle={handleToggle} on:select={handleSelect} />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { GCP } from '$lib/types';

	/** List of Ground Control Points */
	export let gcps: GCP[] = [];
	/** Whether GCPs can be toggled/edited */
	export let editable: boolean = true;
	/** Currently selected GCP ID */
	export let selectedId: number | null = null;
	/** Residual threshold for high residual warning (pixels) */
	export let highResidualThreshold: number = 3;

	const dispatch = createEventDispatcher<{
		toggle: { id: number; enabled: boolean };
		select: { id: number };
	}>();

	// Sort state
	type SortField = 'id' | 'residual' | 'image_x' | 'geo_x';
	type SortOrder = 'asc' | 'desc';
	let sortField: SortField = 'id';
	let sortOrder: SortOrder = 'asc';

	// Sorted GCPs
	$: sortedGcps = [...gcps].sort((a, b) => {
		let aVal: number;
		let bVal: number;

		switch (sortField) {
			case 'id':
				aVal = a.id;
				bVal = b.id;
				break;
			case 'residual':
				aVal = a.residual ?? Infinity;
				bVal = b.residual ?? Infinity;
				break;
			case 'image_x':
				aVal = a.image_x;
				bVal = b.image_x;
				break;
			case 'geo_x':
				aVal = a.geo_x;
				bVal = b.geo_x;
				break;
			default:
				aVal = a.id;
				bVal = b.id;
		}

		if (sortOrder === 'asc') {
			return aVal - bVal;
		} else {
			return bVal - aVal;
		}
	});

	function toggleSort(field: SortField): void {
		if (sortField === field) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortField = field;
			sortOrder = 'asc';
		}
	}

	function getSortIcon(field: SortField): string {
		if (sortField !== field) return '↕';
		return sortOrder === 'asc' ? '↑' : '↓';
	}

	function getResidualClass(residual: number | undefined): string {
		if (residual === undefined) return 'text-gray-500';
		if (residual < 1) return 'text-green-600 font-medium';
		if (residual < highResidualThreshold) return 'text-yellow-600';
		return 'text-red-600 font-bold';
	}

	function isHighResidual(residual: number | undefined): boolean {
		return residual !== undefined && residual >= highResidualThreshold;
	}

	function handleToggle(gcp: GCP): void {
		if (!editable) return;
		dispatch('toggle', { id: gcp.id, enabled: !gcp.enabled });
	}

	function handleSelect(gcp: GCP): void {
		dispatch('select', { id: gcp.id });
	}
</script>

<div class="gcp-table-container overflow-x-auto">
	<table class="min-w-full divide-y divide-gray-200 text-sm">
		<thead class="bg-gray-50">
			<tr>
				<th
					class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
					on:click={() => toggleSort('id')}
				>
					<span class="inline-flex items-center gap-1">
						ID
						<span class="text-gray-400">{getSortIcon('id')}</span>
					</span>
				</th>
				<th
					class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
					on:click={() => toggleSort('image_x')}
				>
					<span class="inline-flex items-center gap-1">
						画像 (px)
						<span class="text-gray-400">{getSortIcon('image_x')}</span>
					</span>
				</th>
				<th
					class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
					on:click={() => toggleSort('geo_x')}
				>
					<span class="inline-flex items-center gap-1">
						地理座標
						<span class="text-gray-400">{getSortIcon('geo_x')}</span>
					</span>
				</th>
				<th
					class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
					on:click={() => toggleSort('residual')}
				>
					<span class="inline-flex items-center gap-1">
						残差
						<span class="text-gray-400">{getSortIcon('residual')}</span>
					</span>
				</th>
				<th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
					状態
				</th>
			</tr>
		</thead>
		<tbody class="bg-white divide-y divide-gray-200">
			{#each sortedGcps as gcp (gcp.id)}
				<tr
					class="transition-colors duration-150
						{gcp.enabled ? '' : 'opacity-50 bg-gray-50'}
						{selectedId === gcp.id ? 'ring-2 ring-inset ring-primary-500 bg-primary-50' : ''}
						{isHighResidual(gcp.residual) && gcp.enabled ? 'bg-red-50' : ''}
						hover:bg-gray-100 cursor-pointer"
					on:click={() => handleSelect(gcp)}
				>
					<td class="px-3 py-2 whitespace-nowrap font-mono text-gray-900">
						{gcp.id}
					</td>
					<td class="px-3 py-2 whitespace-nowrap font-mono text-gray-700">
						{gcp.image_x.toFixed(1)}, {gcp.image_y.toFixed(1)}
					</td>
					<td class="px-3 py-2 whitespace-nowrap font-mono text-gray-700">
						<span title="経度: {gcp.geo_x.toFixed(6)}, 緯度: {gcp.geo_y.toFixed(6)}, 標高: {gcp.geo_z.toFixed(1)}m">
							{gcp.geo_x.toFixed(4)}, {gcp.geo_y.toFixed(4)}
						</span>
					</td>
					<td class="px-3 py-2 whitespace-nowrap font-mono {getResidualClass(gcp.residual)}">
						{#if gcp.residual !== undefined}
							{gcp.residual.toFixed(2)} px
							{#if isHighResidual(gcp.residual)}
								<span class="ml-1" title="残差が大きい">⚠</span>
							{/if}
						{:else}
							<span class="text-gray-400">-</span>
						{/if}
					</td>
					<td class="px-3 py-2 whitespace-nowrap">
						{#if editable}
							<button
								type="button"
								class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
									{gcp.enabled ? 'bg-green-500' : 'bg-gray-300'}"
								role="switch"
								aria-checked={gcp.enabled}
								on:click|stopPropagation={() => handleToggle(gcp)}
							>
								<span class="sr-only">Toggle GCP {gcp.id}</span>
								<span
									class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
										{gcp.enabled ? 'translate-x-5' : 'translate-x-0'}"
								></span>
							</button>
						{:else}
							{#if gcp.enabled}
								<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
									有効
								</span>
							{:else}
								<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
									無効
								</span>
							{/if}
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	{#if gcps.length === 0}
		<div class="py-8 text-center text-gray-500">
			地上基準点 (GCP) がありません
		</div>
	{/if}
</div>

<!-- Summary -->
<div class="mt-3 text-sm text-gray-600 flex justify-between items-center">
	<span>
		{gcps.length}個中{gcps.filter((g) => g.enabled).length}個のGCPが有効
	</span>
	{#if gcps.some((g) => isHighResidual(g.residual) && g.enabled)}
		<span class="text-yellow-600">
			⚠ {gcps.filter((g) => isHighResidual(g.residual) && g.enabled).length}個のGCPの残差が大きい
		</span>
	{/if}
</div>

<style>
	.gcp-table-container {
		max-height: 400px;
		overflow-y: auto;
	}
</style>
