#!/usr/bin/env python
"""
Batch runner for the OpenSCENARIO 2.0 (.osc) scenarios.

For every scenario file it repeats the whole cycle as many times as --repetitions says
(20 by default):

    start CARLA -> load the map -> run the scenario -> (trajectory + video are recorded
    by DataBridge / CameraRecorder inside scenario_runner.py) -> stop CARLA

The recordings are named after the generation and the run number, so nothing is overwritten:

    trace/<file name without extension>/trace_<file stem>_<generation>_<run>.json
    traffic_accident_video/ego_accident_<generation>_<run>.avi

(data_bridge.py strips the .osc extension, so s4_v3.osc writes into trace/s4_v3/)

Every scenario of the batch gets its own generation (--generation is the one of the first scenario,
the following ones get +1), and the run number counts the repetitions of that scenario. Run a later
batch with a higher --generation, otherwise its recordings overwrite the ones of this batch
(the script warns about that at startup).

Both numbers come from the --config_json argument, which has to match
"generation_<n>/ind_<m>.json" (data_bridge.py and camera_recorder.py parse it with that regex,
without it no video is written at all), so this script writes that file itself.

Usage:
    python batch_run_osc.py                                     # 10 scenarios x 20 runs
    python batch_run_osc.py --scenarios s4_v1.osc --repetitions 5
    python batch_run_osc.py --generation 11                     # next batch, no overwriting
    python batch_run_osc.py --keep-carla                        # one CARLA for the whole batch
"""

import argparse
import glob
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time

CARLA_DIR = "/home/abc/Carla"
CARLA_BINARY = os.path.join(CARLA_DIR, "CarlaUE4.sh")
CARLA_ARGS = ["-carla-rpc-port=2000", "-quality-level=Low", "-RenderOffScreen", "-nosound", "-stdout"]
CARLA_PORT = 2000
CARLA_START_TIMEOUT = 180
CARLA_SERVER_TIMEOUT = 120
CARLA_SHUTDOWN_GRACE = 8

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(REPO_DIR, "srunner", "examples")
SCENARIO_RUNNER = os.path.join(REPO_DIR, "scenario_runner.py")
VIDEO_DIR = os.path.join(REPO_DIR, "traffic_accident_video")


def log(message):
    print("[batch %s] %s" % (time.strftime("%H:%M:%S"), message), flush=True)


def natural_sort(names):
    """Sort names by their trailing number, so that _2 comes before _10"""
    def key(name):
        match = re.search(r"(\d+)(?=\D*$)", name)
        return (name[:match.start()], int(match.group(1))) if match else (name, -1)
    return sorted(names, key=key)


