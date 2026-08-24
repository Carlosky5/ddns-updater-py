# Running on an Android phone

You can run this updater on an old Android phone as a second (or standby) DDNS node. It needs
the same `ddns.json` config as the PC, and both nodes update the same Dynadot record — which is
safe, because they report the same public IP (same ISP), so whichever notices a change first
simply sets the same value again.

## Requirements
- Android 8 or newer
- [Termux](https://f-droid.org/packages/com.termux/) — install from **F-Droid or the Termux
  GitHub releases, not the Google Play Store** (the Play Store build is outdated and can break)
- Phone plugged into power — a 24/7 polling loop drains a battery, and a warm old battery left
  unattended is a safety risk.

## Setup (one time)
1. Copy this folder (including the existing `ddns.json`) onto the phone, e.g. to
   `/sdcard/DDNS-PY/` (File transfer app, `adb push`, or a USB cable).
2. Open Termux and install Python:
   ```
   pkg update
   pkg install python
   ```
3. Grant Termux storage access so it can even *see* `/sdcard` (without this, `ls /sdcard` may
   show an empty or partial listing):
   ```
   termux-setup-storage
   ```
   Tap **Allow** on the Android prompt.
4. Run a test cycle:
   ```
   cd /sdcard/DDNS-PY
   python ddns.py --live --once --force
   ```
   Expect `LIVE: success` and a `{"status":"success"}` Dynadot response. If you'd rather not
   send an update immediately, do the dry-run first: `python ddns.py --once --force`.

## Run it continuously
```
termux-wake-lock
python ddns.py --live
```
`termux-wake-lock` stops Android from suspending Python when the screen turns off. Then leave the
phone plugged in and Termux open.

## Caveats
- **Rebooting the phone stops the loop.** Re-run the two commands above. (Later you can add the
  `Termux:Boot` add-on app to auto-start on boot.)
- **OEM battery optimizers** on some phones kill background apps anyway. If updates stop for >5
  minutes, keep Termux in the foreground or exempt it from battery optimization.
- **`ddns.json` is plaintext** and now lives on two devices. Protect the phone the same way you
  protect the PC's copy.
