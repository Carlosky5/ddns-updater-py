# ddns-updater-py

A small, zero-dependency Python tool for Windows that keeps a domain's A record pointed at your
machine's current public IPv4 address. It watches your public IP (via `api.ipify.org`, with an
`ifconfig.me` fallback) and updates the DNS record whenever it changes.

## Supported registrars
- **Dynadot** — the domain must be at Dynadot, on Dynadot's nameservers, with a DDNS password
  enabled in the Dynadot panel (Domains → manage → domain → DDNS settings).

## Requirements
- Windows
- Python 3 (standard library only — nothing to install)
- A domain on a supported registrar with DDNS enabled

## Quick start
1. Run setup (asks for domain, DDNS password, optional poll interval and TTL):
   ```
   python ddns.py --once --force
   ```
   On the first run it prompts for your settings and saves them to `ddns.json` in the same folder.
2. Check it looks right:
   ```
   python ddns.py --show
   ```
3. Run it for real (single test cycle that sends the update):
   ```
   python ddns.py --live --once --force
   ```
4. Confirm the record actually flipped:
   ```
   nslookup yourdomain.com
   ```
   (If your local resolver caches, check a public one: `nslookup yourdomain.com 1.1.1.1`.)

## Run it continuously
Double-click `start_ddns.bat`. It opens a console window and loops, updating the record whenever
your public IP changes and printing a timestamped line each cycle. The window stays open by design —
close it (or press Ctrl+C) to stop.

You can also run it manually:
```
python ddns.py
```

## Flags
| Flag | Meaning |
|---|---|
| `--live` | Send real update requests to the registrar (without it, the tool only logs what it would do) |
| `--once` | Run a single cycle and exit |
| `--force` | Act as if the IP changed this cycle, even if it didn't |
| `--show` | Print the saved config (password masked) and exit |
| `--interval N` | Override the poll interval in seconds for this run |

## Configuration
Settings are stored in `ddns.json` next to the script:

```json
{"v": 2, "domain": "example.com", "ddns_pwd": "...", "interval": 300, "ttl": 600}
```

- The DDNS password is a registrar-specific password for DDNS updates, not your account password.
- This file is **plaintext** on purpose (see below), so keep it out of version control — the
  `.gitignore` in this repo already excludes it.
- `ddns_state.json` tracks the last IP that was successfully pushed so unchanged IPs don't
  re-trigger updates; it is also git-ignored.

## Notes
- **Plaintext config.** On some Windows systems DPAPI (`win32crypt.dll`) is unavailable, so this
  build stores the config unencrypted. Anyone who can read `ddns.json` can read the DDNS
  password. If that's a concern, restrict file permissions or regenerate the registrar password
  after copying the tool elsewhere.
- **Dynadot + Email Settings.** If the domain has active Email Settings (parking/redirect
  services) in the Dynadot panel, update requests are rejected until they are removed — the tool
  prints Dynadot's raw error response, which explains it.
- **Dry-run is the built-in default.** Without `--live`, no request is ever sent to the
  registrar; the tool logs the (password-masked) URL it would call. `start_ddns.bat` passes
  `--live` automatically.

## Files
| File | Purpose |
|---|---|
| `ddns.py` | The entire tool: setup, IP detection, registrar update, flags |
| `start_ddns.bat` | Double-click launcher (runs the live loop in a visible window) |
| `README.md` | This file |
