#!/usr/bin/env python3
"""
Minecraft Bedrock Addon Deployer (CLI)
Automatically installs .mcaddon / .mcpack files into a Bedrock server world,
detects pack types, and updates world_resource_packs.json / world_behavior_packs.json.

Packs are installed inside the world folder:
    worlds/MyWorld/resource_packs/PackName/
    worlds/MyWorld/behavior_packs/PackName/

Usage:
    python mc_addon_deploy.py --addon my_addon.mcaddon --world path/to/worlds/MyWorld
    python mc_addon_deploy.py --addon pack.mcpack --world path/to/worlds/MyWorld
    python mc_addon_deploy.py --addon addons/ --world path/to/worlds/MyWorld   # batch folder

Part of the mc-addon-deployer project by Zonure (zonure.xyz)
"""

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path


# ─── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def log(msg, colour=RESET): print(f"{colour}{msg}{RESET}")
def ok(msg):                log(f"  ✔  {msg}", GREEN)
def warn(msg):              log(f"  ⚠  {msg}", YELLOW)
def err(msg):               log(f"  ✘  {msg}", RED)
def info(msg):              log(f"  →  {msg}", CYAN)


# ─── Pack type detection ──────────────────────────────────────────────────────
PACK_TYPE_MAP = {
    "resources":      "resource",
    "data":           "behavior",
    "script":         "behavior",
    "javascript":     "behavior",
    "skin_pack":      "resource",
    "world_template": "resource",
}

def detect_pack_type(manifest: dict) -> str:
    """Return 'resource', 'behavior', 'both', or 'unknown'."""
    modules = manifest.get("modules", [])
    types_found = set()
    for module in modules:
        raw = module.get("type", "").lower()
        mapped = PACK_TYPE_MAP.get(raw, "unknown")
        types_found.add(mapped)

    if "resource" in types_found and "behavior" in types_found:
        return "both"
    if "resource" in types_found:
        return "resource"
    if "behavior" in types_found:
        return "behavior"
    return "unknown"


# ─── JSON helpers ─────────────────────────────────────────────────────────────
def read_json(path: Path) -> list:
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            warn(f"Could not parse {path.name}, treating as empty.")
    return []

