#!/usr/bin/env python3
import sys
import argparse
import hashlib
import math
import selectors
import tempfile
import os
import re
import glob
import json
import time
import fcntl
import sqlite3
import subprocess
import ssl
import urllib.request
from datetime import datetime, timezone

CACHE_TTL = 60  # seconds

GLOG_RE = re.compile(r"^[IWEF](\d{2})(\d{2})\s+(\d{2}):(\d{2}):(\d{2})\.(\d{6})")

# SQLite step_type constants in Antigravity conversation DB
STEP_USER_INPUT = 14
STEP_PLANNER_RESPONSE = 15
STEP_ERROR_MESSAGE = 17
IGNORED_SYSTEM_STEP_TYPES = (23, 90, 98, 101)
TOOL_STEP_TYPES = (5, 7, 8, 9, 21, 31, 33, 127, 132)

# SQLite status constants
STATUS_PENDING = 1
STATUS_RUNNING = 2
STATUS_DONE = 3
STATUS_CANCELED = 4
STATUS_INVALID = 5
STATUS_RUNNING_ALT = 6
STATUS_ERROR = 7
STATUS_STREAMING = 8
ACTIVE_STATUSES = (STATUS_PENDING, STATUS_RUNNING, STATUS_RUNNING_ALT, STATUS_STREAMING)
TERMINAL_STATUSES = (STATUS_DONE, STATUS_CANCELED, STATUS_INVALID, STATUS_ERROR)

STATUS_PRIORITY = {
    "спит": 0,
    "отдыхает": 1,
    "думает": 2,
    "работает": 3,
    "ошибка": 4,
}


def format_reset_time(iso_str):
    if not iso_str:
        return ""
    try:
        target = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((target - now).total_seconds())
        if diff <= 0:
            return "скоро"
        hours = diff // 3600
        mins = (diff % 3600) // 60
        if hours >= 24:
            days = hours // 24
            rem_h = hours % 24
            return f"{days}д {rem_h}ч"
        elif hours > 0:
            return f"{hours}ч {mins}м"
        return f"{mins}м"
    except Exception:
        return ""


