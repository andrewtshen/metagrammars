import pandas as pd
from sexpdata import loads, dumps, Symbol # Everything we need to read SyGuS files (.sl)
import typing
import re
import subprocess
import copy
from pathlib import Path


"""
Things to do:
1. Create a function that can parse a SyGuS problem (.sl file)
2. Create a function that can replace a grammar using metagrammar rules
3. Create a function that can write back a modified SyGuS benchmark
4. Create a script to run solver on specific file
5. ???
6. Profit
"""


def remove_sexp_comments(contents: list):
    """
    Remove all comments from contents of sexp.
    Returns resulting sexp.
    """
    return [ line for line in contents if line and line[0] != ';' ]


def get_sexp(filename: str):
    """
    Reads a (.sl) using sexpdata to parse through the information.
    Returns a list of Symbols.
    """
    try:
        with open(filename, 'r') as f:
            contents = f.readlines()
            return loads('(' + ''.join(remove_sexp_comments(contents)) + ')')
    except:
        raise ValueError("Error with reading filename: ", filename)


def export_sexp_raw(sexp):
    """
    Returns sexp with replaced special character #.
    """
    return dumps(sexp).replace('\\#', '#')


def export_sexp(sexp):
    """
    Returns sexp ready to write back as SyGuS problem (.sl file).
    """
    return export_sexp_raw(sexp)[1:-1]


def create_symbol(term: str):
    """
    Returns a Symbol containing term.
    """
    return loads(term)


def starts_with_symbol(test_symbol, symbol):
    return type(test_symbol) == list and test_symbol[0] == symbol


