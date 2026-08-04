use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

pub struct PythonBackend(pub Mutex<Option<Child>>);

fn start_backend() -> Option<Child> {
    Command::new("python")
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
        .ok()
}

fn kill_backend(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let child = start_backend().expect("Failed to start Python backend");

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
        .expect("error while running tauri application");
}
