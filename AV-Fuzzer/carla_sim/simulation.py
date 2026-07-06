import carla
import time
import math
import sys
import os
import json

from start_docker import start_pro, send_routing_request, stop_all
from camera_recorder.camera_recorder import CameraRecorder
from data_bridge import DataBridge
from judge_by_dis import JudgeByDis

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../PythonAPI')))
from agents.navigation.behavior_agent import BehaviorAgent
import liability
import tools
from collections import namedtuple
from collections import deque


SimulationResult = namedtuple('SimulationResult', [
    'deltaDlist',  # List of per-NPC lists of deltaD over time
    'dList',       # List of per-NPC lists of raw distances over time
    'isHit',       # Whether a collision occurred
    'isEgoFault',  # If collision, whether ego vehicle was at fault
    'hitTime'      # Frame index when collision happened
])

WindowEntry = namedtuple('WindowEntry', [
    'tick',        # Associated time value
    'transform',   # Transform of a vehicle at t = tick
    'velocity',    # Velocity of a vehicle at t = tick
    'acceleration',# Acceleration of a vehicle at t = tick
])

TIMING_DIR = os.path.join(os.path.dirname(__file__), 'timing')
SCENE_SETUP_TIME_PATH = os.path.join(TIMING_DIR, 'scene_setup_time.json')
TEST_EXECUTION_TIME_PATH = os.path.join(TIMING_DIR, 'test_execution_time.json')


