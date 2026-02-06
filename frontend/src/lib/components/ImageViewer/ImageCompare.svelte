<!--
  ImageCompare Component

  A component for comparing two images using different view modes:
  - Slider: Split view with draggable divider
  - Overlay: Adjustable opacity overlay
  - Toggle: Switch between images

  Usage:
    <ImageCompare original="/path/to/original.jpg" processed="/path/to/processed.jpg" />
-->
<script lang="ts">
	/** URL or path to the original image */
	export let original: string | null;
	/** URL or path to the processed image */
	export let processed: string | null;
	/** Initial view mode */
	export let mode: 'slider' | 'overlay' | 'toggle' = 'slider';

	// State
	let sliderPosition = 50; // percentage
	let overlayOpacity = 0.5;
	let showProcessed = true;
	let isDragging = false;
	let containerRef: HTMLDivElement;
	let hasImages = false;

	function handleMouseDown() {
		isDragging = true;
	}

	function handleMouseUp() {
		isDragging = false;
	}

	function handleMouseMove(event: MouseEvent) {
		if (!isDragging || !containerRef) return;
		updateSliderPosition(event.clientX);
	}

	function handleTouchMove(event: TouchEvent) {
		if (!isDragging || !containerRef || event.touches.length === 0) return;
		event.preventDefault();
		updateSliderPosition(event.touches[0].clientX);
	}

	function updateSliderPosition(clientX: number) {
		const rect = containerRef.getBoundingClientRect();
		const x = clientX - rect.left;
		const percentage = (x / rect.width) * 100;
		sliderPosition = Math.min(100, Math.max(0, percentage));
	}

	function handleClick(event: MouseEvent) {
		if (!containerRef) return;
		updateSliderPosition(event.clientX);
	}

	function setMode(newMode: 'slider' | 'overlay' | 'toggle') {
		mode = newMode;
	}

	$: hasImages = Boolean(original && processed);
</script>

<svelte:window on:mouseup={handleMouseUp} on:mousemove={handleMouseMove} />

<div class="space-y-4">
	<!-- Mode Selector -->
	<div class="flex justify-center gap-2">
		<button
			class="px-4 py-2 text-sm font-medium rounded-md transition-colors {mode === 'slider'
				? 'bg-primary-600 text-white'
				: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			on:click={() => setMode('slider')}
		>
			スライダー
		</button>
		<button
			class="px-4 py-2 text-sm font-medium rounded-md transition-colors {mode === 'overlay'
				? 'bg-primary-600 text-white'
				: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			on:click={() => setMode('overlay')}
		>
			オーバーレイ
		</button>
		<button
			class="px-4 py-2 text-sm font-medium rounded-md transition-colors {mode === 'toggle'
				? 'bg-primary-600 text-white'
				: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			on:click={() => setMode('toggle')}
		>
			切り替え
		</button>
	</div>

	<!-- Image Container -->
	<div
		bind:this={containerRef}
		class="relative w-full aspect-video bg-gray-100 rounded-lg overflow-hidden select-none"
		role="img"
		aria-label="Image comparison viewer"
	>
		{#if hasImages}
			{#if mode === 'slider'}
				<!-- Slider Mode -->
				<div class="absolute inset-0">
					<!-- 処理後 (right/full) -->
					<img
						src={processed}
						alt="処理後"
						class="absolute inset-0 w-full h-full object-contain"
					/>
					<!-- 元画像 (left, clipped) -->
					<img
						src={original}
						alt="元画像"
						class="absolute inset-0 w-full h-full object-contain"
						style="clip-path: inset(0 {100 - sliderPosition}% 0 0);"
					/>
					<!-- Slider Handle -->
					<div
						class="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize"
						style="left: {sliderPosition}%;"
						on:mousedown={handleMouseDown}
						on:touchstart={() => (isDragging = true)}
						on:touchend={() => (isDragging = false)}
						on:touchcancel={() => (isDragging = false)}
						on:touchmove={handleTouchMove}
						role="slider"
						aria-valuenow={sliderPosition}
						aria-valuemin={0}
						aria-valuemax={100}
						tabindex="0"
					>
						<div
							class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center"
						>
							<svg
								class="w-4 h-4 text-gray-600"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 9l4-4 4 4m0 6l-4 4-4-4"
								/>
							</svg>
						</div>
					</div>
					<!-- Labels -->
					<div class="absolute top-2 left-2 px-2 py-1 bg-black/50 text-white text-xs rounded">
						元画像
					</div>
					<div class="absolute top-2 right-2 px-2 py-1 bg-black/50 text-white text-xs rounded">
						処理後
					</div>
				</div>
			{:else if mode === 'overlay'}
				<!-- Overlay Mode -->
				<div class="absolute inset-0">
					<img
						src={original}
						alt="元画像"
						class="absolute inset-0 w-full h-full object-contain"
					/>
					<img
						src={processed}
						alt="処理後"
						class="absolute inset-0 w-full h-full object-contain"
						style="opacity: {overlayOpacity};"
					/>
				</div>
				<!-- Opacity Control -->
				<div class="absolute bottom-4 left-4 right-4 bg-black/50 rounded-lg p-3">
					<div class="flex items-center gap-3">
						<span class="text-white text-xs">元画像</span>
						<input
							type="range"
							min="0"
							max="1"
							step="0.01"
							bind:value={overlayOpacity}
							class="flex-1 h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer"
						/>
						<span class="text-white text-xs">処理後</span>
					</div>
				</div>
			{:else if mode === 'toggle'}
				<!-- Toggle Mode -->
				<div class="absolute inset-0">
					{#if showProcessed}
						<img
							src={processed}
							alt="処理後"
							class="absolute inset-0 w-full h-full object-contain"
						/>
					{:else}
						<img
							src={original}
							alt="元画像"
							class="absolute inset-0 w-full h-full object-contain"
						/>
					{/if}
				</div>
				<!-- Toggle Button -->
				<button
					class="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-black/50 hover:bg-black/70 text-white text-sm rounded-lg transition-colors"
					on:click={() => (showProcessed = !showProcessed)}
				>
					表示中: {showProcessed ? '処理後' : '元画像'}
					<span class="ml-2 text-xs opacity-75">（クリックで切替）</span>
				</button>
			{/if}
		{:else}
			<div class="absolute inset-0 flex items-center justify-center text-sm text-gray-500">
				画像がありません。
			</div>
		{/if}
	</div>

	<!-- Legend -->
	<div class="flex justify-center gap-6 text-sm text-gray-600">
		<div class="flex items-center gap-2">
			<div class="w-3 h-3 bg-blue-500 rounded"></div>
			<span>元画像</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-3 h-3 bg-green-500 rounded"></div>
			<span>処理後（ジオレクティフィケーション済）</span>
		</div>
	</div>
</div>
