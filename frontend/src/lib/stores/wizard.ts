/**
 * Wizard State Management Store
 *
 * Manages the state of the georectification wizard including
 * current step, navigation, and data between steps.
 */

import { writable, derived, get } from 'svelte/store';
import type {
	RasterFile,
	ImageFile,
	CameraParamsValues,
	ProcessResult,
	Project,
	MatchingParams,
	EstimationParams
} from '$lib/types';

/**
 * Individual wizard step definition
 */
export interface WizardStep {
	id: string;
	title: string;
	path: string;
	completed: boolean;
}

/**
 * Input data for the wizard (detailed)
 */
export interface WizardInputData {
	dsm: RasterFile | null;
	ortho: RasterFile | null;
	targetImage: ImageFile | null;
	dsmThumbnail: string | null;
	orthoThumbnail: string | null;
	targetImageThumbnail: string | null;
}

/**
 * Complete wizard state
 */
export interface WizardState {
	currentStep: number;
	steps: WizardStep[];
	projectId: string | null;
	inputData: WizardInputData;
	cameraParams: CameraParamsValues | null;
	processResult: ProcessResult | null;
	matchingPlot: string | null;
	matchingLog: string[];
	matchCount: number | null;
	matchingParams: MatchingParams | null;
	cameraSimulation: string | null;
	estimationSimulation: string | null;
	estimationLog: string[];
	estimatedParams: CameraParamsValues | null;
	estimationParams: EstimationParams | null;
	geotiffPath: string | null;
	jobId: string | null;
	isProcessing: boolean;
}

/**
 * Default wizard steps configuration
 */
const DEFAULT_STEPS: WizardStep[] = [
	{
		id: 'data-input',
		title: 'wizard.step1',
		path: '/georectify/steps/data-input',
		completed: false
	},
	{
		id: 'camera-setup',
		title: 'wizard.step2',
		path: '/georectify/steps/camera-setup',
		completed: false
	},
	{
		id: 'processing',
		title: 'wizard.step3',
		path: '/georectify/steps/processing',
		completed: false
	},
	{
		id: 'result',
		title: 'wizard.step4',
		path: '/georectify/steps/result',
		completed: false
	},
	{
		id: 'export',
		title: 'wizard.step5',
		path: '/georectify/steps/export',
		completed: false
	}
];

/**
 * Initial input data state
 */
const initialInputData: WizardInputData = {
	dsm: null,
	ortho: null,
	targetImage: null,
	dsmThumbnail: null,
	orthoThumbnail: null,
	targetImageThumbnail: null
};

/**
 * Initial wizard state
 */
const initialState: WizardState = {
	currentStep: 0,
	steps: DEFAULT_STEPS.map((step) => ({ ...step })),
	projectId: null,
	inputData: { ...initialInputData },
	cameraParams: null,
	processResult: null,
	matchingPlot: null,
	matchingLog: [],
	matchCount: null,
	matchingParams: null,
	cameraSimulation: null,
	estimationSimulation: null,
	estimationLog: [],
	estimatedParams: null,
	estimationParams: null,
	geotiffPath: null,
	jobId: null,
	isProcessing: false
};

/**
 * Create the wizard store
 */
