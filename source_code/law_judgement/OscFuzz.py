import json
import math
import os
import shutil
import sys

import random
import copy
from random import gauss

import subprocess
import time

import numpy as np

from score_for_scenario import ScoreForScenario
from law_judgement_extra import Monitor
import start_docker

def load_template(path):
    with open(path, "r") as f:
        return json.load(f)

def save_result(scene, path):
    with open(path, "w") as f:
        json.dump(scene, f, indent=4)


def evaluate(scene, gen, idx):
    json_trace, runtime = generate_trace(scene, gen, idx)
    # monitor = Monitor(data)
    # value = monitor.continuous_monitor_for_muti_traffic_rules()
    record = ScoreForScenario(json_trace, gen, idx)
    # judge = JudgeByDis(json_trace)
    # record = RecordTestResult(data, gen, idx)
    value = record.value
    record.get_run_scenario_time(runtime)
    # value处理待定
    # fitness = max(value)
    # return value
    return value

def generate_trace(scene, gen, idx):
    try:
        start_docker.start_pro(f'generation_{gen + 1}/ind_{idx}.json') # 需要输入data数据信息，以加载地图
        bashCommand = f"conda run -n scen python ../scenario_runner.py --sync --waitForEgo --GA True --openscenario2 ../AVUnit_Osc/avunit_s4.osc\
            --config_json /home/abc/scenario_runner/law_judgement/mutation/generation_{gen + 1}/ind_{idx}.json"
        start_run = time.perf_counter()
        process = subprocess.Popen(bashCommand.split(), stdout=sys.stdout, stderr=sys.stderr)
        output, error = process.communicate()
        end_run = time.perf_counter()
        run_time = end_run - start_run
        if not error is None:
            print(error.decode("utf-8"))
    except Exception as e:
        print("Error! Stop All Process!")
        sys.exit(1)
    finally:
        print("Stop docker and prepare for next generation!")
        # 终止全部docker进程
        start_docker.stop_all()

    time.sleep(4)
    # input_folder = "/home/abc/scenario_runner/trace/test_script"
    # files = os.listdir(input_folder)
    # length = len(files) q
    # file = "/home/abc/scenario_runner/trace/test_script/trace_test_script_" + str(length-1) + ".json"
    file = "/home/abc/scenario_runner/trace/avunit_s4/trace_avunit_s4_{}_{}.json".format(gen + 1, idx)
    return file, run_time

#
# class TestCaseRandom:
#     def __init__(self, msg):
#         testcase_ = {}
#         testcase_['ego'] = msg['ego']
#         testcase_['npcList'] = msg['npcList']
#         testcase_['pedestrianList'] = msg['pedestrianList']
#         testcase_['obstacleList'] = msg['obstacleList']
#         testcase_['AgentNames'] = msg['AgentNames']
#
#         self.original = testcase_
#         self.cases = [testcase_]
#
#     def npc_random(self):
#         pass
#
#     def testcase_random(self, num):
#         pass


