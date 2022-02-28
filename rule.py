from sygusproblem import SyGuSProblem
from sexp_utils import *

class Rule:
    def __init__(self, name: str, nonterminal_type, base_subrule):
        # Subrules for this specific nonterminal
        self.subrules = []

        # Whether rule is active or not
        self.active_rules = []

        # 3 nonterminals within this Rule, TODO: Change to arbitrary number later
        self.num_nonterminals = 3

        for _ in range(self.num_nonterminals):
            self.active_rules.append([])

        # Name of nonterminal
        self.name = name

        # Number of subrules
        self.num_rules = 0

        # Type of nonterminal
        self.nonterminal_type = nonterminal_type

        # Whether a new rule is active by default
        self.active_default = True

        # A subrule that is always in the generated grammar
        # TODO: See if there is anything we can do about removing the nonterminal entirely
        self.base_subrule = base_subrule


    def add_subrule(self, subrule, is_active: bool = True):
        self.subrules.append(subrule)

        # By default rule is activiated
        for i in range(self.num_nonterminals):
            self.active_rules[i].append(is_active)

        self.num_rules += 1


    def to_string(self) -> str:
        ret = ""
        for i in range(self.num_nonterminals):
            for is_active in self.active_rules[i]:
                if is_active:
                    ret += "1"
                else:
                    ret += "0"
        return ret


    def get_length(self) -> int:
        return self.num_nonterminals * self.num_rules


    def from_string(self, active_string: str):
        assert self.get_length() == len(active_string), "String incorrect length"
        for i in range(self.num_nonterminals):
            for j in range(self.num_rules):
                if active_string[i * self.num_rules + j] == "1":
                    self.active_rules[i][j] = 1
                else:
                    self.active_rules[i][j] = 0




    def generate_grammar(self, p: SyGuSProblem):
        ret = []
        for i in range(self.num_nonterminals):
            # Each tmp is a nonterminal in the grammar
            tmp = [create_symbol(self.name + str(i)), self.nonterminal_type, []]
            # Include base rule
            tmp[2].append(self.base_subrule(p))
            
            for rule, is_active in zip(self.subrules, self.active_rules[i]):
                if is_active:
                    for r in rule(p):
                        # Index 2 corresponds to the production rules
                        tmp[2].append(r)
            ret.append(tmp)
        return ret


    def get_num_rules(self):
        return self.num_rules


    def get_name(self):
        return self.name


    def get_num_nonterminals(self):
        return self.num_nonterminals


    def get_nonterminal_type(self):
        return self.nonterminal_type