#!/usr/bin/env python3
import subprocess
import re
import sys
import os

DOCKERS_ROOT = "/opt/dockers"


def discover_containers():
    """Scan DOCKERS_ROOT for subdirs that contain docker-compose.yml."""
    result = {}
    try:
        entries = sorted(os.scandir(DOCKERS_ROOT), key=lambda e: e.name)
    except FileNotFoundError:
        return result
    for entry in entries:
        if entry.is_dir() and os.path.isfile(os.path.join(entry.path, "docker-compose.yml")):
            result[entry.name] = entry.path
    return result


CONTAINERS = discover_containers()

# ANSI colours
YELLOW = "\033[33m"
BLUE   = "\033[34m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def get_running_containers():
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
        capture_output=True,
        text=True,
    )
    containers = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        containers.append({
            "name":   parts[0] if len(parts) > 0 else "",
            "status": parts[1] if len(parts) > 1 else "",
            "ports":  parts[2] if len(parts) > 2 else "",
        })
    return containers


def extract_host_ports(ports_str):
    """Return deduplicated list of host-side mapped ports."""
    found = re.findall(r'(?:0\.0\.0\.0|\[::\]):(\d+)->', ports_str)
    seen, unique = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def parse_uptime(status):
    """Return the 'Up X minutes' portion, stripping health annotation."""
    m = re.match(r'(Up\s+.+?)(?:\s*\(|$)', status)
    return m.group(1).strip() if m else status


def is_unhealthy(status):
    return "(unhealthy)" in status.lower()


def display_status():
    containers = get_running_containers()
    print()
    if not containers:
        print("  No running containers.")
    for c in containers:
        name   = c["name"]
        status = c["status"]
        ports  = c["ports"]

        host_ports = extract_host_ports(ports)
        uptime     = parse_uptime(status)
        unhealthy  = is_unhealthy(status)

        if host_ports:
            name_colour = YELLOW if unhealthy else BLUE
            coloured_name  = f"{name_colour}{name}{RESET}"
            coloured_ports = f"{BLUE}" + ", ".join(host_ports) + f"{RESET}"
            parts = [coloured_name, "on", coloured_ports]
        else:
            parts = [name]
        if unhealthy:
            parts.append(f"{YELLOW}[unhealthy]{RESET}")
        parts.append(uptime)

        print("  " + " ".join(parts))
    print()


def run_command(cmd):
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd)
    print()


def compose_action(action, name):
    compose_file = f"{CONTAINERS[name]}/docker-compose.yml"
    if action == "start":
        cmd = ["docker", "compose", "-f", compose_file, "up", "-d"]
    elif action == "stop":
        cmd = ["docker", "compose", "-f", compose_file, "stop"]
    elif action == "down":
        cmd = ["docker", "compose", "-f", compose_file, "down"]
    else:
        return
    run_command(cmd)


def prompt_container(names=None):
    """Return list of chosen container names, or None to go back.

    names: list of names to display and select from; defaults to all CONTAINERS.
    """
    if names is None:
        names = list(CONTAINERS.keys())
    print()
    if not names:
        print("  No containers to act on.")
        return None
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    print(f"  {len(names) + 1}. all")
    print(f"  {len(names) + 2}. back")

    while True:
        raw = input("\n  Which container? ").strip().lower()
        if raw in ("0", "exit", "q", "quit"):
            print("  Bye.")
            break

        if raw in ("back", "b", ""):
            return None
        if raw == "all":
            return names
        if raw in names:
            return [raw]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(names):
                return [names[idx]]
            if idx == len(names):
                return names
            if idx == len(names) + 1:
                return None
        print("  Invalid choice, try again.")


def main():
    print("do_manager.py - Docker Manager")
    while True:
        display_status()
        print("  1. Start a container")
        print("  2. Stop a container")
        print("  3. Down a container")
        print("  4. Refresh")
        print("  5. Exit")

        raw = input("\n  Choice: ").strip().lower()

        if raw in ("5", "exit", "q", "quit", ""):
            print("  Bye.")
            break
        elif raw in ("4", "refresh", "r"):
            continue
        elif raw in ("1", "start"):
            action = "start"
            targets = prompt_container()
        elif raw in ("2", "stop"):
            action = "stop"
            running = get_running_containers()
            if not running:
                print("  nothing running.")
                break
            running_names = [c["name"] for c in running if c["name"] in CONTAINERS]
            if len(running_names) == 1:
                default_name = running_names[0]
                choice = input(f"\n  Stop {default_name}? (Enter to confirm, anything else to cancel): ").strip()
                targets = [default_name] if choice == "" else None
            else:
                targets = prompt_container(names=running_names)
        elif raw in ("3", "down"):
            action = "down"
            targets = prompt_container()
        else:
            print("  Invalid choice.")
            continue

        if targets is None:
            continue

        print()
        for name in targets:
            compose_action(action, name)

        if action in ("start", "stop", "down"):
            display_status()
            break


if __name__ == "__main__":
    main()
