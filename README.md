# mcaddon-cli

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Zonure-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/zonure)

> A standalone Python CLI tool that automatically deploys and uninstalls Minecraft Bedrock addons on your server. No dependencies, no panel needed — just Python 3 and SSH access.

---

## Features

- 🔎 Automatically finds Bedrock worlds by searching for `level.dat` — no need to know the path
- 📦 Accepts `.mcaddon` and `.mcpack` files — single or multiple at once
- 🔍 Auto-detects resource packs, behavior packs, or both from `manifest.json`
- ⚡ Smart version checking — installs new, updates outdated, skips already installed
- 🗑 Addon uninstaller — lists installed addons, pick what to remove, cleans folders and JSON entries
- 🔁 Multi-select — pick specific addons by number or process all at once
- 🐍 No `pip install` needed — pure Python 3 standard library

---

## Requirements

- Python 3.6 or higher
- SSH access to your Bedrock server

That's it. No path hunting needed — the tool finds your world automatically.

---

## Usage

```bash
python mcaddon-cli.py
```

The tool starts an interactive menu and guides you through everything.

---

## How it works

### 1. World detection

When you run the script it immediately searches for `level.dat` files — the Bedrock world indicator. It checks common server paths first (home directories, Pelican/Pterodactyl volumes, `/opt`, `/srv`) so it finds your world in seconds in most cases.

- **One world found** — confirms it with you
- **Multiple worlds found** — shows a numbered list, you pick the right one
- **Nothing found** — falls back to manual path input

### 2. Main menu

```
[1] Install addons
[2] Uninstall addons
[3] Exit
```

The world is selected once at startup. You can install and uninstall without re-selecting.

### 3. Installing addons

Drop your addon files into an `addons/` folder in the same directory as the script — the tool picks them up automatically:

```
mcaddon-cli.py
addons/
  ├── MyCoolAddon.mcaddon
  ├── AnotherPack.mcpack
  └── ...
```

If the `addons/` folder is empty or doesn't exist, the tool asks for a file or folder path instead.

Either way you get a numbered list to pick from:

```
[1] MyCoolAddon.mcaddon        (142.3 KB)
[2] AnotherPack.mcpack          (38.1 KB)
[0] Process all
```

Enter numbers separated by spaces or commas, or `0` for all.

The tool then checks what's already installed and categorizes each pack:
- **Install** — new pack, not on the server yet
- **Update** — same UUID but higher version, replaces the old one cleanly
- **Skip** — same or older version already installed

### 4. Uninstalling addons

The tool reads both world JSON files and scans the `resource_packs/` and `behavior_packs/` folders directly. Resource and behavior packs from the same addon are grouped together by name:

```
[1] MyCoolAddon        (resource + behavior)
[2] AnotherPack        (resource)
[3] OrphanedPack       (behavior) [orphaned]
[0] Remove all
```

> **Orphaned** means the folder exists on disk but has no matching JSON entry — the tool will still clean it up.

Select what to remove — the tool deletes the pack folder(s) and removes the entries from the world JSON files.

---

## Example session

```
━━━ mcaddon-cli — Bedrock Addon Manager — zonure.xyz ━━━

  Searching for Bedrock worlds (level.dat)…
  ✔  Found world: /var/lib/pelican/volumes/25bcb378.../worlds/default

  Is this the correct world? [Y/n] y

What would you like to do?
  [1] Install addons
  [2] Uninstall addons
  [3] Exit

  Choice: 1

  Found 3 addon file(s) in ./addons/

Select addon(s) to process:
  [1] MyCoolAddon.mcaddon        (142.3 KB)
  [2] AnotherPack.mcpack          (38.1 KB)
  [3] OldAddon.mcaddon            (21.0 KB)
  [0] Process all

  Enter number(s) — space or comma separated [0 for all]: 1 2

  →  Found 10 installed pack(s) on this world.
  ✔  MyCoolAddon: resource pack installed
  ⚠  AnotherPack: same version already installed, skipping.

Summary
  Installed: 1  Updated: 0  Skipped: 1  Failed: 0

  ✔  Restart your server to apply changes.
```

---

## Prefer a web interface?

If you're on Pelican or Pterodactyl, check out **[MC-Addon-Deployer](https://github.com/Z0nure/MC-Addon-Deployer)** — upload addons and deploy straight from your browser. Live at [zonure.xyz](https://zonure.xyz).

---

## Support

If this saved you time, consider buying me a coffee ☕

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/zonure)

---

Made by [Zonure](https://zonure.xyz) — *The Lazy Lizard*
