/**
 * Project State Management Store
 *
 * Manages the state of projects including:
 * - Project list
 * - Current project
 * - Loading states
 * - Project file operations
 */

import { writable, derived, get } from 'svelte/store';
import type {
	Project,
	ProjectSummary,
	CreateProjectRequest,
	SaveProjectResponse,
	UpdateProjectRequest
} from '$lib/types';
import { api } from '$lib/services/api';
import { wizardStore } from './wizard';

/**
 * Recovery file information
 */
export interface RecoveryFile {
	path: string;
	projectName: string;
	savedAt: string;
}

/**
 * Project store state
 */
export interface ProjectState {
	projects: ProjectSummary[];
	currentProject: Project | null;
	currentFilePath: string | null;
	loading: boolean;
	saving: boolean;
	error: string | null;
	recoveryFiles: RecoveryFile[];
	hasUnsavedChanges: boolean;
}

/**
 * Initial project state
 */
const initialState: ProjectState = {
	projects: [],
	currentProject: null,
	currentFilePath: null,
	loading: false,
	saving: false,
	error: null,
	recoveryFiles: [],
	hasUnsavedChanges: false
};

/**
 * Create the project store
 */
function createProjectStore() {
	const { subscribe, set, update } = writable<ProjectState>(initialState);

	return {
		subscribe,

		/**
		 * Fetch all projects from the backend
		 */
		fetchProjects: async (): Promise<void> => {
			update((state) => ({ ...state, loading: true, error: null }));
			try {
				const projects = await api.get<ProjectSummary[]>('/api/projects');
				update((state) => ({ ...state, projects, loading: false }));
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to fetch projects';
				update((state) => ({ ...state, error: message, loading: false }));
				throw error;
			}
		},

		/**
		 * Create a new project
		 * @param name - Project name
		 */
		createProject: async (name: string): Promise<Project> => {
			update((state) => ({ ...state, loading: true, error: null }));
			try {
				const request: CreateProjectRequest = { name };
				const project = await api.post<Project>('/api/projects', request);
				update((state) => ({
					...state,
					currentProject: project,
					currentFilePath: null,
					hasUnsavedChanges: true,
					loading: false
				}));
				wizardStore.loadFromProject(project);
				return project;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to create project';
				update((state) => ({ ...state, error: message, loading: false }));
				throw error;
			}
		},

		/**
		 * Open a project file
		 * @param path - Path to the .alproj file
		 */
		openProjectFile: async (path: string): Promise<Project> => {
			update((state) => ({ ...state, loading: true, error: null }));
			try {
				const project = await api.post<Project>('/api/projects/open', { path });
				update((state) => ({
					...state,
					currentProject: project,
					currentFilePath: path,
					hasUnsavedChanges: false,
					loading: false
				}));
				wizardStore.loadFromProject(project);
				return project;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to open project';
				update((state) => ({ ...state, error: message, loading: false }));
				throw error;
			}
		},

		/**
		 * Save the current project
		 * @param path - Optional path to save to (for Save As)
		 */
		saveProject: async (path?: string): Promise<string> => {
			const state = get({ subscribe });
			if (!state.currentProject) {
				throw new Error('No project to save');
			}

			update((s) => ({ ...s, saving: true, error: null }));
			try {
				const savePath = path || state.currentFilePath;
				if (!savePath) {
					throw new Error('No file path specified');
				}

				// Extract project name from file path (without .alproj extension)
				const filename = savePath.split(/[/\\]/).pop() || '';
				const projectName = filename.replace(/\.alproj$/i, '') || state.currentProject.name;

				const wizardState = wizardStore.getState();
				const request: UpdateProjectRequest = {
					name: projectName,
					input_data: {
						dsm: wizardState.inputData.dsm ?? null,
						ortho: wizardState.inputData.ortho ?? null,
						target_image: wizardState.inputData.targetImage ?? null
					},
					camera_simulation: wizardState.cameraSimulation ?? null,
					camera_params: wizardState.cameraParams
						? { initial: wizardState.cameraParams, optimized: wizardState.estimatedParams || undefined }
						: wizardState.estimatedParams
							? { optimized: wizardState.estimatedParams }
							: null,
					process_result: wizardState.processResult ?? null
				};

				const updatedProject = await api.put<Project>(
					`/api/projects/${state.currentProject.id}`,
					request
				);
				update((s) => ({ ...s, currentProject: updatedProject }));

				const response = await api.post<SaveProjectResponse>(
					`/api/projects/${state.currentProject.id}/save?path=${encodeURIComponent(savePath)}`
				);
				update((s) => ({
					...s,
					currentFilePath: response.path,
					hasUnsavedChanges: false,
					saving: false
				}));
				return response.path;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to save project';
				update((s) => ({ ...s, error: message, saving: false }));
				throw error;
			}
		},

		/**
		 * Close the current project
		 */
		closeProject: (): void => {
			update((state) => ({
				...state,
				currentProject: null,
				currentFilePath: null,
				hasUnsavedChanges: false
			}));
			wizardStore.loadFromProject(null);
		},

		/**
		 * Delete a project
		 * @param id - Project ID
		 */
		deleteProject: async (id: string): Promise<void> => {
			update((state) => ({ ...state, loading: true, error: null }));
			try {
				await api.delete(`/projects/${id}`);
				update((state) => ({
					...state,
					projects: state.projects.filter((p) => p.id !== id),
					currentProject: state.currentProject?.id === id ? null : state.currentProject,
					loading: false
				}));
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to delete project';
				update((state) => ({ ...state, error: message, loading: false }));
				throw error;
			}
		},

		/**
		 * Set the current project
		 * @param project - Project to set as current
		 */
		setCurrentProject: (project: Project | null): void => {
			update((state) => ({
				...state,
				currentProject: project,
				hasUnsavedChanges: false
			}));
			wizardStore.loadFromProject(project);
		},

		/**
		 * Mark project as having unsaved changes
		 */
		markUnsaved: (): void => {
			update((state) => ({ ...state, hasUnsavedChanges: true }));
		},

		/**
		 * Check for recovery files
		 */
		checkRecoveryFiles: async (): Promise<RecoveryFile[]> => {
			try {
				const files = await api.get<RecoveryFile[]>('/api/recovery/check');
				update((state) => ({ ...state, recoveryFiles: files }));
				return files;
			} catch {
				// Recovery check is optional, don't throw
				return [];
			}
		},

		/**
		 * Recover a project from a recovery file
		 * @param path - Path to the recovery file
		 */
		recoverProject: async (path: string): Promise<Project> => {
			update((state) => ({ ...state, loading: true, error: null }));
			try {
				const project = await api.post<Project>('/api/recovery/restore', { path });
				update((state) => ({
					...state,
					currentProject: project,
					currentFilePath: null,
					hasUnsavedChanges: true,
					recoveryFiles: state.recoveryFiles.filter((f) => f.path !== path),
					loading: false
				}));
				wizardStore.loadFromProject(project);
				return project;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to recover project';
				update((state) => ({ ...state, error: message, loading: false }));
				throw error;
			}
		},

		/**
		 * Discard a recovery file
		 * @param path - Path to the recovery file
		 */
		discardRecovery: async (path: string): Promise<void> => {
			try {
				await api.delete(`/api/recovery/${encodeURIComponent(path)}`, { timeout: 5000 });
				update((state) => ({
					...state,
					recoveryFiles: state.recoveryFiles.filter((f) => f.path !== path)
				}));
			} catch {
				// Discard is best-effort
			}
		},

		/**
		 * Clear error state
		 */
		clearError: (): void => {
			update((state) => ({ ...state, error: null }));
		},

		/**
		 * Reset store to initial state
		 */
		reset: (): void => {
			set(initialState);
			wizardStore.loadFromProject(null);
		},

		/**
		 * Get current state snapshot
		 */
		getState: () => get({ subscribe })
	};
}

// Create and export the singleton store
export const projectStore = createProjectStore();

// Derived stores for convenience
export const currentProject = derived(projectStore, ($project) => $project.currentProject);
export const projects = derived(projectStore, ($project) => $project.projects);
export const projectLoading = derived(projectStore, ($project) => $project.loading);
export const projectSaving = derived(projectStore, ($project) => $project.saving);
export const projectError = derived(projectStore, ($project) => $project.error);
export const hasUnsavedChanges = derived(projectStore, ($project) => $project.hasUnsavedChanges);
export const recoveryFiles = derived(projectStore, ($project) => $project.recoveryFiles);
export const currentFilePath = derived(projectStore, ($project) => $project.currentFilePath);

// Derived store for project status badge
export const projectStatusInfo = derived(currentProject, ($project) => {
	if (!$project) return null;

	const statusMap: Record<string, { label: string; color: string }> = {
		draft: { label: 'status.draft', color: 'gray' },
		processing: { label: 'status.processing', color: 'yellow' },
		completed: { label: 'status.completed', color: 'green' },
		error: { label: 'status.error', color: 'red' }
	};

	return statusMap[$project.status] || statusMap.draft;
});
