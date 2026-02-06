/**
 * TypeScript Type Definitions for ALPROJ GUI
 *
 * These types correspond to the OpenAPI schema defined in:
 * specs/001-georectification/contracts/openapi.yaml
 */

// === Project ===

/**
 * Project status enum
 */
export type ProjectStatus = 'draft' | 'processing' | 'completed' | 'error';

/**
 * Project summary for list view
 */
export interface ProjectSummary {
	id: string;
	name: string;
	status: ProjectStatus;
	updated_at: string;
}

/**
 * Full project details
 */
export interface Project {
	id: string;
	version: string;
	name: string;
	status: ProjectStatus;
	created_at: string;
	updated_at: string;
	input_data: InputData;
	camera_params?: CameraParams | null;
	camera_simulation?: string | null;
	process_result?: ProcessResult | null;
}

/**
 * Request to create a new project
 */
export interface CreateProjectRequest {
	name: string;
}

/**
 * Request to update a project
 */
export interface UpdateProjectRequest {
	name?: string;
	input_data?: InputData | null;
	camera_params?: CameraParams | null;
	camera_simulation?: string | null;
	process_result?: ProcessResult | null;
}

// === Input Data ===

/**
 * Input data for georectification
 */
export interface InputData {
	dsm?: RasterFile | null;
	ortho?: RasterFile | null;
	target_image?: ImageFile | null;
}

/**
 * Raster file information (DSM or orthophoto)
 */
export interface RasterFile {
	path: string;
	crs: string;
	bounds: [number, number, number, number]; // [xmin, ymin, xmax, ymax] in native CRS
	bounds_wgs84?: [number, number, number, number]; // [xmin, ymin, xmax, ymax] in WGS84 (EPSG:4326)
	resolution: [number, number];
	size: [number, number]; // [width, height]
}

/**
 * Image file information (target photo)
 */
export interface ImageFile {
	path: string;
	size: [number, number]; // [width, height]
	exif?: ExifData;
}

/**
 * EXIF metadata extracted from image
 */
export interface ExifData {
	datetime?: string;
	gps_lat?: number;
	gps_lon?: number;
	gps_alt?: number;
	focal_length?: number;
	camera_model?: string;
}

// === Camera Parameters ===

/**
 * Camera parameters container (initial and optimized)
 */
export interface CameraParams {
	initial?: CameraParamsValues;
	optimized?: CameraParamsValues;
}

/**
 * Camera parameter values
 */
export interface CameraParamsValues {
	// Position
	x: number;
	y: number;
	z: number;
	// Orientation
	fov: number; // 1-180
	pan: number; // 0-360
	tilt: number; // -90 to 90
	roll: number; // -180 to 180
	// Distortion (optional)
	a1?: number;
	a2?: number;
	k1?: number;
	k2?: number;
	k3?: number;
	k4?: number;
	k5?: number;
	k6?: number;
	p1?: number;
	p2?: number;
	s1?: number;
	s2?: number;
	s3?: number;
	s4?: number;
	// Principal point (optional)
	cx?: number;
	cy?: number;
}

/**
 * Default camera parameters
 */
export const DEFAULT_CAMERA_PARAMS: CameraParamsValues = {
	x: 0,
	y: 0,
	z: 0,
	fov: 60,
	pan: 0,
	tilt: 0,
	roll: 0,
	a1: 1,
	a2: 1,
	k1: 0,
	k2: 0,
	k3: 0,
	k4: 0,
	k5: 0,
	k6: 0,
	p1: 0,
	p2: 0,
	s1: 0,
	s2: 0,
	s3: 0,
	s4: 0
};

// === Process Result ===

/**
 * Georectification process result
 */
export interface ProcessResult {
	gcps?: GCP[];
	metrics?: ProcessMetrics;
	geotiff_path?: string;
	log?: string[];
}

/**
 * Ground Control Point
 */
export interface GCP {
	id: number;
	image_x: number;
	image_y: number;
	geo_x: number;
	geo_y: number;
	geo_z: number;
	residual?: number;
	enabled: boolean;
}

/**
 * Process quality metrics
 */
export interface ProcessMetrics {
	rmse: number;
	gcp_count: number;
	gcp_total: number;
	residual_mean?: number;
	residual_std?: number;
	residual_max?: number;
}

// === Simulation ===

/**
 * Simulation request
 */
export interface SimulationRequest {
	dsm_path: string;
	ortho_path: string;
	target_image_path: string;
	camera_params: CameraParamsValues;
	max_size?: number;
}