def write_json(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def ensure_pack_entry(json_path: Path, pack_uuid: str, pack_version: list) -> bool:
    """Add pack entry to world JSON if not already present. Returns True if added."""
    entries = read_json(json_path)
    if any(e.get("pack_id") == pack_uuid for e in entries):
        warn(f"Pack {pack_uuid[:8]}… already in {json_path.name}, skipping.")
        return False
    entries.append({"pack_id": pack_uuid, "version": pack_version})
    write_json(json_path, entries)
    return True


# ─── Core installer ───────────────────────────────────────────────────────────
def install_pack(zip_path: Path, tmp_root: Path, world_dir: Path) -> bool:
    """
    Extract a single .mcpack, detect its type, copy it into the world folder,
    and register it in the appropriate world JSON file.

    Pack destinations (relative to world_dir):
        resource_packs/PackName/
        behavior_packs/PackName/
    """
    info(f"Processing: {zip_path.name}")

    tmp = tmp_root / ("_tmp_" + zip_path.stem)
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
    except zipfile.BadZipFile:
        err(f"{zip_path.name} is not a valid zip/mcpack file.")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    manifests = list(tmp.rglob("manifest.json"))
    if not manifests:
        err(f"No manifest.json found in {zip_path.name}. Skipping.")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    success = True
    for manifest_path in manifests:
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            err(f"Malformed manifest.json in {zip_path.name}. Skipping.")
            continue

        header    = manifest.get("header", {})
        pack_uuid = header.get("uuid", "")
        pack_ver  = header.get("version", [0, 0, 1])
        # Sanitize name — replace spaces with underscores for safe folder names
        pack_name = header.get("name", zip_path.stem).replace(" ", "_")
        pack_type = detect_pack_type(manifest)
        pack_content_dir = manifest_path.parent

        if not pack_uuid:
            err(f"No UUID in manifest for {pack_name}. Skipping.")
            continue

        info(f"Pack: '{pack_name}'  |  Type: {pack_type}  |  UUID: {pack_uuid[:8]}…")

        def copy_and_register(subfolder: str, world_json_name: str):
            dest_dir = world_dir / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / pack_name
            if dest.exists():
                warn(f"'{pack_name}' already exists in {subfolder}/, overwriting.")
                shutil.rmtree(dest)
            shutil.copytree(pack_content_dir, dest)
            ok(f"Copied to {dest}")
            added = ensure_pack_entry(world_dir / world_json_name, pack_uuid, pack_ver)
            if added:
                ok(f"Registered in {world_json_name}")

        if pack_type == "resource" or pack_type == "both":
            copy_and_register("resource_packs", "world_resource_packs.json")
        if pack_type == "behavior" or pack_type == "both":
            copy_and_register("behavior_packs", "world_behavior_packs.json")
        if pack_type == "unknown":
            warn(f"Unknown pack type for '{pack_name}'. Skipping registration.")
            success = False

    shutil.rmtree(tmp, ignore_errors=True)
    return success


def install_addon(addon_path: Path, world_dir: Path, tmp_root: Path):
    """Handle .mcaddon (zip of packs) or a single .mcpack."""
    suffix = addon_path.suffix.lower()

    if suffix == ".mcaddon":
        info(f"Unpacking .mcaddon: {addon_path.name}")
        unpack_dir = tmp_root / ("_addon_" + addon_path.stem)
        unpack_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(addon_path, "r") as zf:
            zf.extractall(unpack_dir)

        packs = list(unpack_dir.rglob("*.mcpack"))
        if not packs:
            warn("No .mcpack files found inside .mcaddon; treating as single pack.")
            install_pack(addon_path, tmp_root, world_dir)
        else:
            for pack in packs:
                install_pack(pack, tmp_root, world_dir)

        shutil.rmtree(unpack_dir, ignore_errors=True)

    elif suffix == ".mcpack":
        install_pack(addon_path, tmp_root, world_dir)
    else:
        err(f"Unsupported file type: {suffix}. Use .mcaddon or .mcpack")


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description="Deploy Minecraft Bedrock addons to a server world automatically."
    )
    parser.add_argument(
        "--addon", required=True,
        help="Path to .mcaddon, .mcpack, or a folder of addon files."
    )
    parser.add_argument(
        "--world", required=True,
        help="Full absolute path to the world folder (e.g. /home/user/bedrock-server/worlds/MyWorld). "
             "Do NOT use a relative path like worlds/default — use the full path. "
             "Resource and behavior packs will be placed inside this folder."
    )
    args = parser.parse_args()

    world_dir  = Path(args.world).resolve()
    addon_path = Path(args.addon).resolve()

    if not world_dir.exists():
        err(f"World directory not found: {world_dir}")
        sys.exit(1)

    if not addon_path.exists():
        err(f"Addon path not found: {addon_path}")
        sys.exit(1)

    tmp_root = Path("/tmp/mc_addon_deploy")
    tmp_root.mkdir(parents=True, exist_ok=True)

    print()
    log("━━━ Minecraft Bedrock Addon Deployer — zonure.xyz ━━━", CYAN)
    info(f"World:     {world_dir}")
    info(f"Resources: {world_dir / 'resource_packs'}")
    info(f"Behaviors: {world_dir / 'behavior_packs'}")
    warn("Make sure --world is the full absolute path to your world folder.")
    warn("Example: /home/user/bedrock-server/worlds/MyWorld")
    print()

    if addon_path.is_dir():
        files = list(addon_path.glob("*.mcaddon")) + list(addon_path.glob("*.mcpack"))
        if not files:
            err("No .mcaddon or .mcpack files found in the folder.")
            sys.exit(1)
        for f in files:
            print()
            install_addon(f, world_dir, tmp_root)
    else:
        install_addon(addon_path, world_dir, tmp_root)

    shutil.rmtree(tmp_root, ignore_errors=True)
    print()
    ok("All done! Restart your server to apply changes.")
    print()


if __name__ == "__main__":
    main()
