from __future__ import print_function

import json
import re
import sys


STL_keywords = ["always", "eventually", "until", "F", "G", "U"]
keywords = [
    "count",
    "avg",
    "std",
    "max",
    "min",
    "duration",
    "switch_count",
    "acc",
    "speed",
    "brake",
    "steer",
    "dist",
    "distance",
    "changingLane",
    "ChangingLane",
    "isChangingLane",
    "Overtaking",
    "overtaking",
    "isOverTaking",
    "TurningAround",
    "turningAround",
    "isTurningAround",
]

TEMPORAL_ALIASES = {
    "F": "eventually",
    "G": "always",
    "U": "until",
    "eventually": "eventually",
    "always": "always",
    "until": "until",
}

FUNCTION_ALIASES = {
    "distance": "dist",
    "changingLane": "isChangingLane",
    "ChangingLane": "isChangingLane",
    "overtaking": "isOverTaking",
    "Overtaking": "isOverTaking",
    "turningAround": "isTurningAround",
    "TurningAround": "isTurningAround",
}

COMPARATORS = [">=", "<=", "==", "!=", ">", "<"]


def process_raw_rule(raw_rule, return_variables=False):
    """
    Convert OpenBehavior spec syntax into an STL string that rtamt can parse.
    """
    variables = []
    expression = _strip_outer_brackets(raw_rule.strip())
    expression = _replace_api_calls(expression, variables)
    expression = _normalize_temporal_operators(expression)
    variables = _dedupe(variables)
    if return_variables:
        return expression, variables
    return expression


def parse_spec_line(line, line_no=None):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        location = "line {}".format(line_no) if line_no is not None else "spec line"
        raise RuntimeError("{} is missing '=': {}".format(location, line.rstrip()))

    oracle_name, raw_rule = stripped.split("=", 1)
    stl_rule, variables = process_raw_rule(raw_rule, return_variables=True)
    return {
        "oracle": oracle_name.strip(),
        "raw": raw_rule.strip(),
        "stl": stl_rule,
        "variables": variables,
    }


def parse_spec_file(path):
    parsed_rules = []
    with open(path, "r") as spec_file:
        for line_no, line in enumerate(spec_file, 1):
            parsed_rule = parse_spec_line(line, line_no)
            if parsed_rule is not None:
                parsed_rules.append(parsed_rule)
    return parsed_rules


def parse_spec_file_grouped(path):
    grouped_rules = {}
    for parsed_rule in parse_spec_file(path):
        grouped_rules.setdefault(parsed_rule["oracle"], []).append(parsed_rule)
    return grouped_rules


def extract_stl_keywords(raw_rule):
    return process_raw_rule(raw_rule)


def extract_keywords(temp):
    expression, _ = process_raw_rule(temp, return_variables=True)
    return expression


def del_bracket(s):
    return _strip_outer_brackets(s)


def del_all_bracket(s):
    return s.replace("(", "").replace(")", "")


def _dedupe(items):
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _strip_outer_brackets(expression):
    expression = expression.strip()
    while expression.startswith("(") and expression.endswith(")"):
        try:
            close_idx = _find_matching_paren(expression, 0)
        except RuntimeError:
            break
        if close_idx != len(expression) - 1:
            break
        expression = expression[1:-1].strip()
    return expression


def _find_matching_paren(expression, open_idx):
    depth = 0
    for idx in range(open_idx, len(expression)):
        if expression[idx] == "(":
            depth += 1
        elif expression[idx] == ")":
            depth -= 1
            if depth == 0:
                return idx
    raise RuntimeError("Unmatched '(' in expression: {}".format(expression))


def _read_identifier(expression, start):
    idx = start
    while idx < len(expression) and (expression[idx].isalnum() or expression[idx] == "_"):
        idx += 1
    return expression[start:idx], idx


def _skip_spaces(expression, start):
    idx = start
    while idx < len(expression) and expression[idx].isspace():
        idx += 1
    return idx


def _is_identifier_start(char):
    return char.isalpha() or char == "_"


def _is_api_function(name):
    return name in keywords or name in FUNCTION_ALIASES


def _canonical_function_name(name):
    return FUNCTION_ALIASES.get(name, name)


def _sanitize_api_expression(expression):
    return re.sub(r"[^0-9A-Za-z_]+", "", expression)


def _replace_api_calls(expression, variables, collect=True):
    result = []
    idx = 0
    while idx < len(expression):
        char = expression[idx]
        if not _is_identifier_start(char):
            result.append(char)
            idx += 1
            continue

        name, name_end = _read_identifier(expression, idx)
        call_start = _skip_spaces(expression, name_end)
        if call_start >= len(expression) or expression[call_start] != "(":
            result.append(name)
            idx = name_end
            continue

        call_end = _find_matching_paren(expression, call_start)
        inner = expression[call_start + 1:call_end]
        if name in TEMPORAL_ALIASES:
            inner_expression = _replace_api_calls(inner, variables, collect=True)
            result.append("{}({})".format(name, inner_expression))
        elif _is_api_function(name):
            inner_expression = _replace_api_calls(inner, variables, collect=False)
            variable_name = "{}{}".format(_canonical_function_name(name), _sanitize_api_expression(inner_expression))
            if collect:
                variables.append(variable_name)
            result.append(variable_name)
        else:
            inner_expression = _replace_api_calls(inner, variables, collect=collect)
            result.append("{}({})".format(name, inner_expression))

        idx = call_end + 1

    return "".join(result)


def _normalize_temporal_operators(expression):
    result = []
    idx = 0
    while idx < len(expression):
        char = expression[idx]
        if not _is_identifier_start(char):
            result.append(char)
            idx += 1
            continue

        name, name_end = _read_identifier(expression, idx)
        call_start = _skip_spaces(expression, name_end)
        if name not in TEMPORAL_ALIASES or call_start >= len(expression) or expression[call_start] != "(":
            result.append(name)
            idx = name_end
            continue

        call_end = _find_matching_paren(expression, call_start)
        inner = expression[call_start + 1:call_end]
        inner = _normalize_temporal_operators(inner)
        alias = TEMPORAL_ALIASES[name]

        after_call = _skip_spaces(expression, call_end + 1)
        comparator = _read_comparator(expression, after_call)
        if comparator is not None:
            rhs_start = _skip_spaces(expression, after_call + len(comparator))
            rhs_end = _find_rhs_end(expression, rhs_start)
            rhs = expression[rhs_start:rhs_end].strip()
            result.append("{}({} {} {})".format(alias, inner.strip(), comparator, rhs))
            idx = rhs_end
        else:
            result.append("{}({})".format(alias, inner))
            idx = call_end + 1

    return "".join(result)


def _read_comparator(expression, start):
    for comparator in COMPARATORS:
        if expression.startswith(comparator, start):
            return comparator
    return None


def _find_rhs_end(expression, start):
    depth = 0
    idx = start
    while idx < len(expression):
        char = expression[idx]
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and _is_logical_boundary(expression, idx):
            break
        idx += 1
    return idx


def _is_logical_boundary(expression, idx):
    return (
        expression.startswith(" and ", idx)
        or expression.startswith(" or ", idx)
        or expression.startswith("&&", idx)
        or expression.startswith("||", idx)
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_rule.py <path-to-spec>")
        sys.exit(1)
    print(json.dumps(parse_spec_file(sys.argv[1]), indent=2))
