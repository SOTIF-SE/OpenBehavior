from __future__ import print_function

import argparse
import json
import math
import re

try:
    from OpenBehavior_spec.process_rule import parse_spec_file
except ImportError:
    from process_rule import parse_spec_file


class TraceSignalBuilder(object):
    AGGREGATORS = ["switch_count", "duration", "count", "avg", "std", "max", "min"]
    BASE_SIGNALS = [
        "isChangingLane",
        "isOverTaking",
        "isTurningAround",
        "speed",
        "acc",
        "brake",
        "steer",
        "dist",
    ]

    def __init__(self, trace_data):
        self.trace_data = trace_data
        self.frames = trace_data.get("trace", [])
        self.times = list(range(len(self.frames)))
        self.npcs = {npc.get("ID"): npc for npc in trace_data.get("npcList", [])}
        self.actors = ["ego"] + sorted([actor for actor in self.npcs if actor])
        self.special_targets = {"target_position": self._target_position()}

    def build_many(self, variable_names):
        return {name: self.build(name) for name in variable_names}

    def build(self, variable_name):
        aggregation = self._split_aggregation(variable_name)
        if aggregation is not None:
            aggregator, inner_variable = aggregation
            values = self.build(inner_variable)
            return self._aggregate(aggregator, values)

        if variable_name.startswith("dist"):
            actor_a, actor_b = self._parse_dist_variable(variable_name)
            return self._distance(actor_a, actor_b)

        if variable_name.startswith("acc"):
            actor = variable_name[len("acc"):]
            return self._actor_acc(actor)

        if variable_name.startswith("speed"):
            actor = variable_name[len("speed"):]
            return self._actor_speed(actor)

        if variable_name.startswith("brake"):
            actor = variable_name[len("brake"):]
            return self._actor_brake(actor)

        if variable_name.startswith("steer"):
            actor = variable_name[len("steer"):]
            return self._actor_steer(actor)

        if variable_name.startswith("isChangingLane"):
            actor = variable_name[len("isChangingLane"):]
            return self._actor_lane_changing(actor)

        if variable_name.startswith("isOverTaking"):
            actor = variable_name[len("isOverTaking"):]
            return self._ego_overtaking(actor)

        if variable_name.startswith("isTurningAround"):
            actor = variable_name[len("isTurningAround"):]
            return self._ego_event(actor, "isTurningAround")

        raise RuntimeError("Unsupported signal variable '{}'".format(variable_name))

    def _split_aggregation(self, variable_name):
        for aggregator in self.AGGREGATORS:
            if variable_name.startswith(aggregator):
                inner_variable = variable_name[len(aggregator):]
                if inner_variable and self._looks_like_signal(inner_variable):
                    return aggregator, inner_variable
        return None

    def _looks_like_signal(self, variable_name):
        if any(variable_name.startswith(base_signal) for base_signal in self.BASE_SIGNALS):
            return True
        return self._split_aggregation(variable_name) is not None

    def to_rtamt_data(self, signal_values):
        return {
            name: [[self.times[idx], value] for idx, value in enumerate(values)]
            for name, values in signal_values.items()
        }

    def _target_position(self):
        return self.trace_data.get("ego", {}).get("destination", {}).get("location")

    def _actor_speed(self, actor):
        if actor == "ego":
            return [frame["ego"]["Chasis"]["speed"] for frame in self.frames]
        return [motion.get("speed", 0.0) for motion in self._npc_motion(actor)]

    def _actor_brake(self, actor):
        if actor == "ego":
            return [frame["ego"]["Chasis"]["brake"] for frame in self.frames]
        return [motion.get("brake", 0.0) for motion in self._npc_motion(actor)]

    def _actor_steer(self, actor):
        if actor == "ego":
            yaws = [
                frame["ego"].get("pose", {}).get("rotation", {}).get("yaw", 0.0)
                for frame in self.frames
            ]
            return self._yaw_delta_series(yaws)
        return self._yaw_delta_series([motion.get("yaw", 0.0) for motion in self._npc_motion(actor)])

    def _actor_acc(self, actor):
        if actor == "ego":
            return [self._vector_norm(frame["ego"]["pose"]["linearAcceleration"]) for frame in self.frames]
        return [self._vector_norm(motion.get("linearAcceleration", {})) for motion in self._npc_motion(actor)]

    def _actor_position(self, actor):
        if actor == "ego":
            return [frame["ego"]["pose"]["position"] for frame in self.frames]
        return [motion.get("location", {}) for motion in self._npc_motion(actor)]

    def _actor_lane_changing(self, actor):
        if actor == "ego":
            return [bool(frame["ego"].get("isLaneChanging", False)) for frame in self.frames]
        return [bool(motion.get("isLaneChanging", False)) for motion in self._npc_motion(actor)]

    def _ego_overtaking(self, actor):
        if actor != "ego":
            raise RuntimeError("Overtaking is only available for ego because NPC traces do not contain this signal")
        return [
            bool(frame["ego"].get("isOverTaking", False))
            for frame in self.frames
        ]

    def _ego_event(self, actor, field_name):
        if actor != "ego":
            raise RuntimeError("{} is only available for ego because NPC traces do not contain this signal".format(field_name))
        return [bool(frame["ego"].get(field_name, False)) for frame in self.frames]

    def _npc_motion(self, actor):
        npc = self.npcs.get(actor)
        if npc is None:
            raise RuntimeError("Unknown NPC actor '{}'".format(actor))
        motion = npc.get("motion", [])
        if len(motion) < len(self.frames):
            motion = motion + [motion[-1]] * (len(self.frames) - len(motion))
        return motion[:len(self.frames)]

    def _distance(self, actor_a, actor_b):
        if actor_a == "ego" and actor_b in self.npcs:
            truth_distance = self._truth_distance_to_ego(actor_b)
            if truth_distance is not None:
                return truth_distance

        positions_a = self._position_series(actor_a)
        positions_b = self._position_series(actor_b)
        return [self._position_distance(pos_a, pos_b) for pos_a, pos_b in zip(positions_a, positions_b)]

    def _position_series(self, actor):
        if actor in self.special_targets:
            target = self.special_targets[actor]
            if target is None:
                raise RuntimeError("Special target '{}' is not available in trace".format(actor))
            return [target for _ in self.frames]
        return self._actor_position(actor)

    def _truth_distance_to_ego(self, actor):
        values = []
        for frame in self.frames:
            obs_list = frame.get("truth", {}).get("obsList", [])
            matched = None
            for obs in obs_list:
                if obs.get("name") == actor:
                    matched = obs
                    break
            if matched is None:
                return None
            values.append(matched.get("distToEgo", float("inf")))
        return values

    def _parse_dist_variable(self, variable_name):
        suffix = variable_name[len("dist"):]
        candidates = sorted(self.actors + list(self.special_targets.keys()), key=len, reverse=True)
        for actor_a in candidates:
            if suffix.startswith(actor_a):
                actor_b = suffix[len(actor_a):]
                if actor_b in candidates:
                    return actor_a, actor_b
        raise RuntimeError("Cannot parse distance variable '{}'".format(variable_name))

    @staticmethod
    def _vector_norm(vector):
        return math.sqrt(
            float(vector.get("x", 0.0)) ** 2
            + float(vector.get("y", 0.0)) ** 2
            + float(vector.get("z", 0.0)) ** 2
        )

    @staticmethod
    def _position_distance(pos_a, pos_b):
        return math.sqrt(
            (float(pos_a.get("x", 0.0)) - float(pos_b.get("x", 0.0))) ** 2
            + (float(pos_a.get("y", 0.0)) - float(pos_b.get("y", 0.0))) ** 2
            + (float(pos_a.get("z", 0.0)) - float(pos_b.get("z", 0.0))) ** 2
        )

    @staticmethod
    def _cumulative_std(values):
        result = []
        prefix = []
        for value in values:
            prefix.append(float(value))
            mean = sum(prefix) / len(prefix)
            variance = sum((item - mean) ** 2 for item in prefix) / len(prefix)
            result.append(math.sqrt(variance))
        return result

    @staticmethod
    def _cumulative_avg(values):
        result = []
        total = 0.0
        for idx, value in enumerate(values, 1):
            total += float(value)
            result.append(total / idx)
        return result

    @staticmethod
    def _cumulative_max(values):
        result = []
        current = None
        for value in values:
            value = float(value)
            current = value if current is None else max(current, value)
            result.append(current)
        return result

    @staticmethod
    def _cumulative_min(values):
        result = []
        current = None
        for value in values:
            value = float(value)
            current = value if current is None else min(current, value)
            result.append(current)
        return result

    @staticmethod
    def _count_true_edges(values):
        result = []
        count = 0
        previous = False
        for value in values:
            current = bool(value)
            if current and not previous:
                count += 1
            result.append(count)
            previous = current
        return result

    @staticmethod
    def _duration(values):
        result = []
        duration = 0
        for value in values:
            if bool(value):
                duration += 1
            result.append(duration)
        return result

    @staticmethod
    def _switch_count(values):
        result = []
        count = 0
        previous = bool(values[0]) if values else False
        for idx, value in enumerate(values):
            current = bool(value)
            if idx > 0 and current != previous:
                count += 1
            result.append(count)
            previous = current
        return result

    @staticmethod
    def _yaw_delta_series(yaws):
        result = []
        previous = None
        for yaw in yaws:
            yaw = float(yaw)
            if previous is None:
                result.append(0.0)
            else:
                result.append(TraceSignalBuilder._angle_delta(yaw, previous))
            previous = yaw
        return result

    @staticmethod
    def _angle_delta(current, previous):
        return (current - previous + 180.0) % 360.0 - 180.0

    def _aggregate(self, aggregator, values):
        if aggregator == "avg":
            return self._cumulative_avg(values)
        if aggregator == "std":
            return self._cumulative_std(values)
        if aggregator == "max":
            return self._cumulative_max(values)
        if aggregator == "min":
            return self._cumulative_min(values)
        if aggregator == "count":
            return self._count_true_edges(values)
        if aggregator == "duration":
            return self._duration(values)
        if aggregator == "switch_count":
            return self._switch_count(values)
        raise RuntimeError("Unsupported aggregator '{}'".format(aggregator))