class SyGuSProblem:
    def __init__(self, name: str):
        """
        Name: Name of the problem
        Symbols: Symbols currently contained held in the problem
        """
        self.name = name
        self.symbols = []
        self.logic = []
        self.defines_and_declares = []
        # TODO: Look at spec for exact implementation, might not have some of these
        self.synth_fun = []
        self.synth_fun_name = []
        self.synth_fun_parameters = []
        self.synth_fun_ret_type = []
        self.synth_fun_terminals = []
        self.synth_fun_non_terminals = []
        self.constraints = []
        self.check_synth = []

    
    def __str__(self):
        return "SyGuS Problem expression" + " ".join(map(str, self.symbols))

    
    def pretty_format(self):
        """
        Format the symbols a little bit nicer so that it is easier to read.
        """
        if self.symbols == None:
            return "No symbols to print"
        ret = ""
        for s in self.symbols:
            ret += str(s) + "\n"
        return ret


    def combine(self):
        return [self.logic +
                [self.synth_fun + self.synth_fun_name + [self.synth_fun_parameters] + self.synth_fun_ret_type +
                 [self.synth_fun_terminals] + [self.synth_fun_non_terminals]] +
                self.defines_and_declares +
                self.constraints +
                self.check_synth][0] # TODO: Less janky way to combine list together


    def fmt(self):
        all_symbols = self.combine()
        return " ".join(map(str, all_symbols))


    def get_grammar(self):
        """
        Gets the current grammar by searching for "synth-fun" and returning the first matching portion of 
        the sexp.
        # TODO: Might be old/dated
        """
        for s in self.symbols:
            synth_fun_symbol = create_symbol("synth-fun")
            if type(s) == list and s[0] == synth_fun_symbol:
                return s


    def get_synth_fun_parameters(self):
        return self.synth_fun_parameters


    def set_grammar(self, new_symbols: list):
        """
        Set a new grammar by replacing the old one. A new list of symbols is created by slicing out the old
        grammar and inserting the new grammar.
        # TODO: Might be old/dated
        """
        grammar_idx = 0
        for s in self.symbols:
            synth_fun_symbol = create_symbol("synth-fun")
            if type(s) == list and s[0] == synth_fun_symbol:
                break
            grammar_idx += 1

        self.symbols = self.symbols[:grammar_idx] + new_symbols + self.symbols[grammar_idx+1:]


    def set_prod_rules(self, new_rule):
        """
        Set a specific production rule to a new production rule
        # TODO: Set a specific rule rather than 0
        """
        self.synth_fun_non_terminals[0][2] = new_rule


    def get_symbols(self):
        """
        Gets all of the current symbols stored.
        """
        return self.symbols


    def read_sygus_problem(
        self,
        src_dir: str,
        problem_name: str,
    ):
        """
        Reads a SyGuS problem from a given a file.
        Returns a SyGuSProblem instance.
        """
        SyGuS_sexp = get_sexp(src_dir + problem_name)
        self.symbols = SyGuS_sexp
        set_logic_symbol = create_symbol("set-logic")
        define_fun_symbol = create_symbol("define-fun")
        declare_var_symbol = create_symbol("declare-var")
        synth_fun_symbol = create_symbol("synth-fun")
        constraint_symbol = create_symbol("constraint")
        check_synth_symbol = create_symbol("check-synth")

        for s in self.symbols:
            if starts_with_symbol(s, set_logic_symbol):
                # Handle the logic symbol
                self.logic.append(s)

            elif starts_with_symbol(s, synth_fun_symbol):
                # Handle the synth-fun
                for i, s1 in enumerate(s):
                    if i == 0:
                        self.synth_fun.append(s1)
                    elif i == 1:
                        # Get the name
                        self.synth_fun_name.append(s1)
                    elif i == 2:
                        # Get the parameters
                        self.synth_fun_parameters.append(s1)
                    elif i == 3:
                        # Get the return type
                        self.synth_fun_ret_type.append(s1)
                    elif i == 4:
                        # Get the terminals
                        self.synth_fun_terminals.append(s1)
                    else:
                        # Get the non-terminals (production rules)
                        self.synth_fun_non_terminals.append(s1)
            
            elif starts_with_symbol(s, define_fun_symbol) or starts_with_symbol(s, declare_var_symbol):
                # Handle defines and declares
                self.defines_and_declares.append(s)
            
            elif starts_with_symbol(s, constraint_symbol):
                # Handle the constraint symbol
                self.constraints.append(s)

            elif starts_with_symbol(s, check_synth_symbol):
                self.check_synth.append(s)

            else:
                ValueError("Unknown Symbol Type: ", s)
    

        # Adjust brackets to make indexing easier later
        self.synth_fun_parameters = self.synth_fun_parameters[0]
        self.synth_fun_non_terminals = self.synth_fun_non_terminals[0]
        self.synth_fun_terminals = self.synth_fun_terminals[0]
        # print("LOGIC:", self.logic)
        # print("SYNTH_FUN:", self.synth_fun)
        # print("synth_fun_name", self.synth_fun_name)
        # print("synth_fun_parameters", self.synth_fun_parameters)
        # print("synth_fun_ret_type", self.synth_fun_ret_type)
        # print("synth_fun_terminals", self.synth_fun_terminals)
        # print("synth_fun_non_terminals", self.synth_fun_non_terminals)
        # print("DEFINE", self.defines_and_declares)
        # print("CONSTRAINT", self.constraints)
        # print("CHECK", self.check_synth)


    def write_sygus_problem(
        self,
        dest_dir: str,
        problem_name: str,
    ):
        """
        Write a SyGuS problem from a SyGuSProblem instance to a certain file.
        Return boolean value of if write succeeded.
        """
        data = export_sexp(self.combine())
        filename = dest_dir + problem_name

        # Create directory if path to filename does not already exist
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            f.write(data)


    def benchmark_problem(
        self,
        src_dir: str,
        problem_name: str,
        use_stats: bool = True,
        timeout: int = 300,
        seed: int = 1,
    ) -> list:
        """
        Run benchmarks on a SyGuS file and return as an array
        """
        # Construct shell command
        sh_cmd = ["cvc5"]
        if use_stats:
            sh_cmd.append("--stats")
        if timeout:
            sh_cmd.append("--tlimit=" + str(timeout)) # Timeout in MS
        if seed:
            sh_cmd.append("--seed=" + str(seed))
        sh_cmd.append(src_dir + problem_name)

        # Run shell commmand
        output = subprocess.run(sh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        output = output.stdout.strip("\n")

        # Check if unsat or not
        pattern = "(define-fun .*)"
        compiled = re.compile(pattern)
        result = compiled.search(output)
        if not result:
            result = "timeout"
        else:
            result = result.group(1).strip()

        # Compute the total time of execution
        pattern = "global::totalTime = (.*)ms"
        compiled = re.compile(pattern)
        ret = compiled.search(output)
        time_to_solve = ret.group(1).strip()

        return result, time_to_solve


class Metagrammar:
    """
    A list of metagrammar rules
    """

    # Rules to Add
    # ============
    # 1 - create Start nonterminal(NT) for bitvector type
    # 2 - create BoolNT for Bool type
    # 3 - add input parameters to appropriate NT
    # 4- add any constants in the benchmark to appropriate NT
    # 5 - add "(bvadd Start Start) to Start", and "(bvsub Start Start) to Start"
    # 6 - add "(bvneg Start)" and "(bvnot Start)" operators to Start
    # 7 - add "(= Start Start)" operator to appropriate BoolNT
    # 8 - add "(ite BoolNT Start Start)" operator to Start

    def __init__(self) -> list:

        # Rules for terminals
        def create_start_bv_terminal(p):
            return [create_symbol('Start'), [create_symbol('_'), create_symbol('BitVec'), 4]]

        def create_start_bool_terminal(p):
            return [create_symbol('BoolNT'), create_symbol('Bool')]

        # Rules for non terminals
        def rule_input_params_NT(p):
            parameters = p.get_synth_fun_parameters()
            return [parameter[0] for parameter in parameters]

        def rule_constants_NT(p):
            

        def rule_bvadd_NT(p):
            return [create_symbol('bvadd'), create_symbol('Start'), create_symbol('Start')]

        def rule_bvsub_NT(p):
            return [create_symbol('bvsub'), create_symbol('Start'), create_symbol('Start')]

        def rule_bvneg_NT(p):
            return [create_symbol('bvneg'), create_symbol('Start')]

        def rule_bvnot_NT(p):
            return [create_symbol('bvnot'), create_symbol('Start')]

        def rule_equals_NT(p):
            return [create_symbol('bvnot'), create_symbol('Start')]

        def rule_ite_NT(p):
            return [create_symbol('ite'), create_symbol('BoolNT'), create_symbol('Start'), create_symbol('Start')]


        self.non_terminal_rules = [
            rule_input_params_NT,
            rule_bvadd_NT,
            rule_bvsub_NT,
            rule_bvneg_NT,
            rule_bvnot_NT,
            rule_equals_NT,
            rule_ite_NT,
        ]

        self.terminal_rules = [
            create_start_bv_terminal,
            create_start_bool_terminal
        ]

    def apply(self, p: SyGuSProblem) -> list:
        # TODO: Apply rules to p
        non_terminals = []
        terminals = []

        for rule in self.non_terminal_rules:
            non_terminals.append(rule(p))

        for rule in self.terminal_rules:
            terminals.append(rule(p))

        return [non_terminals, terminals]



if __name__ == "__main__":
    print("Starting Program\n")

    # Create parameters
    p = SyGuSProblem("inv0.sl")
    p.read_sygus_problem("benchmarks/lib/General_Track/bv-conditional-inverses/", "find_inv_bvsge_bvadd_4bit.sl")


    # Try getting output from metagrammar
    m = Metagrammar()
    generated_terminals, generated_non_terminals = m.apply(p)[0], m.apply(p)[1]
    print("GENERATED TERMINALS: ", generated_terminals)
    print("GENERATED NON TERMINALS: ", generated_non_terminals)

    
    # Test Different Grammars using 1 Dropout
    # print("TERMINALS: ", p.synth_fun_terminals)
    # print("NON TERMINALS: ", p.synth_fun_non_terminals)
    # prod_rules = p.synth_fun_non_terminals[0][2]
    # for i in range(len(prod_rules)):
    #     new_rule = prod_rules[:i] + prod_rules[i+1:]
    #     print("Dropping out: ", i, " | New rule: ", new_rule)
    #     # Put new rule into copy
    #     p1 = copy.deepcopy(p)
    #     p1.set_prod_rules(new_rule)
    #     p1.write_sygus_problem("results/", "test.sl")
    #     result, time_to_solve = p1.benchmark_problem("results/", "test.sl")
    #     print("Result: ", result, " | Time to Solve: ", time_to_solve, "\n")

    print("Ending Program")

