# Running on an Android phone

Run the same updater on an old Android phone as a second (or standby) DDNS node. It updates the
same Dynadot record as the PC, which is safe: both report the same public IP (same ISP), so
whichever notices a change first just sets the same value.

## What you need
- An Android phone.
- **Termux** — install it from the **Google Play Store or F-Droid** (either source is fine and up
  to date).
- The phone **plugged into power**. A 24/7 loop drains a battery, and a warm old battery left
  unattended is a fire risk — keep it powered.

## 1. Install Python inside Termux
Open Termux and run:
```
pkg install python
```

That's it for setup. You do **not** need `pkg update` first.

## 2. Get the tool onto the phone
The phone needs two files: `ddns.py` and `ddns.json` (the `ddns.json` holds its config, including
the DDNS password). Any of these works:

- **Copy a folder** (e.g. `DDNS-PY/`) onto the phone with a USB cable or a file transfer app,
  landing it in the shared storage, e.g. `/sdcard/DDNS-PY/`.
- **`adb push`** from a PC: `adb push ddns.py ddns.json /sdcard/DDNS-PY/`.
- **`git clone`** the repo straight into Termux (needs a GitHub access token because the repo is
  private).

## 3. Let Termux see the phone's files
On Android, Termux cannot read `/sdcard` until storage access is turned on. Run:
```
termux-setup-storage
```
When the permission prompt appears, **enable the toggle / tap Allow** for external storage. (If
you do this later, you may need to re-open Termux.)

## 4. Navigate and set up a working folder (basics)
Termux starts in your home directory (`~`). If you've never used a terminal on a phone:

| Command | What it does |
|---|---|
| `pwd` | Show the folder you're currently in |
| `ls` | List files in the current folder |
| `ls /sdcard` | List the phone's shared storage |
| `cd /sdcard/DDNS-PY` | Move into that folder |
| `cd ~` | Move back to home |
| `mkdir ~/ddns` | Create a new folder called `ddns` in your home |
| `~` | Short for "your home directory" |

Copy the two files into a home folder (you can then run from `~/ddns` without depending on
`/sdcard`):
```
mkdir -p ~/ddns
cp /sdcard/DDNS-PY/ddns.py /sdcard/DDNS-PY/ddns.json ~/ddns/
cd ~/ddns
ls                      # you should see ddns.py and ddns.json
```

## 5. Test it
```
python ddns.py --live --once --force
```
Expect `LIVE: success` and a Dynadot response of `{"status":"success"}`. If you'd rather not send
an update immediately, run the dry-run first: `python ddns.py --once --force`.

## 6. Run it continuously
```
termux-wake-lock
python ddns.py --live
```
`termux-wake-lock` stops Android from suspending Python when the screen turns off. Then leave the
phone plugged in and Termux left open (you can lock the screen).

## Optional: auto-start on phone boot (Termux:Boot)
If the phone reboots, the loop stops until you start it again. To auto-start, use the **Termux:Boot**
add-on app (same author as Termux; install it from the Play Store or F-Droid, then open it once so
it grabs its required permission).

Termux:Boot runs every `.sh` file inside `~/.termux/boot/` each time the phone powers on. Create one:
```
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-ddns.sh <<'EOF'
termux-wake-lock
python ~/ddns/ddns.py --live
EOF
chmod +x ~/.termux/boot/start-ddns.sh
```
Make sure the path (`~/ddns/ddns.py`) matches wherever you put the files. The next time the phone
boots, it will start the loop by itself.

## Caveats
- **Reboot:** without Termux:Boot you must re-run the start commands after a reboot.
- **OEM battery optimizers** on some phones still kill background apps. If updates stop for more
  than 5 minutes, keep Termux in the foreground or exempt it from battery optimization in Android
  settings.
- **`ddns.json` is plaintext** and now exists on two devices. Protect the phone's copy the same as
  the PC's.
