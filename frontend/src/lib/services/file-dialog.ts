/**
 * File Dialog Service for ALPROJ GUI
 *
 * Provides cross-platform file dialog functionality using Tauri's dialog API.
 * Falls back to web file input when not running in Tauri context.
 */

/**
 * Check if running in Tauri context
 */
function isTauri(): boolean {
	return (
		typeof window !== 'undefined' &&
		('__TAURI__' in window || '__TAURI_INTERNALS__' in window)
	);
}

/**
 * File filter for dialog
 */
interface FileFilter {
	name: string;
	extensions: string[];
}

/**
 * Open file dialog options
 */
interface OpenDialogOptions {
	title?: string;
	filters?: FileFilter[];
	defaultPath?: string;
	multiple?: boolean;
}

/**
 * Save file dialog options
 */
interface SaveDialogOptions {
	title?: string;
	filters?: FileFilter[];
	defaultPath?: string;
}

/**
 * ALPROJ project file filter
 */
const ALPROJ_FILTER: FileFilter = {
	name: 'ALPROJ Project',
	extensions: ['alproj']
};

/**
 * Open a file dialog to select an ALPROJ project file
 * @returns Selected file path or null if cancelled
 */
export async function openProjectDialog(): Promise<string | null> {
	if (isTauri()) {
		try {
			const { open } = await import('@tauri-apps/plugin-dialog');
			const result = (await open({
				title: 'Open Project',
				filters: [ALPROJ_FILTER],
				multiple: false
			})) as string | string[] | null;
			// Result can be string, string[], or null
			if (typeof result === 'string') {
				return result;
			}
			if (Array.isArray(result) && result.length > 0) {
				return result[0];
			}
			return null;
		} catch (error) {
			console.error('Failed to open file dialog:', error);
			throw error;
		}
	} else {
		// Web fallback - use file input
		return openWebFileDialog({ accept: '.alproj' });
	}
}

/**
 * Open a save file dialog for ALPROJ project file
 * @param defaultName - Default file name (without extension)
 * @returns Selected file path or null if cancelled
 */
export async function saveProjectDialog(defaultName?: string): Promise<string | null> {
	if (isTauri()) {
		try {
			const { save } = await import('@tauri-apps/plugin-dialog');
			const result = await save({
				title: 'Save Project',
				filters: [ALPROJ_FILTER],
				defaultPath: defaultName ? `${defaultName}.alproj` : undefined
			});
			return result;
		} catch (error) {
			console.error('Failed to open save dialog:', error);
			throw error;
		}
	} else {
		// Web fallback - return a suggested path (web cannot save to filesystem)
		const name = defaultName || 'project';
		return `${name}.alproj`;
	}
}

/**
 * Open a file dialog to select a raster file (GeoTIFF)
 * @returns Selected file path or null if cancelled
 */
export async function openRasterDialog(): Promise<string | null> {
	const filters: FileFilter[] = [
		{ name: 'GeoTIFF', extensions: ['tif', 'tiff', 'geotiff'] },
		{ name: 'All Files', extensions: ['*'] }
	];

	if (isTauri()) {
		try {
			const { open } = await import('@tauri-apps/plugin-dialog');
			const result = (await open({
				title: 'Select Raster File',
				filters,
				multiple: false
			})) as string | string[] | null;
			if (typeof result === 'string') {
				return result;
			}
			if (Array.isArray(result) && result.length > 0) {
				return result[0];
			}
			return null;
		} catch (error) {
			console.error('Failed to open file dialog:', error);
			throw error;
		}
	} else {
		return openWebFileDialog({ accept: '.tif,.tiff,.geotiff' });
	}
}

/**
 * Open a file dialog to select an image file
 * @returns Selected file path or null if cancelled
 */
export async function openImageDialog(): Promise<string | null> {
	const filters: FileFilter[] = [
		{ name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'tif', 'tiff'] },
		{ name: 'All Files', extensions: ['*'] }
	];

	if (isTauri()) {
		try {
			const { open } = await import('@tauri-apps/plugin-dialog');
			const result = (await open({
				title: 'Select Image File',
				filters,
				multiple: false
			})) as string | string[] | null;
			if (typeof result === 'string') {
				return result;
			}
			if (Array.isArray(result) && result.length > 0) {
				return result[0];
			}
			return null;
		} catch (error) {
			console.error('Failed to open file dialog:', error);
			throw error;
		}
	} else {
		return openWebFileDialog({ accept: '.jpg,.jpeg,.png,.tif,.tiff' });
	}
}

/**
 * Open a file dialog to select multiple image files
 * @returns Selected file paths (empty when cancelled)
 */
