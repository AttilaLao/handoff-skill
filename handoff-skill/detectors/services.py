#!/usr/bin/env python3
"""Service architecture detection for handoff-skill.

Usage:
    python3 services.py [project_root]

Output: JSON with service list, deploy info, and SSH key detection.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def _collect_search_dirs(root: Path) -> list[Path]:
    """Collect root + immediate subdirectories, skipping noise."""
    skip_prefixes = (".", "_", "node_modules", "__pycache__", ".git", ".next", "dist", "out")
    search_dirs = [root]
    try:
        for d in root.iterdir():
            if d.is_dir() and not d.name.startswith(skip_prefixes):
                search_dirs.append(d)
    except Exception:
        pass
    return search_dirs


def _read_plist_text(plist_path: Path) -> str:
    """Read a plist as text (handles binary plists via plutil)."""
    try:
        result = subprocess.run(
            ["plutil", "-convert", "xml1", "-o", "-", str(plist_path)],
            capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    try:
        return plist_path.read_text()
    except Exception:
        return ""


def detect_services(root: Path, project_name: str) -> dict:
    """Detect services from docker-compose, launchd plists, and brew."""
    services = []
    search_dirs = _collect_search_dirs(root)

    # 1. Docker Compose — check root and subdirectories
    for search_dir in search_dirs:
        for fname in ("docker-compose.yml", "docker-compose.yaml"):
            compose_file = search_dir / fname
            if compose_file.exists():
                text = compose_file.read_text()
                try:
                    import yaml
                    data = yaml.safe_load(text)
                    if data and "services" in data:
                        for name, cfg in data["services"].items():
                            svc = {"name": name, "source": "docker-compose", "ports": []}
                            if cfg and "ports" in cfg:
                                for port in cfg["ports"]:
                                    svc["ports"].append(str(port))
                            services.append(svc)
                        continue
                except ImportError:
                    pass
                for m in re.finditer(r'^\s{2,}(\w+):', text, re.MULTILINE):
                    name = m.group(1)
                    if name not in ("services", "version"):
                        services.append({"name": name, "source": "docker-compose", "ports": []})

    # 2. Launchd plists — match by filename, content path, or prefix
    launchd_dir = Path.home() / "Library" / "LaunchAgents"
    prefix = project_name.lower().split("-")[0] if "-" in project_name else ""
    if launchd_dir.exists():
        root_str = str(root)
        for plist in launchd_dir.glob("*.plist"):
            plist_name = plist.stem.lower()
            plist_text = _read_plist_text(plist)
            name_match = project_name.lower() in plist_name
            content_match = root_str.lower() in plist_text.lower() or root.name.lower() in plist_text.lower()
            prefix_match = prefix and len(prefix) >= 3 and prefix in plist_name
            if name_match or content_match or prefix_match:
                ports = re.findall(r'--port\s+(\d+)', plist_text)
                services.append({
                    "name": plist.stem,
                    "source": "launchd",
                    "ports": ports,
                })

    # 3. Brew services — match by project name or prefix
    try:
        brew_result = subprocess.run(
            ["brew", "services", "list"],
            capture_output=True, text=True, timeout=10)
        for line in brew_result.stdout.splitlines():
            line_lower = line.lower()
            if project_name.lower() in line_lower or (prefix and prefix in line_lower):
                parts = line.split()
                if parts:
                    services.append({"name": parts[0], "source": "brew", "ports": []})
    except Exception:
        pass

    # 4. Deploy script — extract deployment commands
    deploy_info = _detect_deploy_script(search_dirs)

    # 5. SSH key existence check (names only, not paths)
    ssh_keys = _detect_ssh_keys()

    return {
        "services": services,
        "project_name": project_name,
        "deploy": deploy_info,
        "ssh_keys_detected": ssh_keys,
    }


def _detect_deploy_script(search_dirs: list[Path]) -> dict:
    """Read deploy.sh if present and extract deployment command summary."""
    deploy_info = {"has_deploy_script": False, "commands": [], "raw_lines": []}
    for search_dir in search_dirs:
        for fname in ("deploy.sh", "deploy.md"):
            p = search_dir / fname
            if p.exists():
                deploy_info["has_deploy_script"] = True
                try:
                    text = p.read_text()
                    for line in text.splitlines():
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            deploy_info["raw_lines"].append(stripped)
                    for line in deploy_info["raw_lines"]:
                        if any(kw in line for kw in ("scp", "rsync", "docker", "ssh", "wrangler", "deploy", "npm run", "pnpm")):
                            deploy_info["commands"].append(line)
                except Exception:
                    pass
                return deploy_info
    return deploy_info


def _detect_ssh_keys() -> list[str]:
    """Check ~/.ssh for key filenames (not contents, not paths in output)."""
    keys = []
    ssh_dir = Path.home() / ".ssh"
    if ssh_dir.exists():
        for key in ssh_dir.iterdir():
            if key.name.startswith("id_") and not key.name.endswith(".pub"):
                keys.append(key.name)
    return keys


def _generate_restart_hints(services: list[dict], deploy_info: dict) -> dict:
    """Generate restart command hints based on detected service management."""
    hints = {
        "backend_restart": [],
        "frontend_restart": [],
        "deploy_commands": [],
        "notes": [],
    }

    for svc in services:
        name = svc.get("name", "")
        source = svc.get("source", "")

        if source == "launchd":
            plist_path = f"~/Library/LaunchAgents/{name}.plist"
            hints["backend_restart"].append(
                f"launchctl unload {plist_path}; sleep 2; launchctl load {plist_path}"
            )
            if any(kw in name.lower() for kw in ("dashboard", "frontend", "next", "web")):
                hints["frontend_restart"].append(
                    f"launchctl unload {plist_path}; sleep 2; launchctl load {plist_path}"
                )

        elif source == "docker-compose":
            hints["backend_restart"].append(f"docker-compose restart {name}")

        elif source == "brew":
            hints["backend_restart"].append(f"brew services restart {name}")

    if deploy_info.get("has_deploy_script"):
        hints["deploy_commands"] = deploy_info.get("commands", [])[:5]

    hints["backend_restart"] = list(dict.fromkeys(hints["backend_restart"]))
    hints["frontend_restart"] = list(dict.fromkeys(hints["frontend_restart"]))

    if not hints["backend_restart"]:
        hints["notes"].append("No backend service manager detected -- restart command unknown, ask user or check docs.")
    if not hints["frontend_restart"]:
        hints["notes"].append("No frontend service manager detected -- frontend may use hot reload (next dev / vite).")

    return hints


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    project_name = root.name
    result = detect_services(root, project_name)
    result["restart_hints"] = _generate_restart_hints(result["services"], result.get("deploy", {}))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
