#!/usr/bin/env python

from __future__ import print_function

import importlib.util
import json
import os
import random
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
REGISTER_PATH = os.path.join(PROJECT_ROOT, "register.json")


def _abs(path, base):
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(base, path))


def _read_config(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        if ext == ".json":
            return json.load(f) or {}
        if ext in (".yaml", ".yml"):
            import yaml
            return yaml.safe_load(f) or {}
    raise RuntimeError("Unsupported config file: {}".format(path))


def _get(data, key):
    cur = data
    for part in str(key).split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise RuntimeError("Key '{}' not found in config".format(key))
        cur = cur[part]
    return cur


def _sample_value(value):
    if isinstance(value, list) and len(value) == 2:
        low, high = value
        if isinstance(low, (int, float)) and isinstance(high, (int, float)):
            if isinstance(low, int) and isinstance(high, int):
                return random.randint(low, high)
            return random.uniform(float(low), float(high))
    return value


def _config_sources(entry, base):
    sources = {}
    for name, path in (entry.get("param_sources") or {}).items():
        if isinstance(path, dict):
            path = path.get("path") or path.get("file") or path.get("config")
        sources[name] = _abs(path, base)
    return sources


def _params_from_entry(entry, configs):
    params = entry.get("params")
    if not params:
        merged = {}
        for cfg in configs.values():
            for name, value in cfg.items():
                merged[name] = _sample_value(value)
        return merged

    selected = {}
    for name, rule in params.items():
        if isinstance(rule, dict) and "value" in rule:
            selected[name] = rule["value"]
            continue

        source = rule.get("source") if isinstance(rule, dict) else rule
        key = rule.get("key") if isinstance(rule, dict) else None
        key = key or name
        if source not in configs:
            raise RuntimeError("Unknown config source '{}' for param '{}'".format(source, name))
        selected[name] = _sample_value(_get(configs[source], key))
    return selected


def load_agent_registry():
    with open(REGISTER_PATH, "r") as f:
        raw = json.load(f)

    registry = {}
    for entry in raw.get("register", []):
        agent_id = entry["id"]
        team_code = entry.get("model_paths")
        if not team_code:
            raise RuntimeError("Agent '{}' has no model_paths".format(agent_id))

        sources = _config_sources(entry, PROJECT_ROOT)
        configs = {name: _read_config(cfg_path) for name, cfg_path in sources.items()}
        first_config = next(iter(sources.values()), "")
        registry[agent_id] = {
            "id": agent_id,
            "team_code": _abs(team_code, PROJECT_ROOT),
            "agent_config": first_config,
            "params": _params_from_entry(entry, configs),
            "raw": entry,
        }

    return registry


def has_registered_agent(agent_id):
    return agent_id in load_agent_registry()


def get_registered_agent(agent_id):
    return load_agent_registry().get(agent_id)


def _load_team_code(agent_id, team_code):
    module_name = "_openbehavior_agent_{}".format(agent_id.replace("-", "_"))
    if module_name in sys.modules:
        return sys.modules[module_name]

    folder = os.path.dirname(team_code)
    if folder not in sys.path:
        sys.path.insert(0, folder)

    spec = importlib.util.spec_from_file_location(module_name, team_code)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _apply_params(agent, params):
    target = getattr(agent, "config", None) or agent
    for name, value in params.items():
        if isinstance(target, dict):
            target[name] = value
        else:
            setattr(target, name, value)


def create_registered_agent(agent_id):
    spec = get_registered_agent(agent_id)
    if not spec:
        raise RuntimeError("Agent '{}' is not registered".format(agent_id))

    module = _load_team_code(agent_id, spec["team_code"])
    entry_point = module.get_entry_point()
    agent_class = getattr(module, entry_point)

    agent = agent_class(spec.get("agent_config") or "")
    _apply_params(agent, spec.get("params", {}))
    return agent
