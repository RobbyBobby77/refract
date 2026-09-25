//! mc-glass-bridge: runs Mission Center's `magpie` data engine and relays its
//! protobuf IPC as JSON lines, so the Python/QML frontend can use it.
//!
//! stdin:  one JSON-encoded `magpie.ipc.Request` per line
//! stdout: one JSON-encoded `magpie.ipc.Response` per line, in order; transport
//!         failures come back as `{"body":{"error":{"message":"…"}}}`
//!
//! The bridge exits when stdin closes. magpie is started with the bridge as its
//! parent and dies with it (magpie sets PR_SET_PDEATHSIG itself).

use std::ffi::{c_void, CStr, CString};
use std::io::{BufRead, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use magpie_types::ipc::{response, Request, Response};
use magpie_types::prost::Message;
use nng_c_sys as nng;

fn strerror(code: i32) -> String {
    unsafe { CStr::from_ptr(nng::nng_strerror(code)) }
        .to_string_lossy()
        .into_owned()
}

fn check(code: i32, what: &str) -> Result<(), String> {
    if code == 0 {
        Ok(())
    } else {
        Err(format!("{what}: {}", strerror(code)))
    }
}

/// A REQ socket talking to one magpie instance.
struct Client {
    socket: nng::nng_socket,
}

impl Client {
    fn connect(addr: &CStr) -> Result<Self, String> {
        let mut socket = nng::nng_socket { id: 0 };
        check(unsafe { nng::nng_req0_open(&mut socket) }, "open socket")?;
        unsafe {
            nng::nng_socket_set_ms(socket, nng::NNG_OPT_RECVTIMEO.as_ptr() as _, 15_000);
            nng::nng_socket_set_ms(socket, nng::NNG_OPT_SENDTIMEO.as_ptr() as _, 5_000);
        }
        // magpie may still be starting up: retry the dial for a while.
        let deadline = Instant::now() + Duration::from_secs(10);
        loop {
            let res = unsafe { nng::nng_dial(socket, addr.as_ptr(), std::ptr::null_mut(), 0) };
            if res == 0 {
                return Ok(Self { socket });
            }
            if Instant::now() > deadline {
                unsafe { nng::nng_socket_close(socket) };
                return Err(format!("connect to magpie: {}", strerror(res)));
            }
            std::thread::sleep(Duration::from_millis(50));
        }
    }

    fn request(&self, payload: &[u8]) -> Result<Vec<u8>, String> {
        let mut data = payload.to_vec();
        check(
            unsafe { nng::nng_send(self.socket, data.as_mut_ptr() as *mut c_void, data.len(), 0) },
            "send",
        )?;
        let mut buf: *mut c_void = std::ptr::null_mut();
        let mut len: usize = 0;
        check(
            unsafe {
                nng::nng_recv(
                    self.socket,
                    &mut buf as *mut *mut c_void as *mut c_void,
                    &mut len,
                    nng::NNG_FLAG_ALLOC,
                )
            },
            "receive",
        )?;
        let out = unsafe { std::slice::from_raw_parts(buf as *const u8, len) }.to_vec();
        unsafe { nng::nng_free(buf, len) };
        Ok(out)
    }
}

impl Drop for Client {
    fn drop(&mut self) {
        unsafe { nng::nng_socket_close(self.socket) };
    }
}

/// magpie location: $MC_MAGPIE, else next to this executable.
fn magpie_path() -> PathBuf {
    if let Some(path) = std::env::var_os("MC_MAGPIE") {
        return PathBuf::from(path);
    }
    let exe = std::env::current_exe().unwrap_or_default();
    let dir = exe.parent().map(PathBuf::from).unwrap_or_default();
    for name in ["missioncenter-magpie", "magpie"] {
        let candidate = dir.join(name);
        if candidate.exists() {
            return candidate;
        }
    }
    PathBuf::from("missioncenter-magpie")
}

struct Engine {
    addr: CString,
    socket_path: PathBuf,
    child: Option<Child>,
    client: Option<Client>,
}

impl Engine {
    fn new() -> Self {
        let runtime = std::env::var_os("XDG_RUNTIME_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir);
        let socket_path = runtime.join(format!("mc-glass-magpie-{}.ipc", std::process::id()));
        let addr = CString::new(format!("ipc://{}", socket_path.display())).unwrap();
        Self { addr, socket_path, child: None, client: None }
    }

    fn start(&mut self) -> Result<(), String> {
        self.client = None;
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        let _ = std::fs::remove_file(&self.socket_path);
        let child = Command::new(magpie_path())
            .arg("--addr")
            .arg(self.addr.to_str().unwrap())
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .spawn()
            .map_err(|e| format!("start magpie: {e}"))?;
        self.child = Some(child);
        self.client = Some(Client::connect(&self.addr)?);
        Ok(())
    }

    fn alive(&mut self) -> bool {
        matches!(self.child.as_mut().map(|c| c.try_wait()), Some(Ok(None)))
    }

    /// One round trip; restarts magpie once if it died or the call failed.
    fn call(&mut self, payload: &[u8]) -> Result<Vec<u8>, String> {
        for attempt in 0..2 {
            if self.client.is_none() || !self.alive() {
                self.start()?;
            }
            match self.client.as_ref().unwrap().request(payload) {
                Ok(bytes) => return Ok(bytes),
                Err(e) if attempt == 1 => return Err(e),
                Err(_) => self.client = None,
            }
        }
        unreachable!()
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.client = None;
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        let _ = std::fs::remove_file(&self.socket_path);
    }
}

fn error_line(message: String) -> String {
    let response = Response {
        body: Some(response::Body::Error(response::Error { message })),
    };
    serde_json::to_string(&response).unwrap_or_else(|_| "{}".into())
}

fn handle(engine: &mut Engine, line: &str) -> String {
    let request: Request = match serde_json::from_str(line) {
        Ok(r) => r,
        Err(e) => return error_line(format!("bad request: {e}")),
    };
    let reply = match engine.call(&request.encode_to_vec()) {
        Ok(bytes) => bytes,
        Err(e) => return error_line(e),
    };
    match Response::decode(reply.as_slice()) {
        Ok(response) => serde_json::to_string(&response)
            .unwrap_or_else(|e| error_line(format!("encode response: {e}"))),
        Err(e) => error_line(format!("decode response: {e}")),
    }
}

fn main() {
    // Leave with our parent (the frontend) even if it doesn't close stdin.
    unsafe { libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGTERM) };

    let mut engine = Engine::new();
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        let out = handle(&mut engine, &line);
        if writeln!(stdout, "{out}").and_then(|_| stdout.flush()).is_err() {
            break;
        }
    }
}