function createWizardStore() {
	const { subscribe, set, update } = writable<WizardState>(initialState);

	return {
		subscribe,

		/**
		 * Navigate to the next step
		 */
		nextStep: () => {
			update((state) => {
				if (state.currentStep < state.steps.length - 1) {
					// Mark current step as completed
					const steps = [...state.steps];
					steps[state.currentStep] = { ...steps[state.currentStep], completed: true };
					return {
						...state,
						steps,
						currentStep: state.currentStep + 1
					};
				}
				return state;
			});
		},

		/**
		 * Navigate to the previous step
		 */
		prevStep: () => {
			update((state) => {
				if (state.currentStep > 0) {
					return {
						...state,
						currentStep: state.currentStep - 1
					};
				}
				return state;
			});
		},

		/**
		 * Navigate to a specific step by index
		 * @param index - Step index (0-based)
		 */
		goToStep: (index: number) => {
			update((state) => {
				if (index >= 0 && index < state.steps.length) {
					return {
						...state,
						currentStep: index
					};
				}
				return state;
			});
		},

		/**
		 * Navigate to a specific step by id
		 * @param stepId - Step identifier
		 */
		goToStepById: (stepId: string) => {
			update((state) => {
				const index = state.steps.findIndex((s) => s.id === stepId);
				if (index >= 0) {
					return {
						...state,
						currentStep: index
					};
				}
				return state;
			});
		},

		/**
		 * Mark a step as completed
		 * @param index - Step index (0-based)
		 */
		completeStep: (index: number) => {
			update((state) => {
				if (index >= 0 && index < state.steps.length) {
					const steps = [...state.steps];
					steps[index] = { ...steps[index], completed: true };
					return { ...state, steps };
				}
				return state;
			});
		},

		/**
		 * Invalidate all steps from a given index onwards
		 * This clears the results and marks steps as incomplete when earlier steps are re-run
		 * @param fromIndex - Step index (0-based) from which to invalidate
		 */
		invalidateFromStep: (fromIndex: number) => {
			update((state) => {
				if (fromIndex < 0 || fromIndex >= state.steps.length) {
					return state;
				}

				// Mark steps from fromIndex onwards as incomplete
				const steps = [...state.steps];
				for (let i = fromIndex; i < steps.length; i++) {
					steps[i] = { ...steps[i], completed: false };
				}

				// Clear data based on which step is being invalidated
				let newState: Partial<WizardState> = { steps };

				// Step 3 (processing) invalidated -> clear matching results and onwards
				if (fromIndex <= 2) {
					newState = {
						...newState,
						matchingPlot: null,
						matchingLog: [],
						matchCount: null
						// Keep matchingParams for restoration
					};
				}

				// Step 2 (camera setup) invalidated -> clear camera simulation preview
				if (fromIndex <= 1) {
					newState = {
						...newState,
						cameraSimulation: null
					};
				}

				// Step 4 (result) invalidated -> clear estimation results and onwards
				if (fromIndex <= 3) {
					newState = {
						...newState,
						estimationSimulation: null,
						estimationLog: [],
						estimatedParams: null
						// Keep estimationParams for restoration
					};
				}

				// Step 5 (export) invalidated -> clear geotiff
				if (fromIndex <= 4) {
					newState = {
						...newState,
						geotiffPath: null
					};
				}

				return { ...state, ...newState };
			});
		},

		/**
		 * Update DSM data
		 */
		setDsm: (dsm: RasterFile | null, thumbnail: string | null = null) =>
			update((state) => ({
				...state,
				inputData: {
					...state.inputData,
					dsm,
					dsmThumbnail: thumbnail
				}
			})),

		/**
		 * Update ortho data
		 */
		setOrtho: (ortho: RasterFile | null, thumbnail: string | null = null) =>
			update((state) => ({
				...state,
				inputData: {
					...state.inputData,
					ortho,
					orthoThumbnail: thumbnail
				}
			})),

		/**
		 * Update target image data
		 */
		setTargetImage: (targetImage: ImageFile | null, thumbnail: string | null = null) =>
			update((state) => ({
				...state,
				inputData: {
					...state.inputData,
					targetImage,
					targetImageThumbnail: thumbnail
				}
			})),

		/**
		 * Update input data directly
		 */
		setInputData: (inputData: Partial<WizardInputData>) =>
			update((state) => ({
				...state,
				inputData: {
					...state.inputData,
					...inputData
				}
			})),

		/**
		 * Set camera parameters
		 * @param params - Camera parameters
		 */
		setCameraParams: (params: CameraParamsValues | null) => {
			update((state) => ({
				...state,
				cameraParams: params
			}));
		},

		/**
		 * Set process result
		 * @param result - Processing result (GCPs, metrics, etc.)
		 */
		setProcessResult: (result: ProcessResult | null) => {
			update((state) => ({
				...state,
				processResult: result
			}));
		},
		/**
		 * Set matching step result
		 */
		setMatchingResult: (payload: {
			plot: string | null;
			log?: string[];
			count?: number | null;
			params?: MatchingParams | null;
		}) =>
			update((state) => ({
				...state,
				matchingPlot: payload.plot,
				matchingLog: payload.log ?? [],
				matchCount: payload.count ?? null,
				matchingParams: payload.params ?? state.matchingParams
			})),

		/**
		 * Set camera setup simulation preview image
		 */
		setCameraSimulation: (simulation: string | null) =>
			update((state) => ({
				...state,
				cameraSimulation: simulation
			})),

		/**
		 * Set estimation step result
		 */
		setEstimationResult: (payload: {
			simulation: string | null;
			log?: string[];
			estimatedParams?: CameraParamsValues | null;
			params?: EstimationParams | null;
		}) =>
			update((state) => ({
				...state,
				estimationSimulation: payload.simulation,
				estimationLog: payload.log ?? [],
				estimatedParams: payload.estimatedParams ?? null,
				estimationParams: payload.params ?? state.estimationParams
			})),

		/**
		 * Set GeoTIFF output path
		 */
		setGeotiffPath: (path: string | null) =>
			update((state) => ({
				...state,
				geotiffPath: path
			})),

		/**
		 * Set project ID
		 * @param id - Project identifier
		 */
		setProjectId: (id: string | null) => {
			update((state) => ({
				...state,
				projectId: id
			}));
		},

		/**
		 * Set job ID for tracking processing
		 * @param id - Job identifier
		 */
		setJobId: (id: string | null) => {
			update((state) => ({
				...state,
				jobId: id
			}));
		},

		/**
		 * Set processing state
		 */
		setProcessing: (isProcessing: boolean) =>
			update((state) => ({
				...state,
				isProcessing
			})),

		/**
		 * Reset wizard to initial state
		 */
		resetWizard: () => {
			set({
				...initialState,
				steps: DEFAULT_STEPS.map((step) => ({ ...step })),
				inputData: { ...initialInputData }
			});
		},

		/**
		 * Load wizard state from a project
		 * @param project - Project to load (null clears wizard)
		 */
		loadFromProject: (project: Project | null) => {
			if (!project) {
				set({
					...initialState,
					steps: DEFAULT_STEPS.map((step) => ({ ...step })),
					inputData: { ...initialInputData }
				});
				return;
			}

			const inputData = {
				dsm: project.input_data?.dsm ?? null,
				ortho: project.input_data?.ortho ?? null,
				targetImage: project.input_data?.target_image ?? null,
				dsmThumbnail: null,
				orthoThumbnail: null,
				targetImageThumbnail: null
			};

			const cameraParams = project.camera_params?.initial ?? project.camera_params?.optimized ?? null;
			const estimatedParams = project.camera_params?.optimized ?? null;

			const steps = DEFAULT_STEPS.map((step) => ({ ...step }));
			const hasInput = Boolean(inputData.dsm && inputData.ortho && inputData.targetImage);
			if (hasInput) {
				steps[0].completed = true;
			}
			if (hasInput && cameraParams) {
				steps[1].completed = true;
			}
			if (project.process_result) {
				for (let i = 2; i < steps.length; i += 1) {
					steps[i].completed = true;
				}
			}

			const nextStepIndex = steps.findIndex((step) => !step.completed);
			const currentStep = nextStepIndex === -1 ? steps.length - 1 : nextStepIndex;

			set({
				...initialState,
				steps,
				currentStep,
				projectId: project.id,
				inputData,
				cameraParams,
				estimatedParams,
				cameraSimulation: project.camera_simulation ?? null,
				processResult: project.process_result ?? null,
				geotiffPath: project.process_result?.geotiff_path ?? null
			});
		},

		/**
		 * Get current state snapshot
		 */
		getState: () => get({ subscribe })
	};
}

