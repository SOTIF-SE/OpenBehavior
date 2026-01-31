import json
import math
import os
import re
import statistics
import time

Record_Path = "/home/abc/scenario_runner/scenario_record/avunit_s4.json"


def load_template(path):
    with open(path, "r") as f:
        return json.load(f)

def save_result(scene, path):
    with open(path, "w") as f:
        json.dump(scene, f, indent=4)

def compute_distance(pos1, pos2):
    return math.sqrt((pos1['x'] - pos2['x']) ** 2 + (pos1['y'] - pos2['y']) ** 2 + (pos1['z'] - pos2['z']) ** 2)

def process_acc(acc):
    return math.sqrt(acc["x"]**2 + acc["y"]**2 + acc["z"]**2)

def calculate_rel_speed(speed1, speed2):
    return math.sqrt((speed2["x"] - speed1["x"])**2 + (speed2["y"] - speed1["y"])**2 + (speed2["z"] - speed1["z"])**2)

def lateral_displacement_with_yaw(p0, p1, yaw_deg):
    dx = p1["x"] - p0["x"]
    dy = p1["y"] - p0["y"]
    psi = math.radians(yaw_deg)
    return dx * (-math.sin(psi)) + dy * math.cos(psi)

def log_data(data, filename="/home/abc/scenario_runner/log.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(data + "\n")

def log_special_data(data, filename="/home/abc/scenario_runner/special_log.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(data + "\n")

# def detect_lane_change(lane_trace_vehicle):
#     change_lane_num = 0
#     for i in range(1, len(lane_trace_vehicle)):
#         # if lane_trace_vehicle[i-1][0] == lane_trace_vehicle[i][0]:
#         if lane_trace_vehicle[i-1] != lane_trace_vehicle[i]:
#                 change_lane_num += 1
#     return change_lane_num

class ScoreForScenario:
    def __init__(self, json_path, gen, idx):
        self.path = json_path
        self.json_data = load_template(json_path)

        self.timestamp = None
        self.npc_num = None
        self.npc_name = []
        self.trace_data = {}
        self.ego_trace_date = []
        self.min_dist_to_ego = []
        self.lane_trace = {}
        self.acc_trace = {}
        self.steer_trace = {}
        self.final_location = {}
        self.target_location = None
        self.min_between_vehicles = 0.5
        self.max_to_target = 2.0

        self.scoreA = 0
        self.scoreB = 0
        self.scoreC = 0
        self.change_lane_times = 0
        self.value = 0

        # record info
        self.record_result_path = Record_Path
        self.gen = gen
        self.idx = idx
        self.initial_data = {}
        self.exist_file = True

        # 评价场景时临时使用的数据
        self.is_collision = False
        self.min_distance = None
        self.min_distance_speed = None
        self.min_distance_ego_speed = None

        # 用于记录的数据
        self.collision_num = None
        self.scenario_num = None
        self.Not_reach_goal = None
        self.violated_num = None
        self.steer_scope_max = None
        self.steer_scope_min = None
        self.average_steer_scope = None
        self.average_ttc = None
        self.average_acc_scope = None
        self.average_change_lane_times = None
        self.acc_scope_max = None
        self.acc_scope_min = None
        self.average_gen_scenario_time = None
        self.average_run_scenario_time = None
        self.average_start_scenario_time = None
        self.average_run_scenario_time_1 = None
        self.min_distance_ego_yaw = None
        self.min_distance_npc_location = None
        self.min_distance_ego_location = None

        self.init_all()

    def init_all(self):
        self.start()
        self.read_record_result()
        self.record_result()
        self.compute_score()

    def read_record_result(self):
        if not os.path.exists(self.record_result_path):
            self.exist_file = False
            return
        with open(self.record_result_path, "r") as f:
            self.initial_data = json.load(f)

    def start(self):
        self.get_target_location()
        self.init_trace_data()
        self.compute_min_between()
        self.compute_max_to()
        self.compute_lane_change_by_is_lane_changing()
        # self.compute_acc_std()

    def record_result(self):
        if self.exist_file:
            self.process_data()
        else:
            self.process_data_first()
        self.remove_avi()

    def process_data_first(self):
        self.init_data_first()
        self.get_is_collision()
        self.get_ttc()
        self.get_average_change_lane_times()
        self.get_acc_scope()
        self.get_steer_scope()
        self.get_violated_num()
        self.change_initial_data()
        self.write_record_result()

    def process_data(self):
        self.init_data()
        self.get_is_collision()
        self.get_ttc()
        self.get_average_change_lane_times()
        self.get_acc_scope()
        self.get_steer_scope()
        self.get_violated_num()
        self.change_initial_data()
        self.write_record_result()

    def init_trace_data(self):
        self.timestamp = len(self.json_data["trace"]) - 1
        self.npc_num = len(self.json_data["trace"][0]["truth"]["obsList"])

        # minDist
        for i in range(self.timestamp):
            self.min_dist_to_ego.append(self.json_data["trace"][i]["truth"]["minDistToEgo"])

        # ego trace
        for l in range(0, self.timestamp):
            self.ego_trace_date.append(self.json_data["trace"][l]["ego"]["pose"]["position"])

        for j in range(self.npc_num):
            self.trace_data[self.json_data["trace"][0]["truth"]["obsList"][j]["name"]] = []
            self.npc_name.append(self.json_data["trace"][0]["truth"]["obsList"][j]["name"])
        for l in range(0, self.timestamp):
            for i in range(0, self.npc_num):
                self.trace_data[self.json_data["trace"][l]["truth"]["obsList"][i]["name"]].append(
                    self.json_data["trace"][l]["truth"]["obsList"][i]["distToEgo"])

        # for lane_change
        for j in range(self.npc_num):
            self.lane_trace[self.json_data["npcList"][j]["ID"]] = []
            for i in range(self.timestamp):
                self.lane_trace[self.json_data["npcList"][j]["ID"]].append(self.json_data["npcList"][j]["motion"][i]["lane_position"]["roadID"])
                if i == self.timestamp - 1:
                    self.final_location[self.json_data["npcList"][j]["ID"]] = self.json_data["npcList"][j]["motion"][i]["location"]
        self.lane_trace["ego"] = []
        for i in range(self.timestamp):
            self.lane_trace["ego"].append(self.json_data["trace"][i]["ego"]["currentLane"]["number"])

        # for acc
        for j in range(self.npc_num):
            self.acc_trace[self.json_data["npcList"][j]["ID"]] = []
            for i in range(self.timestamp):
                self.acc_trace[self.json_data["npcList"][j]["ID"]].append(
                    process_acc(self.json_data["npcList"][j]["motion"][i]["linearAcceleration"]))
        self.acc_trace["ego"] = []
        for i in range(self.timestamp):
            self.acc_trace["ego"].append(
                process_acc(self.json_data["trace"][i]["ego"]["pose"]["linearAcceleration"]))

        # for steer
        self.steer_trace["ego"] = []
        for i in range(self.timestamp):
            self.steer_trace["ego"].append(self.json_data["trace"][i]["ego"]["pose"]["rotation"]["yaw"])

    # 获取ego目标位置
    def get_target_location(self):
        file = "/home/abc/scenario_runner/trace/avunit_s4/trace_avunit_s4_0_-1.json"
        with open(file, "r") as f:
            data = json.load(f)
        self.target_location = data["ego"]["destination"]["location"]

    # 计算与NPC之间最短距离
    def compute_min_between(self):
        min_score_npc = {}
        for npc in self.npc_name:
            min_score = float('inf')
            for t in range(self.timestamp):
                score_npc = self.trace_data[npc][t] - self.min_between_vehicles
                min_score = min(min_score, score_npc)
            min_score_npc[npc] = min_score
        self.scoreA = min(min_score_npc.values()) - 3.0

    # def compute_acc_std(self):
    #     self.scoreC = statistics.stdev(self.acc_trace["ego"])

    def com_final_location(self):
        fin_ego_location = self.ego_trace_date[self.timestamp - 1]
        yaw = self.json_data["trace"][self.timestamp - 1]["ego"]["pose"]["rotation"]["yaw"]
        psi = math.radians(yaw)
        fx = math.cos(psi)
        fy = math.sin(psi)
        destination_dis_dx = self.target_location["x"] - fin_ego_location["x"]
        destination_dis_dy = self.target_location["y"] - fin_ego_location["y"]
        destination_dis = destination_dis_dx * fx + destination_dis_dy * fy
        for i in self.final_location:
            dx = self.final_location[i]["x"] - fin_ego_location["x"]
            dy = self.final_location[i]["y"] - fin_ego_location["y"]
            forward_dist = dx * fx + dy * fy
            lateral_dist = dx * (-fy) + dy * fx
            if 0 < forward_dist <= destination_dis and abs(lateral_dist) < 2.0:
                return True
        return False

    # 计算与终点最长距离
    def compute_max_to(self):
        # 目的地到主车之间有NPC，且NPC距离本车 < 6m
        if self.com_final_location():
            dis = self.max_to_target - compute_distance(self.target_location, self.ego_trace_date[self.timestamp - 1])
        else:
            # 前方无NPC
            dis = self.max_to_target - compute_distance(self.target_location, self.ego_trace_date[self.timestamp - 1]) + 6.0
        self.scoreB = dis

        # 增加log，定位异常数据文件
        if self.scoreB < -12:
            error_path = self.path
            log_special_data(error_path)

        self.scoreB = max(self.scoreB, -12)

    # def compute_lane_change(self):
    #     total_lane_change_num = 0
    #     for c in self.lane_trace:
    #         total_lane_change_num += detect_lane_change(self.lane_trace[c])
    #     self.change_lane_times = total_lane_change_num
    #     self.scoreC = self.change_lane_times

    def compute_lane_change_by_is_lane_changing(self):
        for j in range(self.npc_num):
            flag = 0
            for i in range(self.timestamp):
                if self.json_data["npcList"][j]["motion"][i]["isLaneChanging"] and flag == 0:
                    flag = 1
                    first_location = self.json_data["npcList"][j]["motion"][i]["location"]
                    yaw = self.json_data["npcList"][j]["motion"][i]["yaw"]
                elif self.json_data["npcList"][j]["motion"][i]["isLaneChanging"]:
                    now_location = self.json_data["npcList"][j]["motion"][i]["location"]
                    lateral = lateral_displacement_with_yaw(first_location, now_location, yaw)
                    if abs(lateral) > 3.5 * 0.3:
                        self.change_lane_times += 1
                        first_location = self.json_data["npcList"][j]["motion"][i]["location"]
                        yaw = self.json_data["npcList"][j]["motion"][i]["yaw"]
                else:
                    flag = 0
        flag = 0
        for i in range(self.timestamp):
            if self.json_data["trace"][i]["ego"]["isLaneChanging"] and flag == 0:
                flag = 1
                first_location = self.json_data["trace"][i]["ego"]["pose"]["position"]
                yaw = self.json_data["trace"][i]["ego"]["pose"]["rotation"]["yaw"]
            elif self.json_data["trace"][i]["ego"]["isLaneChanging"]:
                now_location = self.json_data["trace"][i]["ego"]["pose"]["position"]
                lateral = lateral_displacement_with_yaw(first_location, now_location, yaw)
                if abs(lateral) > 3.5 * 0.3:
                    self.change_lane_times += 1
                    first_location = self.json_data["trace"][i]["ego"]["pose"]["position"]
                    yaw = self.json_data["trace"][i]["ego"]["pose"]["rotation"]["yaw"]
            else:
                flag = 0
        self.scoreC = self.change_lane_times

    def compute_score(self):
        if self.scoreB == -12 and not self.is_collision:
            self.value = float('-inf')
            return
        if self.scoreC > 10 and not self.is_collision:
            self.value = float('-inf')
            return
        testtask_rob = min(self.scoreA, self.scoreB) * (-1)
        designtask_score = self.scoreC
        # r = [self.scoreA, self.scoreB, testtask_rob, self.scoreC, testtask_rob * 0.3 + designtask_score * 0.7]
        # log_data(str(r))

        self.value = testtask_rob * 1.0 + designtask_score * 0.1
        # self.value = testtask_rob
        # return testtask_rob


    def init_data_first(self):
        self.average_ttc = 0
        self.scenario_num = 0
        self.collision_num = 0
        self.Not_reach_goal = 0
        self.violated_num = 0
        self.average_change_lane_times = 0
        self.average_gen_scenario_time = 0
        self.average_run_scenario_time = 0
        self.average_run_scenario_time_1 = 0
        self.average_start_scenario_time = 0
        self.average_steer_scope = 0
        self.average_acc_scope = 0
        self.steer_scope_max = float('-inf')
        self.steer_scope_min = float('inf')
        self.acc_scope_max = float('-inf')
        self.acc_scope_min = float('inf')

    def init_data(self):
        self.average_ttc = self.initial_data["average_ttc"]
        self.scenario_num = self.initial_data["scenario_num"]
        self.collision_num = self.initial_data["collision_num"]
        self.Not_reach_goal = self.initial_data["Not_reach_goal"]
        self.violated_num = self.initial_data["violated_num"]
        self.acc_scope_max = self.initial_data["acc_scope_max"]
        self.acc_scope_min = self.initial_data["acc_scope_min"]
        self.steer_scope_max = self.initial_data["steer_scope_max"]
        self.steer_scope_min = self.initial_data["steer_scope_min"]
        self.average_acc_scope = self.initial_data["average_acc_scope"]
        self.average_change_lane_times = self.initial_data["average_change_lane_times"]
        self.average_run_scenario_time = self.initial_data.get("average_run_scenario_time", 0)
        self.average_steer_scope = self.initial_data["average_steer_scope"]

    def get_run_scenario_time(self, run_scenario_time):
        total_run_scenario_time = self.average_run_scenario_time * self.scenario_num
        self.average_run_scenario_time = (total_run_scenario_time + run_scenario_time)/(self.scenario_num+1)
        self.initial_data["average_run_scenario_time"] = self.average_run_scenario_time
        self.write_record_result()

    def write_record_result(self):
        with open(self.record_result_path, "w") as f:
            json.dump(self.initial_data, f, indent=2)

    def get_steer_scope(self):
        steer_scope_max = max(self.steer_scope_max, statistics.stdev(self.steer_trace["ego"]))
        steer_scope_min = min(self.steer_scope_min, statistics.stdev(self.steer_trace["ego"]))
        total_steer_scope = self.average_steer_scope * self.scenario_num
        self.average_steer_scope = (total_steer_scope + statistics.stdev(self.steer_trace["ego"])) / (self.scenario_num + 1)

        self.steer_scope_max = steer_scope_max
        self.steer_scope_min = steer_scope_min

    def get_acc_scope(self):
        max_scope = max(self.acc_scope_max, statistics.stdev(self.acc_trace["ego"]))
        min_scope = min(self.acc_scope_min, statistics.stdev(self.acc_trace["ego"]))
        total_acc_scope = self.average_acc_scope * self.scenario_num
        self.average_acc_scope = (total_acc_scope + statistics.stdev(self.acc_trace["ego"])) / (self.scenario_num + 1)

        self.acc_scope_max = max_scope
        self.acc_scope_min = min_scope

    def get_violated_num(self):
        if self.scoreB < -2:
            self.Not_reach_goal = self.Not_reach_goal + 1
        if self.is_collision or self.scoreB < -2:
            self.violated_num = self.violated_num + 1

    # def calculate_rel_speed(self, npc_v, ego_v, npc_p, ego_p):
    #     rx = npc_p["x"] - ego_p["x"]
    #     ry = npc_p["y"] - ego_p["y"]
    #     rz = npc_p["z"] - ego_p["z"]
    #
    #     vx = npc_v["x"] - ego_v["x"]
    #     vy = npc_v["y"] - ego_v["y"]
    #     vz = npc_v["z"] - ego_v["z"]
    #
    #     rv_dot = rx * vx + ry * vy + rz * vz
    #     v_norm_sq = vx * vx + vy * vy + vz * vz
    #
    #     # # 4. 判定
    #     # if v_norm_sq < eps:
    #     #     return float("inf")  # 相对静止
    #     #
    #     # if rv_dot >= 0:
    #     #     return float("inf")  # 未逼近 ego
    #
    #     # 5. TTC
    #     ttc = -rv_dot / v_norm_sq
    #     return ttc

    def is_true_collision(self, ego_location, npc_location, ego_yaw):
        dx = npc_location["x"] - ego_location["x"]
        dy = npc_location["y"] - ego_location["y"]
        yaw = math.radians(ego_yaw)
        fx = math.cos(yaw)
        fy = math.sin(yaw)
        forward_dist = dx * fx + dy * fy
        return forward_dist

    def get_is_collision(self):
        self.min_distance = float('inf')
        for i in range(self.timestamp):
            if self.min_distance > self.min_dist_to_ego[i]:
                self.min_distance = self.min_dist_to_ego[i]
                self.min_distance_speed = self.json_data["trace"][i]["truth"]["NearestNPCSpeed"]
                self.min_distance_ego_speed = self.json_data["trace"][i]["ego"]["pose"]["linearVelocity"]
                self.min_distance_ego_yaw = self.json_data["trace"][i]["ego"]["pose"]["rotation"]["yaw"]
                self.min_distance_ego_location = self.json_data["trace"][i]["ego"]["pose"]["position"]
                self.min_distance_npc_location = self.json_data["trace"][i]["truth"]["NearestNPCLocation"]
            if self.min_dist_to_ego[i] < 3.0 and self.is_true_collision(self.min_distance_ego_location,
                                                                        self.min_distance_npc_location,
                                                                        self.min_distance_ego_yaw) >= 0:
                self.is_collision = True
                self.collision_num += 1
                break

    def remove_avi(self):
        video_path = "traffic_accident_video/ego_accident_{}_{}.avi".format(self.gen+1, self.idx)
        if self.is_collision or self.scoreB < -5:
            log_data("{}_{}".format(self.gen, self.idx))
        else:
            if os.path.exists(video_path):
                os.remove(video_path)

    def get_ttc(self):
        if self.is_collision:
            ttc = 0
        else:
            rel_speed = calculate_rel_speed(self.min_distance_speed, self.min_distance_ego_speed)
            ttc = self.min_distance / rel_speed
            # ttc = self.calculate_rel_speed(self.min_distance_speed, self.min_distance_ego_speed,
            #                                self.min_distance_npc_location,self.min_distance_ego_location)
        total_ttc = self.average_ttc * self.scenario_num
        self.average_ttc = (total_ttc + ttc)/(self.scenario_num+1)

    def get_average_change_lane_times(self):
        total_change_lane_num = self.average_change_lane_times * self.scenario_num
        self.average_change_lane_times = (total_change_lane_num + self.change_lane_times) / (self.scenario_num + 1)

    def change_initial_data(self):
        self.scenario_num += 1

        self.initial_data["average_ttc"] = self.average_ttc
        self.initial_data["scenario_num"] = self.scenario_num
        self.initial_data["collision_num"] = self.collision_num
        self.initial_data["Not_reach_goal"] = self.Not_reach_goal
        self.initial_data["violated_num"] = self.violated_num

        self.initial_data["average_acc_scope"] = self.average_acc_scope
        self.initial_data["acc_scope_max"] = self.acc_scope_max
        self.initial_data["acc_scope_min"] = self.acc_scope_min

        self.initial_data["steer_scope_max"] = self.steer_scope_max
        self.initial_data["steer_scope_min"] = self.steer_scope_min
        self.initial_data["average_steer_scope"] = self.average_steer_scope

        self.initial_data["average_change_lane_times"] = self.average_change_lane_times
        self.initial_data["average_acc_scope"] = self.average_acc_scope

        # self.initial_data["law_result"] = self.law_result


if __name__ == "__main__":
    file = "/home/abc/scenario_runner/trace/avunit_s4/"
    ai_num = 0
    for filename in sorted(os.listdir(file)):
        if filename == "trace_avunit_s4_0_-1.json":
            continue
        match = re.search(r"trace_avunit_s4_(\d+)_(\d+)\.json", filename)
        gen_value = int(match.group(1))
        idx_value = int(match.group(2))
        config_path = "mutation/generation_{}/ind_{}.json".format(gen_value, idx_value)
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        if filename.endswith(".json"):
            file_path = os.path.join(file, filename)
            start_time = time.time()
            record_s = ScoreForScenario(file_path, 0, 0)
            end_time = time.time()
            print(end_time - start_time)
            testtask_rob = min(record_s.scoreA, record_s.scoreB) * (-1)
            designtask_score = record_s.scoreC
            if record_s.is_collision:
                print(gen_value, idx_value, config_data["npc4"]["model_name"])
                if config_data["npc4"]["model_name"] == "adv_ai_agent":
                    ai_num += 1
                print(record_s.is_collision, record_s.scoreA, record_s.scoreB, testtask_rob, record_s.scoreC, testtask_rob * 1.0 + designtask_score * 0.1)
            # record_s.record_result()
            # print(record_s.acc_scope_max, record_s.acc_scope_min, record_s.average_acc_scope)
