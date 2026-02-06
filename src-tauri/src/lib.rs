// ALPROJ GUI - Tauri application library
// This module initializes the Tauri application and manages the Python sidecar

use log::{error, info, warn};
use std::fs::{self, OpenOptions};
use std::io::{Read, Seek, SeekFrom};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
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
const HEALTH_CHECK_URL_LOCALHOST: &str = "http://localhost:8765/api/health";
const HEALTH_CHECK_TIMEOUT_SECS: u64 = 180;
const HEALTH_CHECK_INTERVAL_MS: u64 = 500;
const BACKEND_LOG_FILE_NAME: &str = "backend-sidecar.log";
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

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
            info!(
                "Killing child process {} ({})",
                pid,
                process.name().to_string_lossy()
            );
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
    /// Sidecar log file path (production mode)
    pub backend_log_path: Mutex<Option<PathBuf>>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            sidecar: Mutex::new(None),
            backend_ready: Mutex::new(false),
            backend_log_path: Mutex::new(None),
        }
    }
}

#[derive(serde::Serialize)]
struct BackendLogChunk {
    next_offset: usize,
    text: String,
}

fn resolve_backend_log_path(app: &tauri::AppHandle) -> PathBuf {
    if let Ok(log_dir) = app.path().app_log_dir() {
        return log_dir.join(BACKEND_LOG_FILE_NAME);
    }
    if let Ok(data_dir) = app.path().app_data_dir() {
        return data_dir.join("logs").join(BACKEND_LOG_FILE_NAME);
    }
    std::env::temp_dir()
        .join("alproj-gui")
        .join(BACKEND_LOG_FILE_NAME)
}

fn format_log_tail(log_path: &Path, max_lines: usize) -> String {
    let bytes = match fs::read(log_path) {
        Ok(bytes) => bytes,
        Err(e) => {
            return format!("Backend log read failed: {} ({})", e, log_path.display());
        }
    };

    let text = String::from_utf8_lossy(&bytes);
    let lines: Vec<&str> = text.lines().collect();
    let start = lines.len().saturating_sub(max_lines);
    let mut tail = lines[start..].join("\n");

    const MAX_CHARS: usize = 4000;
    if tail.chars().count() > MAX_CHARS {
        tail = tail
            .chars()
            .rev()
            .take(MAX_CHARS)
            .collect::<String>()
            .chars()
            .rev()
            .collect::<String>();
    }

    format!(
        "Backend log: {}\n--- log tail ---\n{}\n----------------",
        log_path.display(),
        tail
    )
}

async fn read_backend_log_tail(state: &Arc<AppState>, max_lines: usize) -> Option<String> {
    let log_path = state.backend_log_path.lock().await.clone();
    log_path.map(|path| format_log_tail(&path, max_lines))
}

async fn check_sidecar_exited(state: &Arc<AppState>) -> Option<String> {
    let exit = {
        let mut sidecar = state.sidecar.lock().await;
        match sidecar.as_mut() {
            Some(ProcessHandle::StdChild(child)) => match child.try_wait() {
                Ok(Some(status)) => Some(status),
                Ok(None) => None,
                Err(e) => {
                    return Some(format!("Failed to query backend process status: {}", e));
                }
            },
            _ => None,
        }
    };

    if let Some(status) = exit {
        let code_text = match status.code() {
            Some(code) => format!("exit code {}", code),
            None => "terminated by signal".to_string(),
        };
        if let Some(log_tail) = read_backend_log_tail(state, 80).await {
            return Some(format!(
                "Backend process exited before ready ({})\n{}",
                code_text, log_tail
            ));
        }
        return Some(format!(
            "Backend process exited before ready ({})",
            code_text
        ));
    }

    None
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
    {
        "sidecar-aarch64-apple-darwin"
    }
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    {
        "sidecar-x86_64-apple-darwin"
    }
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    {
        "sidecar-aarch64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    {
        "sidecar-x86_64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    {
        "sidecar-x86_64-pc-windows-msvc"
    }
}

/// Get the platform-specific sidecar binary name
fn get_sidecar_binary_name() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    {
        "backend-sidecar-aarch64-apple-darwin"
    }
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    {
        "backend-sidecar-x86_64-apple-darwin"
    }
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    {
        "backend-sidecar-aarch64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    {
        "backend-sidecar-x86_64-unknown-linux-gnu"
    }
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    {
        "backend-sidecar-x86_64-pc-windows-msvc.exe"
    }
}

