<!--
  Language Switcher Component

  A dropdown select for switching between available languages.
  Changes are persisted to localStorage and trigger a page reload
  to apply the new language across all components.
-->
<script lang="ts">
	import { locale, setLocale, type Locale } from '$lib/i18n';

	const languages: { code: Locale; label: string }[] = [
		{ code: 'en', label: 'EN' },
		{ code: 'ja', label: '日本語' }
	];

	function handleChange(event: Event) {
		const target = event.currentTarget as HTMLSelectElement;
		setLocale(target.value as Locale);
	}
</script>

<select class="language-switcher" value={$locale} on:change={handleChange} aria-label="Language">
	{#each languages as lang}
		<option value={lang.code}>{lang.label}</option>
	{/each}
</select>

<style>
	.language-switcher {
		padding: 0.375rem 0.5rem;
		background-color: rgba(255, 255, 255, 0.85);
		border: 1px solid rgba(11, 35, 51, 0.12);
		border-radius: 0.375rem;
		font-size: 0.875rem;
		color: var(--ink-700);
		cursor: pointer;
		transition: all 0.15s ease;
		appearance: none;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.5rem center;
		padding-right: 1.75rem;
	}

	.language-switcher:hover {
		background-color: rgba(255, 255, 255, 1);
		border-color: rgba(11, 35, 51, 0.2);
	}

	.language-switcher:focus {
		outline: none;
		border-color: var(--brand-500);
		box-shadow: 0 0 0 2px rgba(var(--brand-500-rgb), 0.2);
	}
</style>
