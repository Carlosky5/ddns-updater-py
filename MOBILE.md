# Running on an Android phone

Run this updater on an old Android phone as a second (or standby) DDNS node. It keeps the same
domain pointing at your home internet connection, just like the PC does.

## What you need
- An Android phone (you can dedicate an old one).
- **Termux** — a terminal app for Android. Install it from the **Google Play Store** or **F-Droid**.
- The phone **plugged into power**. A tool running 24/7 drains a battery, and a warm battery left
  unattended is a safety risk.
- **The phone must be on the same home Wi-Fi/internet connection as the PC** (i.e. the same
  provider line). This tool points the domain at whatever public IP the phone reports — if the
  phone were on a different network (say, mobile data), it would point your domain there instead.

## Step 1 — Install Python inside Termux
Open Termux and type:
```
pkg install python
```
Wait for it to finish. That's the only package you need.

## Step 2 — Let Termux see the phone's storage
Termux cannot read the phone's normal storage (`/sdcard`) until you turn that on. In Termux, run:
```
termux-setup-storage
```
Android will show a permission prompt — **switch the toggle on / tap Allow** for external storage.
If you already have Termux open, close and reopen it afterwards.

## Step 3 — Learn the basics of moving around (only if new to terminals)
Termux starts in your "home" folder. Handy commands:

| Command | What it does |
|---|---|
| `pwd` | Show which folder you're in |
| `ls` | List the files in the current folder |
| `cd /sdcard` | Go to the phone's main shared storage (the "root" you can use without rooting) |
| `mkdir name` | Create a new folder called `name` here |
| `cp file folder/` | Copy a file into a folder |
| `~` | A shortcut that means "your home folder" |

## Step 4 — Put the tool on the phone
1. Using a USB cable or any file-transfer method, copy **this folder** (at minimum `ddns.py`)
   from a computer onto the phone — e.g. into the `Download` folder in shared storage.
2. Now in Termux, go to `/sdcard` first, create your own folder there, and move the file in:
   ```
   cd /sdcard
   mkdir ddns
   cp Download/ddns.py ddns/
   cd ddns
   ls
   ```
   The last command should show `ddns.py`.

   (Tip: you do **not** need to copy any `ddns.json` — Step 5 creates a fresh one on the phone.)

## Step 5 — First run creates its own config
```
python ddns.py --once --force
```
On the phone's **first** run there is no `ddns.json` yet, so the tool asks you:

```
Domain to update (e.g. example.com):
DDNS password:
Poll interval seconds [300]:
TTL seconds [600]:
```

Type your domain and the **DDNS password** (the registrar's DDNS password, *not* your account
password). For the last two questions just press **Enter** to accept the defaults. It saves a new
`ddns.json` right next to `ddns.py` and then does a dry-run test cycle, printing a `DRY-RUN:
would call …` line with the password hidden.

## Step 6 — Test a real update
```
python ddns.py --live --once --force
```
Expect a `LIVE: success` line and a Dynadot response of `{"status":"success"}`.

## Step 7 — Run it continuously
```
termux-wake-lock
python ddns.py --live
```
`termux-wake-lock` keeps Android from putting Python to sleep when the screen is off. Then lock
the screen, keep the phone **plugged in**, and leave the Termux window open.

## Things to know
- **Rebooting the phone stops the loop.** When it comes back, open Termux and run the two lines
  from Step 7 again.
- Some phones aggressively kill background apps to save battery. If the tool stops working for
  more than ~5 minutes (check the window's last printed line), either keep Termux in the
  foreground or exclude it from battery optimization in the phone's settings.
- **`ddns.json` is a plaintext file** and now exists on your phone too — treat it like any other
  password file.
- The phone and the PC are two independent updaters of the same record. That's safe: they sit on
  the same connection, so they always report the same IP.