/// Start the Python backend sidecar process
async fn start_sidecar(app: &tauri::AppHandle) -> Result<(ProcessHandle, Option<PathBuf>), String> {
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
        let backend_dir = src_tauri_dir
            .parent()
            .ok_or("Failed to get project root")?
            .join("backend");

        info!("Backend directory: {:?}", backend_dir);

        // Verify backend directory exists
        if !backend_dir.exists() {
            return Err(format!(
                "Backend directory does not exist: {:?}",
                backend_dir
            ));
        }

        // Try to find uv in common locations since Tauri doesn't inherit shell PATH
        let uv_path = find_uv_path().ok_or("Could not find uv. Please ensure uv is installed.")?;
        info!("Using uv at: {:?}", uv_path);

        let log_path = resolve_backend_log_path(app);
        if let Some(parent) = log_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create backend log dir {:?}: {}", parent, e))?;
        }
        let stdout_log = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .map_err(|e| format!("Failed to open backend log file {:?}: {}", log_path, e))?;
        let stderr_log = stdout_log
            .try_clone()
            .map_err(|e| format!("Failed to clone backend log file handle: {}", e))?;

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
            .stdout(Stdio::from(stdout_log))
            .stderr(Stdio::from(stderr_log))
            .spawn()
            .map_err(|e| format!("Failed to spawn uv process: {}", e))?;

        info!("Backend process started with PID: {:?}", child.id());
        info!("Backend log path: {:?}", log_path);

        Ok((ProcessHandle::StdChild(child), Some(log_path)))
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
        let log_path = resolve_backend_log_path(app);
        if let Some(parent) = log_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create backend log dir {:?}: {}", parent, e))?;
        }
        let stdout_log = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .map_err(|e| format!("Failed to open backend log file {:?}: {}", log_path, e))?;
        let stderr_log = stdout_log
            .try_clone()
            .map_err(|e| format!("Failed to clone backend log file handle: {}", e))?;

        let mut command = Command::new(&sidecar_path);
        command
            .args(["--host", BACKEND_HOST, "--port", &BACKEND_PORT.to_string()])
            .current_dir(&sidecar_dir)
            .stdout(Stdio::from(stdout_log))
            .stderr(Stdio::from(stderr_log));

        #[cfg(windows)]
        command.creation_flags(CREATE_NO_WINDOW);

        let child = command
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

        info!("Backend process started with PID: {:?}", child.id());
        info!("Backend log path: {:?}", log_path);

        Ok((ProcessHandle::StdChild(child), Some(log_path)))
    }
}

/// Wait for the backend to become ready by polling the health endpoint
async fn wait_for_backend(state: &Arc<AppState>) -> Result<(), String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let start = std::time::Instant::now();
    let timeout = Duration::from_secs(HEALTH_CHECK_TIMEOUT_SECS);
    let health_urls = [HEALTH_CHECK_URL, HEALTH_CHECK_URL_LOCALHOST];

    info!(
        "Waiting for backend to become ready at {}",
        HEALTH_CHECK_URL
    );

    while start.elapsed() < timeout {
        if let Some(exit_error) = check_sidecar_exited(state).await {
            return Err(exit_error);
        }

        for url in health_urls {
            match client.get(url).send().await {
                Ok(response) => {
                    if response.status().is_success() {
                        info!("Backend is ready at {}", url);
                        return Ok(());
                    }
                    warn!(
                        "Backend returned non-success status at {}: {}",
                        url,
                        response.status()
                    );
                }
                Err(e) => {
                    // Connection refused is expected while backend is starting
                    if !e.is_connect() {
                        warn!("Health check failed at {}: {}", url, e);
                    }
                }
            }
        }

        sleep(Duration::from_millis(HEALTH_CHECK_INTERVAL_MS)).await;
    }

    let mut error_message = format!(
        "Backend failed to start within {} seconds",
        HEALTH_CHECK_TIMEOUT_SECS
    );
    if let Some(log_tail) = read_backend_log_tail(state, 80).await {
        error_message.push('\n');
        error_message.push_str(&log_tail);
    }
    Err(error_message)
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
                    Ok((child, log_path)) => {
                        // Store the child process handle
                        *state.sidecar.lock().await = Some(child);
                        *state.backend_log_path.lock().await = log_path;

                        // Wait for backend to be ready
                        match wait_for_backend(&state).await {
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
            get_backend_log_cursor,
            read_backend_log_chunk,
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
        return Err(format!(
            "Health check failed with status: {}",
            response.status()
        ));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse health check response: {}", e))
}

#[tauri::command]
async fn get_backend_log_cursor(state: tauri::State<'_, Arc<AppState>>) -> Result<usize, String> {
    let log_path = state.backend_log_path.lock().await.clone();
    let Some(path) = log_path else {
        return Ok(0);
    };

    let meta = fs::metadata(&path)
        .map_err(|e| format!("Failed to read backend log metadata {:?}: {}", path, e))?;
    Ok(meta.len() as usize)
}

#[tauri::command]
async fn read_backend_log_chunk(
    state: tauri::State<'_, Arc<AppState>>,
    offset: usize,
    max_bytes: Option<usize>,
) -> Result<BackendLogChunk, String> {
    let log_path = state.backend_log_path.lock().await.clone();
    let Some(path) = log_path else {
        return Ok(BackendLogChunk {
            next_offset: offset,
            text: String::new(),
        });
    };

    let mut file = fs::File::open(&path)
        .map_err(|e| format!("Failed to open backend log {:?}: {}", path, e))?;
    let file_len = file
        .metadata()
        .map_err(|e| format!("Failed to read backend log metadata {:?}: {}", path, e))?
        .len() as usize;

    let normalized_offset = offset.min(file_len);
    file.seek(SeekFrom::Start(normalized_offset as u64))
        .map_err(|e| format!("Failed to seek backend log {:?}: {}", path, e))?;

    let limit = max_bytes.unwrap_or(64 * 1024).clamp(1024, 1024 * 1024);
    let to_read = (file_len - normalized_offset).min(limit);
    if to_read == 0 {
        return Ok(BackendLogChunk {
            next_offset: normalized_offset,
            text: String::new(),
        });
    }

    let mut buffer = vec![0u8; to_read];
    let read = file
        .read(&mut buffer)
        .map_err(|e| format!("Failed to read backend log {:?}: {}", path, e))?;
    buffer.truncate(read);
    let text = String::from_utf8_lossy(&buffer).to_string();

    Ok(BackendLogChunk {
        next_offset: normalized_offset + read,
        text,
    })
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