class GAGeneration:
    def __init__(self, population_size=20, generation=26, crossover_prob=1.0, mutation_prob=1.0):
        self.population_size = population_size
        self.generation = generation
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        # self.scenario_mode = ["natural", "diverse", "adversarial"]
        # self.mutation_position_start = {}
        # self.mutation_position_end = {}
        self.mutation_position_start = []
        self.mutation_position_end = []

    def extract_exist_position(self, scene, mutate_npc):
        for k in scene.keys():
            if not k.startswith("npc") or k == mutate_npc:
                continue

            # self.mutation_position_start[k] = {"lane_id_start": scene[k]["start_position"]["lane_id"],
            #                                    "position_start": scene[k]["start_position"]["position"]}
            # self.mutation_position_end[k] = {"lane_id_start": scene[k]["end_position"]["lane_id"],
            #                                    "position_start": scene[k]["end_position"]["position"]}

            self.mutation_position_start.append([scene[k]["start_position"]["lane_id"],
                                                 scene[k]["start_position"]["position"]])
            self.mutation_position_end.append([scene[k]["end_position"]["lane_id"],
                                               scene[k]["end_position"]["position"]])

    def is_range(self, mutant, npc):
        is_range_lane_start = False
        is_range_lane_end = False
        is_range_position_start = False
        is_range_position_end = False
        if mutant[npc]["range"]["range_lane_start"][0] and mutant[npc]["range"]["range_lane_start"][1]:
            is_range_lane_start = True
        if mutant[npc]["range"]["range_lane_end"][0] and mutant[npc]["range"]["range_lane_end"][1]:
            is_range_lane_end = True
        if mutant[npc]["range"]["range_position_start"][0] and mutant[npc]["range"]["range_position_start"][1]:
            is_range_position_start = True
        if mutant[npc]["range"]["range_position_end"][0] and mutant[npc]["range"]["range_position_end"][1]:
            is_range_position_end = True
        return is_range_lane_start, is_range_lane_end, is_range_position_start, is_range_position_end

    def judge_truth(self, lane_id_start, position_start, lane_id_end, position_end, min_dist=5):
        if lane_id_start is None and position_start is None:
            return False
        # if position_end - position_start < 10:
        #     return False
        elif all((lane_id_start != p[0]) or (abs(position_start - p[1]) >= min_dist) for p in self.mutation_position_start) \
                and all(lane_id_end != p[0] or (abs(position_end - p[1]) >= min_dist) for p in self.mutation_position_end):
            return True
        return True

    def mutate(self, scene):
        speed_max = 20
        speed_min = 5
        acc_max = 5
        acc_min = 0.5
        mutant = copy.deepcopy(scene)

        orch_npc = []
        for k in mutant.keys():
            if k.startswith("npc") and mutant[k]["orch"]:
                orch_npc.append(k)

        # ego is not mutated

        """
        注意：如果后续涉及特定npc的问题，需要在此处进行筛选。例如，对于autoorchestrates的NPC，可能需要将其排除在外
        """
        npc = random.choice([k for k in mutant.keys() if k.startswith("npc")])
        while npc in orch_npc:
            npc = random.choice([k for k in mutant.keys() if k.startswith("npc")])
        # if npc in orch_npc:
        #     orch_npc.remove(npc)

        for k in orch_npc:
            mutant[k]["change_mode"] = False

        npc_lane_id_start = None
        npc_position_start = None
        npc_lane_id_end = None
        npc_position_end = None
        self.mutation_position_end.clear()
        self.mutation_position_start.clear()
        self.extract_exist_position(scene, npc)

        is_range_lane_start, is_range_lane_end, is_range_position_start, is_range_position_end = self.is_range(mutant, npc)

        while not self.judge_truth(npc_lane_id_start, npc_position_start, npc_lane_id_end, npc_position_end):
            if is_range_lane_start:
                npc_lane_id_start = random.randint(mutant[npc]["range"]["range_lane_start"][0],
                                                   mutant[npc]["range"]["range_lane_start"][1])
            else:
                npc_lane_id_start = mutant[npc]["start_position"]["lane_id"]
            if is_range_lane_end:
                npc_lane_id_end = random.randint(mutant[npc]["range"]["range_lane_end"][0],
                                                 mutant[npc]["range"]["range_lane_end"][1])
            else:
                npc_lane_id_end = mutant[npc]["end_position"]["lane_id"]
            if "position" in mutant[npc]["start_position"] and is_range_position_start:
                # mutant_start_position = gauss(mutant[npc]["start_position"]["position"], 1)
                # npc_position_start = float(np.clip(mutant_start_position, mutant[npc]["range"]["range_position_start"][0],
                #                                    mutant[npc]["range"]["range_position_start"][1]))
                npc_position_start = random.uniform(mutant[npc]["range"]["range_position_start"][0], mutant[npc]["range"]["range_position_start"][1])
            else:
                npc_position_start = mutant[npc]["start_position"]["position"]

            if "position" in mutant[npc]["end_position"] and is_range_position_end:
                # mutant_end_position = gauss(mutant[npc]["end_position"]["position"], 1)
                # npc_position_end = float(np.clip(mutant_end_position, mutant[npc]["range"]["range_position_end"][0],
                #                                  mutant[npc]["range"]["range_position_end"][1]))
                npc_position_end = random.uniform(mutant[npc]["range"]["range_position_end"][0], mutant[npc]["range"]["range_position_end"][1])
            else:
                npc_position_end = mutant[npc]["end_position"]["position"]

        mutant[npc]["start_position"]["lane_id"] = npc_lane_id_start
        mutant[npc]["end_position"]["lane_id"] = npc_lane_id_end
        mutant[npc]["start_position"]["position"] = npc_position_start
        mutant[npc]["end_position"]["position"] = npc_position_end
        if mutant.get("scenario_mode"):
            choose_num = mutant["scenario_mode"]["choose_num"]
            now_num = mutant["scenario_mode"]["now_num"]
            new_num = random.randint(0, choose_num-1)
            mutant["scenario_mode"]["now_num"] = new_num

            # 注：这里修改了len(orch_npc)，原本len(orch_npc) - 1
            mutate_orch_npc_num = random.randint(1, len(orch_npc))
            change_mode_orch_npc = random.sample(orch_npc, mutate_orch_npc_num)
            if len(change_mode_orch_npc) > 0:
                for k in change_mode_orch_npc:
                    mutant[k]["change_mode"] = True

        mutant_max_speed = gauss(mutant[npc]["hyperparameters"]["max_speed"], 1)
        mutant[npc]["hyperparameters"]["max_speed"] = float(np.clip(mutant_max_speed, speed_min, speed_max))
        mutant_max_acc = gauss(mutant[npc]["hyperparameters"]["max_acc"], 1)
        mutant[npc]["hyperparameters"]["max_acc"] = float(np.clip(mutant_max_acc, acc_min, acc_max))

        return mutant

    def crossover(self, scene1, scene2):
        p1 = copy.deepcopy(scene1)
        p2 = copy.deepcopy(scene2)
        for i in range(1, len(scene1)):
            if random.random() < self.crossover_prob:
                p1[i], p2[i] = p2[i], p1[i]
        return p1, p2

    # 新增遗传算法选择策略，每一代都保留最佳population_size个样本。
    # 设计新的数据结构来保留历史数据，在设置的generation结束后，选择最佳的
    # 增加数据存储

    def genetic_fuzz2(self, template):
        # template没有参与，是否算是一个遗漏？

        population = []
        temp = []
        for i in range(self.population_size):
            population.append(self.mutate(template))

        for gen in range(self.generation):

            gen_dir = f"mutation/generation_{gen + 1}"
            os.makedirs(gen_dir, exist_ok=True)
            for idx, scene in enumerate(population):
                filename = os.path.join(gen_dir, f"ind_{idx}.json")
                with open(filename, "w") as f:
                    json.dump(scene, f, indent=4)

            scores = [evaluate(scene, gen, idx) for idx, scene in enumerate(population)]

            scored_pop = list(zip(population, scores))
            scored_pop = scored_pop + temp
            # 找最小的
            scored_pop.sort(key=lambda x: x[1], reverse=False)
            scored_pop = scored_pop[:self.population_size]

            temp = scored_pop.copy()
            survivors = [copy.deepcopy(scored_pop[0][0]),
                         copy.deepcopy(scored_pop[1][0]),
                         copy.deepcopy(scored_pop[2][0])]

            children = []
            for i in range(0, self.population_size - 1, 2):
                if i + 1 <= self.population_size - 2:
                    p1 = copy.deepcopy(scored_pop[i][0])
                    p2 = copy.deepcopy(scored_pop[i + 1][0])
                    if random.random() < self.crossover_prob:
                        p1, p2 = self.crossover(p1, p2)
                    if random.random() < self.mutation_prob:
                        p1 = self.mutate(p1)
                    if random.random() < self.mutation_prob:
                        p2 = self.mutate(p2)
                    children.append(p1)
                    children.append(p2)
                else:
                    children.append(self.mutate(copy.deepcopy(scored_pop[i][0])))
            population = survivors + children

            print(f"Generation {gen+1}, best fitness: {scores[0]}")

        return population

    def selection2(self, scorted_pop):
        selected_population = []
        for i in range(self.population_size):
            first_int = random.sample(range(0, math.ceil(self.population_size/2)), 1)[0]
            second_int = random.sample(range(0, self.population_size), 1)[0]
            # two_int = random.sample(range(0, self.population_size), 2)
            # p1 = copy.deepcopy(self.population[two_int[0]])
            # p2 = copy.deepcopy(self.population[two_int[1]])
            p1 = copy.deepcopy(scorted_pop[first_int][0])
            p2 = copy.deepcopy(scorted_pop[second_int][0])
            if scorted_pop[first_int][1] > scorted_pop[second_int][1]:
                selected_population.append(p1)
            else:
                selected_population.append(p2)
            del p1, p2
        return selected_population

    def random_initial_population(self, template):
        population = []
        for i in range(self.population_size):
            population.append(self.mutate(template))
        initial_path = os.path.join("mutation", "generation_0")
        os.makedirs(initial_path, exist_ok=True)
        for idx, scene in enumerate(population):
            filename = os.path.join(initial_path, f"ind_{idx}.json")
            with open(filename, "w") as f:
                json.dump(scene, f, indent=4)

    def genetic_fuzz(self):
        population = []
        total_gen_time = 0

        # 断点继续
        config_path = "mutation/generation_0"
        for filename in sorted(os.listdir(config_path)):
            if filename.endswith(".json"):
                file_path = os.path.join(config_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    population.append(data)
        # 断点继续

        for gen in range(0, self.generation+1):

            gen_dir = f"mutation/generation_{gen + 1}"
            os.makedirs(gen_dir, exist_ok=True)
            for idx, scene in enumerate(population):
                filename = os.path.join(gen_dir, f"ind_{idx}.json")
                with open(filename, "w") as f:
                    json.dump(scene, f, indent=4)

            scores = [evaluate(scene, gen, idx) for idx, scene in enumerate(population)]

            scored_pop = list(zip(population, scores))
            scored_pop.sort(key=lambda x: x[1], reverse=True)
            # survivors = [copy.deepcopy(scored_pop[0][0]),
            #              copy.deepcopy(scored_pop[1][0])]
            survivors = []

            children = []
            selected_pop = []

            for i in range(self.population_size):
                selected_pop.append(copy.deepcopy(scored_pop[i][0]))
            # selected_pop = self.selection2(scored_pop)
            start_gen = time.perf_counter()
            for i in range(0, self.population_size , 2):
                if i + 1 <= self.population_size - 1:
                    p1 = copy.deepcopy(selected_pop[i])
                    p2 = copy.deepcopy(selected_pop[i + 1])
                    # if random.random() < self.crossover_prob:
                    #     p1, p2 = self.crossover(p1, p2)
                    if random.random() < self.mutation_prob:
                        p1 = self.mutate(p1)
                    if random.random() < self.mutation_prob:
                        p2 = self.mutate(p2)
                    children.append(p1)
                    children.append(p2)
                else:
                    children.append(self.mutate(copy.deepcopy(selected_pop[i])))
            end_gen = time.perf_counter()
            gen_time = end_gen - start_gen
            total_gen_time = total_gen_time + gen_time
            population = survivors + children

            print(f"Generation {gen+2}, best fitness: {scores[0]}")

        record_result_path = "/home/abc/scenario_runner/scenario_record/avunit_s4.json"
        record_data = load_template(record_result_path)
        record_data["average_gen_scenario_time"] = total_gen_time / (self.generation * self.population_size)
        save_result(record_data, record_result_path)
        return population


if __name__ == "__main__":
    APOLLO = "/home/abc/apollo/data"
    if os.path.isdir(APOLLO + "/core"):
        shutil.rmtree(APOLLO + "/core")
    template = load_template("../config/6.json")
    GA = GAGeneration()
    if not os.path.isdir("mutation/generation_0"):
        GA.random_initial_population(template)
    results = GA.genetic_fuzz()

    for i, scene in enumerate(results[:3]):
        save_result(scene, f"scene_result_{i}.json")
