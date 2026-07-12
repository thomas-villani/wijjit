# wijjit-ssh — Implementation Spec

Status: **draft**. This document specifies the work to take `wijjit-ssh` from
the current prototype (a working `RemoteTerminalBackend` + a minimal
`WijjitSSH` server, verified with a real asyncssh round trip) to something you
could actually deploy: a real async byte-parser input path, pluggable
authentication, terminal-capability negotiation, resource limits, graceful
shutdown, logging, tests, and packaging.

It is deliberately concrete — interface signatures, file layout, and phased
milestones — so it can be read top-to-bottom to understand the whole design,
then executed phase by phase.

---

## 1. Goals & non-goals

**Goals**
- Serve any Wijjit app over SSH with per-connection isolation, one app instance
  per session, N sessions per process.
- Zero changes required to an existing Wijjit app beyond `Wijjit(backend=...)`.
- Real auth (public key, password, keyboard-interactive), configurable per
  deployment.
- Correct terminal handling: raw byte I/O, full key/mouse parsing, resize,
  UTF-8, sane defaults for real-world SSH clients (OpenSSH, PuTTY, mobile).
- Bounded resources: max sessions, idle/absolute timeouts, per-IP limits.
- Clean shutdown that restores every client and cancels every app task.

**Non-goals (for v0.1)**
- Not a general SSH server: no exec/subsystem/sftp/port-forwarding. Sessions
  only ever run a Wijjit app; there is no shell, no command execution, no
  filesystem access. This is a feature (attack surface), not a limitation.
- No multi-process/worker model. One event loop, one process. Horizontal
  scale is "run more instances behind a TCP load balancer" (see §12).
- No built-in TLS/cert stuff — SSH provides the transport crypto.

---

## 2. Architecture recap

Wijjit's event loop talks to "the terminal" through a `TerminalBackend`
(`wijjit.terminal.backend`). The seam is already in core:

```
asyncssh channel  ──bytes──▶  RemoteTerminalBackend  ──Key/MouseEvent──▶  Wijjit event loop
       ▲                            (this package)                              │
       └────────────────────────  frame bytes  ◀───────────────────────────────┘
```

Per connection we build: a backend, an input source, and a `Wijjit` app, then
run `app.event_loop.run_async()` as its own asyncio task. Wijjit's render
context and terminal-size override are **contextvar-based and task-local**, so
concurrent sessions never collide. `owns_terminal=False` on the backend keeps
the app from installing any process-global signal/atexit/suspend handlers.

The prototype takes two shortcuts this spec removes:
1. Input goes through a prompt_toolkit **pipe input + reader thread** (one
   thread per session). → Replace with an async byte parser (§4).
2. The channel is opened in **UTF-8 text mode**. → Switch to raw bytes
   (`encoding=None`) so the parser sees exactly what the client sent (§6).

---

## 3. Target package layout

```
wijjit-ssh/
  pyproject.toml
  README.md
  SPEC.md                     (this file)
  src/wijjit_ssh/
    __init__.py               public API
    server.py                 WijjitSSH, session glue (asyncssh callbacks)
    backend.py                RemoteTerminalBackend  (bytes I/O + size)
    input.py                  ChannelInputSource + KeyDecoder  (NEW, §4)
    auth.py                   AuthPolicy + presets                 (NEW, §5)
    keys.py                   host-key loading/generation          (NEW, §7)
    limits.py                 SessionRegistry, timeouts, rate limit (NEW, §8)
    config.py                 ServerConfig dataclass               (NEW, §10)
    logging.py                structured per-session logging       (NEW, §9)
  examples/
    hello_ssh.py              current minimal demo
    dashboard_ssh.py          auth + multiple views (NEW)
  tests/
    test_input_decoder.py     table-driven byte→Key/Mouse (NEW)
    test_auth.py              (NEW)
    test_roundtrip.py         in-process client↔server (promote scratch) (NEW)
    test_limits.py            (NEW)
```

