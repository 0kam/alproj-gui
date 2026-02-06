// ALPROJ GUI - Tauri application library
// This module initializes the Tauri application and manages the Python sidecar

use log::{error, info, warn};
use std::process::{Child, Command, Stdio};
use std::sync::Arc;
use sysinfo::{Pid, System};
use tauri::async_runtime::Mutex;
use tauri::Emitter;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tokio::time::{sleep, Duration};

/// Backend configuration
const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: u16 = 8765;
const HEALTH_CHECK_URL: &str = "http://127.0.0.1:8765/api/health";
const HEALTH_CHECK_TIMEOUT_SECS: u64 = 180;
const HEALTH_CHECK_INTERVAL_MS: u64 = 500;

/// Enum to hold different types of process handles
pub enum ProcessHandle {
    /// Tauri sidecar process (production)
    TauriChild(CommandChild),
    /// Standard process (development)
    StdChild(Child),
}

impl ProcessHandle {
    /// Get the process ID if available
    pub fn pid(&self) -> Option<u32> {
        match self {
            ProcessHandle::TauriChild(child) => Some(child.pid()),
            ProcessHandle::StdChild(ref child) => Some(child.id()),
        }
    }

    /// Kill the process and all its children, consuming self
    pub fn kill(self) -> Result<(), String> {
        // First, kill all child processes
        if let Some(pid) = self.pid() {
            info!("Killing process tree for PID: {}", pid);
            kill_process_tree(pid);
        }

        // Then kill the main process
        match self {
            ProcessHandle::TauriChild(child) => child.kill().map_err(|e| e.to_string()),
            ProcessHandle::StdChild(mut child) => child.kill().map_err(|e| e.to_string()),
        }
    }
}

/// Kill a process and all its descendant processes
fn kill_process_tree(root_pid: u32) {
    let mut sys = System::new();
    sys.refresh_processes(sysinfo::ProcessesToUpdate::All, true);

    // Collect all descendant PIDs first
    let descendants = collect_descendants(&sys, root_pid);

    // Kill descendants in reverse order (children before parents)
    for pid in descendants.iter().rev() {
        if let Some(process) = sys.process(Pid::from_u32(*pid)) {
            info!("Killing child process {} ({})", pid, process.name().to_string_lossy());
            process.kill();
        }
    }
}

/// Recursively collect all descendant process IDs
fn collect_descendants(sys: &System, parent_pid: u32) -> Vec<u32> {
    let mut descendants = Vec::new();
    let parent_pid_obj = Pid::from_u32(parent_pid);

    for (pid, process) in sys.processes() {
        if let Some(ppid) = process.parent() {
            if ppid == parent_pid_obj {
                let child_pid = pid.as_u32();
                descendants.push(child_pid);
                // Recursively collect children of this child
                descendants.extend(collect_descendants(sys, child_pid));
            }
        }
    }

    descendants
}

/// Application state for managing the Python backend sidecar
pub struct AppState {
    /// Sidecar process handle
    pub sidecar: Mutex<Option<ProcessHandle>>,
    /// Backend ready flag
    pub backend_ready: Mutex<bool>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            sidecar: Mutex::new(None),
            backend_ready: Mutex::new(false),
        }
    }
}

/// Check if we're running in development mode
fn is_dev_mode() -> bool {
    cfg!(debug_assertions)
}

/// Find uv executable in common installation locations
/// Tauri doesn't inherit the shell PATH, so we need to check common paths
fn find_uv_path() -> Option<String> {
    let home = std::env::var("HOME").ok()?;

    // Common uv installation paths
    let candidates = [
        format!("{}/.local/bin/uv", home),
        format!("{}/.cargo/bin/uv", home),
        "/usr/local/bin/uv".to_string(),
        "/opt/homebrew/bin/uv".to_string(),
        // Also check if uv is in PATH (in case it works)
        "uv".to_string(),
    ];

    for path in candidates {
        if path == "uv" {
            // For plain "uv", just return it and let the shell try
            continue;
        }
        if std::path::Path::new(&path).exists() {
            return Some(path);
        }
    }

    // Fallback to plain "uv" if no absolute path found
    Some("uv".to_string())
}

