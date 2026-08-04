use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

pub struct PythonBackend(pub Mutex<Option<Child>>);

fn start_backend() -> Option<Child> {
    match Command::new("python")
        .args([
            "-m",
            "uvicorn",
            "backend.src.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "19876",
        ])
        .spawn()
    {
        Ok(child) => {
            eprintln!("[Tauri] Python backend started (PID: {})", child.id());
            Some(child)
        }
        Err(err) => {
            eprintln!(
                "[Tauri] FATAL: Failed to start Python backend: {}\n\
                 Make sure Python is installed and 'pip install uvicorn fastapi' has been run.\n\
                 Working directory: {:?}",
                err,
                std::env::current_dir().unwrap_or_default(),
            );
            None
        }
    }
}

fn kill_backend(child: &mut Child) {
    eprintln!("[Tauri] Stopping Python backend (PID: {})...", child.id());
    let _ = child.kill();
    let _ = child.wait();
    eprintln!("[Tauri] Python backend stopped.");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let child = match start_backend() {
        Some(child) => child,
        None => {
            eprintln!("[Tauri] Cannot start without Python backend. Exiting.");
            std::process::exit(1);
        }
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(PythonBackend(Mutex::new(Some(child))))
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.try_state::<PythonBackend>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            kill_backend(child);
                        }
                        *guard = None;
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Tauri runtime error");
}
