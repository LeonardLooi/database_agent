#!/usr/bin/env python3
"""
with_server.py — Start one or more dev servers, wait until ready, run a command, then clean up.

Adapted for the workspace tech stacks:
  Angular (ng serve)       → port 4200
  NestJS (npm run start)   → port 3000
  FastAPI (uvicorn)        → port 8000
  Spring Boot (mvn)        → port 8080
  Flutter Web (flutter run) → port 8080 (configurable)

Usage — single server:
    python scripts/with_server.py --server "ng serve" --port 4200 -- playwright-cli goto http://localhost:4200

Usage — multiple servers (e.g. NestJS backend + Angular frontend):
    python scripts/with_server.py \
      --server "npm run start:dev" --port 3000 \
      --server "ng serve" --port 4200 \
      -- playwright-cli -s=e2e goto http://localhost:4200

Usage — Flutter web:
    python scripts/with_server.py \
      --server "flutter run -d web-server --web-port 8080" --port 8080 \
      -- playwright-cli goto http://localhost:8080

Usage — FastAPI backend + Angular frontend:
    python scripts/with_server.py \
      --server "uvicorn main:app --host 0.0.0.0 --port 8000" --port 8000 \
      --server "ng serve --port 4200" --port 4200 \
      -- playwright-cli -s=test goto http://localhost:4200

Options:
    --server CMD    Server start command (repeatable for multiple servers)
    --port N        Port to poll for that server (must pair 1-to-1 with --server)
    --timeout N     Seconds to wait per server (default: 60)
    -- CMD ARGS     Command to run once all servers are ready
"""

import subprocess
import socket
import time
import sys
import argparse


# ── Stack presets (for quick reference in scripts) ─────────────────────────
STACK_PRESETS = {
    "angular":     {"cmd": "ng serve --port 4200",                            "port": 4200},
    "nestjs":      {"cmd": "npm run start:dev",                               "port": 3000},
    "fastapi":     {"cmd": "uvicorn main:app --host 0.0.0.0 --port 8000",     "port": 8000},
    "spring":      {"cmd": "mvn spring-boot:run",                             "port": 8080},
    "flutter-web": {"cmd": "flutter run -d web-server --web-port 8080",       "port": 8080},
}


def is_server_ready(port: int, timeout: int = 60) -> bool:
    """Poll TCP port until server accepts connections or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start dev server(s), run a command, then stop servers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--server", action="append", dest="servers", required=True,
                        help="Server start command (repeat for multiple servers)")
    parser.add_argument("--port", action="append", dest="ports", type=int, required=True,
                        help="Port to wait on for each --server (must match count)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Seconds to wait per server before failing (default: 60)")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="Command + args to run after all servers are ready")

    args = parser.parse_args()

    # Strip leading '--' separator
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        parser.error("No command specified. Add -- <command> after server args.")

    if len(args.servers) != len(args.ports):
        parser.error(f"--server count ({len(args.servers)}) must match --port count ({len(args.ports)})")

    server_configs = list(zip(args.servers, args.ports))
    processes: list[subprocess.Popen] = []

    try:
        for i, (cmd, port) in enumerate(server_configs, 1):
            print(f"[{i}/{len(server_configs)}] Starting: {cmd}")
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            processes.append(proc)

            print(f"          Waiting for port {port} (timeout: {args.timeout}s)...")
            if not is_server_ready(port, timeout=args.timeout):
                raise RuntimeError(
                    f"Server '{cmd}' did not open port {port} within {args.timeout}s.\n"
                    f"Check that the command starts the server on that port."
                )
            print(f"          ✅ Ready on port {port}")

        print(f"\nAll {len(processes)} server(s) ready. Running: {' '.join(args.command)}\n")
        result = subprocess.run(args.command)
        sys.exit(result.returncode)

    except RuntimeError as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if processes:
            print(f"\nStopping {len(processes)} server(s)...")
            for i, proc in enumerate(processes, 1):
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                print(f"  Server {i} stopped")


if __name__ == "__main__":
    main()