export async function openImageDialogs(): Promise<string[]> {
	const filters: FileFilter[] = [
		{ name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'tif', 'tiff'] },
		{ name: 'All Files', extensions: ['*'] }
	];

	if (isTauri()) {
		try {
			const { open } = await import('@tauri-apps/plugin-dialog');
			const result = (await open({
				title: 'Select Image Files',
				filters,
				multiple: true
			})) as string | string[] | null;
			if (Array.isArray(result)) {
				return result;
			}
			if (typeof result === 'string') {
				return [result];
			}
			return [];
		} catch (error) {
			console.error('Failed to open file dialog:', error);
			throw error;
		}
	} else {
		const selected = await openWebFileDialog({ accept: '.jpg,.jpeg,.png,.tif,.tiff' });
		return selected ? [selected] : [];
	}
}

/**
 * Open a directory selection dialog
 * @param title - Dialog title
 * @returns Selected directory path or null if cancelled
 */
export async function openDirectoryDialog(title?: string): Promise<string | null> {
	if (isTauri()) {
		try {
			const { open } = await import('@tauri-apps/plugin-dialog');
			const result = await open({
				title: title || 'Select Directory',
				directory: true
			});
			if (typeof result === 'string') {
				return result;
			}
			return null;
		} catch (error) {
			console.error('Failed to open directory dialog:', error);
			throw error;
		}
	} else {
		// Web doesn't support directory selection in the same way
		console.warn('Directory selection not supported in web context');
		return null;
	}
}

/**
 * Save file dialog for GeoTIFF export
 * @param defaultName - Default file name (without extension)
 * @returns Selected file path or null if cancelled
 */
export async function saveGeoTiffDialog(defaultName?: string): Promise<string | null> {
	const filters: FileFilter[] = [{ name: 'GeoTIFF', extensions: ['tif', 'tiff'] }];
	const hasExtension = (name: string) => /\.[^./\\]+$/.test(name);
	const defaultPath = defaultName
		? hasExtension(defaultName)
			? defaultName
			: `${defaultName}.tiff`
		: undefined;

	if (isTauri()) {
		try {
			const { save } = await import('@tauri-apps/plugin-dialog');
			const result = await save({
				title: 'Export GeoTIFF',
				filters,
				defaultPath
			});
			return result;
		} catch (error) {
			console.error('Failed to open save dialog:', error);
			throw error;
		}
	} else {
		const name = defaultName || 'output';
		return hasExtension(name) ? name : `${name}.tiff`;
	}
}

/**
 * Show a message dialog
 * @param title - Dialog title
 * @param message - Dialog message
 * @param type - Dialog type
 */
export async function showMessage(
	title: string,
	message: string,
	kind: 'info' | 'warning' | 'error' = 'info'
): Promise<void> {
	if (isTauri()) {
		try {
			const { message: showMsg } = await import('@tauri-apps/plugin-dialog');
			await showMsg(message, { title, kind });
		} catch (error) {
			console.error('Failed to show message:', error);
			alert(message);
		}
	} else {
		alert(message);
	}
}

/**
 * Show a confirmation dialog
 * @param title - Dialog title
 * @param message - Dialog message
 * @returns true if confirmed, false if cancelled
 */
export async function showConfirm(title: string, message: string): Promise<boolean> {
	if (isTauri()) {
		try {
			const { confirm } = await import('@tauri-apps/plugin-dialog');
			return await confirm(message, { title });
		} catch (error) {
			console.error('Failed to show confirm:', error);
			return window.confirm(message);
		}
	} else {
		return window.confirm(message);
	}
}

/**
 * Web fallback for file input
 */
function openWebFileDialog(options: { accept?: string }): Promise<string | null> {
	return new Promise((resolve) => {
		const input = document.createElement('input');
		input.type = 'file';
		if (options.accept) {
			input.accept = options.accept;
		}

		input.onchange = () => {
			const file = input.files?.[0];
			if (file) {
				// In web context, we return the file name
				// The actual file handling would need to be different
				resolve(file.name);
			} else {
				resolve(null);
			}
		};

		input.oncancel = () => {
			resolve(null);
		};

		input.click();
	});
}

/**
 * Export all dialog functions
 */
export const fileDialog = {
	openProject: openProjectDialog,
	saveProject: saveProjectDialog,
	openRaster: openRasterDialog,
	openImage: openImageDialog,
	openImages: openImageDialogs,
	openDirectory: openDirectoryDialog,
	saveGeoTiff: saveGeoTiffDialog,
	showMessage,
	showConfirm
};
