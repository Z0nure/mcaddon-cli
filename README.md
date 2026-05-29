# mcaddon-cli

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Zonure-ff5e5b?logo=ko-fi&logoColor=white)](https://ko-fi.com/zonure)

> A standalone Python CLI tool that automatically deploys Minecraft Bedrock addons to your server. No dependencies, no panel needed — just Python 3 and SSH access.

---

## Features

- 📦 Accepts `.mcaddon` and `.mcpack` files
- 🔍 Auto-detects resource packs, behavior packs, or both from `manifest.json`
- 📁 Copies pack files into the correct folder inside your world
- 📝 Registers packs in `world_resource_packs.json` and `world_behavior_packs.json`
- 🔁 Batch mode — point it at a folder of addons
- ✅ Skips packs already registered — safe to run multiple times
- 🐍 No `pip install` needed — pure Python 3 standard library

---

## Requirements

- Python 3.6 or higher
- SSH access to your Bedrock server
- Your server's world folder full path

---

## Usage

```bash
# Single addon
python mc_addon_deploy.py --addon my_addon.mcaddon --world /full/path/to/worlds/MyWorld

# Single pack
python mc_addon_deploy.py --addon my_pack.mcpack --world /full/path/to/worlds/MyWorld

# Batch — folder of addons
python mc_addon_deploy.py --addon /path/to/addons/ --world /full/path/to/worlds/MyWorld
```

> ⚠️ **Always use the full absolute path for `--world`** — not a relative path like `worlds/default`.
> Find it by navigating to your world folder and running `pwd`.

---

## What it does

1. Extracts the `.mcaddon` or `.mcpack` file
2. Reads `manifest.json` to detect the pack type (resource, behavior, or both)
3. Copies pack files into the correct folder inside your world:
   - `worlds/MyWorld/resource_packs/PackName/`
   - `worlds/MyWorld/behavior_packs/PackName/`
4. Registers the pack in `world_resource_packs.json` or `world_behavior_packs.json`
5. Skips registration if the pack UUID is already present — safe to re-run

---

## Finding your world path

**Direct SSH access:**
```bash
cd /path/to/your/server/worlds/MyWorld
pwd
```

**Pelican Panel with Wings:**

The container path looks like:
```
/var/lib/pelican/volumes/<random-uuid>/worlds/MyWorld
```

Find it by checking the Wings volume directory:
```bash
ls /var/lib/pelican/volumes/
```

---

## Example output

```
━━━ Minecraft Bedrock Addon Deployer — zonure.xyz ━━━
  →  World:     /home/user/bedrock-server/worlds/MyWorld
  →  Resources: /home/user/bedrock-server/worlds/MyWorld/resource_packs
  →  Behaviors: /home/user/bedrock-server/worlds/MyWorld/behavior_packs

  →  Processing: MyAddon.mcaddon
  →  Pack: 'MyCoolPack'  |  Type: resource  |  UUID: a1b2c3d4…
  ✔  Copied to .../resource_packs/MyCoolPack
  ✔  Registered in world_resource_packs.json

  ✔  All done! Restart your server to apply changes.
```

---

## Prefer a web interface?

If you're on Pelican or Pterodactyl, check out **[MC-Addon-Deployer](https://github.com/Z0nure/MC-Addon-Deployer)** — no terminal needed. Live at [zonure.xyz](https://zonure.xyz).

---

## Support

If this saved you time, consider buying me a coffee ☕

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/zonure)

---

Made by [Zonure](https://zonure.xyz) — *The Lazy Lizard*
