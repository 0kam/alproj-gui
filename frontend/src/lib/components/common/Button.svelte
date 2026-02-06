<!--
  Button Component

  A reusable button component with multiple variants and states.
  Uses Tailwind CSS for styling.

  Usage:
    <Button variant="primary" on:click={handleClick}>Click me</Button>
    <Button variant="secondary" disabled>Disabled</Button>
    <Button variant="danger" size="sm">Delete</Button>
-->
<script lang="ts">
	/** Button variant determines the visual style */
	export let variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
	/** Button size */
	export let size: 'sm' | 'md' | 'lg' = 'md';
	/** Whether the button is disabled */
	export let disabled: boolean = false;
	/** Whether the button is in a loading state */
	export let loading: boolean = false;
	/** Button type attribute */
	export let type: 'button' | 'submit' | 'reset' = 'button';
	/** Full width button */
	export let fullWidth: boolean = false;

	// Compute classes based on props
	const baseClasses =
		'inline-flex items-center justify-center font-medium rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed';

	const variantClasses: Record<string, string> = {
		primary: 'bg-primary-700 text-white shadow-sm hover:bg-primary-800 focus:ring-primary-500',
		secondary:
			'bg-white/80 text-slate-700 border border-slate-200 backdrop-blur-sm hover:bg-white focus:ring-primary-500',
		danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
		ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-primary-500'
	};

	const sizeClasses: Record<string, string> = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2 text-base',
		lg: 'px-6 py-3 text-lg'
	};

	$: computedClass = [
		baseClasses,
		variantClasses[variant],
		sizeClasses[size],
		fullWidth ? 'w-full' : '',
		loading ? 'cursor-wait' : ''
	]
		.filter(Boolean)
		.join(' ');
</script>

<button
	{type}
	class={computedClass}
	disabled={disabled || loading}
	on:click
	aria-busy={loading}
>
	{#if loading}
		<svg
			class="animate-spin -ml-1 mr-2 h-4 w-4"
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
	{/if}
	<slot />
</button>
