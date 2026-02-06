/**
 * Simple i18n utility for ALPROJ GUI
 *
 * Provides a translation function `t` that retrieves translated strings
 * from a JSON translation file using dot-notation keys.
 *
 * Supports multiple locales (en, ja) with automatic detection
 * based on localStorage or browser language settings.
 */

import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import ja from './ja.json';
import en from './en.json';

type TranslationValue = string | Record<string, unknown>;

interface TranslationData {
	[key: string]: TranslationValue;
}

export type Locale = 'en' | 'ja';

// Translation data for each locale
const translations: Record<Locale, TranslationData> = { en, ja };

/**
 * Determine the initial locale based on:
 * 1. localStorage (if previously set)
 * 2. Browser language preference
 * 3. Default to 'ja'
 */
function getInitialLocale(): Locale {
	if (!browser) return 'ja';

	const saved = localStorage.getItem('locale');
	if (saved === 'ja' || saved === 'en') return saved;

	return navigator.language.startsWith('ja') ? 'ja' : 'en';
}

/**
 * Current locale value (computed once on module load)
 * This ensures consistent behavior across SSR and client
 */
const currentLocale: Locale = getInitialLocale();

/**
 * Svelte store for the current locale
 */
export const locale = writable<Locale>(currentLocale);

/**
 * Set the locale and persist to localStorage
 * Reloads the page to apply changes across all components
 */
export function setLocale(lang: Locale): void {
	locale.set(lang);
	if (browser) {
		localStorage.setItem('locale', lang);
		// Reload page to apply language change across all components
		window.location.reload();
	}
}

/**
 * Get a nested value from an object using dot notation
 * @param obj - The object to traverse
 * @param path - Dot-separated path (e.g., "common.loading")
 * @returns The value at the path or undefined if not found
 */
function getNestedValue(obj: TranslationData, path: string): string | undefined {
	const keys = path.split('.');
	let current: unknown = obj;

	for (const key of keys) {
		if (current === null || current === undefined || typeof current !== 'object') {
			return undefined;
		}
		current = (current as Record<string, unknown>)[key];
	}

	return typeof current === 'string' ? current : undefined;
}

/**
 * Translate a key to the current locale's string
 *
 * @param key - Dot-notation key (e.g., "common.loading", "home.welcome")
 * @param params - Optional parameters for interpolation (e.g., { name: "John" })
 * @returns Translated string or the key itself if translation not found
 *
 * @example
 * ```ts
 * t('common.loading') // "Loading..." (en) or "読み込み中..." (ja)
 * t('home.welcome') // "Welcome to ALPROJ GUI" (en) or "ALPROJ GUI へようこそ" (ja)
 * t('greeting', { name: 'John' }) // "Hello, John!" (if template exists)
 * ```
 */
export function t(key: string, params?: Record<string, string | number>): string {
	const currentLocale = get(locale);
	const value = getNestedValue(translations[currentLocale], key);

	if (value === undefined) {
		console.warn(`Translation not found for key: ${key}`);
		return key;
	}

	// Simple parameter interpolation: replace {param} with value
	if (params) {
		return value.replace(/\{(\w+)\}/g, (_, paramName) => {
			const paramValue = params[paramName];
			return paramValue !== undefined ? String(paramValue) : `{${paramName}}`;
		});
	}

	return value;
}

/**
 * Check if a translation key exists
 * @param key - Dot-notation key to check
 * @returns true if the key exists and has a string value
 */
export function hasTranslation(key: string): boolean {
	const currentLocale = get(locale);
	return getNestedValue(translations[currentLocale], key) !== undefined;
}

/**
 * Get all translation keys under a namespace
 * @param namespace - The namespace to get keys from (e.g., "common")
 * @returns Record of key-value pairs or empty object if namespace not found
 */
export function getNamespace(namespace: string): Record<string, string> {
	const currentLocale = get(locale);
	const currentTranslations = translations[currentLocale];
	const value = getNestedValue(currentTranslations, namespace);

	if (value === undefined) {
		return {};
	}

	// If the value is a string, return it wrapped
	if (typeof value === 'string') {
		return { [namespace]: value };
	}

	// If the value is an object, flatten and return string values only
	const result: Record<string, string> = {};
	const obj = currentTranslations[namespace];

	if (typeof obj === 'object' && obj !== null) {
		for (const [key, val] of Object.entries(obj)) {
			if (typeof val === 'string') {
				result[key] = val;
			}
		}
	}

	return result;
}

// Export translations for direct access if needed
export { translations };
