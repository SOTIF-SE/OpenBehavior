import json
import os

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class ScenarioConfigRecord:
    def __init__(self):
        self.ego = {}
        self.config = {}
        self.config_path = "/home/abc/scenario_runner/config/"
        self.index = 1
        map_name = CarlaDataProvider.get_map().name
        map_name = map_name.split('/')[-1]
        self.config['map'] = map_name

    def ego_info_w(self, ego_info):
        self.ego = {
            "name": ego_info["name"],
            "behavior_type": ego_info["behavior_type"],
            "model_name": ego_info["model_name"],
            "hyperparameters": {
                "max_speed": ego_info["max_speed"],
                "max_acc": ego_info["max_acc"]
            },
            "end_position": {
                "lane_id": ego_info["end_lane_id"]
            },
            "start_position": ego_info["start_position"],
            "distance_to_go": ego_info["distance_to_go"],
            "range": {
                "range_lane_start": ego_info["range_lane_start"],
                "range_lane_end": ego_info["range_lane_end"],
                "range_position_start": ego_info["range_position_start"],
                "range_position_end": ego_info["range_position_end"]
            }
        }
        self.config['ego_vehicle'] = self.ego


    def npc_info_w(self, npc_info):
        npc = {
            "name": npc_info["name"],
            "behavior_type": npc_info["behavior_type"],
            "model_name": npc_info["model_name"],
            "hyperparameters": {
                "max_speed": npc_info["max_speed"],
                "max_acc": npc_info["max_acc"]
            },
            "start_position": {
                "lane_id": npc_info["start_lane_id"],
                "position": npc_info["start_position"]
            },
            "end_position": {
                "lane_id": npc_info["end_lane_id"],
                "position": npc_info["end_position"]
            },
            "range": {
                "range_lane_start": npc_info["range_lane_start"],
                "range_lane_end": npc_info["range_lane_end"],
                "range_position_start": npc_info["range_position_start"],
                "range_position_end": npc_info["range_position_end"]
            },
            "orch": npc_info.get("orch", False),
            "change_mode": npc_info.get("change_mode", False)
        }
        self.config['npc'+str(self.index)] = npc
        self.index += 1

    def scenario_mode_w(self, mode):
        self.config["scenario_mode"] = {
            "mode": mode["mode"],
            "choose_num": mode["choose_num"],
            "now_num": mode["now_num"]
        }

    def write_to_json(self):
        fileidx = 0
        while os.path.exists(self.config_path + '{}.json'.format(fileidx)):
            fileidx += 1

        with open(self.config_path +'{}.json'.format(fileidx), 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

