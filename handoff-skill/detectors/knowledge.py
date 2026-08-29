#!/usr/bin/env python3
"""Knowledge base wrapper for handoff-skill.

Provides wrappers around memory_search and memory_add for use in handoff generation.
When MCP is unavailable, falls back to reading local project documents.

Usage:
    python3 knowledge.py search <project_name> <project_root>
    python3 knowledge.py add <title> <content> <project_name> <tags_comma>
"""

import json
import sys
from pathlib import Path


def search(project_name: str, root: Path) -> dict:
    """Search knowledge base for project context.

    Returns structured results with fallback to local document scanning.
    """
    queries = [
        f"{project_name} 部署",
        f"{project_name} 架构",
        f"{project_name} VPS 服务器",
        f"{project_name} 凭据",
    ]

    results = {"mcp_available": False, "findings": {}, "fallback_sources": []}

    # Note: actual memory_search calls are made by the LLM at runtime.
    # This script provides the query list and fallback logic for local docs.
    results["queries_to_try"] = queries

    # Fallback: scan local project documents
    local_docs = ["AGENTS.md", "README.md", "deploy.sh", "deploy.md"]
    for doc in local_docs:
        p = root / doc
        if p.exists():
            try:
                content = p.read_text()
                results["fallback_sources"].append({
                    "file": str(p),
                    "size_chars": len(content),
                })
            except Exception:
                pass

    # Also look for HANDOFF_* files
    for hp in root.glob("HANDOFF_*.md"):
        try:
            results["fallback_sources"].append({
                "file": str(hp),
                "size_chars": len(hp.read_text()),
            })
        except Exception:
            pass

    return results


def add_entry(title: str, content: str, project_name: str, tags: list[str]) -> dict:
    """Prepare a knowledge base entry for the LLM to write via memory_add.

    Does NOT call memory_add directly — returns the parameters for the LLM.
    """
    all_tags = list(set(["交接", project_name] + tags))
    return {
        "action": "memory_add",
        "params": {
            "title": title,
            "content": content,
            "tags": all_tags,
            "confidence": 0.85,
        },
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: knowledge.py <search|add> ..."}))
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        project_name = sys.argv[2] if len(sys.argv) > 2 else ""
        root = Path(sys.argv[3]) if len(sys.argv) > 3 else Path.cwd()
        result = search(project_name, root)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "add":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        project_name = sys.argv[4] if len(sys.argv) > 4 else ""
        tags = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[5] else []
        result = add_entry(title, content, project_name, tags)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