def update_average_time_record(path, current_seconds):
    count = 0
    average_seconds = 0.0
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                record = json.load(f)
            count = int(record.get('count', 0))
            average_seconds = float(record.get('average_seconds', 0.0))
        except (OSError, ValueError, TypeError):
            count = 0
            average_seconds = 0.0

    new_count = count + 1
    new_average = (average_seconds * count + current_seconds) / new_count
    new_record = {
        'count': new_count,
        'average_seconds': new_average,
        'last_seconds': current_seconds,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(new_record, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, path)
    return new_record

def ego_arrived(ego_vehicle, dest_location, arrive_distance=2.0):
    ego_location = ego_vehicle.get_location()
    distance = dest_location.distance(ego_location)
    return distance <= arrive_distance

def run_simulation(spawn_config, weather_params,
                   npc1_behaviors, npc2_behaviors, npc3_behaviors, npc4_behaviors,
                   tick_interval=0.05,
                   max_frames=500):

    start_pro()
    setup_start_time = time.perf_counter()
    client = carla.Client("localhost", 2000)
    client.set_timeout(20.0)

    world = client.get_world()
    map = world.get_map()
    tools.set_weather(world, weather_params)

    spectator = world.get_spectator()
    spectator.set_transform(carla.Transform(
        carla.Location(x=-50, y=0, z=100),
        carla.Rotation(pitch=-35, yaw=0, roll=0)))

    blueprint_library = world.get_blueprint_library()
    #s1
    ev_tf   = tools.list_to_transform(spawn_config['ev']['start'], yaw=-19.1055)
    ev_end  = tools.list_to_transform(spawn_config['ev']['end'],yaw=-88.8599).location

    #s2
    # ev_tf   = tools.list_to_transform(spawn_config['ev']['start'], yaw=89.47)
    # ev_end  = tools.list_to_transform(spawn_config['ev']['end'],yaw=89.09).location

    #s3
    # ev_tf   = tools.list_to_transform(spawn_config['ev']['start'], yaw=-85.7697)
    # ev_end  = tools.list_to_transform(spawn_config['ev']['end'],yaw=-89.2102).location

    #s4
    # ev_tf   = tools.list_to_transform(spawn_config['ev']['start'], yaw=-84.2751)
    # ev_end  = tools.list_to_transform(spawn_config['ev']['end'],yaw=-89.2102).location

    vehicle = world.get_actors().filter('*vehicle*')[0]
    vehicle.set_transform(ev_tf)
    send_routing_request(ev_end)

#s1
    npc1 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc1']['start'], yaw=0.2347))
    npc2 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc2']['start'], yaw=0.2347))
    npc3 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc3']['start'], yaw=0.2347))
    npc4 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc4']['start'], yaw=-89.3786))

# s2
#     npc1 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc1']['start'], yaw=-0.20))
#     npc2 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc2']['start'], yaw=-0.18))
#     npc3 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc3']['start'], yaw=-0.20))
#     npc4 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc4']['start'], yaw=89.48))

    # s3
    # npc1 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc1']['start'], yaw=-85.5682))
    # npc2 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc2']['start'], yaw=-85.1433))
    # npc3 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc3']['start'], yaw=-89.5609))
    # npc4 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc4']['start'], yaw=-88.0136))

    # # s4
    # npc1 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc1']['start'], yaw=-86.3876))
    # npc2 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc2']['start'], yaw=-85.1433))
    # npc3 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc3']['start'], yaw=-89.5609))
    # npc4 = tools.spawn_npc(world, blueprint_library, tools.list_to_transform(spawn_config['npc4']['start'], yaw=-88.0136))

    collision_bp = blueprint_library.find('sensor.other.collision')
    collision_sensor = world.spawn_actor(collision_bp, carla.Transform(), attach_to=vehicle)
    isHit = False; isEgoFault = False; hitTime = None
    ego_history = None; npc1_history = None; npc2_history = None; npc3_history = None; npc4_history = None
    def on_collision(event):
        nonlocal isHit, isEgoFault, hitTime, ego_history
        nonlocal npc1, npc1_history, npc2, npc2_history, npc3, npc3_history, npc4, npc4_history
        if isHit:
            return
        other = event.other_actor
        if ('vehicle' in event.actor.type_id and
            'vehicle' in other.type_id and
            (event.actor.id == vehicle.id or other.id == vehicle.id)):

            waypoint = map.get_waypoint(event.actor.get_transform().location)
            isHit = True
            hitTime = event.frame
            ev, npc = (event.actor, other) if event.actor.id == vehicle.id else (other, event.actor)

            ev_history = ego_history
        
            if npc.id == npc1.id:
                npc_history = npc1_history
            elif npc.id == npc2.id:
                npc_history = npc2_history
            elif npc.id == npc3.id:
                npc_history = npc3_history
            elif npc.id == npc4.id:
                npc_history = npc4_history
            else:
                npc_history = deque(maxlen=50)

            isEgoFault = liability.is_ego_fault(ev, ev_history, npc, npc_history, waypoint)
        
    collision_sensor.listen(on_collision)

    # npc1.apply_control(npc1_behaviors[0])
    # npc2.apply_control(npc2_behaviors[0])
    # npc3.apply_control(npc3_behaviors[0])
    # npc4.apply_control(npc4_behaviors[0])

    world.tick()
    # time.sleep(10)

    deltaDlist, dList = [[],[],[],[]], [[],[],[],[]]
    lane_change_interval = int(1.0 / tick_interval)
    frame_count = 0

    window_size = 50

    ego_history = deque(maxlen=window_size)
    ego_start = tools.window_entry(frame_count, vehicle)
    ego_history.append(ego_start)

    npc1_history = deque(maxlen=window_size)
    npc1_start = tools.window_entry(frame_count, npc1)
    npc1_history.append(npc1_start)
    npc2_history = deque(maxlen=window_size)
    npc2_start = tools.window_entry(frame_count, npc2)
    npc2_history.append(npc2_start)
    npc3_history = deque(maxlen=window_size)
    npc3_start = tools.window_entry(frame_count, npc3)
    npc3_history.append(npc3_start)
    npc4_history = deque(maxlen=window_size)
    npc4_start = tools.window_entry(frame_count, npc4)
    npc4_history.append(npc4_start)
    recorder = CameraRecorder(world, vehicle)
    recorder.start()
    data_bridge = DataBridge(world)
    data_bridge.set_actors(vehicle, [npc1, npc2, npc3, npc4])
    data_bridge.update_ego_vehicle_start()
    data_bridge.update_npc_vehicle_start()

    scene_setup_time = time.perf_counter() - setup_start_time
    test_start_time = time.perf_counter()


    while frame_count < max_frames:
        world.tick()
        if isHit:
            break

        if frame_count % lane_change_interval == 0:
            idx = frame_count // lane_change_interval
            if idx < len(npc1_behaviors):
                npc1.apply_control(npc1_behaviors[idx])
            if idx < len(npc2_behaviors):
                npc2.apply_control(npc2_behaviors[idx])
            if idx < len(npc3_behaviors):
                npc3.apply_control(npc3_behaviors[idx])
            if idx < len(npc4_behaviors):
                npc4.apply_control(npc4_behaviors[idx])


        ego_loc = vehicle.get_location()
        ego_vel = vehicle.get_velocity()
        ego_speed = math.sqrt(ego_vel.x**2 + ego_vel.y**2 + ego_vel.z**2)
        brake_dist = max(0.0, 0.0467*ego_speed**2 + 0.4116*ego_speed - 1.9913 + 0.5)

        for i, npc in enumerate((npc1, npc2, npc3, npc4)):
            loc = npc.get_location()
            d = math.hypot(ego_loc.x-loc.x, ego_loc.y-loc.y)
            delta = d - 4.6 - brake_dist
            dList[i].append(d)
            deltaDlist[i].append(delta)

        frame_count += 1

        ego_entry = tools.window_entry(frame_count, vehicle)
        ego_history.append(ego_entry)

        npc1_entry = tools.window_entry(frame_count, npc1)
        npc1_history.append(npc1_entry)
        npc2_entry = tools.window_entry(frame_count, npc2)
        npc2_history.append(npc2_entry)
        npc3_entry = tools.window_entry(frame_count, npc3)
        npc3_history.append(npc3_entry)
        npc4_entry = tools.window_entry(frame_count, npc4)
        npc4_history.append(npc4_entry)

        data_bridge.update_trace()
        data_bridge.update_npc_vehicle_motion()

        time.sleep(tick_interval)
        
    test_execution_time = time.perf_counter() - test_start_time
    scene_setup_record = update_average_time_record(SCENE_SETUP_TIME_PATH, scene_setup_time)
    test_execution_record = update_average_time_record(TEST_EXECUTION_TIME_PATH, test_execution_time)
    recorder.stop_camera()
    
    record_path = "/home/xie/AV-Fuzzer/carla_sim/trace/s1"
    data_bridge.end_trace(record_path)
    fileidx = 0
    while os.path.exists(record_path +'/{}.json'.format(fileidx)):
        fileidx += 1
    judge = JudgeByDis(record_path + '/{}.json'.format(fileidx-1))
    
    judge.remove_avi()
    for actor in (npc1, npc2, npc3, npc4):
        if actor:
            try:
                actor.destroy()
            except:
                pass
    if collision_sensor:
        collision_sensor.destroy()

    stop_all()
    time.sleep(10)

    return SimulationResult(deltaDlist, dList, isHit, isEgoFault, hitTime)


def evaluate_individual(spawn_config, weather_params, individual,
                        tick_interval=0.05, max_frames=500):

    npc1_behaviors, npc2_behaviors, npc3_behaviors, npc4_behaviors = individual

    #start_time = time.time()


    result = run_simulation(
        spawn_config,
        weather_params,
        npc1_behaviors,
        npc2_behaviors,
        npc3_behaviors,
        npc4_behaviors,
        tick_interval=tick_interval,
        max_frames=max_frames
    )


    fitness = tools.find_fitness(
        result.deltaDlist,
        result.dList,
        result.isEgoFault,
        result.isHit,
        result.hitTime
    )

    #elapsed_time = time.time() - start_time
    #print(f" evaluate_individual {elapsed_time:.2f}")

    return fitness, result


if __name__ == "__main__":
    weather_config = tools.load_weather_yaml('./parameters/weather.yaml')
    spawn_config  = tools.load_spawn_yaml('./parameters/test.yaml')

    tick_interval  = 0.05
    max_frames     = 500
    interval       = int(1.0/tick_interval)
    num_intervals  = max_frames//interval + 1

    b1 = tools.generate_npc_behaviors(spawn_config['npc1'], num_intervals, extra_steer_perturb=False)
    b2 = tools.generate_npc_behaviors(spawn_config['npc2'], num_intervals, extra_steer_perturb=False)
    b3 = tools.generate_npc_behaviors(spawn_config['npc3'], num_intervals, extra_steer_perturb=False)
    b4 = tools.generate_npc_behaviors(spawn_config['npc4'], num_intervals, extra_steer_perturb=False)

    run_simulation(spawn_config, weather_config, b1, b2, b3, b4, tick_interval, max_frames)