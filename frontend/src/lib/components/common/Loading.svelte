<!--
  Loading Component

  A reusable loading spinner with optional message.
  Uses Tailwind CSS for styling.

  Usage:
    <Loading />
    <Loading message="Loading data..." />
    <Loading size="lg" />
    <Loading fullScreen />
-->
<script lang="ts">
	import { t } from '$lib/i18n';

	/** Loading message to display below spinner */
	export let message: string | undefined = undefined;
	/** Spinner size */
	export let size: 'sm' | 'md' | 'lg' = 'md';
	/** Cover full screen with overlay */
	export let fullScreen: boolean = false;
	/** Center the spinner in its container */
	export let center: boolean = true;

	const sizeClasses: Record<string, string> = {
		sm: 'h-5 w-5',
		md: 'h-8 w-8',
		lg: 'h-12 w-12'
	};

	const textSizeClasses: Record<string, string> = {
		sm: 'text-sm',
		md: 'text-base',
		lg: 'text-lg'
	};
</script>

{#if fullScreen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm"
		role="status"
		aria-live="polite"
	>
		<div class="flex flex-col items-center gap-4 p-6 bg-white rounded-lg shadow-xl">
			<svg
				class="animate-spin text-primary-600 {sizeClasses[size]}"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
			<span class="text-gray-700 {textSizeClasses[size]}">
				{message ?? t('common.loading')}
			</span>
		</div>
	</div>
{:else}
	<div
		class="flex flex-col items-center gap-3 {center ? 'justify-center' : ''}"
		role="status"
		aria-live="polite"
	>
		<svg
			class="animate-spin text-primary-600 {sizeClasses[size]}"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			aria-hidden="true"
		>
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
			></circle>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			></path>
		</svg>
		{#if message}
			<span class="text-gray-600 {textSizeClasses[size]}">{message}</span>
		{/if}
	</div>
{/if}