def check_custom_script(script_path):
    if script_path and os.path.exists(script_path) and os.access(script_path, os.X_OK):
        try:
            res = subprocess.run([script_path], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return json.loads(res.stdout.strip())
        except Exception:
            pass
    return None


def process_args(pid, proc_root="/proc"):
    try:
        with open(f"{proc_root}/{pid}/cmdline", "rb") as stream:
            return [os.fsdecode(arg) for arg in stream.read().split(b"\0") if arg]
    except OSError:
        return []


def agy_prompt(args):
    for index, arg in enumerate(args[1:], 1):
        if arg in ("-p", "--print", "--prompt"):
            return args[index + 1] if index + 1 < len(args) else ""
        for flag in ("--print=", "--prompt=", "-p="):
            if arg.startswith(flag):
                return arg[len(flag):]
    return None


def is_agy_session(args):
    if not args or os.path.basename(args[0]) not in ("agy", "antigravity-cli"):
        return False
    prompt = agy_prompt(args)
    if prompt is not None:
        # Only exclude the actual slash command, not prompts mentioning /usage.
        return bool(prompt.strip()) and prompt.strip().split()[0] != "/usage"
    if any(arg in ("--help", "-h", "--version", "-v") for arg in args[1:]):
        return False
    housekeeping = {"models", "mcp", "agent", "agents", "help", "install", "update",
                    "plugin", "plugins", "remote-control", "mic-serve", "changelog"}
    return len(args) < 2 or args[1] not in housekeeping


def get_active_agy_pids(proc_root="/proc"):
    """Track interactive AND headless agent sessions; TTY is not required."""
    pids = []
    for path in glob.glob(f"{proc_root}/[0-9]*/cmdline"):
        try:
            if os.stat(path).st_uid != os.getuid():
                continue
            pid = int(path.split("/")[-2])
            if is_agy_session(process_args(pid, proc_root)):
                pids.append(pid)
        except (OSError, ValueError):
            continue
    return pids


def command_option(args, name):
    for index, arg in enumerate(args):
        if arg == name and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith(name + "="):
            return arg[len(name) + 1:]
    return None


def is_antigravity_server(args):
    if not args:
        return False
    executable = args[0].lower()
    name = os.path.basename(executable)
    return (name == "language-server" or name.startswith("language_server")) and (
        command_option(args, "--app_data_dir") in ("antigravity", "antigravity-ide")
        or command_option(args, "--override_ide_name") == "antigravity"
        or "/extensions/antigravity/" in executable)


def is_antigravity_gui(args):
    return bool(args) and (is_antigravity_server(args) or (
        os.path.basename(args[0]).lower() in (
            "antigravity", "antigravity.appimage", "antigravity-ide")
        and command_option(args, "--type") is None
        and not any(arg in ("--help", "-h", "--version", "-v") for arg in args[1:])))


def antigravity_gui_pids(proc_root="/proc"):
    pids = []
    for path in glob.glob(f"{proc_root}/[0-9]*/cmdline"):
        try:
            if os.stat(path).st_uid != os.getuid():
                continue
            pid = int(path.split("/")[-2])
            if is_antigravity_gui(process_args(pid, proc_root)):
                pids.append(pid)
        except (OSError, ValueError):
            continue
    return pids


def listening_ports(pid, proc_root="/proc"):
    """Only ports owned by this process, never arbitrary localhost services."""
    sockets = set()
    for path in glob.glob(f"{proc_root}/{pid}/fd/*"):
        try:
            target = os.readlink(path)
            if target.startswith("socket:["):
                sockets.add(target[8:-1])
        except OSError:
            continue
    ports = set()
    for protocol in ("tcp", "tcp6"):
        try:
            with open(f"{proc_root}/{pid}/net/{protocol}") as stream:
                for line in stream:
                    fields = line.split()
                    if len(fields) > 9 and fields[3] == "0A" and fields[9] in sockets:
                        address, port = fields[1].split(":")
                        # Servers may bind to all interfaces; requests always use loopback.
                        if address in ("0100007F", "00000000", "0" * 32,
                                       "00000000000000000000000001000000"):
                            ports.add(int(port, 16))
        except (OSError, ValueError):
            continue
    return sorted(ports)


def fetch_antigravity_gui_quota():
    """Read the running GUI's quota summary; never read its cloud credentials."""
    deadline = time.monotonic() + 8
    # No proxies or redirects: the ephemeral CSRF token must stay on loopback.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    for pid in antigravity_gui_pids():
        args = process_args(pid)
        if not is_antigravity_server(args):
            continue
        token = command_option(args, "--csrf_token")
        if not token:
            continue
        for port in listening_ports(pid)[:8]:
            for scheme in ("https", "http"):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                request = urllib.request.Request(
                    f"{scheme}://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary",
                    data=b"{}", headers={"Content-Type": "application/json",
                        "Connect-Protocol-Version": "1", "X-Codeium-Csrf-Token": token})
                try:
                    with opener.open(request, timeout=min(0.75, remaining)) as response:
                        payload = response.read(1048577)
                    if len(payload) > 1048576:
                        continue
                    quota = parse_agy_quota(json.loads(payload))
                    if quota:
                        return quota
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
    return None


def decode_varint(buf, pos):
    val = 0
    shift = 0
    while pos < len(buf):
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7
    return val, pos


def protobuf_fields(buf):
    """Read protobuf fields, tolerating a bounded prefix of a larger payload."""
    pos = 0
    while pos < len(buf):
        tag, pos = decode_varint(buf, pos)
        number, wire = tag >> 3, tag & 7
        if not number:
            return
        if wire == 0:
            value, pos = decode_varint(buf, pos)
        elif wire == 2:
            length, pos = decode_varint(buf, pos)
            value = buf[pos:pos + length]
            pos += length
        elif wire in (1, 5):
            pos += 8 if wire == 1 else 4
            continue
        else:
            return
        yield number, wire, value


def planner_has_tool_calls(payload):
    # CascadeStep.planner_response (20) -> repeated tool_calls (7).
    # A completed planner message proposing tools is not the end of the turn.
    for number, wire, response in protobuf_fields(payload or b""):
        if number == 20 and wire == 2:
            return any(field == 7 and kind == 2 and value
                       for field, kind, value in protobuf_fields(response))
    return False


def parse_meta_timestamps(meta):
    """Extract protobuf timestamps (1=created, 6=started, 7=updated, 8=completed) from steps.metadata."""
    res = {}
    if not meta:
        return res
    i = 0
    n = len(meta)
    while i < n:
        tag, i = decode_varint(meta, i)
        wire = tag & 7
        field_num = tag >> 3
        if wire == 2:
            length, i = decode_varint(meta, i)
            sub = meta[i : i + length]
            i += length
            if field_num in (1, 6, 7, 8) and len(sub) >= 5 and sub[0] == 0x08:
                sec, p2 = decode_varint(sub, 1)
                nanos = 0
                if p2 < len(sub) and sub[p2] == 0x10:
                    nanos, _ = decode_varint(sub, p2 + 1)
                if 1700000000 < sec < 2100000000:
                    res[field_num] = sec + nanos / 1e9
        elif wire == 0:
            _, i = decode_varint(meta, i)
        else:
            break
    return res


def parse_glog_timestamp(line):
    m = GLOG_RE.match(line)
    if not m:
        return None
    month, day, hour, minute, second, micro = map(int, m.groups())
    now = datetime.now()
    try:
        dt = datetime(now.year, month, day, hour, minute, second, micro)
        return dt.timestamp()
    except Exception:
        return None


def get_latest_cancel_ts(log_file, cid=None):
    """Detect if an in-progress response or conversation was cancelled / interrupted by the user."""
    if not log_file or not os.path.exists(log_file):
        return 0
    try:
        with open(log_file, "r", errors="ignore") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 32768))
            lines = f.read().splitlines()[-100:]
        for line in reversed(lines):
            if "Cancelling in-progress response" in line or "Cancelling conversation" in line or "context canceled" in line:
                if cid and cid in line:
                    ts = parse_glog_timestamp(line)
                    if ts:
                        return ts
                elif not cid or not re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", line):
                    ts = parse_glog_timestamp(line)
                    if ts:
                        return ts
    except Exception:
        pass
    return 0


