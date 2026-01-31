#!/usr/bin/env python

# Copyright (c) 2018-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This module provides the ScenarioManager implementation.
It must not be modified and is for reference only!
"""

from __future__ import print_function

import re
import sys
import time
from carla import Transform, Location, Rotation, TrafficLightState
import math
import json
from websocket import create_connection
import os

import py_trees

from srunner.autoagents.agent_wrapper import AgentWrapper
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.result_writer import ResultOutputProvider
from srunner.scenariomanager.timer import GameTime
from srunner.scenariomanager.watchdog import Watchdog

from camera_recorder.camera_recorder import CameraRecorder

def load_template(path="/home/abc/scenario_runner/scenario_record/avunit_s4_extra_time.json"):
    with open(path, "r") as f:
        return json.load(f)

def save_result(scene, path="/home/abc/scenario_runner/scenario_record/avunit_s4_extra_time.json"):
    with open(path, "w") as f:
        json.dump(scene, f, indent=4)


class ScenarioManager(object):

    """
    Basic scenario manager class. This class holds all functionality
    required to start, and analyze a scenario.

    The user must not modify this class.

    To use the ScenarioManager:
    1. Create an object via manager = ScenarioManager()
    2. Load a scenario via manager.load_scenario()
    3. Trigger the execution of the scenario manager.run_scenario()
       This function is designed to explicitly control start and end of
       the scenario execution
    4. Trigger a result evaluation with manager.analyze_scenario()
    5. If needed, cleanup with manager.stop_scenario()
    """

    def __init__(self, debug_mode=False, sync_mode=False, timeout=2.0):
        """
        Setups up the parameters, which will be filled at load_scenario()

        """
        self.config_json_path = None
        self.scenario = None
        self.scenario_tree = None
        self.scenario_class = None
        self.ego_vehicles = None
        self.other_actors = None

        self._debug_mode = debug_mode
        self._agent = None
        self._sync_mode = sync_mode
        self._watchdog = None
        self._timeout = timeout

        self._running = False
        self._timestamp_last_run = 0.0
        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None

        self.data_bridge = None
        self.able_data = None

    def _reset(self):
        """
        Reset all parameters
        """
        self._running = False
        self._timestamp_last_run = 0.0
        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None
        GameTime.restart()

    def cleanup(self):
        """
        This function triggers a proper termination of a scenario
        """

        if self._watchdog is not None:
            self._watchdog.stop()
            self._watchdog = None

        if self.scenario is not None:
            self.scenario.terminate()

        if self._agent is not None:
            self._agent.cleanup()
            self._agent = None

        CarlaDataProvider.cleanup()

    def load_scenario(self, scenario, agent=None, config_json=None):
        """
        Load a new scenario
        """
        self._reset()
        self._agent = AgentWrapper(agent) if agent else None
        if self._agent is not None:
            self._sync_mode = True
        self.scenario_class = scenario
        self.scenario = scenario.scenario
        self.scenario_tree = self.scenario.scenario_tree
        self.ego_vehicles = scenario.ego_vehicles
        self.other_actors = scenario.other_actors
        self.config_json_path = config_json
        self.data_bridge.set_actors(self.ego_vehicles[0], self.other_actors)

        # To print the scenario tree uncomment the next line
        # py_trees.display.render_dot_tree(self.scenario_tree)

        if self._agent is not None:
            self._agent.setup_sensors(self.ego_vehicles[0], self._debug_mode)

    def set_camera(self):
        world = CarlaDataProvider.get_world()
        if world:
            spectator = world.get_spectator()
        if len(self.other_actors) > 0:
            ACTOR_ID = 0
            CAMERA_DIST = 40
            if ACTOR_ID == 0:
                npc_location = self.ego_vehicles[0].get_transform().location
                npc_rotation = self.ego_vehicles[0].get_transform().rotation
            else:
                npc_location = self.other_actors[ACTOR_ID-1].get_transform().location
                npc_rotation = self.other_actors[ACTOR_ID-1].get_transform().rotation
            if spectator and npc_location and npc_rotation:
                npc_forward_vector = npc_rotation.get_forward_vector() * CAMERA_DIST
                npc_up_vector = npc_rotation.get_up_vector() * CAMERA_DIST
                spectator.set_transform(Transform(npc_location - npc_forward_vector + npc_up_vector, Rotation(pitch=-45, yaw=npc_rotation.yaw)))

    def get_ego_info_from_data(self):
        # path = self.config_json_path
        # if path is not None:
        #     match = re.search(r"generation_(\d+)/ind_(\d+)\.json", path)
        #     gen_value = int(match.group(1))
        #     idx_value = int(match.group(2))
        #     file = "/home/abc/scenario_runner/trace/test_script/trace_test_script_/{}_{}.json".format(gen_value-1, idx_value)
        # else:
        #     print("Error! Need data json")
        #     exit(0)
        file = "/home/abc/scenario_runner/trace/avunit_s4/trace_avunit_s4_0_-1.json"
        with open(file, "r") as f:
            data = json.load(f)
        self.able_data = data

    def send_routing_request_apollo(self, waypoints = []):
        world = CarlaDataProvider.get_world()
        ego_vehicle = self.ego_vehicles[0]
        start_transform = ego_vehicle.get_transform()
        correcting_vector = start_transform.get_forward_vector()
        shift = 1.355
        start_location = start_transform.location - shift * correcting_vector

        self.get_ego_info_from_data()
        lane_position_destination = self.able_data["ego"]["destination"]['lane_position']
        end_location = world.get_map().get_waypoint_xodr(
            int(lane_position_destination['lane'].replace("lane_", "")),
            lane_position_destination['roadID'],
            lane_position_destination['offset']
        ).transform.location

        apollo_socket = create_connection("ws://localhost:8888/websocket")
        apollo_socket.send(json.dumps({\
            'type': 'SendRoutingRequest',\
            'start': {\
                'x': start_location.x,\
                'y': -start_location.y,\
                'z': start_location.z,\
                'heading': math.radians(-start_transform.rotation.yaw)\
            },\
            'end': {\
                'x': end_location.x,\
                'y': -end_location.y,\
                'z': end_location.z,\
            },\
            'waypoint':waypoints\
        }))
        # print(apollo_socket.recv())
        apollo_socket.close()

    def ego_arrived(self, arrive_distance = 8.0):
        world = CarlaDataProvider.get_world()
        ego_location = self.ego_vehicles[0].get_location()
        if self.able_data:
            lane_position_destination = self.able_data["ego"]["destination"]['lane_position']
            dest_location = world.get_map().get_waypoint_xodr(
                int(lane_position_destination['lane'].replace("lane_", "")),
                lane_position_destination['roadID'],
                lane_position_destination['offset']
            ).transform.location
        elif self._agent:
            dest_location = self._agent._agent.destination
        else:
            return False
        distance = dest_location.distance(ego_location)
        return distance <= arrive_distance

    def run_scenario(self):
        """
        Trigger the start of the scenario and wait for it to finish/fail
        """
        print("ScenarioManager: Running scenario {}".format(self.scenario_tree.name))
        self.start_system_time = time.time()
        start_game_time = GameTime.get_time()

        self._watchdog = Watchdog(float(self._timeout))
        self._watchdog.start()
        self._running = True

        tick_counter = 0
        start_tick_threshold = 10
        world = CarlaDataProvider.get_world()
        recorder = CameraRecorder(world, self.ego_vehicles[0], self.config_json_path)
        recorder.start()
        while self._running:
            timestamp = None
            world = CarlaDataProvider.get_world()
            if world:
                snapshot = world.get_snapshot()
                if snapshot:
                    timestamp = snapshot.timestamp
            if timestamp:
                self._tick_scenario(timestamp)
                if tick_counter == start_tick_threshold:
                    self.data_bridge.update_ego_vehicle_start()
                    self.data_bridge.update_npc_vehicle_start()
                    self.send_routing_request_apollo()
                    self.set_camera()
                elif tick_counter > start_tick_threshold:
                    self.data_bridge.update_trace()
                    self.data_bridge.update_npc_vehicle_motion()
                    self.set_camera()
                # End the scenario once the ego vehicle has arrived
                if self.ego_arrived():
                    self.stop_scenario()

                tick_counter += 1

        self.cleanup()
        recorder.stop_camera()

        self.end_system_time = time.time()
        end_game_time = GameTime.get_time()

        self.scenario_duration_system = self.end_system_time - \
            self.start_system_time
        self.scenario_duration_game = end_game_time - start_game_time

        if os.path.exists("/home/abc/scenario_runner/scenario_record/avunit_s4_extra_time.json"):
            time_data = load_template()
        else:
            time_data = {}
        time_data["average_run_scenario_time_1"] = ((time_data.get("average_run_scenario_time_1", 0) * time_data.get("scenario_num", 0)
                                                     + self.scenario_duration_system)/(time_data.get("scenario_num", 0)+1))
        save_result(time_data)


        if self.scenario_tree.status == py_trees.common.Status.FAILURE:
            print("ScenarioManager: Terminated due to failure")

    def _tick_scenario(self, timestamp):
        """
        Run next tick of scenario and the agent.
        If running synchornously, it also handles the ticking of the world.
        """

        if self._timestamp_last_run < timestamp.elapsed_seconds and self._running:
            self._timestamp_last_run = timestamp.elapsed_seconds

            self._watchdog.update()

            if self._debug_mode:
                print("\n--------- Tick ---------\n")

            # Update game time and actor information
            GameTime.on_carla_tick(timestamp)
            CarlaDataProvider.on_carla_tick()

            if self._agent is not None:
                ego_action = self._agent()  # pylint: disable=not-callable

            if self._agent is not None:
                self.ego_vehicles[0].apply_control(ego_action)

            # Tick scenario
            self.scenario_tree.tick_once()

            if self._debug_mode:
                print("\n")
                py_trees.display.print_ascii_tree(self.scenario_tree, show_status=True)
                sys.stdout.flush()

            if self.scenario_tree.status != py_trees.common.Status.RUNNING:
                self._running = False

        if self._sync_mode and self._running and self._watchdog.get_status():
            CarlaDataProvider.get_world().tick()

    def get_running_status(self):
        """
        returns:
           bool:  False if watchdog exception occured, True otherwise

        """
        return self._watchdog.get_status()

    def stop_scenario(self):
        """
        This function is used by the overall signal handler to terminate the scenario execution
        """
        self._running = False

    def analyze_scenario(self, stdout, filename, junit, json):
        """
        This function is intended to be called from outside and provide
        the final statistics about the scenario (human-readable, in form of a junit
        report, etc.)
        """

        failure = False
        timeout = False
        result = "SUCCESS"

        if self.scenario.test_criteria is None:
            print("Nothing to analyze, this scenario has no criteria")
            return True

        for criterion in self.scenario.get_criteria():
            if (not criterion.optional and
                    criterion.test_status != "SUCCESS" and
                    criterion.test_status != "ACCEPTABLE"):
                failure = True
                result = "FAILURE"
            elif criterion.test_status == "ACCEPTABLE":
                result = "ACCEPTABLE"

        if self.scenario.timeout_node.timeout and not failure:
            timeout = True
            result = "TIMEOUT"

        output = ResultOutputProvider(self, result, stdout, filename, junit, json)
        output.write()

        return failure or timeout
