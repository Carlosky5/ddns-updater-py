import base64
import ctypes
import getpass
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "ddns.json")
STATE_PATH = os.path.join(SCRIPT_DIR, "ddns_state.json")
IP_URLS = ("https://api.ipify.org", "https://ifconfig.me/ip")
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
USAGE = "usage: python ddns.py [--live] [--once] [--force] [--show] [--interval N]"

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


class DpapiError(Exception):
    pass


def _load_win32crypt():
    try:
        return ctypes.WinDLL("win32crypt", use_last_error=True)
    except Exception:
        return None


def _local_free(ptr):
    try:
        ctypes.WinDLL("kernel32").LocalFree(ptr)
    except Exception:
        pass


def out(msg):
    print(msg, flush=True)


def stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def is_admin():
    try:
        return bool(ctypes.WinDLL("shell32").IsUserAdmin())
    except Exception:
        pass
    try:
        res = subprocess.run(["net", "session"], capture_output=True, text=True, timeout=15)
        return res.returncode == 0
    except Exception:
        return False


def dpapi_protect(data):
    crypt = _load_win32crypt()
    if crypt is None:
        raise DpapiError("DPAPI is unavailable on this system")
    buf = ctypes.create_string_buffer(data, len(data))
    src = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    got = DATA_BLOB()
    ok = crypt.CryptProtectData(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(got))
    if not ok:
        raise DpapiError("CryptProtectData failed (error %d)" % ctypes.get_last_error())
    try:
        return ctypes.string_at(got.pbData, got.cbData)
    finally:
        _local_free(got.pbData)


def dpapi_unprotect(blob):
    crypt = _load_win32crypt()
    if crypt is None:
        raise DpapiError("DPAPI is unavailable on this system")
    buf = ctypes.create_string_buffer(blob, len(blob))
    src = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    got = DATA_BLOB()
    ok = crypt.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(got))
    if not ok:
        raise DpapiError("CryptUnprotectData failed (error %d)" % ctypes.get_last_error())
    try:
        return ctypes.string_at(got.pbData, got.cbData)
    finally:
        _local_free(got.pbData)


