#!/usr/bin/env python3
"""
mcaddon-cli — Minecraft Bedrock Addon Manager
Automatically installs and uninstalls addons on a Bedrock server.
Searches for worlds via level.dat, handles multi-file installs,
version checking, and clean uninstallation.

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
BLUE   = "\033[94m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}  ✔  {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ⚠  {msg}{RESET}")
def err(msg):   print(f"{RED}  ✘  {msg}{RESET}")
def info(msg):  print(f"{CYAN}  →  {msg}{RESET}")
def head(msg):  print(f"\n{BOLD}{msg}{RESET}")
def dim(msg):   print(f"{DIM}     {msg}{RESET}")


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
    modules = manifest.get("modules", [])
    types = set()
    for m in modules:
        mapped = PACK_TYPE_MAP.get(m.get("type", "").lower(), "unknown")
        types.add(mapped)
    if "resource" in types and "behavior" in types: return "both"
    if "resource" in types: return "resource"
    if "behavior" in types: return "behavior"
    return "unknown"

def compare_versions(a: list, b: list) -> int:
    """1 if a > b, 0 if equal, -1 if a < b"""
    for i in range(3):
        av = a[i] if i < len(a) else 0
        bv = b[i] if i < len(b) else 0
        if av > bv: return 1
        if av < bv: return -1
    return 0


# ─── JSON helpers ─────────────────────────────────────────────────────────────
def read_json(path: Path) -> list:
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            warn(f"Could not parse {path.name}, treating as empty.")
    return []

def write_json(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ─── World finder ─────────────────────────────────────────────────────────────
# Paths to check first before doing a broad search
PRIORITY_ROOTS = [
    Path("/root"),
    Path("/home"),
    Path("/opt"),
    Path("/srv"),
    Path("/var/lib/pelican/volumes"),
    Path("/var/lib/pterodactyl/volumes"),
    Path("/var/lib/docker/volumes"),
    Path.cwd(),
    Path.cwd().parent,
    Path.cwd().parent.parent,
]

def _print_search_progress(directory: str):
    """Overwrite the current line with the directory being searched."""
    truncated = directory if len(directory) <= 65 else "…" + directory[-64:]
    sys.stdout.write(f"\r{DIM}  Searching: {truncated:<65}{RESET}")
    sys.stdout.flush()

def _clear_search_line():
    sys.stdout.write(f"\r{' ' * 80}\r")
    sys.stdout.flush()

def find_worlds(max_depth: int = 6) -> list[Path]:
    """
    Search for level.dat files (Bedrock world indicator).
    Checks priority paths first, then does a broader walk.
    Returns list of world directory Paths.
    """
    found = set()

    # Directories that will never contain a Bedrock world
    skip_dirs = {
        "proc", "sys", "dev", "run", "tmp", "boot", "lost+found",
        "snap", "media", "mnt", "cdrom",
        "lib", "lib64", "lib32", "libx32",
        "bin", "sbin", "usr", "etc",
        "include", "share", "locale",
        "node_modules", ".git", "__pycache__",
        ".cache", ".npm", ".config", ".local", ".vscode",
        "dist", "build", "vendor",
    }

    def walk_for_leveldat(root: Path, depth: int):
        if depth < 0 or not root.exists():
            return
        try:
            for entry in root.iterdir():
                _print_search_progress(str(entry))
                if entry.is_file() and entry.name == "level.dat":
                    found.add(entry.parent.resolve())
                elif (entry.is_dir()
                      and entry.name not in skip_dirs
                      and not entry.name.startswith(".")):
                    walk_for_leveldat(entry, depth - 1)
        except PermissionError:
            pass

    print(f"\n{CYAN}  Searching for Bedrock worlds (level.dat)…{RESET}")

    # Priority paths first
    for root in PRIORITY_ROOTS:
        if root.exists():
            walk_for_leveldat(root, max_depth)

    # If nothing found yet, try a broader search from filesystem root
    if not found:
        warn("Nothing found in common paths, doing a full filesystem search…")
        walk_for_leveldat(Path("/"), max_depth)

    _clear_search_line()
    return sorted(found)


def select_world() -> Path:
    """Find worlds and let the user pick one."""
    worlds = find_worlds()

    if not worlds:
        err("No Bedrock worlds found (no level.dat detected).")
        info("Enter the full path to your world folder manually:")
        manual = input("  > ").strip()
        world = Path(manual)
        if not world.exists():
            err(f"Path not found: {world}")
            sys.exit(1)
        return world

    if len(worlds) == 1:
        ok(f"Found world: {worlds[0]}")
        confirm = input(f"\n  Is this the correct world? [Y/n] ").strip().lower()
        if confirm in ("", "y", "yes"):
            return worlds[0]
        else:
            info("Enter the full path to your world folder manually:")
            manual = input("  > ").strip()
            return Path(manual)

    head("Found multiple worlds — select one:")
    for i, w in enumerate(worlds, 1):
        print(f"  {CYAN}[{i}]{RESET} {w}")
    print(f"  {DIM}[0] Enter path manually{RESET}")

    while True:
        choice = input(f"\n  Select world: ").strip()
        if choice == "0":
            info("Enter the full path to your world folder:")
            return Path(input("  > ").strip())
        try:
            idx = int(choice)
            if 1 <= idx <= len(worlds):
                return worlds[idx - 1]
        except ValueError:
            pass
        warn("Invalid choice, try again.")


# ─── Addon file selection ─────────────────────────────────────────────────────
ADDONS_FOLDER_NAME = "addons"

def get_addon_files() -> list[Path]:
    """
    Check for an 'addons/' folder next to the script.
    If it has files, scan and list them for selection.
    Otherwise, ask the user for a path and scan that.
    """
    script_dir = Path(os.path.abspath(__file__)).parent
    addons_dir = script_dir / ADDONS_FOLDER_NAME

    if addons_dir.exists():
        files = [
            f for f in addons_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".mcaddon", ".mcpack")
        ]
        if files:
            info(f"Found {len(files)} addon file(s) in ./{ADDONS_FOLDER_NAME}/")
            return _select_from_list(sorted(files))

    # No addons folder or empty — ask for path
    warn(f"No addon files found in ./{ADDONS_FOLDER_NAME}/ (create it and drop files there to use it automatically)")
    info("Enter path to an addon file or folder containing addons:")
    raw = input("  > ").strip()
    target = Path(raw)

    if not target.exists():
        err(f"Path not found: {target}")
        sys.exit(1)

    if target.is_file():
        return [target]

    # It's a folder — scan it
    files = [
        f for f in target.iterdir()
        if f.is_file() and f.suffix.lower() in (".mcaddon", ".mcpack")
    ]
    if not files:
        err("No .mcaddon or .mcpack files found in that folder.")
        sys.exit(1)

    return _select_from_list(sorted(files))


def _select_from_list(files: list[Path]) -> list[Path]:
    """Show a numbered list and let the user pick. Supports multi-select."""
    head("Select addon(s) to process:")
    for i, f in enumerate(files, 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {CYAN}[{i}]{RESET} {f.name} {DIM}({size_kb:.1f} KB){RESET}")
    print(f"  {CYAN}[0]{RESET} Process all")

    while True:
        raw = input(f"\n  Enter number(s) — space or comma separated [0 for all]: ").strip()
        if not raw:
            continue

        if raw == "0":
            return files

        # Accept both comma and space separators
        parts = raw.replace(",", " ").split()
        selected = []
        valid = True

        for part in parts:
            try:
                idx = int(part)
                if 1 <= idx <= len(files):
                    if files[idx - 1] not in selected:
                        selected.append(files[idx - 1])
                else:
                    warn(f"{idx} is out of range.")
                    valid = False
                    break
            except ValueError:
                warn(f"'{part}' is not a valid number.")
                valid = False
                break

        if valid and selected:
            return selected
        warn("Invalid selection, try again.")


# ─── Pack extraction ──────────────────────────────────────────────────────────
def extract_packs(zip_path: Path, tmp_root: Path) -> list[dict]:
    """
    Extract a .mcaddon or .mcpack and return list of pack dicts:
    { manifest, content_dir, source }
    """
    packs = []
    tmp = tmp_root / ("_tmp_" + zip_path.stem)
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
    except zipfile.BadZipFile:
        err(f"{zip_path.name} is not a valid zip file.")
        shutil.rmtree(tmp, ignore_errors=True)
        return []

    suffix = zip_path.suffix.lower()

    if suffix == ".mcaddon":
        # Check for inner .mcpack files
        inner_packs = list(tmp.rglob("*.mcpack"))
        if inner_packs:
            for inner in inner_packs:
                packs.extend(extract_packs(inner, tmp_root))
            shutil.rmtree(tmp, ignore_errors=True)
            return packs
        # No inner packs — treat as single pack (folder-structure addon)

    # Find all manifest.json files
    manifests = list(tmp.rglob("manifest.json"))
    if not manifests:
        err(f"No manifest.json found in {zip_path.name}.")
        shutil.rmtree(tmp, ignore_errors=True)
        return []

    for manifest_path in manifests:
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            warn(f"Malformed manifest.json in {zip_path.name}, skipping.")
            continue
        packs.append({
            "manifest": manifest,
            "content_dir": manifest_path.parent,
            "source": zip_path.name,
        })

    return packs


# ─── Installed pack polling ───────────────────────────────────────────────────
def poll_installed(world_dir: Path) -> dict:
    """
    Read both world JSON files.
    Returns { uuid: { version, types: set("resource"|"behavior") } }
    """
    installed = {}

    for json_name, pack_type in [
        ("world_resource_packs.json", "resource"),
        ("world_behavior_packs.json", "behavior"),
    ]:
        for entry in read_json(world_dir / json_name):
            uuid = entry.get("pack_id", "")
            version = entry.get("version", [0, 0, 1])
            if uuid not in installed:
                installed[uuid] = {"version": version, "types": set()}
            installed[uuid]["types"].add(pack_type)

    return installed


# ─── Installer ────────────────────────────────────────────────────────────────
def install_packs(world_dir: Path, addon_files: list[Path]):
    tmp_root = Path("/tmp/mcaddon_cli")
    tmp_root.mkdir(parents=True, exist_ok=True)

    installed_map = poll_installed(world_dir)
    info(f"Found {len(installed_map)} installed pack(s) on this world.")

    all_packs = []
    for addon_file in addon_files:
        info(f"Reading {addon_file.name}…")
        packs = extract_packs(addon_file, tmp_root)
        all_packs.extend(packs)

    if not all_packs:
        warn("No valid packs found to install.")
        shutil.rmtree(tmp_root, ignore_errors=True)
        return

    installed_count = updated_count = skipped_count = failed_count = 0

    for pack in all_packs:
        manifest   = pack["manifest"]
        content_dir = Path(pack["content_dir"])
        header     = manifest.get("header", {})
        uuid       = header.get("uuid", "")
        version    = header.get("version", [0, 0, 1])
        name       = header.get("name", pack["source"]).replace(" ", "_")
        pack_type  = detect_pack_type(manifest)

        if not uuid:
            err(f"{name}: no UUID in manifest, skipping.")
            failed_count += 1
            continue

        existing = installed_map.get(uuid)
        if existing:
            cmp = compare_versions(version, existing["version"])
            if cmp <= 0:
                reason = "same version" if cmp == 0 else "older version"
                warn(f"{name}: {reason} already installed, skipping.")
                skipped_count += 1
                continue
            else:
                info(f"{name}: updating {'.'.join(map(str, existing['version']))} → {'.'.join(map(str, version))}")
                is_update = True
        else:
            is_update = False

        def deploy(subfolder: str, json_file: str):
            dest_parent = world_dir / subfolder
            dest = dest_parent / name
            dest_parent.mkdir(parents=True, exist_ok=True)

            if is_update and dest.exists():
                shutil.rmtree(dest)

            shutil.copytree(content_dir, dest)

            json_path = world_dir / json_file
            entries = read_json(json_path)

            if is_update:
                for entry in entries:
                    if entry.get("pack_id") == uuid:
                        entry["version"] = version
                        break
            else:
                if not any(e.get("pack_id") == uuid for e in entries):
                    entries.append({"pack_id": uuid, "version": version})

            write_json(json_path, entries)

        try:
            if pack_type in ("resource", "both"):
                deploy("resource_packs", "world_resource_packs.json")
            if pack_type in ("behavior", "both"):
                deploy("behavior_packs", "world_behavior_packs.json")
            if pack_type == "unknown":
                warn(f"{name}: unknown pack type, skipping.")
                skipped_count += 1
                continue

            if is_update:
                ok(f"{name}: {pack_type} pack updated")
                updated_count += 1
            else:
                ok(f"{name}: {pack_type} pack installed")
                installed_count += 1

        except Exception as e:
            err(f"{name}: failed — {e}")
            failed_count += 1

    shutil.rmtree(tmp_root, ignore_errors=True)

    head("Summary")
    print(f"  {GREEN}Installed: {installed_count}{RESET}  "
          f"{BLUE}Updated: {updated_count}{RESET}  "
          f"{YELLOW}Skipped: {skipped_count}{RESET}  "
          f"{RED}Failed: {failed_count}{RESET}")
    print()
    if installed_count + updated_count > 0:
        ok("Restart your server to apply changes.")


# ─── Uninstaller ──────────────────────────────────────────────────────────────
def normalize_name(name: str) -> str:
    """Strip BP/RP/BH/RH suffix for grouping."""
    import re
    return re.sub(r"[\s_\-]*(BP|RP|BH|RH|Behavior|Resource)$", "", name, flags=re.IGNORECASE).strip()


def fetch_installed_addons(world_dir: Path) -> list[dict]:
    """
    Read JSON files and scan pack folders, match by UUID,
    group resource+behavior pairs by name.
    Returns list of { name, resource, behavior } dicts.
    """
    resource_json = read_json(world_dir / "world_resource_packs.json")
    behavior_json = read_json(world_dir / "world_behavior_packs.json")

    resource_uuids = {e["pack_id"]: e["version"] for e in resource_json if "pack_id" in e}
    behavior_uuids = {e["pack_id"]: e["version"] for e in behavior_json if "pack_id" in e}

    addon_map = {}

    def scan_folder(subfolder: str, uuid_map: dict, pack_type: str):
        folder = world_dir / subfolder
        if not folder.exists():
            return
        for pack_dir in folder.iterdir():
            if not pack_dir.is_dir():
                continue
            manifest_path = pack_dir / "manifest.json"
            uuid = name = None
            version = None
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        m = json.load(f)
                    header = m.get("header", {})
                    uuid    = header.get("uuid")
                    name    = header.get("name", pack_dir.name)
                    version = header.get("version", [0, 0, 1])
                except Exception:
                    pass
            if not name:
                name = pack_dir.name

            in_json = uuid and uuid in uuid_map
            key = normalize_name(name).lower()

            if key not in addon_map:
                addon_map[key] = {"name": normalize_name(name), "resource": None, "behavior": None}

            addon_map[key][pack_type] = {
                "uuid": uuid,
                "version": version,
                "folder": pack_dir.name,
                "in_json": in_json,
                "orphaned": not in_json,
            }

            # Prefer shorter display name
            clean = normalize_name(name)
            if len(clean) < len(addon_map[key]["name"]):
                addon_map[key]["name"] = clean

    scan_folder("resource_packs", resource_uuids, "resource")
    scan_folder("behavior_packs", behavior_uuids, "behavior")

    return sorted(addon_map.values(), key=lambda x: x["name"].lower())


def uninstall_packs(world_dir: Path):
    info("Scanning installed addons…")
    addons = fetch_installed_addons(world_dir)

    if not addons:
        warn("No addons found in this world.")
        return

    head("Installed addons:")
    for i, addon in enumerate(addons, 1):
        types = []
        if addon["resource"]: types.append(f"{GREEN}resource{RESET}")
        if addon["behavior"]: types.append(f"{BLUE}behavior{RESET}")
        orphan_flag = ""
        if (addon["resource"] and addon["resource"].get("orphaned")) or \
           (addon["behavior"] and addon["behavior"].get("orphaned")):
            orphan_flag = f" {YELLOW}[orphaned]{RESET}"
        type_str = " + ".join(types)
        print(f"  {CYAN}[{i}]{RESET} {addon['name']} {DIM}({type_str}){RESET}{orphan_flag}")

    print(f"  {CYAN}[0]{RESET} Remove all")

    while True:
        raw = input(f"\n  Select addon(s) to remove — space or comma separated [0 for all]: ").strip()
        if not raw:
            continue
        if raw == "0":
            to_remove = addons
            break

        parts = raw.replace(",", " ").split()
        to_remove = []
        valid = True
        for part in parts:
            try:
                idx = int(part)
                if 1 <= idx <= len(addons):
                    if addons[idx - 1] not in to_remove:
                        to_remove.append(addons[idx - 1])
                else:
                    warn(f"{idx} is out of range.")
                    valid = False
                    break
            except ValueError:
                warn(f"'{part}' is not a valid number.")
                valid = False
                break

        if valid and to_remove:
            break
        warn("Invalid selection, try again.")

    head(f"Removing {len(to_remove)} addon(s)…")
    removed = failed = 0

    for addon in to_remove:
        name = addon["name"]

        for pack_type, subfolder, json_file in [
            ("resource", "resource_packs", "world_resource_packs.json"),
            ("behavior", "behavior_packs", "world_behavior_packs.json"),
        ]:
            pack = addon.get(pack_type)
            if not pack:
                continue

            try:
                # Remove folder
                folder_path = world_dir / subfolder / pack["folder"]
                if folder_path.exists():
                    shutil.rmtree(folder_path)

                # Remove JSON entry
                if pack.get("uuid"):
                    entries = read_json(world_dir / json_file)
                    entries = [e for e in entries if e.get("pack_id") != pack["uuid"]]
                    write_json(world_dir / json_file, entries)

                ok(f"{name}: {pack_type} pack removed")
                removed += 1
            except Exception as e:
                err(f"{name}: failed to remove {pack_type} pack — {e}")
                failed += 1

    head("Summary")
    print(f"  {GREEN}Removed: {removed}{RESET}  {RED}Failed: {failed}{RESET}")
    print()
    if removed > 0:
        ok("Restart your server to apply changes.")


# ─── Main menu ────────────────────────────────────────────────────────────────
def main():
    print()
    print(f"{BOLD}{CYAN}━━━ mcaddon-cli — Bedrock Addon Manager — zonure.xyz ━━━{RESET}")
    print()

    world_dir = select_world()
    info(f"World: {world_dir}")
    print()

    while True:
        head("What would you like to do?")
        print(f"  {CYAN}[1]{RESET} Install addons")
        print(f"  {CYAN}[2]{RESET} Uninstall addons")
        print(f"  {CYAN}[3]{RESET} Exit")

        choice = input(f"\n  Choice: ").strip()

        if choice == "1":
            addon_files = get_addon_files()
            install_packs(world_dir, addon_files)
        elif choice == "2":
            uninstall_packs(world_dir)
        elif choice == "3":
            print()
            sys.exit(0)
        else:
            warn("Invalid choice.")

        input(f"\n  {DIM}Press Enter to return to the menu…{RESET}")
        print()


if __name__ == "__main__":
    main()
