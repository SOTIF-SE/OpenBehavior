import carla
import time
import math
import sys
import os
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../PythonAPI')))
from agents.navigation.behavior_agent import BehaviorAgent
import liability
import  tools
import simulation
import random
from collections import namedtuple
import yaml
import start_docker
import traceback
import signal
from datetime import datetime


NPC_KEYS = ('npc1', 'npc2', 'npc3', 'npc4')


def control_to_dict(control):
    return {
        'throttle': float(control.throttle),
        'brake': float(control.brake),
        'steer': float(control.steer),
    }


def dict_to_control(data):
    ctrl = carla.VehicleControl()
    ctrl.throttle = data['throttle']
    ctrl.brake = data['brake']
    ctrl.steer = data['steer']
    return ctrl


def individual_to_checkpoint(individual):
    return {
        npc_key: [control_to_dict(control) for control in behaviors]
        for npc_key, behaviors in zip(NPC_KEYS, individual)
    }


def checkpoint_to_individual(data):
    return tuple(
        [dict_to_control(control) for control in data[npc_key]]
        for npc_key in NPC_KEYS
    )


def save_resume_state(checkpoint_path, state):
    checkpoint_dir = os.path.dirname(checkpoint_path)
    if checkpoint_dir:
        os.makedirs(checkpoint_dir, exist_ok=True)
    tmp_path = checkpoint_path + '.tmp'
    with open(tmp_path, 'w') as f:
        yaml.safe_dump(state, f, default_flow_style=False)
    os.replace(tmp_path, checkpoint_path)


def load_resume_state(checkpoint_path):
    with open(checkpoint_path, 'r') as f:
        data = yaml.safe_load(f)

    return {
        'last_population': [
            checkpoint_to_individual(ind)
            for ind in data['last_population']
        ],
        'history_best': [
            checkpoint_to_individual(ind)
            for ind in data.get('history_best', [])
        ],
        'best_ind': checkpoint_to_individual(data['best_ind']) if data.get('best_ind') else None,
        'best_fit': data.get('best_fit', float('-inf')),
        'next_generation': data.get('next_generation', 0),
        'raw': data,
    }

def get_similarity_between_npc_behaviors(b1, b2):
    n = min(len(b1), len(b2))
    if n == 0:
        return 0.0
    total = 0.0
    for i in range(n):
        t1, br1, st1 = b1[i].throttle, b1[i].brake, b1[i].steer
        t2, br2, st2 = b2[i].throttle, b2[i].brake, b2[i].steer
        dx = t1 - t2
        dy = br1 - br2
        dz = st1 - st2
        total += math.sqrt(dx*dx + dy*dy + dz*dz)
    return total / n


# def get_similarity_between_scenarios(ind1, ind2):
#     b11, b12 = ind1
#     b21, b22 = ind2

#     sim1 = get_similarity_between_npc_behaviors(b11, b21)
#     sim2 = get_similarity_between_npc_behaviors(b12, b22)
#     return (sim1 + sim2) / 2.0

def get_similarity_between_scenarios(ind1, ind2):
    b11, b12, b13, b14 = ind1
    b21, b22, b23, b24 = ind2
    sims = [
        get_similarity_between_npc_behaviors(b11, b21),
        get_similarity_between_npc_behaviors(b12, b22),
        get_similarity_between_npc_behaviors(b13, b23),
        get_similarity_between_npc_behaviors(b14, b24),
    ]
    return sum(sims) / 4.0

def tournament_select(population, fitnesses, k=3):

    candidates = random.sample(list(zip(population, fitnesses)), k)
    winner = max(candidates, key=lambda x: x[1])[0]
    return winner

