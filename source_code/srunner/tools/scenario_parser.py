#!/usr/bin/env python

# Copyright (c) 2019 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This module provides access to a scenario configuration parser
"""

import glob
import math
import os
import xml.etree.ElementTree as ET

from srunner.scenarioconfigs.scenario_configuration import ScenarioConfiguration, ActorConfigurationData
from srunner.scenarioconfigs.route_scenario_configuration import RouteConfiguration


class ScenarioConfigurationParser(object):

    """
    Pure static class providing access to parser methods for scenario configuration files (*.xml)
    """

    @staticmethod
    def parse_scenario_configuration(scenario_name, config_file_name):
        """
        Parse all scenario configuration files at srunner/examples and the additional
        config files, providing a list of ScenarioConfigurations @return

        If scenario_name starts with "group:" all scenarios that
        have that type are parsed and returned. Otherwise only the
        scenario that matches the scenario_name is parsed and returned.
        """

        list_of_config_files = glob.glob("{}/srunner/examples/*.xml".format(os.getenv('SCENARIO_RUNNER_ROOT', "./")))
        list_of_config_files += glob.glob("{}/srunner/examples/*.xosc".format(os.getenv('SCENARIO_RUNNER_ROOT', "./")))

        if config_file_name != '':
            list_of_config_files.append(config_file_name)

        single_scenario_only = True
        if scenario_name.startswith("group:"):
            single_scenario_only = False
            scenario_name = scenario_name[6:]

        scenario_configurations = []

        for file_name in list_of_config_files:
            if file_name.endswith(".xosc"):
                scenario_configurations.extend(
                    ScenarioConfigurationParser.parse_openscenario_configuration(
                        file_name, scenario_name, single_scenario_only))
                continue

            tree = ET.parse(file_name)

            for scenario in tree.iter("scenario"):

                scenario_config_name = scenario.attrib.get('name', None)
                scenario_config_type = scenario.attrib.get('type', None)

                if single_scenario_only:
                    # Check the scenario is the correct one
                    if scenario_config_name != scenario_name:
                        continue
                else:
                    # Check the scenario is of the correct type
                    if scenario_config_type != scenario_name:
                        continue

                new_config = ScenarioConfiguration()
                new_config.town = scenario.attrib.get('town', None)
                new_config.name = scenario_config_name
                new_config.type = scenario_config_type
                new_config.other_actors = []
                new_config.ego_vehicles = []
                new_config.trigger_points = []

                for weather in scenario.iter("weather"):
                    new_config.weather.cloudiness = float(weather.attrib.get("cloudiness", 0))
                    new_config.weather.precipitation = float(weather.attrib.get("precipitation", 0))
                    new_config.weather.precipitation_deposits = float(weather.attrib.get("precipitation_deposits", 0))
                    new_config.weather.wind_intensity = float(weather.attrib.get("wind_intensity", 0.35))
                    new_config.weather.sun_azimuth_angle = float(weather.attrib.get("sun_azimuth_angle", 0.0))
                    new_config.weather.sun_altitude_angle = float(weather.attrib.get("sun_altitude_angle", 15.0))
                    new_config.weather.fog_density = float(weather.attrib.get("fog_density", 0.0))
                    new_config.weather.fog_distance = float(weather.attrib.get("fog_distance", 0.0))
                    new_config.weather.wetness = float(weather.attrib.get("wetness", 0.0))

                for ego_vehicle in scenario.iter("ego_vehicle"):

                    new_config.ego_vehicles.append(ActorConfigurationData.parse_from_node(ego_vehicle, 'hero'))
                    new_config.trigger_points.append(new_config.ego_vehicles[-1].transform)

                for route in scenario.iter("route"):
                    route_conf = RouteConfiguration()
                    route_conf.parse_xml(route)
                    new_config.route = route_conf

                for other_actor in scenario.iter("other_actor"):
                    new_config.other_actors.append(ActorConfigurationData.parse_from_node(other_actor, 'scenario'))

                scenario_configurations.append(new_config)

        return scenario_configurations

    @staticmethod
    def parse_openscenario_configuration(file_name, scenario_name, single_scenario_only):
        """
        Parse an ASAM OpenSCENARIO 1.0 file into the same ScenarioConfiguration the
        xml scenarios produce: town, entities with their initial poses, and weather.

        Like the xml form, the file describes the initial scene only - the driving
        behaviour comes from the python scenario class. The class is named by the
        scenario_type property of the ego vehicle, because OpenSCENARIO itself has
        no field for it.
        """
        root = ET.parse(file_name).getroot()
        if root.tag != "OpenSCENARIO":
            return []

        header = root.find("FileHeader")
        config_name = header.attrib.get("description", None) if header is not None else None
        logic_file = root.find("RoadNetwork/LogicFile")
        config_type = None

        # the initial poses are the Init teleports, one per entity
        poses = {}
        for private in root.iter("Private"):
            world_position = private.find(".//WorldPosition")
            if world_position is not None:
                poses[private.attrib.get("entityRef", None)] = world_position.attrib

        actors = []
        for scenario_object in root.iter("ScenarioObject"):
            vehicle = scenario_object.find("Vehicle")
            if vehicle is None:
                continue
            properties = {property_tag.attrib.get("name", None): property_tag.attrib.get("value", None)
                          for property_tag in vehicle.iter("Property")}
            if "scenario_type" in properties:
                config_type = properties["scenario_type"]
            pose = poses.get(scenario_object.attrib.get("name", None), {})
            actors.append(ET.Element("actor", {
                "model": vehicle.attrib.get("name", "vehicle.*"),
                "rolename": properties.get("type", "scenario"),
                "x": pose.get("x", "0"),
                "y": pose.get("y", "0"),
                "z": pose.get("z", "0"),
                "yaw": str(math.degrees(float(pose.get("h", 0)))),   # OpenSCENARIO headings are radians
            }))

        if single_scenario_only:
            if config_name != scenario_name:
                return []
        elif config_type != scenario_name:
            return []

        new_config = ScenarioConfiguration()
        new_config.town = logic_file.attrib.get("filepath", None) if logic_file is not None else None
        new_config.name = config_name
        new_config.type = config_type
        new_config.other_actors = []
        new_config.ego_vehicles = []
        new_config.trigger_points = []

        for actor in actors:
            if actor.attrib["rolename"] == "ego_vehicle":
                new_config.ego_vehicles.append(ActorConfigurationData.parse_from_node(actor, 'hero'))
                new_config.trigger_points.append(new_config.ego_vehicles[-1].transform)
            else:
                new_config.other_actors.append(ActorConfigurationData.parse_from_node(actor, 'scenario'))

        ScenarioConfigurationParser.parse_openscenario_weather(root, new_config)
        return [new_config]

    @staticmethod
    def parse_openscenario_weather(root, new_config):
        """
        Apply the Weather of an OpenSCENARIO EnvironmentAction.

        OpenSCENARIO 1.0 has no fields for the wind intensity or the precipitation
        deposits CARLA knows about, so those keep the carla.WeatherParameters
        defaults.
        """
        weather = root.find(".//Weather")
        if weather is None:
            return

        sun = weather.find("Sun")
        if sun is not None:
            new_config.weather.sun_azimuth_angle = math.degrees(float(sun.attrib.get("azimuth", 0)))
            new_config.weather.sun_altitude_angle = math.degrees(float(sun.attrib.get("elevation", 0)))
            new_config.weather.cloudiness = 100.0 - float(sun.attrib.get("intensity", 0)) * 100.0

        precipitation = weather.find("Precipitation")
        if precipitation is not None and precipitation.attrib.get("precipitationType", "dry") != "dry":
            new_config.weather.precipitation = float(precipitation.attrib.get("intensity", 0)) * 100.0
            new_config.weather.precipitation_deposits = 100.0
            new_config.weather.wetness = new_config.weather.precipitation

    @staticmethod
    def get_list_of_scenarios(config_file_name):
        """
        Parse *all* config files and provide a list with all scenarios @return
        """

        list_of_config_files = glob.glob("{}/srunner/examples/*.xml".format(os.getenv('SCENARIO_RUNNER_ROOT', "./")))
        list_of_config_files += glob.glob("{}/srunner/examples/*.xosc".format(os.getenv('SCENARIO_RUNNER_ROOT', "./")))

        if config_file_name != '':
            list_of_config_files.append(config_file_name)

        scenarios = []
        for file_name in list_of_config_files:
            if ".xosc" in file_name:
                tree = ET.parse(file_name)
                scenarios.append("{} (OpenSCENARIO)".format(tree.find("FileHeader").attrib.get('description', None)))
            else:
                tree = ET.parse(file_name)
                for scenario in tree.iter("scenario"):
                    scenarios.append(scenario.attrib.get('name', None))

        return scenarios
