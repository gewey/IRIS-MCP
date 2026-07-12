#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


SERVER_NAME = "IRIS-MCP"


def _candidate_mcp_paths() -> list[Path]:
    home = Path.home()
    paths = []

    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_path = Path(appdata)
        paths.extend(
            [
                appdata_path / "Code" / "User" / "mcp.json",
                appdata_path / "Code - Insiders" / "User" / "mcp.json",
            ]
        )

    paths.extend(
        [
            home / ".config" / "Code" / "User" / "mcp.json",
            home / ".config" / "Code - Insiders" / "User" / "mcp.json",
            home / "Library" / "Application Support" / "Code" / "User" / "mcp.json",
            home / "Library" / "Application Support" / "Code - Insiders" / "User" / "mcp.json",
        ]
    )

    unique_paths = []
    seen = set()
    for path in paths:
        if path not in seen:
            unique_paths.append(path)
            seen.add(path)
    return unique_paths


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level JSON object.")
    return data


def _servers_key(data: dict) -> str:
    if isinstance(data.get("servers"), dict):
        return "servers"
    if isinstance(data.get("mcpServers"), dict):
        return "mcpServers"
    return "servers"


def _server_definition(repo_root: Path) -> dict:
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": [str(repo_root / "IRIS-MCP.py")],
        "cwd": str(repo_root),
    }


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    server_config = _server_definition(repo_root)
    updated = 0

    for mcp_path in _candidate_mcp_paths():
        try:
            data = _read_json(mcp_path)
        except Exception as exc:
            print(f"Skipping {mcp_path}: {exc}", file=sys.stderr)
            continue

        key = _servers_key(data)
        servers = data.get(key)
        if not isinstance(servers, dict):
            servers = {}
            data[key] = servers

        existing = servers.get(SERVER_NAME)
        before = json.dumps(existing, sort_keys=True) if isinstance(existing, dict) else None
        after = json.dumps(server_config, sort_keys=True)
        if before == after:
            print(f"Already configured: {mcp_path}")
            continue

        servers[SERVER_NAME] = server_config
        _write_json(mcp_path, data)
        updated += 1
        print(f"Updated: {mcp_path}")

    if updated == 0:
        print("No files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
