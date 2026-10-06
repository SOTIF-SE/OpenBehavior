import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT_DIR = os.path.join(REPO_DIR, "source_code/OpenBehavior_Osc")
BATCH_RUNNER = os.path.join(REPO_DIR, "batch_run_osc.py")
VIDEO_DIR = os.path.join(REPO_DIR, "traffic_accident_video")
STATE_FILE = os.path.join(REPO_DIR, "batch_logs", "s4_variants_state.json")
CARLA_PORT = 2000


def load_batch_runner():
    """batch_run_osc.py, which does the actual work (CARLA per run, recordings, resume)"""
    spec = importlib.util.spec_from_file_location("batch_run_osc", BATCH_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def port_is_open(port=CARLA_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def fingerprint(paths):
    """Hash of the variant files, so a changed variant starts a new batch"""
    digest = hashlib.sha1()
    for path in paths:
        digest.update(os.path.basename(path).encode())
        with open(path, "rb") as scenario_file:
            digest.update(scenario_file.read())
    return digest.hexdigest()


def used_generations():
    """Generations that already have a recording on disk (video and trace are named after them)"""
    used = set()
    for path in glob.glob(os.path.join(VIDEO_DIR, "ego_accident_*.avi")):
        match = re.search(r"ego_accident_(\d+)_\d+\.avi$", os.path.basename(path))
        if match:
            used.add(int(match.group(1)))
    for path in glob.glob(os.path.join(REPO_DIR, "trace", "*", "trace_*.json")):
        match = re.search(r"_(\d+)_(-?\d+)\.json$", os.path.basename(path))
        if match:
            used.add(int(match.group(1)))
    return used


def read_state():
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE) as state_file:
                return json.load(state_file)
        except ValueError:
            print("WARNING: cannot read %s, starting a new batch" % STATE_FILE)
    return {}


def write_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as state_file:
        json.dump(state, state_file, indent=2, sort_keys=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pattern", default="avunit_s4_v*.osc",
                        help="glob of the variants inside AVUnit_Osc (default: avunit_s4_v*.osc)")
    parser.add_argument("--repetitions", type=int, default=20,
                        help="how many times every variant is run (default: 20)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="timeout of one run in seconds (default: 600)")
    parser.add_argument("--retries", type=int, default=2,
                        help="how often a failed run is repeated (default: 2)")
    parser.add_argument("--keep-carla", action="store_true",
                        help="one CARLA for the whole batch instead of one per run")
    parser.add_argument("--new-batch", action="store_true",
                        help="ignore the state and start with fresh generations, the recordings "
                             "of the previous batch are kept")
    parser.add_argument("--force", action="store_true",
                        help="start even if another CARLA listens on the port (the batch kills it)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        import carla  # pylint: disable=unused-import
    except ImportError:
        print("ERROR: this interpreter (%s) cannot import carla, use the one of your carla "
              "environment (conda env 'scen')" % sys.executable)
        return 1

    batch_runner = load_batch_runner()
    paths = batch_runner.natural_sort(glob.glob(os.path.join(VARIANT_DIR, args.pattern)))
    names = [os.path.basename(path) for path in paths]
    if not names:
        print("ERROR: no variant matches %s" % os.path.join(VARIANT_DIR, args.pattern))
        return 1

    # A batch keeps its generations, they are part of the recording names and of the resume
    state = {} if args.new_batch else read_state()
    batch_fingerprint = fingerprint(paths)
    if not state.get("generation") or state.get("fingerprint") != batch_fingerprint:
        generation = max(used_generations() or {0}) + 1
        write_state({"generation": generation, "fingerprint": batch_fingerprint,
                     "scenarios": names, "repetitions": args.repetitions,
                     "created": time.strftime("%Y-%m-%d %H:%M:%S")})
        print("new batch: %d variants, generations %d..%d"
              % (len(names), generation, generation + len(names) - 1))
    else:
        generation = state["generation"]
        recorded = sum(1 for index, name in enumerate(names) for run in range(args.repetitions)
                       if os.path.isfile(batch_runner.trace_path(name, generation + index, run)))
        print("continuing the batch of %s: generations %d..%d, %d of %d runs are recorded and "
              "will be skipped" % (state.get("created", "?"), generation,
                                   generation + len(names) - 1, recorded,
                                   len(names) * args.repetitions))

    if port_is_open() and not args.force:
        print("ERROR: port %d is already in use, another CARLA is running. Stop it first (a batch "
              "would kill it), or pass --force" % CARLA_PORT)
        return 1

    command = [sys.executable, BATCH_RUNNER,
               "--scenarios", ",".join(os.path.relpath(path, batch_runner.EXAMPLES_DIR)
                                       for path in paths),
               "--generation", str(generation),
               "--repetitions", str(args.repetitions),
               "--timeout", str(args.timeout),
               "--retries", str(args.retries)]
    if args.keep_carla:
        command.append("--keep-carla")
    print(" ".join(command), flush=True)
    return subprocess.call(command, cwd=REPO_DIR)


if __name__ == "__main__":
    sys.exit(main())