def one_point_crossover(parent1, parent2):

    # b1a, b2a = parent1
    # b1b, b2b = parent2
    # length = len(b1a)
    # if length < 2:
    #     return parent1, parent2
    # k = random.randrange(1, length)
    # child1 = (b1a[:k] + b1b[k:], b2a[:k] + b2b[k:])
    # child2 = (b1b[:k] + b1a[k:], b2b[:k] + b2a[k:])
    # return child1, child2
    b1a, b2a, b3a, b4a = parent1
    b1b, b2b, b3b, b4b = parent2
    L = len(b1a)
    if L < 2:
        return parent1, parent2
    k = random.randrange(1, L)
    c1 = (
        b1a[:k] + b1b[k:], b2a[:k] + b2b[k:],
        b3a[:k] + b3b[k:], b4a[:k] + b4b[k:]
    )
    c2 = (
        b1b[:k] + b1a[k:], b2b[:k] + b2a[k:],
        b3b[:k] + b3a[k:], b4b[:k] + b4a[k:]
    )
    return c1, c2

def mutate(individual, spawn_config, mutation_rate):

    # b1, b2 = individual
    # cfg1 = spawn_config['npc1']
    # cfg2 = spawn_config['npc2']
    # for lst, cfg in [(b1, cfg1), (b2, cfg2)]:
    #     for i in range(len(lst)):
    #         if random.random() < mutation_rate:
    #             lst[i] = tools.generate_npc_behaviors(cfg, 1, extra_steer_perturb=True)[0]
    # return (b1, b2)
    b1, b2, b3, b4 = individual
    cfgs = [spawn_config['npc1'], spawn_config['npc2'], spawn_config['npc3'], spawn_config['npc4']]
    for lst, cfg in zip((b1, b2, b3, b4), cfgs):
        for i in range(len(lst)):
            if random.random() < mutation_rate:
                lst[i] = tools.generate_npc_behaviors(cfg, 1, extra_steer_perturb=True)[0]
    return (b1, b2, b3, b4)


def generate_random_population(spawn_config, pop_size, num_intervals):
    population = []
    for _ in range(pop_size):
        b1 = tools.generate_npc_behaviors(spawn_config['npc1'], num_intervals, extra_steer_perturb=True)
        b2 = tools.generate_npc_behaviors(spawn_config['npc2'], num_intervals, extra_steer_perturb=True)
        b3 = tools.generate_npc_behaviors(spawn_config['npc3'], num_intervals, extra_steer_perturb=True)
        b4 = tools.generate_npc_behaviors(spawn_config['npc4'], num_intervals, extra_steer_perturb=True)
        population.append((b1, b2, b3, b4))
    return population

class FlowSeq(list):
    pass

def represent_flowseq(dumper, data):
    #
    return dumper.represent_sequence(
        'tag:yaml.org,2002:seq', data, flow_style=True
    )


yaml.add_representer(FlowSeq, represent_flowseq, Dumper=yaml.SafeDumper)

# def tournament_select(population, fitnesses, k=3):
#     candidates = random.sample(list(zip(population, fitnesses)), k)
#     return max(candidates, key=lambda x: x[1])[0]

# def one_point_crossover(p1, p2):
#     b1a, b2a = p1; b1b, b2b = p2
#     L = len(b1a)
#     if L<2: return p1, p2
#     k = random.randrange(1, L)
#     return (b1a[:k]+b1b[k:], b2a[:k]+b2b[k:]), (b1b[:k]+b1a[k:], b2b[:k]+b2a[k:])

# def mutate(ind, spawn_config, mutation_rate=0.02):
#     b1, b2 = ind
#     for lst,cfg in [(b1, spawn_config['npc1']), (b2, spawn_config['npc2'])]:
#         for i in range(len(lst)):
#             if random.random()<mutation_rate:
#                 lst[i] = tools.generate_npc_behaviors(cfg,1,extra_steer_perturb=True)[0]
#     return (b1, b2)