class BasicSTLEvaluator(object):
    PREDICATE_PATTERN = re.compile(
        r"^\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>-?\d+(?:\.\d+)?)\s*$"
    )

    TEMPORAL_PATTERN = re.compile(r"^\s*(?P<op>eventually|always)\((?P<body>.*)\)\s*$")

    def evaluate(self, stl_rule, signals):
        temporal_match = self.TEMPORAL_PATTERN.match(stl_rule)
        if temporal_match:
            temporal_op = temporal_match.group("op")
            robustness, truth_values = self._predicate_series(temporal_match.group("body"), signals)
            score = max(robustness) if temporal_op == "eventually" else min(robustness)
            satisfied = any(truth_values) if temporal_op == "eventually" else all(truth_values)
            return {"robustness": score, "satisfied": satisfied}

        robustness, truth_values = self._predicate_series(stl_rule, signals)
        score = robustness[0]
        return {"robustness": score, "satisfied": truth_values[0]}

    def _predicate_series(self, predicate, signals):
        match = self.PREDICATE_PATTERN.match(predicate)
        if not match:
            raise RuntimeError("Fallback evaluator only supports simple predicates, got '{}'".format(predicate))

        variable = match.group("var")
        operator = match.group("op")
        threshold = float(match.group("value"))
        values = signals[variable]
        robustness = [self._robustness(value, operator, threshold) for value in values]
        truth_values = [self._truth(value, operator, threshold) for value in values]
        return robustness, truth_values

    @staticmethod
    def _robustness(value, operator, threshold):
        value = float(value)
        if operator in (">", ">="):
            return value - threshold
        if operator in ("<", "<="):
            return threshold - value
        if operator == "==":
            return -abs(value - threshold)
        if operator == "!=":
            return abs(value - threshold)
        raise RuntimeError("Unsupported comparator '{}'".format(operator))

    @staticmethod
    def _truth(value, operator, threshold):
        value = float(value)
        if operator == ">":
            return value > threshold
        if operator == ">=":
            return value >= threshold
        if operator == "<":
            return value < threshold
        if operator == "<=":
            return value <= threshold
        if operator == "==":
            return value == threshold
        if operator == "!=":
            return value != threshold
        raise RuntimeError("Unsupported comparator '{}'".format(operator))