// Create and export the singleton store
export const wizardStore = createWizardStore();

// Derived stores for navigation
export const currentStep = derived(wizardStore, ($wizard) => $wizard.currentStep);
export const currentStepData = derived(wizardStore, ($wizard) => $wizard.steps[$wizard.currentStep]);
export const steps = derived(wizardStore, ($wizard) => $wizard.steps);
export const canGoNext = derived(
	wizardStore,
	($wizard) => $wizard.currentStep < $wizard.steps.length - 1
);
export const canGoPrev = derived(wizardStore, ($wizard) => $wizard.currentStep > 0);
export const isFirstStep = derived(wizardStore, ($wizard) => $wizard.currentStep === 0);
export const isLastStep = derived(
	wizardStore,
	($wizard) => $wizard.currentStep === $wizard.steps.length - 1
);
export const progressPercent = derived(
	wizardStore,
	($wizard) => (($wizard.currentStep + 1) / $wizard.steps.length) * 100
);

// Derived stores for validation
export const isInputDataComplete = derived(wizardStore, ($wizard) => {
	const { dsm, ortho, targetImage } = $wizard.inputData;
	return dsm !== null && ortho !== null && targetImage !== null;
});

export const crsMatch = derived(wizardStore, ($wizard) => {
	const { dsm, ortho } = $wizard.inputData;
	if (!dsm || !ortho) return null;
	return dsm.crs === ortho.crs;
});

export const isStep1Valid = derived(
	[isInputDataComplete, crsMatch],
	([$isInputDataComplete]) => {
		// All inputs required, CRS mismatch is a warning but not blocking
		return $isInputDataComplete;
	}
);
