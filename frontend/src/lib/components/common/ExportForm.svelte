<!--
  ExportForm Component

  A form for configuring GeoTIFF export options:
  - Output mode (current / single / batch)
  - Output path or batch destination settings
  - Resolution (meters per pixel)
  - Output CRS (EPSG code)
  - Interpolation toggle

  Usage:
    <ExportForm projectId={projectId} defaultCrs="EPSG:4326" on:export={handleExport} />
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Button } from '$lib/components/common';
	import {
		openDirectoryDialog,
		openImageDialog,
		openImageDialogs,
		saveGeoTiffDialog
	} from '$lib/services/file-dialog';
	import type { ExportRequest } from '$lib/types';

	type ExportMode = 'current' | 'single' | 'batch';

	/** Project ID for the export */
	export let projectId: string;
	/** Default CRS from the project */
	export let defaultCrs: string = 'EPSG:4326';
	/** Optional template raster path for georeferencing */
	export let templatePath: string | null = null;
	/** Target image path used to build default output filename */
	export let targetImagePath: string | null = null;
	/** Whether the form is in submitting state */
	export let submitting: boolean = false;

	const dispatch = createEventDispatcher<{
		export: ExportRequest;
	}>();

	// Form state
	let mode: ExportMode = 'current';
	let outputPath = '';
	let singleTargetImagePath = '';
	let batchTargetImagePaths: string[] = [];
	let batchOutputDir = '';
	let batchNameTemplate = '{name}_alproj_{date}';
	let resolution = 1.0;
	let interpolate = true;
	let maxDist: number | null = null;
	let crs = defaultCrs;

	// Validation
	$: if (defaultCrs) {
		crs = defaultCrs;
	}
	$: baseValid = resolution > 0 && crs.trim() !== '';
	$: isValid =
		baseValid &&
		(mode === 'current'
			? outputPath.trim() !== ''
			: mode === 'single'
				? singleTargetImagePath.trim() !== '' && outputPath.trim() !== ''
				: batchTargetImagePaths.length > 0 &&
					batchOutputDir.trim() !== '' &&
					batchNameTemplate.trim() !== '');

	function getDateStamp(): string {
		const now = new Date();
		const yyyy = String(now.getFullYear());
		const mm = String(now.getMonth() + 1).padStart(2, '0');
		const dd = String(now.getDate()).padStart(2, '0');
		return `${yyyy}${mm}${dd}`;
	}

	function getTargetImageStem(path: string | null): string {
		if (!path) return 'target';
		const filename = path.split(/[/\\]/).pop() ?? 'target';
		const stem = filename.replace(/\.[^/.]+$/, '').trim();
		return stem || 'target';
	}

	function getDefaultOutputName(path: string | null): string {
		const dateStr = getDateStamp();
		const targetStem = getTargetImageStem(path);
		return `${targetStem}_alproj_${dateStr}`;
	}

	function ensureTiffName(name: string): string {
		if (/\.(tif|tiff)$/i.test(name)) {
			return name;
		}
		return `${name}.tiff`;
	}

	function buildBatchPreviewNames(): string[] {
		const date = getDateStamp();
		return batchTargetImagePaths.slice(0, 3).map((path, index) => {
			const stem = getTargetImageStem(path);
			const raw = batchNameTemplate
				.replaceAll('{name}', stem)
				.replaceAll('{date}', date)
				.replaceAll('{index}', String(index + 1).padStart(3, '0'));
			return ensureTiffName(raw);
		});
	}

	function handleSubmit() {
		if (!isValid) return;

		const request: ExportRequest = {
			project_id: projectId,
			resolution: resolution,
			crs: crs,
			interpolate: interpolate,
			max_dist: maxDist,
			template_path: templatePath
		};

		if (mode === 'current') {
			request.output_path = outputPath;
		} else if (mode === 'single') {
			request.output_path = outputPath;
			request.target_image_path = singleTargetImagePath;
		} else {
			request.output_path = null;
			request.target_image_paths = batchTargetImagePaths;
			request.output_dir = batchOutputDir;
			request.output_name_template = batchNameTemplate;
		}

		dispatch('export', request);
	}

	async function browseOutputPath() {
		const sourcePath = mode === 'single' ? singleTargetImagePath : targetImagePath;
		const selected = await saveGeoTiffDialog(getDefaultOutputName(sourcePath));
		if (selected) {
			outputPath = selected;
		}
	}

	async function browseSingleTargetImage() {
		const selected = await openImageDialog();
		if (selected) {
			singleTargetImagePath = selected;
		}
	}

	async function browseBatchTargetImages() {
		const selected = await openImageDialogs();
		if (selected.length > 0) {
			batchTargetImagePaths = [...new Set(selected)];
		}
	}

	async function browseBatchOutputDir() {
		const selected = await openDirectoryDialog('GeoTIFF出力フォルダを選択');
		if (selected) {
			batchOutputDir = selected;
		}
	}
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-6">
	<div>
		<p class="block text-sm font-medium text-gray-700 mb-2">
			適用対象
		</p>
		<div class="space-y-2">
			<label class="flex items-start gap-2 text-sm text-gray-700">
				<input type="radio" bind:group={mode} value="current" class="mt-1" />
				<span>現在のターゲット画像に出力</span>
			</label>
			<label class="flex items-start gap-2 text-sm text-gray-700">
				<input type="radio" bind:group={mode} value="single" class="mt-1" />
				<span>別の画像1枚に適用して出力</span>
			</label>
			<label class="flex items-start gap-2 text-sm text-gray-700">
				<input type="radio" bind:group={mode} value="batch" class="mt-1" />
				<span>複数画像に一括適用して出力</span>
			</label>
		</div>
		{#if mode === 'current'}
			<p class="mt-2 text-xs text-gray-500 font-mono break-all">
				対象: {targetImagePath || '（未設定）'}
			</p>
		{/if}
	</div>

	{#if mode === 'single'}
		<div>
			<label for="single-target-image" class="block text-sm font-medium text-gray-700 mb-1">
				適用先画像
			</label>
			<div class="flex gap-2">
				<input
					type="text"
					id="single-target-image"
					bind:value={singleTargetImagePath}
					placeholder="/path/to/target.jpg"
					class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
					required={mode === 'single'}
				/>
				<Button type="button" variant="secondary" on:click={browseSingleTargetImage}>
					参照...
				</Button>
			</div>
		</div>
	{/if}

	{#if mode === 'batch'}
		<div class="space-y-4">
			<div>
				<p class="block text-sm font-medium text-gray-700 mb-1">適用先画像（複数）</p>
				<div class="flex gap-2">
					<input
						type="text"
						value={batchTargetImagePaths.length > 0
							? `${batchTargetImagePaths.length} 件選択済み`
							: ''}
						placeholder="画像を複数選択してください"
						class="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm"
						readonly
					/>
					<Button type="button" variant="secondary" on:click={browseBatchTargetImages}>
						複数選択...
					</Button>
				</div>
				{#if batchTargetImagePaths.length > 0}
					<div class="mt-2 text-xs text-gray-500 space-y-1 max-h-24 overflow-auto">
						{#each batchTargetImagePaths.slice(0, 10) as path}
							<div class="font-mono break-all">{path}</div>
						{/each}
						{#if batchTargetImagePaths.length > 10}
							<div>...他 {batchTargetImagePaths.length - 10} 件</div>
						{/if}
					</div>
				{/if}
			</div>

			<div>
				<label for="batch-output-dir" class="block text-sm font-medium text-gray-700 mb-1">
					出力フォルダ
				</label>
				<div class="flex gap-2">
					<input
						type="text"
						id="batch-output-dir"
						bind:value={batchOutputDir}
						placeholder="/path/to/output_directory"
						class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
						required={mode === 'batch'}
					/>
					<Button type="button" variant="secondary" on:click={browseBatchOutputDir}>
						参照...
					</Button>
				</div>
			</div>

			<div>
				<label for="batch-name-template" class="block text-sm font-medium text-gray-700 mb-1">
					出力名テンプレート
				</label>
				<input
					type="text"
					id="batch-name-template"
					bind:value={batchNameTemplate}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
					required={mode === 'batch'}
				/>
				<p class="mt-1 text-xs text-gray-500">
					使用可能: {'{name}'} {'{date}'} {'{index}'}（例: {'{name}_alproj_{date}'}）
				</p>
				{#if batchTargetImagePaths.length > 0}
					<div class="mt-1 text-xs text-gray-500 space-y-1">
						{#each buildBatchPreviewNames() as preview}
							<div class="font-mono">{preview}</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	{#if mode !== 'batch'}
		<div>
			<label for="output-path" class="block text-sm font-medium text-gray-700 mb-1">
				出力ファイルパス
			</label>
			<div class="flex gap-2">
				<input
					type="text"
					id="output-path"
					bind:value={outputPath}
					placeholder="/path/to/output.tiff"
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
	{/if}

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
		<p class="block text-sm font-medium text-gray-700 mb-1">
			出力座標参照系
		</p>
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
				<dt class="text-gray-500">モード:</dt>
				<dd class="text-gray-900">
					{mode === 'current' ? '現在画像' : mode === 'single' ? '別画像1枚' : '複数画像'}
				</dd>
			</div>
			{#if mode !== 'batch'}
				<div class="flex justify-between">
					<dt class="text-gray-500">出力:</dt>
					<dd class="text-gray-900 font-mono text-xs truncate max-w-xs" title={outputPath}>
						{outputPath || '（未設定）'}
					</dd>
				</div>
			{:else}
				<div class="flex justify-between">
					<dt class="text-gray-500">対象数:</dt>
					<dd class="text-gray-900">{batchTargetImagePaths.length} 件</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-gray-500">出力フォルダ:</dt>
					<dd class="text-gray-900 font-mono text-xs truncate max-w-xs" title={batchOutputDir}>
						{batchOutputDir || '（未設定）'}
					</dd>
				</div>
			{/if}
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
