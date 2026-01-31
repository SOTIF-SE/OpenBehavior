import random
import time
import numpy as np
import os
import carla
from agents.navigation.global_route_planner import GlobalRoutePlanner

class GetObs():
    def __init__(self, world, current_wp=None, des_wp=None):
        self.actor_list = []
        self.vehicle = None
        self.collision_hist = []

        ## Route planner
        self.map = world.get_map()
        self.sampling_resolution = 1.0
        self.route_planner = GlobalRoutePlanner(self.map, sampling_resolution=self.sampling_resolution)
        self.spawn_points = self.map.get_spawn_points()
        self.traffic_lights = world.get_actors().filter('traffic.traffic_light')
        self.traffic_light_info = []
        self.route = None
        self.route = self.generate_route(current_wp, des_wp)
        self.start_waypoint = None
        self.dest_waypoint = None
        self.curr_waypoint = None
        self.observation = None
        self.debug = False

    def get_observation(self, vehicle_transform, curr_waypoint, velocity):

        speed = self.get_speed(velocity, vehicle_transform.get_forward_vector())
        speed = speed / 60.0  # Normalize speed to [-1, 1]
        lateral_distance = self.get_lateral_distance(vehicle_transform, curr_waypoint)
        heading = self.get_future_heading(vehicle_transform, curr_waypoint)
        normalized_yaw = self.calculate_relative_heading(vehicle_transform, curr_waypoint)
        traffic_light_state, traffic_light_distance = self.get_traffic_light_info(vehicle_transform, curr_waypoint)
        if traffic_light_state == 'Green' or traffic_light_state == 0:
            traffic_light_distance = 15
        traffic_light_distance = np.clip(traffic_light_distance / 15.0, 0, 1)  # Normalize traffic light distance
        obs = np.array([
            lateral_distance,
            speed,
            heading,
            normalized_yaw,
            traffic_light_distance
        ], dtype=np.float32)
        return obs

    def get_speed(self, velocity, velocity_vector, max_speed=60.0):
        if self.vehicle:
            dot_product = (velocity.x * velocity_vector.x +
                           velocity.y * velocity_vector.y +
                           velocity.z * velocity_vector.z)
            speed = 3.6 * np.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2)
            if dot_product < 0:
                return -speed
            return speed
        return 0.0

    def get_lateral_distance(self, vehicle_transform, waypoint, max_distance=4.0):
        # Get vehicle and waypoint positions
        waypoint_location = waypoint.transform.location
        waypoint_forward_vector = waypoint.transform.get_forward_vector()
        vehicle_location = vehicle_transform.location

        # Convert CARLA location objects to NumPy arrays
        waypoint_location_np = np.array([waypoint_location.x, waypoint_location.y])
        waypoint_forward_np = np.array([waypoint_forward_vector.x, waypoint_forward_vector.y])
        vehicle_location_np = np.array([vehicle_location.x, vehicle_location.y])

        # Normalize the waypoint's forward vector (this is the direction of the lane)
        norm = np.linalg.norm(waypoint_forward_np)
        if norm == 0:
            return 0  # Prevent division by zero if the forward vector length is zero
        waypoint_forward_np /= norm

        # Vector from the waypoint (center of the lane) to the vehicle
        vehicle_vector_np = vehicle_location_np - waypoint_location_np

        # Project the vehicle vector onto the waypoint's forward vector (lane direction)
        projection_length = np.dot(vehicle_vector_np, waypoint_forward_np)
        projection_point = projection_length * waypoint_forward_np

        lateral_vector = vehicle_vector_np - projection_point
        lateral_distance = np.linalg.norm(lateral_vector)

        # Normalize the lateral distance to the range [-1, 1]
        normalized_lateral_distance = np.clip(lateral_distance / max_distance, -1, 1)

        # Check if the vehicle is to the left or right of the lane center by using a cross product
        cross_product = np.cross(waypoint_forward_np, vehicle_vector_np)
        if cross_product < 0:
            # If the cross product is negative, the vehicle is to the right of the lane
            normalized_lateral_distance *= -1

        return normalized_lateral_distance

    def get_future_heading(self, vehicle_transform, waypoint, num_lookahead=5, distance_lookahead=2):

        current_waypoint = waypoint  # Start from the current waypoint
        yaw_differences_sum = 0  # Accumulator for the sum of yaw differences
        turn_direction = self.turn_direction(vehicle_transform, waypoint, num_lookahead, distance_lookahead)

        # Sum up yaw differences from the current waypoint and future waypoints
        for i in range(1, num_lookahead + 1):
            future_waypoint = self.find_next_waypoint(current_waypoint)
            if not future_waypoint:
                break  # Stop if no valid future waypoint

            future_yaw = future_waypoint.transform.rotation.yaw
            yaw_diff = abs(current_waypoint.transform.rotation.yaw - future_yaw)
            yaw_diff = yaw_diff if yaw_diff <= 180 else 360 - yaw_diff

            # Accumulate the yaw difference
            yaw_differences_sum += yaw_diff
            current_waypoint = future_waypoint
        relative_heading = (yaw_differences_sum)
        if relative_heading > 180:
            relative_heading -= 360

        if turn_direction == 0:
            normalized_heading = relative_heading / 180.0
        else:
            normalized_heading = turn_direction * (relative_heading / 180.0)

        return np.clip(normalized_heading, -1, 1)

    def turn_direction(self, vehicle_transform, waypoint, num_lookahead=5, distance_lookahead=2):
        vehicle_yaw = vehicle_transform.rotation.yaw % 360
        current_waypoint = waypoint

        # Look ahead at future waypoints
        for _ in range(num_lookahead):
            future_waypoint = self.find_next_waypoint(current_waypoint, distance_lookahead)
            if not future_waypoint:
                break
            current_waypoint = future_waypoint

        # Check if there is a valid future waypoint
        if future_waypoint:
            future_yaw = future_waypoint.transform.rotation.yaw % 360
            yaw_diff = (future_yaw - vehicle_yaw + 180) % 360 - 180

            # Return direction: 1 for left (counterclockwise), -1 for right (clockwise)
            return 1 if yaw_diff >= 0 else -1
        return 0

    def generate_route(self, start_waypoint=None, dest_waypoint=None):

        if start_waypoint is None:
            self.start_waypoint = random.choice(self.spawn_points)
            # print(f"Start waypoint: {self.start_waypoint.location}")
        else:
            self.start_waypoint = start_waypoint
        if dest_waypoint is None:
            self.dest_waypoint = random.choice(self.spawn_points)
        else:
            self.dest_waypoint = dest_waypoint
        distance = self.start_waypoint.transform.location.distance(self.dest_waypoint.transform.location)
        try:
            route = self.route_planner.trace_route(self.start_waypoint.transform.location, self.dest_waypoint.transform.location)
        except Exception as e:
            return None
        return route

    def calculate_relative_heading(self, vehicle_transform, waypoint):
        vehicle_yaw = vehicle_transform.rotation.yaw
        waypoint_yaw = waypoint.transform.rotation.yaw
        # Calculate relative yaw
        relative_yaw = waypoint_yaw - vehicle_yaw

        # Normalize relative yaw to be within [-180, 180]
        def normalize_angle(angle):
            # Ensure the angle is within [-180, 180]
            return ((angle + 180) % 360) - 180

        relative_yaw = normalize_angle(relative_yaw)
        # Scale to [-1, 1]
        return relative_yaw / 180.0

    def find_next_waypoint(self, current_waypoint, distance_lookahead=1):
        for i, (waypoint, _) in enumerate(self.route):
            dist = waypoint.transform.location.distance(current_waypoint.transform.location)
            if dist == 0:
                if i + distance_lookahead < len(self.route):
                    return self.route[i + distance_lookahead][0]
        return None

    def get_traffic_light_info(self, vehicle_transform, current_waypoint):
        vehicle_location = vehicle_transform.location
        # Find the segment of the route that is ahead of the vehicle
        route_tl = self._get_route_segment(current_waypoint)
        closest_light = None
        closest_distance = float('inf')
        # Check for any traffic lights that impact this segment
        for tl, tl_waypoint in self.traffic_light_info:
            if any(self._is_waypoint_close(waypoint, tl_waypoint) for waypoint, _ in route_tl):
                stop_distance = tl_waypoint.transform.location.distance(vehicle_location)
                if stop_distance < closest_distance:
                    closest_distance = stop_distance
                    closest_light = tl

        if closest_light is not None:
            state = closest_light.get_state()
            return state.name, closest_distance
        return 0, 0  # Clear indication that no traffic light affects the route

    def _get_route_segment(self, current_waypoint, length=15):
        """Returns a sublist of self.route starting from the current_waypoint."""
        if not self.route:
            return []
        try:
            start_index = next(
                i for i, (waypoint, _) in enumerate(self.route)
                if waypoint == current_waypoint
            )
            end_index = min(start_index + length, len(self.route))
            return self.route[start_index:end_index]
        except StopIteration:
            return []
        except Exception as e:
            return []

    def _is_waypoint_close(self, waypoint, target_waypoint, threshold=2.0):
        """Checks if a waypoint is within a certain distance (threshold) of the target waypoint."""
        distance = waypoint.transform.location.distance(target_waypoint.transform.location)
        return distance < threshold