/**
 * Simulation response
 */
export interface SimulationResponse {
	image_base64: string;
}

// === Process ===

/**
 * Matching method options
 */
export type MatchingMethod =
	| 'akaze'
	| 'sift'
	| 'superpoint-lightglue'
	| 'minima-roma'
	| 'tiny-roma';

/**
 * Optimizer options
 */
export type OptimizerType = 'cma' | 'lsq';

/**
 * Matching parameters (used for estimation)
 */
export interface MatchingParams {
	matching_method: MatchingMethod;
	resize: number | 'none';
	threshold: number;
	outlier_filter: string | null;
	spatial_thin_grid: number | null;
	spatial_thin_selection: string | null;
	surface_distance: number;
	simulation_min_distance: number;
	match_id?: string | null;
}

/**
 * Estimation parameters
 */
export interface EstimationParams {
	optimizer: OptimizerType;
	min_gcp_distance: number;
	two_stage: boolean;
	optimize_position: boolean;
	optimize_orientation: boolean;
	optimize_fov: boolean;
	optimize_distortion: boolean;
}

/**
 * Process options
 */
export interface ProcessOptions {
	matching_method?: MatchingMethod;
	optimizer?: OptimizerType;
	max_generations?: number;
	min_gcp_distance?: number;
}

/**
 * Process request
 */
export interface ProcessRequest {
	project_id: string;
	options?: ProcessOptions;
}

/**
 * Matching step request
 */
export interface MatchRequest {
	dsm_path: string;
	ortho_path: string;
	target_image_path: string;
	camera_params: CameraParamsValues;
	matching_method: MatchingMethod;
	resize?: number | 'none';
	threshold?: number;
	outlier_filter?: string | null;
	spatial_thin_grid?: number | null;
	spatial_thin_selection?: string | null;
	surface_distance?: number;
	simulation_min_distance?: number;
}

/**
 * Matching step response
 */
export interface MatchResponse {
	match_plot_base64: string;
	match_count?: number;
	match_id?: string | null;
	log?: string[];
}

/**
 * Estimation step request
 */
export interface EstimateRequest {
	dsm_path: string;
	ortho_path: string;
	target_image_path: string;
	camera_params: CameraParamsValues;
	matching_method?: MatchingMethod;
	optimizer?: OptimizerType;
	min_gcp_distance?: number;
	match_id?: string | null;
	two_stage?: boolean;
	resize?: number | 'none';
	threshold?: number;
	outlier_filter?: string | null;
	spatial_thin_grid?: number | null;
	spatial_thin_selection?: string | null;
	surface_distance?: number;
	simulation_min_distance?: number;
	optimize_position?: boolean;
	optimize_orientation?: boolean;
	optimize_fov?: boolean;
	optimize_distortion?: boolean;
}

/**
 * Estimation step response
 */
export interface EstimateResponse {
	simulation_base64: string;
	optimized_params?: CameraParamsValues;
	log?: string[];
}

// === Export ===

/**
 * Export request
 */
export interface ExportRequest {
	project_id: string;
	output_path: string;
	resolution?: number;
	crs?: string;
	interpolate?: boolean;
	max_dist?: number | null;
	template_path?: string | null;
	surface_distance?: number;
}

/**
 * Export job response (202 Accepted)
 */
export interface ExportJobResponse {
	id: string;
	status: JobStatus;
	created_at: string;
}

/**
 * Export result (from completed job)
 */
export interface ExportResult {
	path: string;
	log?: string[];
}

// === Job ===

/**
 * Job status enum
 */
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

/**
 * Job information
 */
export interface Job {
	id: string;
	status: JobStatus;
	progress?: number;
	step?: string;
	message?: string;
	created_at: string;
	completed_at?: string;
	error?: string;
	result?: ProcessResult;
}

/**
 * WebSocket progress message
 */
export interface ProgressMessage {
	progress: number;
	step: string;
	message?: string;
}

// === API Responses ===

/**
 * Health check response
 */
export interface HealthCheckResponse {
	status: 'ok';
}

/**
 * Error response
 */
export interface ApiErrorResponse {
	error: string;
	detail?: string;
}

/**
 * Save project response
 */
export interface SaveProjectResponse {
	path: string;
}

/**
 * Open project request
 */
export interface OpenProjectRequest {
	path: string;
}

/**
 * File info request
 */
export interface FileInfoRequest {
	path: string;
}

/**
 * Raster thumbnail request
 */
export interface RasterThumbnailRequest {
	path: string;
	max_size?: number;
}
