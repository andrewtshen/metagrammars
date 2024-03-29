import numpy as np
from sygusproblem import SyGuSProblem
from sexp_utils import *

class Rule:
    """
    A Rule is a group of subrules for a specific nonterminal type (Int, BitVec, etc).
    This class aims to represent a matrix of possibilities with subrules as the columns
    and "[Type]0", "[Type]1", "[Type]3", etc as the rows. These allows us to be more
    flexible with how we use the nonterminal type to generate specific grammars.
    This class also tracks which rules are active.

    Example of Rule/active matrix:
    ---------------------------------------------
         |  Subrule0  |  Subrule1  |  Subrule2  |
    -----|------------|------------|------------|
    Type0| Not Active |   Active   | Not Active |
    -----|------------|------------|------------|
    Type1|   Active   | Not Active |   Active   |
    -----|------------|------------|------------|
    Type2|   Active   | Not Active |   Active   | 
    ---------------------------------------------
    """

    def __init__(
        self, 
        name: str, 
        nonterminal_type, 
        base_subrule
    ):
        """
        Creates an empty Rule with no subrules included
        """

        # Subrules for this specific nonterminal
        self.subrules = []

        # Whether rule is active or not
        self.active_rules = []

        # 3 nonterminals within this Rule, TODO: Try changing number of nonterminals per type
        self.num_nonterminals = 3

        for _ in range(self.num_nonterminals):
            self.active_rules.append([])

        # Name of nonterminal
        self.name = name

        # Number of subrules
        self.num_subrules = 0

        # Type of nonterminal
        self.nonterminal_type = nonterminal_type

        # Whether a new rule is active by default
        self.active_default = True

        # A subrule that is always in the generated grammar
        # TODO: See if there is anything we can do about removing the nonterminal entirely
        self.base_subrule = base_subrule


    def add_subrule(
        self, 
        subrule, 
        is_active: bool = True
    ):
        """
        Adds a subrule to the Rule and active setting is set to is_active
        """
        self.subrules.append(subrule)

        # By default, added rule is activiated
        for i in range(self.num_nonterminals):
            self.active_rules[i].append(is_active)

        self.num_subrules += 1


    def to_string(self) -> str:
        """
        Converts the corresponding active_rules to string format for easy print
        """
        ret = ""
        for i in range(self.num_nonterminals):
            for is_active in self.active_rules[i]:
                if is_active:
                    ret += "1"
                else:
                    ret += "0"
        return ret


    def from_string(
        self, 
        active_string: str
    ):
        """
        Updates the corresponding active_rules based on active_string. Only use when
        initially loading the active_rules matrix
        """
        assert self.get_length() == len(active_string), "String incorrect length"
        for i in range(self.num_nonterminals):
            for j in range(self.num_subrules):
                if active_string[i * self.num_subrules + j] == "1":
                    self.active_rules[i][j] = 1
                else:
                    self.active_rules[i][j] = 0


    def set_active_rules(self, 
        new_rules: list
    ):
        """
        Updates active_rules at i, j with new_value
        """
        assert len(new_rules) == len(self.active_rules) and len(new_rules[0]) == len(self.active_rules[0])
        self.active_rules = new_rules


    def set_active_rule(self, 
        i: int, 
        j: int, 
        new_value: bool
    ):
        """
        Updates active_rules at i, j with new_value
        """
        assert 0 <= i and i < self.num_nonterminals and 0 <= j and j < self.num_subrules, "Out of bounds"
        self.active_rules[i][j] = new_value


    def generate_grammar(
        self, 
        p: SyGuSProblem
    ):
        """
        Generates grammar based on passed in problem as well as Rules matrix
        """
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


    """
    =============
    |GET Methods|
    =============
    """

    def get_active_rule(self, i, j) -> bool:
        """
        Returns whether specific subrule + nonterminal variant is active
        """
        assert 0 <= i and i < self.num_nonterminals and 0 <= j and j < self.num_subrules, "Out of bounds"
        return self.active_rules[i][j]


    def get_active_rules(self):
        """
        Returns active_rules matrix
        """
        return self.active_rules


    def get_length(self) -> int:
        """
        Gets the number of possible rules to be included. Alternatively, gets the 
        size of the matrix
        """
        return self.num_nonterminals * self.num_subrules


    def get_num_subrules(self):
        """
        Gets the number of rules
        """
        return self.num_subrules


    def get_name(self):
        """
        Gets the name of the nonterminal
        """
        return self.name


    def get_num_nonterminals(self):
        """
        Gets the number of nonterminals e.g. Type1, Type2, etc.
        """
        return self.num_nonterminals


    def get_nonterminal_type(self):
        """
        Gets type of the nonterminal
        """
        return self.nonterminal_type
