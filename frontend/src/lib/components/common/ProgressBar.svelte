<!--
  ProgressBar Component

  A progress bar component with support for determinate and indeterminate states.
  Shows current step and progress percentage.

  Usage:
    <ProgressBar progress={0.5} step="Processing..." />
    <ProgressBar indeterminate step="Loading..." />
-->
<script lang="ts">
	/** Progress value from 0 to 1 */
	export let progress: number = 0;
	/** Current step description */
	export let step: string = '';
	/** Whether to show indeterminate animation */
	export let indeterminate: boolean = false;

	// Clamp progress between 0 and 1
	$: normalizedProgress = Math.min(1, Math.max(0, progress));
	$: percentageText = `${Math.round(normalizedProgress * 100)}%`;
</script>

<div class="w-full">
	{#if step}
		<div class="flex justify-between items-center mb-2">
			<span class="text-sm font-medium text-gray-700">{step}</span>
			{#if !indeterminate}
				<span class="text-sm font-medium text-gray-500">{percentageText}</span>
			{/if}
		</div>
	{/if}

	<div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
		{#if indeterminate}
			<div
				class="h-full bg-primary-600 rounded-full animate-progress-indeterminate"
				style="width: 30%;"
			></div>
		{:else}
			<div
				class="h-full bg-primary-600 rounded-full transition-all duration-300 ease-out"
				style="width: {normalizedProgress * 100}%;"
			></div>
		{/if}
	</div>
</div>

<style>
	@keyframes progress-indeterminate {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(400%);
		}
	}

	.animate-progress-indeterminate {
		animation: progress-indeterminate 1.5s ease-in-out infinite;
	}
</style>
