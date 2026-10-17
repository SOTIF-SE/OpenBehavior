#!/usr/bin/env python
"""Batch-run the S4 .osc variants of the language level study.

Each run is executed by source_code/openbehavior_runner.py --openbehavior, the
OpenBehavior entry point of this repository. The runner needs a CARLA server, so the
batch starts one (unless something already listens on the port), waits until it is
reachable, runs every variant the requested number of times and stops the server again.

Before the batch the variants are copied to
source_code/batch_logs/s4_variants/scenarios/ together with the avunit_basic.osc and
adaptive.osc they import, because the .osc compiler resolves an import against the
importing file's own directory (--modules-dir selects where those two come from).

For every run a config json is written to

    source_code/batch_logs/s4_variants/generation_<generation>/ind_<run>.json

because data_bridge.py and camera_recorder.py read the generation and the run number
out of that path. The recordings are named after them:

    experiment_result/openbehavior/s4_trace/trace_s4_trace_<generation>_<run>.json
    source_code/traffic_accident_video/ego_accident_<generation>_<run>.avi

Every variant gets its own generation, so a (generation, run) pair is unique in a
batch. Runs whose trace already exists are skipped, which makes an interrupted batch
resume where it stopped. A state file remembers the generation base and a fingerprint
of the variants, so a changed variant starts a new batch.

Usage:
    python batch_run_s4_variants.py
    python batch_run_s4_variants.py --repetitions 5 --scenarios s4_v1.osc,s4_v3.osc
    python batch_run_s4_variants.py --keep-carla --timeout 900
"""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

HOST = "127.0.0.1"
CARLA_PORT = 2000
CARLA_START_TIMEOUT = 180
CARLA_DIR = "/home/abc/Carla"

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SOURCE_DIR)
VARIANT_DIR = os.path.join(REPO_DIR, "language_level_study", "scripts_with_setting", "OpenBehavior")
RUNNER = os.path.join(SOURCE_DIR, "openbehavior_runner.py")
BATCH_DIR = os.path.join(SOURCE_DIR, "batch_logs", "s4_variants")
LOG_DIR = os.path.join(BATCH_DIR, "logs")
RUN_DIR = os.path.join(BATCH_DIR, "scenarios")
STATE_FILE = os.path.join(BATCH_DIR, "state.json")
VIDEO_DIR = os.path.join(SOURCE_DIR, "traffic_accident_video")
# the only copies in the repository: avunit_basic.osc exists nowhere else, and only
# this adaptive.osc has the avunit_s4 branch the variants ask for
MODULE_DIR = os.path.join(REPO_DIR, "avunit_code", "avunit_scenarios")
MODULES = ("avunit_basic.osc", "adaptive.osc")
# openbehavior_runner.py hardcodes the same directory ("experiment_result/openbehavior/")
TRACE_DIR = os.path.join(REPO_DIR, "experiment_result", "openbehavior", "s4_trace")


def log(message):
    print(message, flush=True)


def natural_sort(names):
    """s4_v2 before s4_v10"""
    def key(name):
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]
    return sorted(names, key=key)


def trace_path(generation, run):
    return os.path.join(TRACE_DIR, "trace_s4_trace_%d_%d.json" % (generation, run))


def fingerprint(paths):
    """Hash of the variant files, so a changed variant starts a new batch"""
    digest = hashlib.sha1()
    for path in paths:
        digest.update(os.path.basename(path).encode())
        with open(path, "rb") as variant_file:
            digest.update(variant_file.read())
    return digest.hexdigest()


def read_state():
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE) as state_file:
                return json.load(state_file)
        except ValueError:
            log("WARNING: cannot read %s, starting a new batch" % STATE_FILE)
    return {}


def write_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as state_file:
        json.dump(state, state_file, indent=2, sort_keys=True)