def inspect_pid_fds(pid, proc_root="/proc"):
    """Find CLI/GUI conversations owned by a live process, not stale history."""
    dbs = set()
    log_file = None
    fd_dir = f"{proc_root}/{pid}/fd"
    try:
        for fd_name in os.listdir(fd_dir):
            try:
                target = os.readlink(f"{fd_dir}/{fd_name}")
                if target.endswith(".db") and "/conversations/" in target and os.path.exists(target):
                    dbs.add(target)
                elif "/presence/" in target and target.endswith(".lock"):
                    cid = os.path.basename(target)[:-5]
                    # Presence belongs to its own profile (CLI and GUI can coexist).
                    root = os.path.dirname(os.path.dirname(target))
                    cand = os.path.join(root, "conversations", cid + ".db")
                    if os.path.isfile(cand):
                        dbs.add(cand)
                elif fd_name in ("1", "2") and target.endswith(".log") and os.path.exists(target):
                    log_file = target
            except Exception:
                continue
    except Exception:
        pass
    if not log_file and is_antigravity_server(process_args(pid, proc_root)):
        config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        candidate = os.path.join(config, "Antigravity", "logs", "language_server.log")
        try:
            with open(candidate, errors="replace") as stream:
                header = stream.read(4096)
            # A shared path can contain another instance's log or a previous run.
            if re.search(rf"Starting language server process with pid {pid}\b", header):
                log_file = candidate
        except OSError:
            pass
    return list(dbs), log_file


