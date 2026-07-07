from srunner.osc2.symbol_manager.base_symbol import BaseSymbol

class JudgeSymbol(BaseSymbol):
    def __init__(self, name, judge_name, mode_value, scope):
        self.judge_name = judge_name
        self.mode_value = mode_value
        super().__init__(name, scope)

    def __str__(self):
        buf = self.judge_name
        buf += "=="
        buf += self.mode_value
        return buf