/// Get the platform-specific sidecar directory name
fn get_sidecar_dir_name() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    { "sidecar-aarch64-apple-darwin" }
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    { "sidecar-x86_64-apple-darwin" }
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    { "sidecar-aarch64-unknown-linux-gnu" }
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    { "sidecar-x86_64-unknown-linux-gnu" }
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    { "sidecar-x86_64-pc-windows-msvc" }
}

/// Get the platform-specific sidecar binary name
fn get_sidecar_binary_name() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    { "backend-sidecar-aarch64-apple-darwin" }
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    { "backend-sidecar-x86_64-apple-darwin" }
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    { "backend-sidecar-aarch64-unknown-linux-gnu" }
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    { "backend-sidecar-x86_64-unknown-linux-gnu" }
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    { "backend-sidecar-x86_64-pc-windows-msvc.exe" }
}

/// Start the Python backend sidecar process
async fn start_sidecar(app: &tauri::AppHandle) -> Result<ProcessHandle, String> {
    if is_dev_mode() {
        // Development mode: use std::process::Command with uv
        info!("Starting backend in development mode with uv");

        // In development mode, the backend is in the project root's "backend" folder
        // Get the src-tauri directory, then go up one level to project root
        let src_tauri_dir = app
            .path()
            .resource_dir()
            .map_err(|e| format!("Failed to get resource dir: {}", e))?
            .parent()
            .ok_or("Failed to get parent dir")?
            .parent()
            .ok_or("Failed to get src-tauri dir")?
            .to_path_buf();

        // Project root is one level up from src-tauri
        let backend_dir = src_tauri_dir.parent()
            .ok_or("Failed to get project root")?
            .join("backend");

        info!("Backend directory: {:?}", backend_dir);

        // Verify backend directory exists
        if !backend_dir.exists() {
            return Err(format!("Backend directory does not exist: {:?}", backend_dir));
        }

        // Try to find uv in common locations since Tauri doesn't inherit shell PATH
        let uv_path = find_uv_path().ok_or("Could not find uv. Please ensure uv is installed.")?;
        info!("Using uv at: {:?}", uv_path);

        let child = Command::new(&uv_path)
            .args([
                "run",
                "uvicorn",
                "app.main:app",
                "--host",
                BACKEND_HOST,
                "--port",
                &BACKEND_PORT.to_string(),
            ])
            .current_dir(&backend_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn uv process: {}", e))?;

        info!("Backend process started with PID: {:?}", child.id());

        Ok(ProcessHandle::StdChild(child))
    } else {
        // Production mode: use bundled sidecar from resources
        // The sidecar is built with PyInstaller --onedir and needs _internal next to it
        info!("Starting backend in production mode with bundled sidecar");

        let resource_dir = app
            .path()
            .resource_dir()
            .map_err(|e| format!("Failed to get resource dir: {}", e))?;

        // Sidecar is in Resources/binaries/sidecar-{platform}/
        let sidecar_dir = resource_dir.join("binaries").join(get_sidecar_dir_name());
        let sidecar_path = sidecar_dir.join(get_sidecar_binary_name());

        info!("Sidecar directory: {:?}", sidecar_dir);
        info!("Sidecar path: {:?}", sidecar_path);

        if !sidecar_path.exists() {
            return Err(format!("Sidecar binary not found: {:?}", sidecar_path));
        }

        // Start the sidecar process
        // Must run from sidecar_dir so it can find _internal
        let child = Command::new(&sidecar_path)
            .args(["--host", BACKEND_HOST, "--port", &BACKEND_PORT.to_string()])
            .current_dir(&sidecar_dir)
            // Avoid deadlock from unread stdout/stderr pipes in GUI mode.
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

        info!("Backend process started with PID: {:?}", child.id());

        Ok(ProcessHandle::StdChild(child))
    }
}

/// Wait for the backend to become ready by polling the health endpoint
async fn wait_for_backend() -> Result<(), String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(HEALTH_CHECK_TIMEOUT_SECS);

    info!("Waiting for backend to become ready at {}", HEALTH_CHECK_URL);

    while start.elapsed() < timeout {
        match client.get(HEALTH_CHECK_URL).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    info!("Backend is ready!");
                    return Ok(());
                }
                warn!(
                    "Backend returned non-success status: {}",
                    response.status()
                );
            }
            Err(e) => {
                // Connection refused is expected while backend is starting
                if !e.is_connect() {
                    warn!("Health check failed: {}", e);
                }
            }
        }

        sleep(Duration::from_millis(HEALTH_CHECK_INTERVAL_MS)).await;
    }

    Err(format!(
        "Backend failed to start within {} seconds",
        HEALTH_CHECK_TIMEOUT_SECS
    ))
}