def genetic_fuzzer(spawn_config, weather_params,
                   pop_size=10, max_gens=5,
                   crossover_rate=0.2,
                   mutation_rate=0.3,
                   tournament_k=3,
                   diversity_weight=0.005,
                   resume=True,
                   checkpoint_path="./logs/ga_checkpoint.yaml",
                   mode="ga"):

    tick_interval  = 0.05
    max_frames     = 500
    interval       = int(1.0/tick_interval)
    num_intervals  = max_frames//interval + 1


    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"./logs/ga_log_{ts}.yaml"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    f = open(log_path,'w')
    yaml.safe_dump({'ga_params': {
        'pop_size':pop_size,'max_gens':max_gens,
        'crossover_rate':crossover_rate,'mutation_rate':mutation_rate,
        'tournament_k':tournament_k,'diversity_weight':diversity_weight,
        'mode': mode
    }}, f, default_flow_style=False)
    f.write('---\n'); f.flush()
    try:
        if resume and os.path.exists(checkpoint_path):
            ckpt = load_resume_state(checkpoint_path)
            population = ckpt['last_population']
            history_best = ckpt['history_best']
            best_ind = ckpt['best_ind']
            best_fit = ckpt['best_fit']
            start_gen = ckpt['next_generation']
            print(f"Resume GA from {checkpoint_path}, next generation = {start_gen}")
        else:
            population = generate_random_population(spawn_config, pop_size, num_intervals)
            history_best = []

            best_ind, best_fit = None, float('-inf')
            start_gen = 0

        for gen in range(start_gen, max_gens):
            raw_fitness = []
            sim_results = []

            for ind in population:
                fit,res = simulation.evaluate_individual(
                    spawn_config, weather_params, ind,
                    tick_interval=tick_interval,
                    max_frames=max_frames
                )
                raw_fitness.append(fit)
                sim_results.append(res)

            adjusted_fitness = []
            for ind, fit in zip(population, raw_fitness):
                if mode == "random":
                    adjusted_fitness.append((fit, fit, 0.0))
                    continue

                if history_best:

                    sims = [
                        get_similarity_between_scenarios(ind, hist)
                        for hist in history_best
                    ]
                    avg_sim = sum(sims) / len(sims)
                else:
                    avg_sim = 0.0


                adj_fit = fit - diversity_weight * avg_sim * 10
                adjusted_fitness.append((adj_fit, fit, avg_sim))


            gen_record = {'generation': gen, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  'individuals': []}
            for idx,(ind,(adj,raw,sim)) in enumerate(zip(population, adjusted_fitness)):
                b1,b2,b3,b4 = ind

                getseq = lambda lst: {
                    'throttle':[c.throttle for c in lst],
                    'brake':   [c.brake    for c in lst],
                    'steer':   [c.steer    for c in lst]
                }
                rec = {
                    'idx': idx,
                    'raw_fitness': raw,
                    'adj_fitness': adj,
                    'diversity_penalty': sim,
                    'isHit': sim_results[idx].isHit,
                    'isEgoFault': sim_results[idx].isEgoFault,
                    'hitTime': sim_results[idx].hitTime,
                    'npc1_behaviors': FlowSeq(getseq(b1)['throttle']), # 也可直接嵌套 dict
                    'npc1_brake':    FlowSeq(getseq(b1)['brake']),
                    'npc1_steer':    FlowSeq(getseq(b1)['steer']),
                    'npc2_throttle': FlowSeq(getseq(b2)['throttle']),
                    'npc2_brake':    FlowSeq(getseq(b2)['brake']),
                    'npc2_steer':    FlowSeq(getseq(b2)['steer']),
                    'npc3_throttle': FlowSeq(getseq(b3)['throttle']),
                    'npc3_brake':    FlowSeq(getseq(b3)['brake']),
                    'npc3_steer':    FlowSeq(getseq(b3)['steer']),
                    'npc4_throttle': FlowSeq(getseq(b4)['throttle']),
                    'npc4_brake':    FlowSeq(getseq(b4)['brake']),
                    'npc4_steer':    FlowSeq(getseq(b4)['steer'])
                }
                gen_record['individuals'].append(rec)

            yaml.safe_dump(gen_record, f, default_flow_style=False)
            f.write('---\n'); f.flush()


            afits = [x[0] for x in adjusted_fitness]
            best_idx = max(range(pop_size), key=lambda i: afits[i])
            if afits[best_idx] > best_fit:
                best_fit, best_ind = afits[best_idx], population[best_idx]

            history_best.append(population[best_idx])


            if mode == "random":
                population = generate_random_population(spawn_config, pop_size, num_intervals)
            else:
                new_pop = [population[best_idx]]
                while len(new_pop)<pop_size:
                    p1 = tournament_select(population, afits, k=tournament_k)
                    p2 = tournament_select(population, afits, k=tournament_k)
                    if random.random()<crossover_rate:
                        c1,c2 = one_point_crossover(p1,p2)
                    else:
                        c1,c2 = p1,p2
                    new_pop.append(mutate(c1, spawn_config, mutation_rate=mutation_rate))
                    if len(new_pop)<pop_size:
                        new_pop.append(mutate(c2, spawn_config, mutation_rate=mutation_rate))
                population = new_pop

            checkpoint_state = {
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'next_generation': gen + 1,
                'ga_params': {
                    'pop_size': pop_size,
                    'max_gens': max_gens,
                    'crossover_rate': crossover_rate,
                    'mutation_rate': mutation_rate,
                    'tournament_k': tournament_k,
                    'diversity_weight': diversity_weight,
                    'mode': mode,
                },
                'best_fit': best_fit,
                'best_ind': individual_to_checkpoint(best_ind) if best_ind else None,
                'history_best': [
                    individual_to_checkpoint(ind)
                    for ind in history_best
                ],
                'last_population': [
                    individual_to_checkpoint(ind)
                    for ind in population
                ],
            }
            save_resume_state(checkpoint_path, checkpoint_state)


        print(f"\nGA finished; log at {log_path}")
        return best_ind, best_fit
    finally:
        f.close()