def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def apply_acl(path):
    try:
        res = subprocess.run(
            ["icacls", path, "/inheritance:r", "/grant", "S-1-5-32-570:F", "/grant", "S-1-5-18:F"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:
        out("WARNING: could not run icacls to lock down %s" % path)
        return
    if res.returncode == 0:
        out("ACL applied: Administrators + SYSTEM only.")
    else:
        out("WARNING: icacls failed (code %d); config ACL may be wider than planned" % res.returncode)


def save_config(cfg):
    store = {"v": 2, "domain": cfg["domain"], "ddns_pwd": cfg["ddns_pwd"],
             "interval": int(cfg.get("interval", 300)), "ttl": int(cfg.get("ttl", 600))}
    atomic_write_json(CONFIG_PATH, store)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        store = json.load(fh)
    if not isinstance(store, dict):
        raise DpapiError("config payload invalid")
    if store.get("v") != 2:
        if store.get("v") == 1:
            raise DpapiError("config v1 (DPAPI) found but DPAPI is disabled in this build — delete ddns.json and re-run setup")
        raise DpapiError("config version mismatch")
    cfg = {"domain": store.get("domain"), "ddns_pwd": store.get("ddns_pwd"),
           "interval": store.get("interval", 300), "ttl": store.get("ttl", 600)}
    if not isinstance(cfg["domain"], str) or not cfg["domain"] or not isinstance(cfg["ddns_pwd"], str) or not cfg["ddns_pwd"]:
        raise DpapiError("config payload invalid")
    return cfg


def looks_like_domain(s):
    if not s or len(s) > 253 or s.startswith(".") or s.endswith(".") or ".." in s:
        return False
    labels = s.split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63 or label[0] == "-" or label[-1] == "-":
            return False
        for ch in label:
            if not (ch.isalnum() or ch == "-"):
                return False
    return True


def prompt_positive_int(prompt, default):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        try:
            val = int(raw)
        except ValueError:
            out("Enter a whole number of seconds.")
            continue
        if val <= 0:
            out("Must be greater than 0.")
            continue
        return val


def setup_interactive():
    out("First run - configure the Dynadot DDNS update.")
    while True:
        try:
            domain = input("Domain to update (e.g. example.com): ").strip()
        except EOFError:
            out("Interactive setup needs a real console. Re-run ddns.py in a terminal.")
            return None
        if looks_like_domain(domain):
            break
        out("That does not look like a domain. Try again.")
    try:
        pwd = getpass.getpass("DDNS password: ")
        interval = prompt_positive_int("Poll interval seconds [300]: ", 300)
        ttl = prompt_positive_int("TTL seconds [600]: ", 600)
    except EOFError:
        out("Interactive setup needs a real console. Re-run ddns.py in a terminal.")
        return None
    cfg = {"domain": domain, "ddns_pwd": pwd, "interval": interval, "ttl": ttl}
    save_config(cfg)
    out("Config saved to %s" % CONFIG_PATH)
    return cfg


def show_config():
    if not os.path.exists(CONFIG_PATH):
        out("No config found. Run ddns.py (no flags) once to set it up.")
        return 1
    try:
        cfg = load_config()
    except PermissionError:
        out("This tool must run elevated. Double-click start_ddns.bat or run from an admin terminal.")
        return 1
    except DpapiError:
        out("Config was created on another machine/user. Delete ddns.json and re-run setup.")
        return 1
    except (OSError, ValueError, TypeError, AttributeError):
        out("Config file is corrupt. Delete ddns.json and re-run setup.")
        return 1
    out("domain:   %s" % cfg["domain"])
    out("ddns_pwd: ***")
    out("storage:  PLAINTEXT JSON (TEST MODE — encryption disabled)")
    out("interval: %ss" % cfg.get("interval", 300))
    out("ttl:      %ss" % cfg.get("ttl", 600))
    out("file:     %s" % CONFIG_PATH)
    return 0


def is_ipv4(s):
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p or len(p) > 3 or any(c not in "0123456789" for c in p):
            return False
        if int(p) > 255:
            return False
    return True


def fetch_public_ip():
    for url in IP_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/plain"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read(256).decode("utf-8", "replace").strip()
            if is_ipv4(text):
                return text
        except Exception:
            continue
    return None


def read_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        ip = data.get("last_ip")
        return ip if isinstance(ip, str) else None
    except Exception:
        return None


def write_state(ip):
    atomic_write_json(STATE_PATH, {"last_ip": ip, "updated": stamp()})


def dynadot_set_ddns(domain, ip, pwd, ttl):
    qs = urllib.parse.urlencode({"domain": domain, "subDomain": "", "type": "A", "ip": ip, "pwd": pwd, "ttl": ttl, "containRoot": "true"})
    url = "https://www.dynadot.com/set_ddns?" + qs
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER_UA,
        "Referer": "https://www.dynadot.com/",
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read(65536).decode("utf-8", "replace")
    try:
        data = json.loads(body)
    except ValueError:
        data = {}
    code = data.get("error_code")
    if isinstance(code, str):
        try:
            code = int(code)
        except ValueError:
            pass
    detail = " ".join(str(x) for x in (data.get("content") or [data.get("error_desc") or ("" if data.get("status") == "success" else "")]))
    raw = body[:300]
    if pwd and pwd in raw:
        raw = raw.replace(pwd, "***")
    status = str(data.get("status", "")).lower()
    if status == "success":
        ok = True
    elif status == "error":
        ok = False
    else:
        ok = code == -1
    return ok, detail, raw


def console_title(text):
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(text)
    except Exception:
        pass


def run_cycle(cfg, opts):
    mode = "LIVE" if opts["live"] else "DRY-RUN"
    ts = stamp()
    ip = fetch_public_ip()
    if ip is None:
        out("[%s] skipped (no IP fetched)" % ts)
        return
    console_title("DDNS %s \u2014 %s \u2192 %s" % (mode, cfg["domain"], ip))
    if not opts["force"] and read_state() == ip:
        out("[%s] IP unchanged: %s" % (ts, ip))
        return
    if not opts["live"]:
        masked = ("https://www.dynadot.com/set_ddns?domain=%s&subDomain=&type=A&ip=%s&pwd=***&ttl=%s&containRoot=true"
                  % (cfg["domain"], ip, cfg["ttl"]))
        out("[%s] DRY-RUN: would call %s" % (ts, masked))
        if opts["force"]:
            write_state(ip)
        return
    ok, detail, raw = dynadot_set_ddns(cfg["domain"], ip, cfg["ddns_pwd"], cfg["ttl"])
    if ok:
        write_state(ip)
        out("[%s] LIVE: success - %s updated to %s" % (ts, cfg["domain"], ip))
        out("[%s] dynadot response: %s" % (ts, raw))
    else:
        out("[%s] LIVE: Dynadot rejected the update: %s (state kept, will retry)" % (ts, detail or "unknown error"))
        out("[%s] dynadot response: %s" % (ts, raw))


def step(cfg, opts):
    pwd = cfg.get("ddns_pwd") or ""
    try:
        run_cycle(cfg, opts)
    except Exception as exc:
        msg = str(exc)
        if pwd and pwd in msg:
            msg = msg.replace(pwd, "***")
        out("[%s] cycle error: %s - continuing" % (stamp(), msg))


def runner(cfg, opts, interval):
    mode = "LIVE" if opts["live"] else "DRY-RUN"
    out("=" * 52)
    out("TEST MODE: config stored in PLAINTEXT (encryption disabled)")
    out("DDNS updater (Dynadot) - mode: %s" % mode)
    out("domain:   %s" % cfg["domain"])
    out("interval: %ss   ttl: %ss" % (interval, cfg["ttl"]))
    out("started:  %s" % stamp())
    out("=" * 52)
    if opts["once"]:
        step(cfg, opts)
        return 0
    while True:
        step(cfg, opts)
        time.sleep(interval)


def parse_flags(argv):
    opts = {"live": False, "once": False, "force": False, "show": False, "interval": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--live":
            opts["live"] = True
        elif a == "--once":
            opts["once"] = True
        elif a == "--force":
            opts["force"] = True
        elif a == "--show":
            opts["show"] = True
        elif a == "--interval":
            i += 1
            if i >= len(argv):
                out(USAGE)
                sys.exit(2)
            try:
                val = int(argv[i])
            except ValueError:
                out(USAGE)
                sys.exit(2)
            if val <= 0:
                out(USAGE)
                sys.exit(2)
            opts["interval"] = val
        else:
            out(USAGE)
            sys.exit(2)
        i += 1
    return opts


def main(argv):
    opts = parse_flags(argv)
    if opts["show"]:
        return show_config()
    if os.path.exists(CONFIG_PATH):
        try:
            cfg = load_config()
        except PermissionError:
            out("Cannot read ddns.json (access denied). Check file ACLs.")
            return 1
        except DpapiError as exc:
            out(exc.args[0] if exc.args else str(exc))
            out("Delete ddns.json and re-run setup.")
            return 1
        except ValueError:
            out("Config file is corrupt. Delete ddns.json and re-run setup.")
            return 1
    else:
        cfg = setup_interactive()
        if cfg is None:
            return 1
    interval = opts["interval"] if opts["interval"] is not None else int(cfg.get("interval", 300))
    return runner(cfg, opts, interval)


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except KeyboardInterrupt:
        out("Stopped.")
        rc = 0
    except Exception as exc:
        out("Unexpected error: %s" % exc)
        rc = 1
    sys.exit(rc)