def port_is_open(port=CARLA_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def kill_carla():
    """
    Stop a leftover CARLA server of this batch. Only instances that use the port of the batch
    are killed, another CARLA of the user (or of another tool) is left alone
    """
    subprocess.call(["pkill", "-f", "CarlaUE4-Linux-Shipping.*carla-rpc-port=%d" % CARLA_PORT],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if not port_is_open():
            # the port can stay busy (or the next instance run into "Address already in use")
            # for a moment after the process is gone
            time.sleep(CARLA_SHUTDOWN_GRACE)
            return
        time.sleep(1)
    log("WARNING: port %d is still busy" % CARLA_PORT)


CARLA_WAIT_SCRIPT = """
import sys
import time
import carla

port, town, timeout = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
client = carla.Client("127.0.0.1", port)
client.set_timeout(10.0)
deadline = time.time() + timeout
while time.time() < deadline:
    try:
        world = client.get_world()
        if town and town not in world.get_map().name:
            client.load_world(town)
            time.sleep(8)
            world = client.get_world()
            if town not in world.get_map().name:
                print("still", world.get_map().name, flush=True)
                continue
        print("ready:", world.get_map().name, flush=True)
        sys.exit(0)
    except RuntimeError:
        time.sleep(2)
sys.exit(1)
"""


def start_carla(log_path):
    """Start a CARLA server and wait until its RPC port accepts connections"""
    process = subprocess.Popen([CARLA_BINARY] + CARLA_ARGS, cwd=CARLA_DIR,
                               stdout=open(log_path, "w"), stderr=subprocess.STDOUT,
                               start_new_session=True)
    start_time = time.time()
    while time.time() - start_time < CARLA_START_TIMEOUT:
        if process.poll() is not None:
            raise RuntimeError("CARLA exited with code %s, see %s" % (process.returncode, log_path))
        if port_is_open():
            return process
        time.sleep(2)
    raise RuntimeError("CARLA did not listen on port %d within %ds" % (CARLA_PORT, CARLA_START_TIMEOUT))


def wait_for_world(town, timeout=CARLA_SERVER_TIMEOUT):
    """
    Wait until the server answers and the map is loaded. This runs in a child process, the
    CARLA client library can abort the whole process when the server is in a bad state
    """
    command = [sys.executable, "-c", CARLA_WAIT_SCRIPT, str(CARLA_PORT), town, str(timeout)]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        log("WARNING: waiting for the world timed out")
        return False
    if result.returncode != 0:
        log("WARNING: server not usable (%s): %s"
            % (result.returncode, result.stdout.decode(errors="replace").strip()[-200:]))
        return False
    log(result.stdout.decode(errors="replace").strip())
    return True


def stop_carla(process):
    """Stop the CARLA server and wait until the port is free again"""
    if process is not None and process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            pass
    kill_carla()



def trace_path(scenario, generation, run):
    """Where data_bridge.py writes the trajectory of this run"""
    # data_bridge.py strips the .osc extension, so s4_v3.osc writes into trace/s4_v3/
    # scenario_runner.py hands data_bridge.py only the file name of the scenario, so a scenario
    # given with a directory (AVUnit_Osc/s4_v3.osc) also lands in trace/s4_v3/ -- taking the
    # basename here as well, otherwise the file is never found and resume runs everything again
    stem = os.path.splitext(os.path.basename(scenario))[0]
    return os.path.join(REPO_DIR, "trace", stem,
                        "trace_%s_%d_%d.json" % (stem, generation, run))


def video_path(generation, run):
    """Where camera_recorder.py writes the video of this run"""
    return os.path.join(VIDEO_DIR, "ego_accident_%d_%d.avi" % (generation, run))


def run_is_done(scenario, generation, run):
    """
    A run counts as finished when its trajectory file is there. The trace is written at the
    very end of the scenario, after the video was closed, so a lost run leaves nothing behind
    and is repeated on the next start
    """
    path = trace_path(scenario, generation, run)
    return os.path.isfile(path) and os.path.getsize(path) > 0


def load_state(path):
    """Load the status of the runs of previous batches, the recordings are the source of truth"""
    if os.path.isfile(path):
        try:
            with open(path) as state_file:
                return json.load(state_file)
        except ValueError:
            log("WARNING: cannot read %s, starting a new state" % path)
    return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as state_file:
        json.dump(state, state_file, indent=2, sort_keys=True)


def run_scenario(osc_file, config_json, log_path, timeout, extra_args):
    """Run one scenario through scenario_runner.py, logging everything to log_path"""
    # The OSC2 preprocessor resolves the scenario against the repository root, so a plain
    # relative path has to be used here (an absolute one gets prefixed twice)
    command = [sys.executable, SCENARIO_RUNNER, "--sync",
               "--openscenario2", os.path.relpath(osc_file, REPO_DIR),
               "--config_json", config_json] + extra_args
    log(" ".join(command))
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(command, cwd=REPO_DIR, stdout=log_file,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            # scenario_runner.py catches the exceptions itself, so only a hiccup of the
            # simulator (or a hang) makes it exit with a signal or run into the timeout
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            return "timeout"

    with open(log_path) as log_file:
        output = log_file.read()
    # A killed process (the simulator crashing takes the runner down with it) leaves no
    # output at all, as the buffered prints are lost
    if process.returncode < 0 or not output.strip():
        return "crash"

    def log_tail():
        """The interesting lines of the log, the recorder writes a lot of noise"""
        noise = ("camera_recorder", "re.search", "TypeError: expected", "Traceback (most recent call last)")
        lines = [line for line in output.splitlines()
                 if line.strip() and not any(word in line for word in noise)]
        for line in lines[-4:]:
            log("    | %s" % line)

    log_tail()
    if "All scenario tests were passed successfully" in output:
        return "passed"
    if "The scenario cannot be loaded" in output:
        return "load error"
    return "failed"


def execute_run(scenario_file, generation, run, run_dir, args, extra_args, carla_process):
    """
    Run one repetition: (re)start CARLA if needed, load the map, run the scenario and stop
    CARLA again. Returns (status, duration, carla_process)
    """
    start_time = time.time()
    name = os.path.basename(scenario_file)
    carla_log = os.path.join(run_dir, "%s_gen%d_run%02d_carla.log" % (name, generation, run))
    scenario_log = os.path.join(run_dir, "%s_gen%d_run%02d.log" % (name, generation, run))
    config_json = write_config_json(run_dir, generation, run, name)
    status = "crash"
    try:
        if carla_process is None or carla_process.poll() is not None:
            carla_process = start_carla(carla_log)
            if not wait_for_world(args.town):
                stop_carla(carla_process)
                carla_process = None
                raise RuntimeError("CARLA is not usable, restarting it")
        status = run_scenario(scenario_file, config_json, scenario_log, args.timeout, extra_args)
    except Exception as error:      # pylint: disable=broad-except
        log("ERROR in %s: %s" % (name, error))
        status = "crash"
    finally:
        if not args.keep_carla:
            stop_carla(carla_process)
            carla_process = None
    return status, time.time() - start_time, carla_process


def write_config_json(directory, generation, index, scenario):
    """
    Write the generation_<n>/ind_<m>.json that the recorder and the trace builder use
    for the naming of their output files
    """
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "generation_%d" % generation, "ind_%d.json" % index)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as config_file:
        config_file.write('{\n    "scenario": "%s",\n    "generation": %d,\n    "index": %d\n}\n'
                          % (scenario, generation, index))
    return path


def count_existing_recordings(scenarios, generations, repetitions):
    """
    Count the recordings of this batch that already exist and would be overwritten. Runs that
    are skipped because they are already recorded do not count
    """
    existing = 0
    for scenario, generation in zip(scenarios, generations):
        for run in range(repetitions):
            if run_is_done(scenario, generation, run):
                continue
            if os.path.isfile(video_path(generation, run)):
                existing += 1
    return existing


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", default="",
                        help="comma separated list of .osc files (default: all that match --pattern)")
    parser.add_argument("--pattern", default="s4_v*.osc",
                        help="glob used to find the scenarios inside srunner/examples (default: s4_v*.osc)")
    parser.add_argument("--town", default="Town04", help="map the scenarios need (default: Town04)")
    parser.add_argument("--generation", type=int, default=1,
                        help="generation of the first scenario, every following scenario gets +1 "
                             "(default: 1). Use a higher value for a later batch, otherwise its "
                             "recordings overwrite the ones of the previous batch")
    parser.add_argument("--repetitions", type=int, default=20,
                        help="how many times every scenario is run (default: 20), the run number is "
                             "the second part of the recording names")
    parser.add_argument("--retries", type=int, default=2,
                        help="how often a run is repeated when CARLA fails (default: 2)")
    parser.add_argument("--timeout", type=int, default=600, help="timeout of one scenario in seconds")
    parser.add_argument("--logdir", default=os.path.join(REPO_DIR, "batch_logs"),
                        help="where the logs and the generation_<n>/ind_<m>.json files are written")
    parser.add_argument("--no-resume", action="store_true",
                        help="run everything again instead of skipping the runs whose trajectory "
                             "already exists (default: resume where the last batch stopped)")
    parser.add_argument("--keep-carla", action="store_true",
                        help="start CARLA once for the whole batch instead of once per run")
    parser.add_argument("--extra-args", nargs=argparse.REMAINDER, default=[],
                        help="extra arguments passed to scenario_runner.py, has to be the last option, "
                             "e.g.  --extra-args --output --repetitions 1")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.scenarios:
        scenarios = [name.strip() for name in args.scenarios.split(",") if name.strip()]
    else:
        scenarios = natural_sort(os.path.basename(path)
                                 for path in glob.glob(os.path.join(EXAMPLES_DIR, args.pattern)))
    if not scenarios:
        print("no scenario found (pattern: %s, directory: %s)" % (args.pattern, EXAMPLES_DIR))
        return 1

    run_dir = os.path.join(args.logdir, time.strftime("osc_%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    extra_args = list(args.extra_args)

    generations = [args.generation + index for index in range(len(scenarios))]
    existing = count_existing_recordings(scenarios, generations, args.repetitions)
    if existing:
        log("WARNING: %d recordings of this batch already exist and will be overwritten, "
            "use a higher --generation" % existing)

    log("%d scenarios x %d runs, generations %s, logs in %s"
        % (len(scenarios), args.repetitions, generations, run_dir))
    kill_carla()

    state_path = os.path.join(args.logdir, "batch_state.json")
    state = load_state(state_path)

    results = []
    skipped = 0
    carla_process = None
    try:
        for index, scenario in enumerate(scenarios):
            generation = generations[index]
            scenario_path = os.path.join(EXAMPLES_DIR, scenario)
            if not os.path.isfile(scenario_path):
                results.append((scenario, generation, -1, "missing", 0.0))
                log("SKIP %s: file not found" % scenario)
                continue

            for run in range(args.repetitions):
                key = "%s|%d|%d" % (scenario, generation, run)
                if not args.no_resume and run_is_done(scenario, generation, run):
                    skipped += 1
                    status = state.get(key, {}).get("status", "done")
                    results.append((scenario, generation, run, "skipped(%s)" % status, 0.0))
                    log("%s gen=%d run=%d -> skipped, already recorded (%s)"
                        % (scenario, generation, run + 1, status))
                    continue

                log("---- %s  gen=%d  run=%d/%d ----"
                    % (scenario, generation, run + 1, args.repetitions))
                status, duration = "crash", 0.0
                for attempt in range(args.retries + 1):
                    if attempt:
                        log("%s gen=%d run=%d: retry %d/%d after %s"
                            % (scenario, generation, run + 1, attempt, args.retries, status))
                    status, duration, carla_process = execute_run(scenario_path, generation, run, run_dir,
                                                                  args, extra_args, carla_process)
                    if status != "crash":
                        break

                results.append((scenario, generation, run, status, duration))
                state[key] = {"scenario": scenario, "generation": generation, "run": run,
                              "status": status, "duration": round(duration, 1)}
                save_state(state_path, state)
                log("%s gen=%d run=%d -> %-12s (%.0f s)"
                    % (scenario, generation, run + 1, status, duration))
    finally:
        stop_carla(carla_process)

    print("\n================ summary ================")
    counts = {}
    for scenario, generation, _, status, _ in results:
        counts.setdefault((scenario, generation), {})
        counts[(scenario, generation)][status] = counts[(scenario, generation)].get(status, 0) + 1
    for (scenario, generation), statuses in counts.items():
        detail = "  ".join("%s=%d" % (name, value) for name, value in sorted(statuses.items()))
        print("%-24s gen=%-4d %s" % (scenario, generation, detail))
    if skipped:
        print("(%d runs were already recorded and got skipped, --no-resume repeats them)" % skipped)
    print("state:  %s" % state_path)
    print("traces: %s" % os.path.join(REPO_DIR, "trace"))
    print("videos: %s" % VIDEO_DIR)
    print("logs:   %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