/// Stop the sidecar process gracefully
async fn stop_sidecar(state: &AppState) {
    let mut sidecar = state.sidecar.lock().await;
    if let Some(handle) = sidecar.take() {
        info!("Stopping backend sidecar...");
        if let Err(e) = handle.kill() {
            error!("Failed to kill sidecar process: {}", e);
        } else {
            info!("Backend sidecar stopped");
        }
    }
}

/// Initialize the Tauri application
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logger
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    info!("Starting ALPROJ GUI");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Arc::new(AppState::default()))
        .setup(|app| {
            // Open devtools in debug mode
            #[cfg(debug_assertions)]
            {
                if let Some(window) = app.get_webview_window("main") {
                    window.open_devtools();
                }
            }

            // Start Python sidecar
            let app_handle = app.handle().clone();
            let state = app.state::<Arc<AppState>>().inner().clone();

            tauri::async_runtime::spawn(async move {
                match start_sidecar(&app_handle).await {
                    Ok(child) => {
                        // Store the child process handle
                        *state.sidecar.lock().await = Some(child);

                        // Wait for backend to be ready
                        match wait_for_backend().await {
                            Ok(()) => {
                                *state.backend_ready.lock().await = true;
                                info!("Backend initialization complete");

                                // Emit event to frontend
                                if let Err(e) = app_handle.emit("backend-ready", true) {
                                    error!("Failed to emit backend-ready event: {}", e);
                                }
                            }
                            Err(e) => {
                                error!("Backend failed to start: {}", e);
                                // Emit error event to frontend
                                if let Err(e) = app_handle.emit("backend-error", e.clone()) {
                                    error!("Failed to emit backend-error event: {}", e);
                                }
                            }
                        }
                    }
                    Err(e) => {
                        error!("Failed to start sidecar: {}", e);
                        // Emit error event to frontend
                        if let Err(emit_err) = app_handle.emit("backend-error", e.clone()) {
                            error!("Failed to emit backend-error event: {}", emit_err);
                        }
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Handle window close to stop sidecar
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<Arc<AppState>>().inner().clone();
                tauri::async_runtime::block_on(async {
                    stop_sidecar(&state).await;
                });
            }
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_backend_status,
            check_backend_health,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Simple greeting command for testing
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to ALPROJ GUI.", name)
}

/// Check if the Python backend is running (from state)
#[tauri::command]
async fn get_backend_status(state: tauri::State<'_, Arc<AppState>>) -> Result<String, String> {
    let ready = *state.backend_ready.lock().await;
    if ready {
        Ok("connected".to_string())
    } else {
        Ok("connecting".to_string())
    }
}

/// Check backend health by calling the health endpoint
#[tauri::command]
async fn check_backend_health() -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let response = client
        .get(HEALTH_CHECK_URL)
        .send()
        .await
        .map_err(|e| format!("Health check request failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Health check failed with status: {}", response.status()));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse health check response: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_dev_mode() {
        // In debug builds, this should return true
        #[cfg(debug_assertions)]
        assert!(is_dev_mode());

        // In release builds, this should return false
        #[cfg(not(debug_assertions))]
        assert!(!is_dev_mode());
    }
}
