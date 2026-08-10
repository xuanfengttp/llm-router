use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

pub struct PythonBackend(pub Mutex<Option<Child>>);

fn kill_port_19876() {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        if let Ok(output) = Command::new("netstat")
            .args(["-ano"])
            .creation_flags(0x08000000)
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if line.contains(":19876") && line.contains("LISTENING") {
                    if let Some(pid) = line.split_whitespace().last() {
                        eprintln!("[Tauri] Killing PID {} occupying port 19876", pid);
                        let _ = Command::new("taskkill")
                            .args(["/F", "/PID", pid])
                            .creation_flags(0x08000000)
                            .output();
                    }
                }
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        if let Ok(output) = Command::new("lsof")
            .args(["-ti:19876"])
            .output()
        {
            if let Ok(pid_str) = String::from_utf8(output.stdout) {
                for pid in pid_str.trim().lines() {
                    eprintln!("[Tauri] Killing PID {} occupying port 19876", pid);
                    let _ = Command::new("kill").arg("-9").arg(pid).output();
                }
            }
        }
    }
    std::thread::sleep(Duration::from_millis(500));
}

fn wait_for_backend(timeout_secs: u64) -> bool {
    let start = Instant::now();
    let addr = "127.0.0.1:19876";
    eprintln!("[Tauri] Waiting for Python backend on {}...", addr);
    loop {
        match TcpStream::connect_timeout(&addr.parse().unwrap(), Duration::from_secs(1)) {
            Ok(_) => {
                eprintln!(
                    "[Tauri] Python backend ready (took {:?})",
                    start.elapsed()
                );
                return true;
            }
            Err(_) => {
                if start.elapsed().as_secs() >= timeout_secs {
                    eprintln!(
                        "[Tauri] ERROR: Backend did not start within {}s",
                        timeout_secs
                    );
                    return false;
                }
                std::thread::sleep(Duration::from_millis(500));
            }
        }
    }
}

fn start_backend() -> Option<Child> {
    kill_port_19876();

    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()));
    if let Some(ref dir) = exe_dir {
        eprintln!("[Tauri] Setting CWD to: {:?}", dir);
        if let Err(e) = std::env::set_current_dir(dir) {
            eprintln!("[Tauri] WARNING: Failed to set CWD: {}", e);
        }
        // Ensure logs directory exists
        let log_dir = dir.join("logs");
        let _ = fs::create_dir_all(&log_dir);
    }

    let log_file_path = exe_dir
        .as_ref()
        .map(|d| d.join("logs").join("llm-router.log"))
        .unwrap_or_else(|| std::path::PathBuf::from("logs/llm-router.log"));

    let log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file_path)
        .ok();

    let mut cmd = Command::new("python");
    cmd.args([
        "-m",
        "uvicorn",
        "backend.src.server:app",
        "--host",
        "0.0.0.0",
        "--port",
        "19876",
    ]);
    // Windows: hide console window
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    match cmd.spawn() {
        Ok(mut child) => {
            eprintln!("[Tauri] Python backend started (PID: {})", child.id());

            // Spawn threads to capture stdout/stderr and write to log file
            if let Some(mut file) = log_file {
                if let Some(stdout) = child.stdout.take() {
                    let mut f = file.try_clone().unwrap();
                    let pid = child.id();
                    std::thread::spawn(move || {
                        let reader = BufReader::new(stdout);
                        for line in reader.lines() {
                            if let Ok(line) = line {
                                let _ = writeln!(f, "[py:{}] {}", pid, line);
                            }
                        }
                    });
                }
                if let Some(stderr) = child.stderr.take() {
                    let mut f = file;
                    let pid = child.id();
                    std::thread::spawn(move || {
                        let reader = BufReader::new(stderr);
                        for line in reader.lines() {
                            if let Ok(line) = line {
                                let _ = writeln!(f, "[py:{}:err] {}", pid, line);
                            }
                        }
                    });
                }
            }

            if !wait_for_backend(30) {
                eprintln!("[Tauri] WARNING: Backend may still be starting...");
            }
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
