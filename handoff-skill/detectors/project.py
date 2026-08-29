#!/usr/bin/env python3
"""Project identity and tech stack detection for handoff-skill.

Usage:
    python3 project.py [project_root]

Output: JSON with project name, path, and detected tech stack.
"""

import json
import sys
from pathlib import Path


def _collect_search_dirs(root: Path, max_depth: int = 2) -> list[Path]:
    """Collect root + subdirectories up to max_depth, skipping noise dirs."""
    skip_prefixes = (".", "_", "node_modules", "__pycache__", "dist", "out", ".next", ".git")
    search_dirs = [root]
    try:
        for d in root.iterdir():
            if d.is_dir() and not d.name.startswith(skip_prefixes):
                search_dirs.append(d)
                if max_depth > 1:
                    for d2 in d.iterdir():
                        if d2.is_dir() and not d2.name.startswith(skip_prefixes):
                            search_dirs.append(d2)
    except Exception:
        pass
    return search_dirs


def detect_project_name(root: Path) -> str:
    """Infer project name from known config files, falling back to directory name."""
    search_dirs = _collect_search_dirs(root)
    for search_dir in search_dirs:
        checks = [
            (search_dir / "package.json", lambda p: _json_field(p, "name")),
            (search_dir / "pyproject.toml", lambda p: _toml_field(p, "name")),
            (search_dir / "Cargo.toml", lambda p: _toml_field(p, "name")),
            (search_dir / "go.mod", lambda p: _go_module_name(p)),
        ]
        for path, extractor in checks:
            if path.exists():
                name = extractor(path)
                if name:
                    return name
    return root.name


def _json_field(path: Path, field: str) -> str | None:
    try:
        data = json.loads(path.read_text())
        return data.get(field)
    except Exception:
        return None


def _toml_field(path: Path, field: str) -> str | None:
    try:
        text = path.read_text()
        in_target_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and field in stripped.lower():
                in_target_section = True
                continue
            if in_target_section and stripped.startswith("["):
                in_target_section = False
                continue
            if in_target_section and stripped.startswith("name") and "=" in stripped:
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        return None


def _go_module_name(path: Path) -> str | None:
    try:
        text = path.read_text()
        for line in text.splitlines():
            if line.startswith("module "):
                module = line.split(" ", 1)[1].strip()
                return module.rsplit("/", 1)[-1]
    except Exception:
        return None


def detect_tech_stack(root: Path) -> dict:
    """Scan for known tech-stack markers and return structured result."""
    markers = {
        "package.json": "Node.js",
        "pyproject.toml": "Python",
        "requirements.txt": "Python",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose",
        "Makefile": "Make",
    }

    languages = []
    tools = []
    frameworks = []

    search_dirs = _collect_search_dirs(root)
    for search_dir in search_dirs:
        for filename, label in markers.items():
            if (search_dir / filename).exists():
                if label in ("Docker", "Docker Compose", "Make"):
                    if label not in tools:
                        tools.append(label)
                else:
                    if label not in languages:
                        languages.append(label)

        # Framework detection
        pkg = search_dir / "package.json"
        if pkg.exists():
            for f in _node_frameworks(pkg):
                if f not in frameworks:
                    frameworks.append(f)
        pyproj = search_dir / "pyproject.toml"
        if pyproj.exists():
            for f in _python_frameworks(pyproj):
                if f not in frameworks:
                    frameworks.append(f)

    return {"languages": languages, "tools": tools, "frameworks": frameworks}


def _node_frameworks(pkg_json: Path) -> list:
    try:
        data = json.loads(pkg_json.read_text())
        deps = {}
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))
        known = {
            "next": "Next.js",
            "react": "React",
            "vue": "Vue.js",
            "express": "Express",
            "fastify": "Fastify",
            "svelte": "Svelte",
            "astro": "Astro",
            "remix": "Remix",
            "nuxt": "Nuxt",
        }
        return [label for pkg, label in known.items() if pkg in deps]
    except Exception:
        return []


def _python_frameworks(pyproject: Path) -> list:
    try:
        text = pyproject.read_text().lower()
        known = {
            "fastapi": "FastAPI",
            "flask": "Flask",
            "django": "Django",
            "litestar": "Litestar",
        }
        return [label for pkg, label in known.items() if pkg in text]
    except Exception:
        return []


def _generate_dev_hints(tech_stack: dict) -> dict:
    """Generate development workflow hints based on detected tech stack."""
    languages = tech_stack.get("languages", [])
    frameworks = tech_stack.get("frameworks", [])
    tools = tech_stack.get("tools", [])

    hints = {
        "backend_hot_reload": False,
        "backend_note": "",
        "frontend_hot_reload": False,
        "frontend_note": "",
    }

    # Backend
    if "Python" in languages:
        fw_lower = [f.lower() for f in frameworks]
        if "fastapi" in fw_lower:
            hints["backend_note"] = "FastAPI with uvicorn --reload auto-reloads; without --reload, restart manually."
        elif "flask" in fw_lower:
            hints["backend_note"] = "Flask with debug=True auto-reloads; otherwise restart manually."
        elif "django" in fw_lower:
            hints["backend_note"] = "Django runserver auto-reloads in debug mode; otherwise restart manually."
        else:
            hints["backend_note"] = "Python backend -- restart service manually after code changes."
    elif "Go" in languages:
        hints["backend_note"] = "Go backend -- recompile and restart after code changes."
    elif "Rust" in languages:
        hints["backend_note"] = "Rust backend -- cargo build and restart after code changes."
    elif "Node.js" in languages:
        fw_lower = [f.lower() for f in frameworks]
        if "next" in fw_lower:
            hints["backend_note"] = "Next.js API routes -- next dev auto-reloads."
        elif "express" in fw_lower or "fastify" in fw_lower:
            hints["backend_note"] = "Node backend -- use nodemon/tsx watch for auto-reload, otherwise restart manually."
        else:
            hints["backend_note"] = "Node.js backend -- restart manually unless using nodemon/tsx watch."

    # Frontend
    fw_lower = [f.lower() for f in frameworks]
    if "next" in fw_lower or "react" in fw_lower:
        hints["frontend_hot_reload"] = True
        hints["frontend_note"] = "Next.js/React dev mode -- hot reload, save to apply."
    elif "vue" in fw_lower or "nuxt" in fw_lower:
        hints["frontend_hot_reload"] = True
        hints["frontend_note"] = "Vue/Nuxt dev mode -- hot reload, save to apply."
    elif "svelte" in fw_lower or "astro" in fw_lower:
        hints["frontend_hot_reload"] = True
        hints["frontend_note"] = "Svelte/Astro dev mode -- hot reload, save to apply."
    elif "Node.js" in languages:
        hints["frontend_note"] = "Node.js frontend -- check if using dev server with HMR."

    return hints


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    tech_stack = detect_tech_stack(root)
    result = {
        "name": detect_project_name(root),
        "path": str(root.resolve()),
        "tech_stack": tech_stack,
        "dev_hints": _generate_dev_hints(tech_stack),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
