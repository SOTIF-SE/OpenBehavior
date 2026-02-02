#!/usr/bin/env python3

import carla

import os
import psutil
import shutil
import signal
import time
import random
import math
import json
import subprocess
from multiprocessing import Process
import docker
from websocket import create_connection

HOME = os.environ["HOME"]

host = '127.0.0.1'
port = 2000

Carla_Python_Path = "/home/abc/Carla/PythonAPI/carla/agents:/home/abc/Carla/PythonAPI/carla"

env_dict_apollo = {}
env_dict_apollo[
    "PATH"] = "/apollo/bazel-bin/modules/tools/visualizer:/apollo/bazel-bin/cyber/tools/cyber_launch:/apollo/bazel-bin/cyber/tools/cyber_service:/apollo/bazel-bin/cyber/tools/cyber_node:/apollo/bazel-bin/cyber/tools/cyber_channel:/apollo/bazel-bin/cyber/tools/cyber_monitor:/apollo/bazel-bin/cyber/tools/cyber_recorder:/apollo/bazel-bin/cyber/mainboard:/usr/local/cuda/bin:/opt/apollo/sysroot/bin:/usr/local/nvidia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/apollo/scripts:/usr/local/qt5/bin"

env_dict_bridge = {}
env_dict_bridge[
    "PATH"] = "/apollo/bazel-bin/cyber:/apollo/bazel-bin/cyber/tools/cyber_recorder:/apollo/bazel-bin/cyber/tools/cyber_monitor:/apollo/cyber/tools/cyber_launch:/apollo/cyber/tools/cyber_channel:/apollo/cyber/tools/cyber_node:/apollo/cyber/tools/cyber_service:/usr/local/Qt5.5.1/5.5/gcc_64/bin:/apollo/bazel-bin/modules/tools/visualizer:/apollo/bazel-bin/modules/experiment_result/tools/rosbag_to_record:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
env_dict_bridge[
    "PYTHONPATH"] = "/root/carla_apollo_bridge_13/carla-python-0.9.13/carla:/root/carla_apollo_bridge_13/carla-python-0.9.13/carla/dist/carla-0.9.13-py2.7-linux-x86_64.egg:/apollo/py_proto:/apollo/bazel-bin/cyber/py_wrapper:/apollo/cyber/python:"
env_dict_bridge["CYBER_PATH"] = "/apollo/cyber"
env_dict_bridge["CARLA_PYTHON_ROOT"] = "/root/carla_apollo_bridge_13/carla-python-0.9.13"


def carla_is_running():
    for proc in psutil.process_iter():
        if "CarlaUE4.sh" in proc.name():
            return True
    return False


def run_carla():
    CARLA_ROOT = "/home/abc/Carla"
    subprocess.run(["bash", CARLA_ROOT + "/CarlaUE4.sh", "-quality-level=low", "-fps=20", "-Resx=600", "-Resy=480"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def change_carla_map(data_map):
    carla_client = carla.Client(host, port)
    carla_world = carla_client.get_world()
    carla_map = carla_world.get_map()

    if data_map is None or data_map == "":
        data_map = "Town01"
    if carla_map.name != "Carla/Maps/" + data_map:
        carla_client.load_world(data_map)
        print("Loading Carla {}...".format(data_map))
        time.sleep(3)


def run_manual_control(container):
    cmd = ["bash", "-c", "source /apollo/cyber/setup.bash && python examples/manual_control.py --rolename ego_vehicle"]
    _, output = container.exec_run(cmd, user='root',
                                   stdin=True,
                                   stream=True,
                                   environment=env_dict_bridge,
                                   workdir="/root/carla_apollo_bridge_13")
    # for sub_output in output:
    #    print(sub_output.decode(), end='')


def run_bridge(container):
    cmd = ["bash", "-c", "source /apollo/cyber/setup.bash && python carla_cyber_bridge/run_bridge.py"]
    _, output = container.exec_run(cmd, user='root',
                                   stdin=True,
                                   stream=True,
                                   environment=env_dict_bridge,
                                   workdir="/root/carla_apollo_bridge_13")
    for sub_output in output:
        print(sub_output.decode(), end='')


def start_all_modules():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "SETUP_MODE"}))
    print("All modules are started.")
    apollo_socket.close()


def reset_all_modules():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "RESET_MODE"}))
    print("All modules are reset.")
    apollo_socket.close()


def start_one_module(module):
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "START_MODULE", 'value': module}))
    print("Module", module, "is started.")
    apollo_socket.close()