def used_generations():
    """Generations that already have a recording on disk"""
    used = set()
    for path in glob.glob(os.path.join(VIDEO_DIR, "ego_accident_*.avi")):
        match = re.search(r"ego_accident_(\d+)_\d+\.avi$", os.path.basename(path))
        if match:
            used.add(int(match.group(1)))
    for path in glob.glob(os.path.join(TRACE_DIR, "trace_*.json")):
        match = re.search(r"_(\d+)_(-?\d+)\.json$", os.path.basename(path))
        if match:
            used.add(int(match.group(1)))
    return used


def select_variants(args):
    if args.scenarios:
        names = [name.strip() for name in args.scenarios.split(",") if name.strip()]
        paths = [os.path.join(VARIANT_DIR, name) for name in names]
    else:
        paths = natural_sort(glob.glob(os.path.join(VARIANT_DIR, args.pattern)))
    missing = [path for path in paths if not os.path.isfile(path)]
    for path in missing:
        log("ERROR: no such variant: %s" % path)
    return [] if missing else paths


def stage_variants(variants, modules_dir):
    """Copy the variants next to the modules they import.

    The .osc compiler resolves an import against the importing file's own directory
    (srunner/osc2/osc_preprocess/import_file.py), so the study variants cannot run in
    place: avunit_basic.osc and adaptive.osc are not part of the study directory.
    The staged copies are refreshed on every batch.
    """
    os.makedirs(RUN_DIR, exist_ok=True)
    for module in MODULES:
        source = os.path.join(modules_dir, module)
        if not os.path.isfile(source):
            log("ERROR: %s does not exist (use --modules-dir)" % source)
            return []
        shutil.copyfile(source, os.path.join(RUN_DIR, module))
    staged = []
    for path in variants:
        target = os.path.join(RUN_DIR, os.path.basename(path))
        shutil.copyfile(path, target)
        staged.append(target)
    return staged


def write_config(generation, run):
    """The config path has to match generation_<n>/ind_<m>.json, see the module docstring"""
    path = os.path.join(BATCH_DIR, "generation_%d" % generation, "ind_%d.json" % run)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as config_file:
        json.dump({"map": "Town04"}, config_file, indent=2)
    return path


