<!--
  Card Component

  A reusable card container with optional header and footer.
  Uses Tailwind CSS for styling.

  Usage:
    <Card>
      <p>Card content</p>
    </Card>

    <Card title="Card Title" subtitle="Optional subtitle">
      <p>Card content</p>
    </Card>

    <Card>
      <svelte:fragment slot="header">
        <h2>Custom Header</h2>
      </svelte:fragment>
      <p>Card content</p>
      <svelte:fragment slot="footer">
        <Button>Action</Button>
      </svelte:fragment>
    </Card>
-->
<script lang="ts">
	/** Card title (simple text header) */
	export let title: string | undefined = undefined;
	/** Card subtitle (shown below title) */
	export let subtitle: string | undefined = undefined;
	/** Remove padding from card body */
	export let noPadding: boolean = false;

	// Check if header slot has content
	let hasHeaderSlot = false;
</script>

<div class="bg-white/80 rounded-xl border border-slate-200 shadow-lg shadow-slate-900/5 backdrop-blur overflow-hidden">
	{#if $$slots.header || title}
		<div class="px-6 py-4 border-b border-slate-200/80">
			{#if $$slots.header}
				<slot name="header" />
			{:else if title}
				<h3 class="text-lg font-semibold text-slate-900">{title}</h3>
				{#if subtitle}
					<p class="mt-1 text-sm text-slate-500">{subtitle}</p>
				{/if}
			{/if}
		</div>
	{/if}

	<div class={noPadding ? '' : 'p-6'}>
		<slot />
	</div>

	{#if $$slots.footer}
		<div class="px-6 py-4 bg-slate-50/70 border-t border-slate-200/80">
			<slot name="footer" />
		</div>
	{/if}
</div>