def summarize_results(results, weights=None):
    weights = weights or {}
    grouped = {}
    for result in results:
        grouped.setdefault(result["oracle"], []).append(float(result["robustness"]))

    summary = {}
    total_score = 0.0
    for oracle_name, robustness_values in grouped.items():
        average_robustness = sum(robustness_values) / len(robustness_values)
        weight = float(weights.get(oracle_name, 1.0))
        score_sign = -1.0 if oracle_name == "safetyOracle" else 1.0
        weighted_score = average_robustness * weight * score_sign
        summary[oracle_name] = {
            "count": len(robustness_values),
            "average_robustness": average_robustness,
            "weight": weight,
            "score_sign": score_sign,
            "weighted_score": weighted_score,
        }
        total_score += weighted_score

    summary["total_score"] = total_score
    return summary


def analyze(trace_path, spec_path, weights=None):
    with open(trace_path, "r") as trace_file:
        trace_data = json.load(trace_file)

    builder = TraceSignalBuilder(trace_data)
    evaluator = BasicSTLEvaluator()
    results = []

    for rule in parse_spec_file(spec_path):
        signals = builder.build_many(rule["variables"])
        evaluation = evaluator.evaluate(rule["stl"], signals)
        results.append({
            "oracle": rule["oracle"],
            "raw": rule["raw"],
            "stl": rule["stl"],
            "variables": rule["variables"],
            "robustness": evaluation["robustness"],
            "satisfied": evaluation["satisfied"],
        })

    return {
        "rules": results,
        "summary": summarize_results(results, weights),
    }


def main():
    parser = argparse.ArgumentParser(description="Basic OpenBehavior spec analyzer")
    parser.add_argument("--trace", required=True, help="Path to trace json")
    parser.add_argument("--spec", required=True, help="Path to .spec file")
    parser.add_argument("--safety-weight", type=float, default=1.0, help="Weight for safetyOracle")
    parser.add_argument("--beh-weight", type=float, default=1.0, help="Weight for BehOracle")
    args = parser.parse_args()
    weights = {
        "safetyOracle": args.safety_weight,
        "BehOracle": args.beh_weight,
    }
    print(json.dumps(analyze(args.trace, args.spec, weights), indent=2))


if __name__ == "__main__":
    main()