def check_db_status(db_path, now, log_file=None):
    """Determine conversation status directly from Antigravity SQLite trajectory steps."""
    cid = os.path.basename(db_path)[:-3] if db_path.endswith(".db") else None
    cancel_ts = get_latest_cancel_ts(log_file, cid) if log_file else 0

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.2)
        cur = conn.cursor()
        cur.execute(
            "SELECT idx, step_type, status, metadata, "
            "substr(step_payload, 1, CASE WHEN step_type=15 AND status=3 THEN 65536 ELSE 1024 END) "
            "FROM steps WHERE step_type NOT IN (23, 90, 98, 101) "
            "ORDER BY idx DESC LIMIT 8"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return None

    if not rows:
        return None

    top_idx, top_type, top_status, top_meta, top_payload = rows[0]
    top_ts_map = parse_meta_timestamps(top_meta)
    top_ts = max(top_ts_map.values()) if top_ts_map else 0
    top_age = (now - top_ts) if top_ts else 999999.0

    # 1. User interrupt / cancellation detected in CLI logs
    if cancel_ts > 0 and (cancel_ts >= top_ts or (now - cancel_ts) <= 2.5):
        return "отдыхает"

    # 2. Step is explicitly marked as canceled or invalid
    if top_status in (STATUS_CANCELED, STATUS_INVALID):
        return "отдыхает"

    # 3. Error check
    if (top_status == STATUS_ERROR or top_type == STEP_ERROR_MESSAGE) and 0 <= top_age <= 12.0:
        return "ошибка"

    # 4. If the turn finished with a completed planner response -> resting / idle
    if top_type == STEP_PLANNER_RESPONSE and top_status == STATUS_DONE:
        if planner_has_tool_calls(top_payload):
            return "работает"
        # Avoid a one-frame idle flash while the next tool step is being appended.
        return "думает" if 0 <= top_age <= 2.0 else "отдыхает"

    # 5. Planner response actively streaming / thinking
    if top_type == STEP_PLANNER_RESPONSE and top_status not in TERMINAL_STATUSES:
        return "думает"

    # 6. User input just submitted -> thinking (starts in <50ms)
    if top_type == STEP_USER_INPUT:
        # The process still owns this DB: long first-token/network waits are active.
        return "думает"

    # 7. Top step is a tool
    if top_type in TOOL_STEP_TYPES:
        if top_status not in TERMINAL_STATUSES:
            if top_payload and b"ask_question" in top_payload:
                return "отдыхает"
            return "работает"
        if top_status == STATUS_DONE:
            if top_payload and b"ask_question" in top_payload:
                return "отдыхает"
            if 0 <= top_age <= 2.5:
                return "работает"
            return "думает"

    if top_type not in (STEP_USER_INPUT, STEP_PLANNER_RESPONSE, STEP_ERROR_MESSAGE):
        if top_status not in TERMINAL_STATUSES:
            return "отдыхает" if top_payload and b"ask_question" in top_payload else "работает"
        if top_status == STATUS_DONE:
            return "думает"

    # 8. Check recent rows for any active concurrent tool
    for idx, st_type, status, meta, payload in rows[1:]:
        if st_type in TOOL_STEP_TYPES and status in ACTIVE_STATUSES:
            ts_map = parse_meta_timestamps(meta)
            latest_ts = max(ts_map.values()) if ts_map else 0
            age = (now - latest_ts) if latest_ts else 999999.0
            if latest_ts:
                if payload and b"ask_question" in payload:
                    return "отдыхает"
                return "работает"

    return "отдыхает"


def check_single_pid_status(pid, now):
    dbs, log_file = inspect_pid_fds(pid)
    if log_file:
        try:
            with open(log_file, "rb") as stream:
                stream.seek(0, os.SEEK_END)
                stream.seek(max(0, stream.tell() - 8192))
                log_tail = stream.read()
            if b"CLI store manager shutting down" in log_tail:
                return "отдыхает"
        except OSError:
            pass
    statuses = [check_db_status(path, now, log_file) for path in dbs]
    statuses = [status for status in statuses if status is not None]
    if statuses:
        return max(statuses, key=lambda status: STATUS_PRIORITY[status])
    # A single-shot prompt is already work while the DB is being created.
    # A streaming/interactive session with no submitted prompt can simply be idle.
    return "думает" if agy_prompt(process_args(pid)) else "отдыхает"


def check_agy_status(active_pids):
    if not active_pids:
        return "спит"

    now = time.time()
    best_status = "отдыхает"
    for pid in active_pids:
        st = check_single_pid_status(pid, now)
        if STATUS_PRIORITY.get(st, 0) > STATUS_PRIORITY.get(best_status, 0):
            best_status = st
    return best_status


def fetch_agy_quota():
    """Fetch Gemini quota from the official Antigravity usage command."""
    log_dir = os.path.expanduser("~/.gemini/antigravity-cli/log")
    before_logs = set(glob.glob(f"{log_dir}/cli-*.log")) if os.path.isdir(log_dir) else set()

    try:
        res = subprocess.run(
            ["agy", "-p", "/usage", "--output-format", "json", "--print-timeout", "20s"],
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res.returncode == 0:
            data = json.loads(res.stdout.strip())
            return parse_agy_quota(data)
    except Exception:
        pass
    finally:
        # Clean up one-shot log files created by `agy -p /usage` so ~/.gemini/antigravity-cli/log doesn't bloat
        if os.path.isdir(log_dir):
            after_logs = set(glob.glob(f"{log_dir}/cli-*.log"))
            for new_log in after_logs - before_logs:
                try:
                    with open(new_log, "r", errors="ignore") as lf:
                        head = lf.read(4096)
                    if "running slash command /usage" in head or "You are not logged into Antigravity" in head:
                        os.remove(new_log)
                except Exception:
                    pass
    return None


def fetch_antigravity_quota():
    # Prefer the open app, including GUI-only installations / GUI-only login.
    return fetch_antigravity_gui_quota() or fetch_agy_quota()


def unknown_quota():
    return {"bar1_label": "5 часов", "bar2_label": "неделя",
            "bar1_percent": -1, "bar2_percent": -1,
            "bar1_exact": -1, "bar2_exact": -1}


def set_bucket(quota, index, remaining, reset_at=None):
    remaining = float(remaining)
    if not math.isfinite(remaining):
        raise ValueError("Invalid quota percentage")
    exact = round(max(0, min(100, remaining)), 1)
    quota[f"bar{index}_percent"] = int(round(exact))
    quota[f"bar{index}_exact"] = exact
    if reset_at:
        if isinstance(reset_at, str):
            reset_at = datetime.fromisoformat(reset_at.replace("Z", "+00:00")).timestamp()
        quota[f"bar{index}_resets_at"] = float(reset_at)


def parse_agy_quota(data):
    groups = data.get("command", {}).get("data", {}).get("groups", [])
    if not groups:
        groups = data.get("response", data).get("groups", [])
    group = next((g for g in groups if
                  (g.get("name") or g.get("displayName", "")).strip().lower()
                  in ("gemini models", "gemini")), None)
    if not group:
        return None
    quota = unknown_quota()
    for bucket in group.get("buckets", []):
        if bucket.get("enabled") is False:
            continue
        index = None
        bucket_id = bucket.get("id") or bucket.get("bucketId")
        if bucket_id == "gemini-5h" or bucket.get("window") == "5h":
            index = 1
        elif bucket_id == "gemini-weekly" or bucket.get("window") == "weekly":
            index = 2
        fraction = bucket.get("remaining_fraction", bucket.get("remainingFraction"))
        if fraction is None:
            fraction = (bucket.get("remaining") or {}).get("remainingFraction")
        if index and fraction is not None:
            set_bucket(quota, index, float(fraction) * 100,
                       bucket.get("reset_time") or bucket.get("resetTime"))
    return quota if any(quota[f"bar{i}_percent"] >= 0 for i in (1, 2)) else None


def parse_codex_quota(result):
    # Explicitly select the Codex bucket, never a separately metered model.
    limits = (result.get("rateLimitsByLimitId") or {}).get("codex") or result.get("rateLimits")
    if not limits or limits.get("limitId") not in (None, "codex"):
        return None
    quota = unknown_quota()
    for index, name in ((1, "primary"), (2, "secondary")):
        bucket = limits.get(name)
        if not bucket or bucket.get("usedPercent") is None:
            continue
        set_bucket(quota, index, 100 - float(bucket["usedPercent"]), bucket.get("resetsAt"))
        minutes = bucket.get("windowDurationMins")
        if minutes:
            if minutes == 10080:
                label = "неделя"
            elif minutes % 1440 == 0:
                label = f"{minutes // 1440} дн."
            elif minutes % 60 == 0:
                hours = minutes // 60
                label = "5 часов" if hours == 5 else f"{hours} ч."
            else:
                label = f"{minutes} мин."
            quota[f"bar{index}_label"] = label
    return quota if any(quota[f"bar{i}_percent"] >= 0 for i in (1, 2)) else None


def fetch_codex_quota():
    """Read-only official app-server API; no model turn and no auth file parsing."""
    proc = subprocess.Popen(["codex", "app-server"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    pending = bytearray()
    deadline = time.monotonic() + 20

    def send(message):
        proc.stdin.write((json.dumps(message) + "\n").encode())
        proc.stdin.flush()

    def receive(request_id):
        while True:
            while b"\n" in pending:
                line, _, rest = pending.partition(b"\n")
                pending[:] = rest
                message = json.loads(line)
                if message.get("id") == request_id:
                    if "error" in message:
                        raise RuntimeError(message["error"].get("message", "Codex API error"))
                    return message["result"]
            timeout = deadline - time.monotonic()
            if timeout <= 0 or not selector.select(timeout):
                raise TimeoutError("Codex quota request timed out")
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Codex app-server closed")
            pending.extend(chunk)

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "plasma_agent_status", "version": "1.2.0"}}})
        receive(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "account/rateLimits/read", "params": {}})
        return parse_codex_quota(receive(2))
    finally:
        selector.close()
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def codex_home():
    return os.path.abspath(os.path.expanduser(os.environ.get("CODEX_HOME", "~/.codex")))


