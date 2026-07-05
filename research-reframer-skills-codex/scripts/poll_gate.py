#!/usr/bin/env python
import argparse
import json
import os
import sys
import time

def read_json_if_exists(path, fallback=None):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON from {path}: {e}")
        return fallback

def main():
    parser = argparse.ArgumentParser(description="Poll for human selection at a specific gate.")
    parser.add_argument("--gate", type=int, required=True, choices=[1, 2, 3], help="Gate number to poll (1, 2, or 3)")
    parser.add_argument("--outputs-dir", type=str, required=True, help="Path to the outputs directory")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    args = parser.parse_args()

    outputs_dir = os.path.abspath(args.outputs_dir)
    status_path = os.path.join(outputs_dir, ".gate_status.json")
    selection_path = os.path.join(outputs_dir, "05_human_selection.json")

    print(f"[poll_gate] Monitoring outputs directory: {outputs_dir}")
    print(f"[poll_gate] Waiting for Gate {args.gate} human selection...")

    start_time = time.time()
    gate_key = f"gate{args.gate}"

    while True:
        elapsed = time.time() - start_time
        if elapsed > args.timeout:
            print("[poll_gate] Error: Timeout waiting for selection.")
            sys.exit(1)

        selection = read_json_if_exists(selection_path, {})
        status = read_json_if_exists(status_path, {})

        gates = selection.get("gates", {})
        gate_data = gates.get(gate_key)
        current_state = status.get("state")

        # We proceed if:
        # 1. Selection for the gate is recorded
        # 2. Server status indicates we are "waiting_for_agent"
        if gate_data and current_state == "waiting_for_agent":
            # For Gate 3, it's a list of objects; for Gate 1 & 2, it's a list of strings
            selected = gate_data.get("selected", [])
            print(f"[poll_gate] Success: Gate {args.gate} selection detected! Selected: {selected}")
            sys.exit(0)

        # Print heartbeat every 15 seconds
        if int(elapsed) % 15 < 3:
            print(f"[poll_gate] Polling... (elapsed: {int(elapsed)}s, state: {current_state or 'unknown'})")
            time.sleep(3)
        else:
            time.sleep(3)

if __name__ == "__main__":
    main()