def run_ga_once():
    ga_cfg = tools.load_ga_config('./parameters/ga.yaml')

    POP_SIZE       = ga_cfg['pop_size']
    MAX_GENS       = ga_cfg['max_gens']
    CROSSOVER_RATE = ga_cfg['crossover_rate']
    MUTATION_RATE  = ga_cfg['mutation_rate']
    TOURNAMENT_K   = ga_cfg['tournament_k']
    RESUME         = ga_cfg.get('resume', True)
    CHECKPOINT_PATH = ga_cfg.get('checkpoint_path', './logs/ga_checkpoint.yaml')
    MODE           = ga_cfg.get('mode', 'ga')

    weather_config = tools.load_weather_yaml('./parameters/weather.yaml')
    spawn_config  = tools.load_spawn_yaml('parameters/spawn_s1.yaml')


    best_ind, best_fit = genetic_fuzzer(
        spawn_config,
        weather_config,
        pop_size       = POP_SIZE,
        max_gens       = MAX_GENS,
        crossover_rate = CROSSOVER_RATE,
        mutation_rate = MUTATION_RATE,
        tournament_k  =  TOURNAMENT_K,
        resume        = RESUME,
        checkpoint_path = CHECKPOINT_PATH,
        mode          = MODE
    )

    print("GA finished best fitness =", best_fit)
    return best_ind, best_fit


def keep_running_ga():
    ga_cfg = tools.load_ga_config('./parameters/ga.yaml')
    retry_delay = ga_cfg.get('retry_delay_seconds', 30)
    restart_count = 0

    while True:
        try:
            return run_ga_once()
        except KeyboardInterrupt:
            print("\nGA stopped by user.")
            raise
        except Exception:
            restart_count += 1
            print(f"\nGA interrupted unexpectedly. Restart #{restart_count} after {retry_delay} seconds.")
            traceback.print_exc()
            old_sigint_handler = signal.getsignal(signal.SIGINT)
            try:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                os.killpg(os.getpgrp(), signal.SIGINT)
            finally:
                signal.signal(signal.SIGINT, old_sigint_handler)
            try:
                start_docker.stop_all()
            except Exception:
                print("Cleanup failed; continue to retry after delay.")
                traceback.print_exc()
            time.sleep(retry_delay)


if __name__ == '__main__':
    keep_running_ga()