def tail_events(path, size=131072):
    """Bound reads even for very long sessions; tolerate partially written JSONL."""
    try:
        with open(path, "rb") as stream:
            stream.seek(0, os.SEEK_END)
            offset = max(0, stream.tell() - size)
            stream.seek(offset)
            if offset:
                stream.readline()
            lines = stream.read().splitlines()
        for line in lines:
            try:
                yield json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
    except OSError:
        return


def codex_session_status(events, now):
    status = "отдыхает"
    finished = False
    pending_tools = set()
    latest_ts = 0
    for event in events:
        payload = event.get("payload", {})
        try:
            latest_ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            continue
        kind = payload.get("type")
        if event.get("type") == "event_msg":
            if kind in ("task_complete", "task_completed", "turn_aborted", "turn_complete"):
                status = "отдыхает"
                finished = True
                pending_tools.clear()
            elif kind in ("task_started", "turn_started"):
                status = "думает"
                finished = False
                pending_tools.clear()
            elif kind == "error":
                status = "ошибка"
            elif kind in ("agent_reasoning", "agent_message", "token_count") and not finished:
                status = "думает"
            elif kind == "item_completed" and not finished:
                item_type = payload.get("item", {}).get("type", "")
                if item_type in ("commandExecution", "command_execution", "mcpToolCall", "mcp_tool_call", "fileChange", "file_change", "webSearch", "web_search"):
                    status = "работает"
        elif event.get("type") == "response_item":
            if kind in ("function_call", "custom_tool_call"):
                pending_tools.add(payload.get("call_id"))
                status = "работает"
            elif kind in ("function_call_output", "custom_tool_call_output"):
                pending_tools.discard(payload.get("call_id"))
                status = "работает" if pending_tools else "думает"
            elif kind == "reasoning":
                status = "думает"
            elif kind == "message" and payload.get("role") == "assistant":
                finished = payload.get("phase") == "final_answer"
                status = "отдыхает" if finished else "думает"
                if finished:
                    pending_tools.clear()
    # Unfinished rollouts can survive a crash. Do not show them as busy forever.
    if now - latest_ts > 180:
        return "отдыхает"
    return "работает" if pending_tools else status


