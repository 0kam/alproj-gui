<!--
  ExportForm Component

  A form for configuring GeoTIFF export options:
  - Output file path
  - Resolution (meters per pixel)
  - Output CRS (EPSG code)
  - Interpolation toggle

  Usage:
    <ExportForm projectId={projectId} defaultCrs="EPSG:4326" on:export={handleExport} />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Button } from '$lib/components/common';
	import { saveGeoTiffDialog } from '$lib/services/file-dialog';
	import type { ExportRequest } from '$lib/types';

	/** Project ID for the export */
	export let projectId: string;
	/** Default CRS from the project */
	export let defaultCrs: string = 'EPSG:4326';
	/** Optional template raster path for georeferencing */
	export let templatePath: string | null = null;
	/** Whether the form is in submitting state */
	export let submitting: boolean = false;

	const dispatch = createEventDispatcher<{
		export: ExportRequest;
	}>();

	// Form state
	let outputPath = '';
	let resolution = 1.0;
	let interpolate = true;
	let maxDist: number | null = null;
	let crs = defaultCrs;

	// Validation
	$: if (defaultCrs) {
		crs = defaultCrs;
	}
	$: isValid = outputPath.trim() !== '' && resolution > 0 && crs.trim() !== '';

	function handleSubmit() {
		if (!isValid) return;

		const request: ExportRequest = {
			project_id: projectId,
			output_path: outputPath,
			resolution: resolution,
			crs: crs,
			interpolate: interpolate,
			max_dist: maxDist,
			template_path: templatePath
		};

		dispatch('export', request);
	}

	async function browseOutputPath() {
		const dateStr = new Date().toISOString().split('T')[0];
		const defaultName = `alproj_${dateStr}_georectified`;
		const selected = await saveGeoTiffDialog(defaultName);
		if (selected) {
			outputPath = selected;
		}
	}
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-6">
	<!-- Output Path -->
	<div>
		<label for="output-path" class="block text-sm font-medium text-gray-700 mb-1">
			出力ファイルパス
		</label>
		<div class="flex gap-2">
			<input
				type="text"
				id="output-path"
				bind:value={outputPath}
				placeholder="/path/to/output.tif"
				class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
				required
			/>
			<Button type="button" variant="secondary" on:click={browseOutputPath}>
				参照...
			</Button>
		</div>
		<p class="mt-1 text-xs text-gray-500">
			オルソ画像がGeoTIFFファイルとして保存されます。
		</p>
	</div>

	<!-- Resolution -->
	<div>
		<label for="resolution" class="block text-sm font-medium text-gray-700 mb-1">
			解像度（メートル/ピクセル）
		</label>
		<div class="flex items-center gap-2">
			<input
				type="number"
				id="resolution"
				bind:value={resolution}
				min="0.01"
				max="100"
				step="any"
				class="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				required
			/>
			<span class="text-sm text-gray-500">m/px</span>
		</div>
		<p class="mt-1 text-xs text-gray-500">
			値が小さいほど高解像度になりますが、ファイルサイズが大きくなります。
		</p>
	</div>

	<!-- CRS Display (fixed to DSM/Ortho CRS) -->
	<div>
		<label class="block text-sm font-medium text-gray-700 mb-1">
			出力座標参照系
		</label>
		<div class="px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm">
			{crs}
		</div>
		<p class="mt-1 text-xs text-gray-500">
			DSM/orthophotoと同じCRSで固定されます。
		</p>
	</div>

	<!-- Interpolation Toggle -->
	<div class="flex items-start gap-3">
		<input
			type="checkbox"
			id="interpolate"
			bind:checked={interpolate}
			class="mt-1 h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
		/>
		<div>
			<label for="interpolate" class="block text-sm font-medium text-gray-700">
				補間を有効化
			</label>
			<p class="text-xs text-gray-500">
				カメラから遠い領域では出力GeoTIFFに空白が生じます。有効にすると周囲の画素値から補間して空白を埋めます。
			</p>
		</div>
	</div>

	<!-- Max Interpolation Distance (only shown when interpolation is enabled) -->
	{#if interpolate}
		<div class="ml-7">
			<label for="max-dist" class="block text-sm font-medium text-gray-700 mb-1">
				最大補間距離（メートル）
			</label>
			<div class="flex items-center gap-2">
				<input
					type="number"
					id="max-dist"
					bind:value={maxDist}
					min="0.01"
					max="100"
					step="any"
					placeholder={String(resolution)}
					class="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				/>
				<span class="text-sm text-gray-500">m</span>
			</div>
			<p class="mt-1 text-xs text-gray-500">
				空白を埋める最大距離。空欄の場合は解像度と同じ値({resolution}m)が使用されます。
			</p>
		</div>
	{/if}

	<!-- Summary -->
	<div class="bg-gray-50 rounded-lg p-4">
		<h4 class="text-sm font-medium text-gray-700 mb-2">エクスポート概要</h4>
		<dl class="text-sm space-y-1">
			<div class="flex justify-between">
				<dt class="text-gray-500">出力:</dt>
				<dd class="text-gray-900 font-mono text-xs truncate max-w-xs" title={outputPath}>
					{outputPath || '（未設定）'}
				</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-gray-500">解像度:</dt>
				<dd class="text-gray-900">{resolution} m/px</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-gray-500">CRS:</dt>
				<dd class="text-gray-900 font-mono">{crs}</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-gray-500">補間:</dt>
				<dd class="text-gray-900">{interpolate ? '有効' : '無効'}</dd>
			</div>
			{#if interpolate}
				<div class="flex justify-between">
					<dt class="text-gray-500">最大補間距離:</dt>
					<dd class="text-gray-900">{maxDist ?? resolution} m</dd>
				</div>
			{/if}
		</dl>
	</div>

	<!-- Submit Button -->
	<div class="pt-4">
		<Button type="submit" variant="primary" fullWidth disabled={!isValid || submitting} loading={submitting}>
			{submitting ? 'エクスポート中...' : 'GeoTIFFをエクスポート'}
		</Button>
	</div>
</form>
