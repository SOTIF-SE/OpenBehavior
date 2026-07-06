import math
import json
import os

class JudgeByDis:
    def __init__(self, json_data_path):
        self.is_collision = None
        self.timestamp_npc = None
        self.npc_num = None
        self.npc_name = []
        self.trace_data = {}
        self.final_location = {}
        self.ego_trace_date = []
        self.min_dist_to_ego = []
        with open(json_data_path, "r") as f:
            self.json_data = json.load(f)
        self.target_location = None
        self.min_between_vehicles = 0.5
        self.max_to_target = 2.0
        self.scoreA = 0
        self.scoreB = 0
        self.start()

    def start(self):
        self.init_trace_data()
        self.get_is_collision()

    def init_trace_data(self):
        self.timestamp_npc = len(self.json_data["trace"]) - 1

        for i in range(self.timestamp_npc):
            self.min_dist_to_ego.append(self.json_data["trace"][i]["truth"]["minDistToEgo"])

    def is_true_collision(self, ego_location, npc_location, ego_yaw):
        dx = npc_location["x"] - ego_location["x"]
        dy = npc_location["y"] - ego_location["y"]
        yaw = math.radians(ego_yaw)
        fx = math.cos(yaw)
        fy = math.sin(yaw)
        forward_dist = dx * fx + dy * fy
        return forward_dist

    def get_is_collision(self):
        min_distance = float('inf')
        for i in range(self.timestamp_npc):
            if min_distance > self.min_dist_to_ego[i]:
                min_distance = self.min_dist_to_ego[i]
                min_distance_speed = self.json_data["trace"][i]["truth"]["NearestNPCSpeed"]
                min_distance_ego_speed = self.json_data["trace"][i]["ego"]["pose"]["linearVelocity"]
                min_distance_ego_yaw = self.json_data["trace"][i]["ego"]["pose"]["rotation"]["yaw"]
                min_distance_ego_location = self.json_data["trace"][i]["ego"]["pose"]["position"]
                min_distance_npc_location = self.json_data["trace"][i]["truth"]["NearestNPCLocation"]
            if self.min_dist_to_ego[i] < 3.0:
                self.is_collision = True
                break

    def remove_avi(self):
        fileidx = 0
        while os.path.exists("/home/xie/AV-Fuzzer/carla_sim/traffic_accident_video/accident_{}.avi".format(fileidx)):
            fileidx += 1
        video_path = "/home/xie/AV-Fuzzer/carla_sim/traffic_accident_video/accident_{}.avi".format(fileidx - 1)
        if self.is_collision:
            print("It is good")
        else:
            if os.path.exists(video_path):
                print("It is bad")
                os.remove(video_path)