def is_quota_worker_child(pid, proc_root="/proc"):
    """Exclude only our quota probe, not the desktop app's persistent server."""
    for _ in range(32):
        args = process_args(pid, proc_root)
        if "--refresh-only" in args and any(
                os.path.basename(arg) == "status_provider.py" for arg in args):
            return True
        try:
            with open(f"{proc_root}/{pid}/stat") as stream:
                parent = int(stream.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if parent <= 1 or parent == pid:
            break
        pid = parent
    return False


def codex_running(proc_root="/proc"):
    for path in glob.glob(f"{proc_root}/[0-9]*/cmdline"):
        try:
            if os.stat(path).st_uid != os.getuid():
                continue
            pid = int(path.split("/")[-2])
            args = process_args(pid, proc_root)
            if not args or os.path.basename(args[0]).lower() not in ("codex", "codex-desktop"):
                continue
            if command_option(args, "--type") is not None or any(
                    arg in ("login", "logout", "--help", "-h", "--version", "-V") for arg in args[1:]):
                continue
            if not is_quota_worker_child(pid, proc_root):
                return True
        except (OSError, ValueError):
            continue
    return False


def check_codex_status():
    now = time.time()
    best = "спит"
    running = codex_running()
    files = glob.glob(os.path.join(codex_home(), "sessions", "*", "*", "*", "*.jsonl"))
    recent = []
    for path in files:
        try:
            modified = os.path.getmtime(path)
            if 0 <= now - modified <= 180:
                recent.append((modified, path))
        except OSError:
            continue
    for _, path in sorted(recent, reverse=True)[:12]:
        status = codex_session_status(tail_events(path), now)
        if STATUS_PRIORITY[status] > STATUS_PRIORITY[best]:
            best = status
    return "отдыхает" if running and best == "спит" else best


def storage_paths(provider, durable=True):
    variable, fallback = ("XDG_STATE_HOME", "~/.local/state") if durable else ("XDG_CACHE_HOME", "~/.cache")
    directory = os.environ.get(variable) or os.path.expanduser(fallback)
    root = os.path.join(directory, "plasma-agent-status")
    os.makedirs(root, mode=0o700, exist_ok=True)
    identity = codex_home() if provider == "codex" else os.path.expanduser("~/.gemini/antigravity-cli")
    key = hashlib.sha256(identity.encode()).hexdigest()[:12]
    base = os.path.join(root, f"{provider}-{key}")
    return base + ".json", base + ".lock"


def cache_paths(provider):
    # Keep the helper name for compatibility; snapshots are now durable state.
    return storage_paths(provider)


def load_quota(provider):
    state_file, _ = cache_paths(provider)
    saved = read_cache(state_file)
    if saved:
        return saved
    # Read-only migration: do not race another widget's in-flight state write.
    legacy_file, _ = storage_paths(provider, durable=False)
    return read_cache(legacy_file) or {}


def read_cache(path):
    try:
        with open(path) as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_cache(path, data):
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".quota-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(os.path.dirname(path), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def refresh_quota(provider):
    cache_file, lock_file = cache_paths(provider)
    with open(lock_file, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        cached = load_quota(provider)
        now = time.time()
        if 0 <= now - cached.get("attempted_at", 0) < CACHE_TTL:
            # Commit migrated snapshots while holding the provider lock.
            if not os.path.exists(cache_file):
                write_cache(cache_file, cached)
            return
        # Persist the attempt before networking to avoid retry storms after failures.
        cached["attempted_at"] = now
        write_cache(cache_file, cached)
        try:
            quota = fetch_codex_quota() if provider == "codex" else fetch_antigravity_quota()
            if not quota:
                raise RuntimeError("Лимиты недоступны: откройте Antigravity или проверьте вход в CLI и тип подписки"
                                   if provider == "antigravity" else
                                   "Лимиты недоступны: проверьте вход в Codex и тип подписки")
            updated_at = time.time()
            merged = dict(cached)
            # A partial response must not erase the other window's last known quota.
            for index in (1, 2):
                if quota.get(f"bar{index}_percent", -1) < 0:
                    continue
                prefix = f"bar{index}_"
                for key in list(merged):
                    if key.startswith(prefix):
                        del merged[key]
                merged.update({key: value for key, value in quota.items() if key.startswith(prefix)})
                merged[f"bar{index}_updated_at"] = updated_at
            merged.update(timestamp=updated_at, attempted_at=now, quota_error="")
            write_cache(cache_file, merged)
        except Exception as error:
            cached["quota_error"] = str(error)
            write_cache(cache_file, cached)


def get_usage(provider):
    cache_file, _ = cache_paths(provider)
    cached = load_quota(provider)
    now = time.time()
    # Fetch even while the agent sleeps: installing the widget should show quotas.
    if not os.path.exists(cache_file) or not 0 <= now - cached.get("attempted_at", 0) < CACHE_TTL:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--provider", provider, "--refresh-only"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    quota = unknown_quota()
    quota.update(cached)
    quota["quota_stale"] = any(
        quota.get(f"bar{index}_percent", -1) >= 0
        and now - quota.get(f"bar{index}_updated_at", quota.get("timestamp", 0)) > CACHE_TTL * 3
        for index in (1, 2))
    for index in (1, 2):
        reset_at = quota.get(f"bar{index}_resets_at")
        quota[f"bar{index}_reset"] = format_reset_time(datetime.fromtimestamp(reset_at, timezone.utc).isoformat()) if reset_at else ""
    return quota


def main():
    parser = argparse.ArgumentParser(description="Plasma AI Status: Antigravity / Codex status provider")
    parser.add_argument("custom_script", nargs="?", default="")
    parser.add_argument("--provider", choices=("antigravity", "codex"), default="antigravity")
    parser.add_argument("--refresh-only", action="store_true")
    args = parser.parse_args()
    if args.refresh_only:
        refresh_quota(args.provider)
        return
    custom = check_custom_script(args.custom_script)
    if custom:
        print(json.dumps(custom, ensure_ascii=False))
        return
    if args.provider == "codex":
        status = check_codex_status()
    else:
        status = check_agy_status(get_active_agy_pids() + antigravity_gui_pids())
    result = get_usage(args.provider)
    result.update(status=status, provider=args.provider)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