def port_is_open(port=CARLA_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((HOST, port)) == 0


def start_carla(carla_dir, port):
    binary = os.path.join(carla_dir, "CarlaUE4.sh")
    if not os.path.isfile(binary):
        log("ERROR: %s does not exist, use --carla-dir" % binary)
        return None
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = open(os.path.join(LOG_DIR, "carla.log"), "w")
    log("starting CARLA (%s)" % binary)
    return subprocess.Popen(
        ["bash", binary, "-carla-rpc-port=%d" % port, "-quality-level=Low",
         "-RenderOffScreen", "-nosound", "-stdout"],
        cwd=carla_dir, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)


def wait_for_carla(port, timeout=CARLA_START_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_is_open(port):
            log("CARLA is ready on port %d" % port)
            return True
        time.sleep(2)
    return False


def stop_carla(process, port):
    subprocess.call(["pkill", "-f", "CarlaUE4.*carla-rpc-port=%d" % port],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if process is None:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def run_variant(variant, generation, run, args):
    """Run one scenario through openbehavior_runner.py, return the run status"""
    config = write_config(generation, run)
    name = os.path.splitext(os.path.basename(variant))[0]
    log_file_path = os.path.join(LOG_DIR, "%s_%d_%d.log" % (name, generation, run))
    command = [sys.executable, RUNNER, "--sync", "--openbehavior", variant,
               "--config_json", config] + args.extra_args
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(log_file_path, "w") as log_file:
        log("  %s run %-2d -> %s" % (name, run, log_file_path))
        process = subprocess.Popen(command, cwd=SOURCE_DIR, stdout=log_file,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            return "timeout"
    if process.returncode != 0:
        return "exit %d" % process.returncode
    if not os.path.isfile(trace_path(generation, run)):
        return "no trace"
    return "ok"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pattern", default="s4_v*.osc",
                        help="glob of the variants inside "
                             "language_level_study/scripts_with_setting/OpenBehavior "
                             "(default: s4_v*.osc)")
    parser.add_argument("--scenarios", default="",
                        help="comma separated variant file names, overrides --pattern")
    parser.add_argument("--repetitions", type=int, default=20,
                        help="how many times every variant is run (default: 20)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="timeout of one run in seconds (default: 600)")
    parser.add_argument("--carla-dir", default=CARLA_DIR,
                        help="directory holding CarlaUE4.sh (default: %s)" % CARLA_DIR)
    parser.add_argument("--modules-dir", default=MODULE_DIR,
                        help="directory holding avunit_basic.osc and adaptive.osc "
                             "(default: %s)" % MODULE_DIR)
    parser.add_argument("--port", type=int, default=CARLA_PORT,
                        help="CARLA rpc port (default: %d)" % CARLA_PORT)
    parser.add_argument("--keep-carla", action="store_true",
                        help="leave the CARLA started by this script running")
    parser.add_argument("--new-batch", action="store_true",
                        help="ignore the state and start with fresh generations")
    parser.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[],
                        help="extra arguments forwarded to openbehavior_runner.py")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        import carla  # pylint: disable=unused-import
    except ImportError:
        log("ERROR: this interpreter (%s) cannot import carla, use the one of your carla "
            "environment (conda env 'scen')" % sys.executable)
        return 1

    variants = select_variants(args)
    if not variants:
        log("ERROR: no variant matches %s" % os.path.join(VARIANT_DIR, args.pattern))
        return 1

    names = [os.path.basename(path) for path in variants]
    state = {} if args.new_batch else read_state()
    batch_fingerprint = fingerprint(variants)
    if not state.get("generation") or state.get("fingerprint") != batch_fingerprint:
        generation = max(used_generations() or {0}) + 1
        write_state({"generation": generation, "fingerprint": batch_fingerprint,
                     "scenarios": names, "repetitions": args.repetitions,
                     "created": time.strftime("%Y-%m-%d %H:%M:%S")})
        log("new batch: %d variants, generations %d..%d"
            % (len(names), generation, generation + len(names) - 1))
    else:
        generation = state["generation"]
        log("continuing the batch of %s: generations %d..%d"
            % (state.get("created", "?"), generation, generation + len(names) - 1))

    run_variants = stage_variants(variants, args.modules_dir)
    if not run_variants:
        return 1

    pending = [(index, variant, run) for index, variant in enumerate(run_variants)
               for run in range(args.repetitions)
               if not os.path.isfile(trace_path(generation + index, run))]
    total = len(variants) * args.repetitions
    if not pending:
        log("nothing to do: all %d runs are already recorded" % total)
        return 0
    log("%d of %d runs still to do" % (len(pending), total))

    carla_process = None
    started_here = False
    if port_is_open(args.port):
        log("using the CARLA already listening on port %d" % args.port)
    else:
        carla_process = start_carla(args.carla_dir, args.port)
        if carla_process is None:
            return 1
        started_here = True
        if not wait_for_carla(args.port):
            log("ERROR: CARLA did not become reachable within %d s (see %s)"
                % (CARLA_START_TIMEOUT, os.path.join(LOG_DIR, "carla.log")))
            stop_carla(carla_process, args.port)
            return 1

    results = []
    try:
        for index, variant, run in pending:
            status = run_variant(variant, generation + index, run, args)
            results.append((os.path.basename(variant), generation + index, run, status))
            log("    -> %s" % status)
    finally:
        if started_here and not args.keep_carla:
            log("stopping CARLA")
            stop_carla(carla_process, args.port)

    failed = [result for result in results if result[3] != "ok"]
    log("")
    log("%d runs executed, %d failed" % (len(results), len(failed)))
    for name, run_generation, run, status in failed:
        log("  FAILED %s generation %d run %d: %s" % (name, run_generation, run, status))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
