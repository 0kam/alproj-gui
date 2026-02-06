<!--
  ProcessLog Component

  A scrollable log viewer with auto-scroll functionality.
  Displays process logs with timestamps and different log levels.

  Usage:
    <ProcessLog logs={['Starting process...', 'Step 1 complete', 'Error: Something went wrong']} />
-->
<script lang="ts">
	import { afterUpdate } from 'svelte';

	/** Array of log messages to display */
	export let logs: string[] = [];
	/** Maximum height of the log container */
	export let maxHeight: string = '300px';
	/** Auto scroll to bottom when new logs are added */
	export let autoScroll: boolean = true;

	let logContainer: HTMLDivElement;
	let userScrolled = false;

	// Auto scroll to bottom when new logs arrive
	afterUpdate(() => {
		if (autoScroll && logContainer && !userScrolled) {
			logContainer.scrollTop = logContainer.scrollHeight;
		}
	});

	function handleScroll() {
		if (!logContainer) return;
		// Check if user has scrolled away from bottom
		const isAtBottom =
			logContainer.scrollHeight - logContainer.scrollTop - logContainer.clientHeight < 10;
		userScrolled = !isAtBottom;
	}

	function scrollToBottom() {
		if (logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
			userScrolled = false;
		}
	}

	// Detect log level from message content
	function getLogLevel(message: string): 'info' | 'warning' | 'error' | 'success' {
		const lowerMessage = message.toLowerCase();
		if (lowerMessage.includes('error') || lowerMessage.includes('failed')) {
			return 'error';
		}
		if (lowerMessage.includes('warning') || lowerMessage.includes('warn')) {
			return 'warning';
		}
		if (
			lowerMessage.includes('success') ||
			lowerMessage.includes('complete') ||
			lowerMessage.includes('done')
		) {
			return 'success';
		}
		return 'info';
	}

	function getLogClass(level: 'info' | 'warning' | 'error' | 'success'): string {
		switch (level) {
			case 'error':
				return 'text-red-600';
			case 'warning':
				return 'text-yellow-600';
			case 'success':
				return 'text-green-600';
			default:
				return 'text-gray-700';
		}
	}
</script>

<div class="relative">
	<div
		bind:this={logContainer}
		on:scroll={handleScroll}
		class="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-y-auto"
		style="max-height: {maxHeight};"
	>
		{#if logs.length === 0}
			<p class="text-gray-500 italic">ログはまだありません...</p>
		{:else}
			{#each logs as log, index}
				{@const level = getLogLevel(log)}
				<div class="py-0.5 flex">
					<span class="text-gray-500 select-none mr-3 min-w-[3ch] text-right">{index + 1}</span>
					<span class={getLogClass(level)}>{log}</span>
				</div>
			{/each}
		{/if}
	</div>

	{#if userScrolled && logs.length > 0}
		<button
			on:click={scrollToBottom}
			class="absolute bottom-4 right-4 bg-primary-600 text-white px-3 py-1 rounded-full text-xs shadow-lg hover:bg-primary-700 transition-colors"
			title="最下部へスクロール"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-4 w-4 inline-block mr-1"
				viewBox="0 0 20 20"
				fill="currentColor"
			>
				<path
					fill-rule="evenodd"
					d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
					clip-rule="evenodd"
				/>
			</svg>
			最新
		</button>
	{/if}
</div>