def reset_one_module(module):
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "STOP_MODULE", 'value': module}))
    print("Module", module, "is reset.")
    apollo_socket.close()


def enter_auto_mode():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "ENTER_AUTO_MODE"}))
    print("Enter auto mode.")
    # print(apollo_socket.recv())
    apollo_socket.close()


def change_mode():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "CHANGE_MODE", 'value': "Mkz Lgsvl"}))
    print("Mode changed to: Mkz Lgsvl")
    # print(apollo_socket.recv())
    apollo_socket.close()


def change_map(map_name):
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "CHANGE_MAP", 'value': map_name}))
    print("Map changed to:", map_name)
    # print(apollo_socket.recv())
    apollo_socket.close()


def change_vehicle():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIAction', 'action': "CHANGE_VEHICLE", 'value': "Lincoln2017MKZ LGSVL"}))
    print("Vehicle change to: Lincoln2017MKZ LGSVL")
    # print(apollo_socket.recv())
    apollo_socket.close()


def get_HMIStatus():
    apollo_socket = create_connection("ws://localhost:8888/websocket")
    apollo_socket.send(json.dumps({'type': 'HMIStatus'}))
    print("Get HMIStatus:")
    print(apollo_socket.recv())
    apollo_socket.close()


def get_current_transform(world):
    for vehicle in world.get_actors().filter('*vehicle*'):
        if vehicle.attributes['role_name'] == "hero" or vehicle.attributes['role_name'] == "ego_vehicle":
            return vehicle.get_transform()


def get_random_transform(world):
    spawn_points = world.get_map().get_spawn_points()
    return random.choice(spawn_points)


def start_pro(config_file_name):
    client = docker.from_env()
    container = client.containers.get("apollo_dev_root")

    # Start Apollo
    if container.status == "exited":
        container.start()
        time.sleep(5)
        print("Container", container.name, "has been started.")
    elif container.status == "running":
        print("Container", container.name, "is already running.")
    else:
        print("Unknown container status:", container.status)
        exit()

    # Start Dreamview
    cmd = "bash /apollo/scripts/bootstrap.sh restart"
    _, output = container.exec_run(cmd, user='root',
                                   stdin=True,
                                   stream=True,
                                   environment=env_dict_apollo)
    for sub_output in output:
        print(sub_output.decode(), end='')

    # Initiate Apollo
    change_mode()
    change_vehicle()
    for module in ["Routing", "Localization", "Prediction", "Planning", "Control"]:
        start_one_module(module)

    # Start Carla
    if not carla_is_running():
        print("Starting Carla...")
        carla_process = Process(target=run_carla)
        carla_process.start()
        time.sleep(13)

    with open(HOME + "/scenario_runner/judgement/mutation/" + config_file_name) as trace_file:
        data = json.load(trace_file)
        data_map = data["map"]

    change_carla_map_process = Process(target=change_carla_map, args=(data_map,))
    change_carla_map_process.start()
    change_carla_map_process.join()

    container_bridge = client.containers.get("carla-apollo-13")
    if container_bridge.status == "exited":
        container_bridge.start()
        time.sleep(5)
        print("Container", container_bridge.name, "has been started.")
    elif container_bridge.status == "running":
        print("Container", container_bridge.name, "is already running.")
    else:
        print("Unknown container status:", container_bridge.status)
        exit()

    # Spawn the ego vehicle
    print("Spawning ego...")
    manual_control_process = Process(target=run_manual_control, args=(container_bridge,))
    manual_control_process.start()
    time.sleep(7)

    # Start the bridge
    print("Starting bridge...")
    bridge_process = Process(target=run_bridge, args=(container_bridge,))
    bridge_process.start()
    time.sleep(6)

    # Reload map
    change_map("Carla Town01")
    time.sleep(3)
    change_map("Carla " + data_map)
    time.sleep(3)
    for module in ["Routing", "Localization", "Prediction", "Planning", "Control"]:
        start_one_module(module)
    time.sleep(3)

    # Setup scenario runner
    print("Starting srunner...")

def stop_all():
    client = docker.from_env()
    container = client.containers.get("apollo_dev_root")
    container_bridge = client.containers.get("carla-apollo-13")

    container_bridge.stop()

    # Stop Carla
    for proc in psutil.process_iter():
        if "CarlaUE4" in proc.name():
            proc.kill()

    # stop DreamView
    cmd = "bash /apollo/scripts/bootstrap.sh stop"
    _, output = container.exec_run(cmd, user='root',
                                stdin=True,
                                stream=True,
                                environment=env_dict_apollo)