---

## 4. Async byte-parser input path (replaces the reader thread)

### 4.1 Why

The prototype reuses `wijjit.terminal.input.InputHandler`, which spawns a
background thread polling prompt_toolkit. That is fine for a local app but wrong
at server scale: one OS thread per connection, plus a prompt_toolkit pipe per
session. We already receive bytes on the event loop in `data_received`; parse
them there, on the loop, with no thread and no prompt_toolkit.

### 4.2 The contract the event loop requires

An input handler is duck-typed. The complete surface Wijjit calls (verified
against `core/event_loop.py`, `core/suspend.py`, `testing/harness.py`):

```python
class InputSource(Protocol):
    mouse_enabled: bool
    async def read_input_async(self, timeout: float) -> Key | MouseEvent | None: ...
    def enable_mouse_tracking(self) -> None: ...
    def disable_mouse_tracking(self) -> None: ...
    def close(self) -> None: ...
    def restore_terminal(self) -> None: ...
```

`ChannelInputSource` implements exactly this. `read_input_async` awaits an
`asyncio.Queue` (populated by the decoder) with the given timeout, returning
`None` on timeout — matching how the loop already treats a quiet frame.
`enable/disable_mouse_tracking` write the DEC private-mode sequences to the
channel (through the backend's byte writer). `restore_terminal`/`close` are
no-ops beyond draining the queue (there is no local tty/termios to restore).

### 4.3 `KeyDecoder` — a resumable byte→event parser

A pure, side-effect-free state machine. `feed(data: bytes)` returns a list of
`Key`/`MouseEvent`; it buffers incomplete trailing sequences across calls.

```python
class KeyDecoder:
    def __init__(self, *, utf8: bool = True) -> None: ...
    def feed(self, data: bytes) -> list[Key | MouseEvent]: ...
    def flush(self) -> list[Key | MouseEvent]:  # resolve a pending lone ESC
```

Parsing rules (reuse existing tables in `wijjit.terminal.input` and
`wijjit.terminal.mouse` wherever possible):

- **Printable / UTF-8**: decode incrementally (`codecs.getincrementaldecoder`)
  so multi-byte runes split across packets are handled. Each rune → a
  `KeyType.CHARACTER` `Key`.
- **C0 control** (`0x00–0x1f`, `0x7f`): map via `SINGLE_CHAR_KEYS` (Enter, Tab,
  Backspace, Ctrl+letter). Ctrl+A..Ctrl+Z = `0x01..0x1a`.
- **CSI** (`ESC [ … final`): match `ESCAPE_SEQUENCES` (arrows, Home/End,
  PgUp/Dn, Delete, F-keys with `~`), including modifier params
  (`ESC [ 1 ; 5 A` = Ctrl+Up) → set modifiers on the `Key`.
- **SS3** (`ESC O …`): application-cursor-mode arrows/Home/End (PuTTY, some
  terminals) → same keys.
- **SGR mouse** (`ESC [ < b ; x ; y M|m`): delegate to
  `wijjit.terminal.mouse.MouseEventParser` (already handles this) → `MouseEvent`.
  Also accept legacy X10/normal mouse (`ESC [ M cb cx cy`) for old clients.
- **Bracketed paste** (`ESC [ 200~ … ESC [ 201~`): collect the payload and emit
  it as character keys (respect `MAX_PASTE_SIZE`), so paste doesn't trigger
  hotkeys.
- **Lone ESC ambiguity**: if the buffer is exactly `ESC` (or `ESC` + an
  incomplete sequence) and no more bytes have arrived, we cannot tell "user hit
  Escape" from "start of a sequence". Resolve with a short timer: the session
  schedules `decoder.flush()` ~30–50 ms after the last byte if the buffer still
  holds a bare ESC, emitting `Keys.ESCAPE`. (SSH batches a full sequence in one
  packet almost always, so this rarely fires.)

The decoder is the crown-jewel unit-test target (§11): a table of
`bytes → [events]` covering every branch, including split-packet cases fed one
byte at a time.

### 4.4 Wiring

`RemoteTerminalBackend.create_input_handler(...)` returns a
`ChannelInputSource`. `_WijjitSSHSession.data_received(data)` calls
`source.feed(data)` (decoder → queue). The prompt_toolkit pipe and the
`input=`/thread path are dropped from the remote backend entirely. (Core's
`InputHandler` keeps its `input=`/`output=` params for the local case — they're
harmless and still used by the local backend.)

---

## 5. Authentication (`auth.py`)

asyncssh drives auth through `SSHServer` callbacks. We wrap them behind an
`AuthPolicy` so deployments choose a strategy without touching server glue.

```python
class AuthPolicy:
    def auth_required(self, username: str) -> bool: ...          # begin_auth
    def password_supported(self) -> bool: ...
    async def verify_password(self, username: str, password: str) -> bool: ...
    def public_key_supported(self) -> bool: ...
    def authorized_keys_for(self, username: str) -> "list[SSHKey] | None": ...
    def kbdint_supported(self) -> bool: ...
    async def verify_kbdint(self, username: str, responses: list[str]) -> bool: ...
```

`_WijjitSSHServer` forwards each asyncssh callback to the policy:
`begin_auth → auth_required`, `validate_password → verify_password`,
`public_key_auth_supported/validate_public_key` via `authorized_keys_for` (or
asyncssh's `authorized_client_keys` on `create_server`), etc.

**Presets shipped:**
- `OpenAuth()` — no auth (any username). Dev only; server logs a loud warning
  at startup when used. This is today's default; it becomes opt-in.
- `AuthorizedKeys(path="~/.ssh/authorized_keys" | mapping)` — public-key auth
  against an OpenSSH `authorized_keys` file (global or per-username mapping).
  Recommended default for real deployments.
- `PasswordAuth(callback)` — `async (username, password) -> bool`. Callback is
  responsible for constant-time comparison / hashing (document `secrets.compare_digest`).
- `ChainAuth(*policies)` — accept if any policy accepts.

The `username` is surfaced to the app via `SSHSession.username` (already wired),
so apps can personalize/authorize per user.

**Default posture:** constructing `WijjitSSH(...)` **without** an `auth=`
argument raises unless `allow_anonymous=True` is passed — fail-closed, so no one
accidentally ships `OpenAuth`.

---

## 6. Terminal capability negotiation (§ in `server.py`/`backend.py`)

- Open the server channel with **`encoding=None`** → `data_received` gets
  `bytes`, backend writes `bytes`. The decoder and frame writer both work in
  bytes; ANSI frames from Wijjit are `str`, encoded once with
  `str.encode("utf-8")` at the boundary.
- `pty_requested(term_type, term_size, term_modes)`: capture `term_type`
  (exposed on `SSHSession`), initial `(cols, rows)`, and the pty modes. Honor
  `term_modes` only insofar as needed; the app draws everything.
- **`line_editor=False`** on `create_server` (already discovered in the
  prototype — asyncssh otherwise echoes and line-buffers input, breaking a TUI).
- Reject non-PTY sessions (`pty_requested` never called → `shell_requested`
  returns an error string) with a friendly message: this server only serves
  interactive TUIs.
- Terminal size on connect and on `terminal_size_changed` → `backend.resize()`;
  the loop republishes it to the task-local size override (already implemented).
- Mouse: `ChannelInputSource.enable_mouse_tracking()` emits the DEC modes;
  Wijjit already decides *whether* to enable based on `ENABLE_MOUSE`.
- Encoding note: assume UTF-8 clients. Optionally read `LANG` from
  `env_requested` later; out of scope for v0.1.

---

## 7. Host keys (`keys.py`)

- `load_host_keys(paths) -> list[SSHKey]` — load one or more host-key files;
  clear error if missing/unreadable.
- `ensure_host_key(path) -> SSHKey` — load, or generate + persist (0600) an
  ed25519 key on first run, logging the fingerprint. Great DX for local/dev and
  containers with a mounted volume.
- Document the standard `ssh-keygen -t ed25519 -f ssh_host_key -N ''` path in
  the README.
- Support key rotation by accepting multiple host keys (asyncssh serves all).

---

## 8. Concurrency, limits, lifecycle (`limits.py`)

A `SessionRegistry` tracks live sessions and enforces bounds; the server
consults it in `session_requested`/`connection_made`.

- **Max concurrent sessions** (`max_sessions`): beyond the cap, refuse new
  sessions with a message and close.
- **Per-IP concurrency + connect rate limit** (`max_per_ip`, token bucket):
  cheap DoS resistance. Source IP from `conn.get_extra_info('peername')`.
- **Login grace timeout**: asyncssh `login_timeout` — drop connections that
  authenticate too slowly.
- **Idle timeout** (`idle_timeout`): no input for N seconds → notify + close.
  Implemented as a per-session timer reset on each `data_received`.
- **Absolute session timeout** (optional): hard cap on session duration.
- **Keepalive** (`keepalive_interval`/`keepalive_count_max`) so dead TCP peers
  are reaped.
- **Backpressure**: if a client stops reading, `chan.write` buffers. Watch
  `chan` drain (asyncssh `SSHWriter`/`drain`), and throttle the app's render
  cadence for that session (or drop frames — the diff renderer self-heals on the
  next full repaint). v0.1: cap the channel write buffer and close on sustained
  overflow.

**Lifecycle (per session):**
```
connection_made → begin_auth → (auth) → pty_requested → shell_requested
  → session_started:  seed size override → build backend+input+app
                      → task = loop.create_task(app.event_loop.run_async())
  → data_received*    → decoder.feed → input queue
  → terminal_size_changed* → backend.resize
  → (app calls quit()  OR  idle/absolute timeout  OR  connection_lost)
  → teardown: app.quit(); task cancel/await; close channel; deregister
```
Teardown must be idempotent and never raise into asyncssh callbacks.

---

## 9. Logging & observability (`logging.py`)

- Reuse Wijjit's `get_logger`. One child logger per session bound with a
  short session id + username + peer IP (contextual `LoggerAdapter`).
- Log lifecycle events at INFO (connect, auth ok/fail, pty, disconnect + reason,
  duration), decode/render errors at ERROR with the session id.
- Never log key material, passwords, or full input streams. Optionally a
  DEBUG-gated, rate-limited input trace for troubleshooting.
- Optional metrics hook (`on_event` callback or counters): active sessions,
  total connections, auth failures, bytes in/out — so a deployment can wire
  Prometheus without us depending on a metrics lib.

---

## 10. Server API surface (`config.py` + `server.py`)

```python
@dataclass
class ServerConfig:
    host: str = ""
    port: int = 8022
    host_keys: list[str] | None = None          # paths; or use ensure_host_key
    auth: AuthPolicy | None = None
    allow_anonymous: bool = False               # must be True to run OpenAuth
    max_sessions: int = 100
    max_per_ip: int = 10
    login_timeout: float = 30.0
    idle_timeout: float | None = 600.0
    session_timeout: float | None = None
    keepalive_interval: float = 30.0
    banner: str | None = None                   # pre-auth SSH banner text

class WijjitSSH:
    def __init__(self, app_factory: Callable[[SSHSession], Wijjit],
                 config: ServerConfig | None = None, **overrides): ...
    async def run_async(self) -> None: ...      # serve until stop()/signal
    def run(self) -> None: ...                   # asyncio.run wrapper
    async def stop(self) -> None: ...            # graceful drain + close
```

`app_factory` stays the SSH analogue of a Flask view. `SSHSession` gains
`peer_ip`, `session_id`, `term_type` (already), `env` (if captured).

**Graceful shutdown:** on SIGINT/SIGTERM (server owns the process here, unlike
the apps), stop accepting, notify sessions, give them a short grace period,
cancel remaining tasks, close the listener.

---

## 11. Testing strategy

- **`test_input_decoder.py`** — the priority. Table-driven `bytes → [events]`
  for: ASCII, Ctrl+letters, all arrows (CSI + SS3), Home/End/PgUp/Dn/Del,
  F1–F12, modified keys (`ESC[1;5A`), SGR + X10 mouse, bracketed paste, split
  UTF-8, and split escape sequences fed one byte at a time. Pure, fast, no I/O.
- **`test_roundtrip.py`** — promote the scratch verification: in-process
  asyncssh client ↔ `WijjitSSH`, generated host key, `known_hosts=None`. Assert
  the initial frame reaches the client, a keystroke mutates state and the next
  frame reflects it, resize reflows, Ctrl+Q disconnects. Cover auth paths
  (pubkey accept/reject, password accept/reject).
- **`test_auth.py`** — each preset in isolation with fake asyncssh callbacks.
- **`test_limits.py`** — max_sessions rejection, per-IP cap, idle timeout fires.
- **Concurrency smoke** — open K simultaneous clients with different sizes;
  assert each renders at its own size (proves task-local size isolation).
- Wire CI mirroring the wijjit repo (ruff/black/mypy-strict + pytest); asyncssh
  is a hard dep of this package so tests always have it.

---

## 12. Deployment notes (README material)

- **Run:** `ensure_host_key("ssh_host_key")`, `WijjitSSH(make_app, auth=...).run()`.
- **systemd:** simple unit, `Restart=on-failure`, a dedicated unprotected user,
  host key under `StateDirectory`.
- **Docker:** copy app + host key volume; expose `8022`; healthcheck via a
  scripted asyncssh client.
- **Scaling:** stateless per-connection apps ⇒ run N instances behind a TCP
  load balancer; no shared state needed unless the app itself has a backend.
- **Security checklist:** real `auth` (never `allow_anonymous` in prod), keep
  `max_sessions`/`max_per_ip`/timeouts set, run as an unprivileged user on a
  high port (or `setcap`/reverse-proxy for 22), rotate host keys, no exec/sftp
  surface (guaranteed by design — we never implement those handlers).

---

## 13. Milestones

- **M1 — Byte parser.** `KeyDecoder` + `ChannelInputSource`; switch backend to
  `encoding=None`; drop the reader thread. Unit tests green. *No behavior
  change visible to apps; removes the thread-per-session cost.*
- **M2 — Auth.** `AuthPolicy` + presets; fail-closed default; `test_auth.py`.
- **M3 — Robust lifecycle.** `keys.py`, `limits.py`, graceful shutdown,
  per-session logging, idle/keepalive.
- **M4 — Config & polish.** `ServerConfig`, second example, README deployment
  section, CI, promote round-trip tests.
- **M5 — Hardening pass.** Backpressure handling, bracketed-paste + mouse edge
  cases, fuzz the decoder, load test (hundreds of concurrent sessions).

Each milestone is independently shippable; M1 alone makes the current prototype
production-shaped on the hot path.

---

## 14. Open questions

- **ESC timeout value** — 30–50 ms is typical; confirm against real latency
  over WAN SSH. Could be adaptive.
- **Wide chars / emoji** — Wijjit's screen buffer treats wide chars as
  single-width (documented limitation). SSH doesn't change that; note it.
- **Windows clients** — PuTTY/Windows Terminal key encodings differ (esp. Alt,
  function keys); the decoder table must be tested against them.
- **Per-session executor** — should the server hand each app a `ThreadPoolExecutor`
  for blocking sync handlers, or document "keep handlers async"? Leaning toward
  a shared, bounded executor with a config knob.
- **Reconnect / session resume** — out of scope, but worth a design note if
  mobile clients (flaky links) become a target.
```
