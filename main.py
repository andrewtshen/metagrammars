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
    return type(test_symbol) == list and dumps(test_symbol[0]) == symbol


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
        return "SyGuS Problem expression: " + " ".join(map(str, self.symbols))

    
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
            if type(s) == list and dumps(s[0]) == "synth-fun":
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
            if type(s) == list and dumps(s[0]) == "synth-fun":
                break
            grammar_idx += 1

        self.symbols = self.symbols[:grammar_idx] + new_symbols + self.symbols[grammar_idx+1:]


    def create_with_new_grammar(self, new_grammar: list) -> list:
        """
        Set a new grammar by replacing the old one. A new list of symbols is created by slicing out the old
        grammar and inserting the new grammar.
        # TODO: Might be old/dated
        """
        grammar_idx = 0
        for s in self.symbols:
            if type(s) == list and dumps(s[0]) == "synth-fun":
                break
            grammar_idx += 1

        return self.symbols[:grammar_idx] + [self.synth_fun + self.synth_fun_name + [self.synth_fun_parameters] + self.synth_fun_ret_type + new_grammar] + self.symbols[grammar_idx+1:]


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


    def get_constants(self):
        # Get a set of constants used in the function definitions
        ret = set()
        for d in self.defines_and_declares:
            definition = d[0]
            if dumps(definition) == "define-fun":
                fn_name, fn_args, fn_ret = d[1], d[2], d[3]
                # We wish to ignore the first 4 arguments in the function tuple:
                # the define-fun, function name, args, return value
                for r in SyGuSProblem.get_constants_helper(d[4:]):
                    ret.add(r)
                # If a function does not take arguments, treat as constant
                if fn_args == []:
                    ret.add(dumps(fn_name))
                else:
                    # If has arguments, remove them from the ret
                    for args in fn_args:
                        ret.discard(dumps(args[0]))
        return list(ret)

    def get_return_type(self):
        print(self.synth_fun_ret_type)
        return self.synth_fun_ret_type[0]


    def get_constants_helper(d):
        ret = set()
        for d1 in d:
            if type(d1) == list:
                # This is a function, ignore the first value (function call)
                # print(d1[1:])
                for r in SyGuSProblem.get_constants_helper(d1[1:]):
                    ret.add(r)
            else:
                # This is just a constant
                ret.add(dumps(d1))
        return ret



    def get_variables(self):
        ret = set()
        for d in self.defines_and_declares:
            definition = d[0]
            if dumps(definition) == "declare-var":
                var_name = d[1]
                ret.add(dumps(var_name))
        return list(ret)


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

        for s in self.symbols:
            if starts_with_symbol(s, "set-logic"):
                # Handle the logic symbol
                self.logic.append(s)

            elif starts_with_symbol(s, "synth-fun"):
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
            
            elif starts_with_symbol(s, "define-fun") or starts_with_symbol(s, "declare-var"):
                # Handle defines and declares
                self.defines_and_declares.append(s)
            
            elif starts_with_symbol(s, "constraint"):
                # Handle the constraint symbol
                self.constraints.append(s)

            elif starts_with_symbol(s, "check-synth"):
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

    def __init__(self):
        self.rules = []


    def generate_grammar_from_rules(self, problem):
        ret = []
        problem_ret_type = problem.get_return_type()

        nonterminals_list = []

        for r in self.rules:

            # Insert the rule into the right plan in the list of terminals

            rule_type = r.get_nonterminal_type()
            if rule_type == problem_ret_type:
                # Note: Need to insert at i to ensure that name0 is first in list
                for i in range(r.get_num_nonterminals()):
                    nonterminals_list.insert(i, [create_symbol(r.get_name() + str(i)), rule_type])
            else:
                for i in range(r.get_num_nonterminals()):
                    nonterminals_list.append([create_symbol(r.get_name() + str(i)), rule_type])

            # Use the rule to generate grammar for that non terminal.
            for nt in r.generate_grammar(problem):
                ret.append([nt])

        ret.insert(0, nonterminals_list)
        return ret


    def add_rule(self, rule):
        self.rules.append(rule)


    def write_problem_with_grammar(
        self,
        problem,
        dest_dir: str,
        problem_name: str,
    ):
        """
        Write a SyGuS problem from a SyGuSProblem instance to a certain file.
        Return boolean value of if write succeeded.
        """
        g = self.generate_grammar_from_rules(problem)
        # print(problem)
        print(g)    
        data = export_sexp(problem.create_with_new_grammar(g))
        filename = dest_dir + problem_name


        # Create directory if path to filename does not already exist
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            f.write(data)


    # def benchmark(
    #     src_dir: str,
    #     problem_name: str,
    #     use_stats: bool = True,
    #     timeout: int = 300,
    #     seed: int = 1,
    # ) -> list:
    #     """
    #     Run benchmarks on a SyGuS file and return as an array
    #     """
    #     # Construct shell command
    #     sh_cmd = ["cvc5"]
    #     if use_stats:
    #         sh_cmd.append("--stats")
    #     if timeout:
    #         sh_cmd.append("--tlimit=" + str(timeout)) # Timeout in MS
    #     if seed:
    #         sh_cmd.append("--seed=" + str(seed))
    #     sh_cmd.append(src_dir + problem_name)

    #     # Run shell commmand
    #     output = subprocess.run(sh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    #     output = output.stdout.strip("\n")

    #     # Check if unsat or not
    #     pattern = "(define-fun .*)"
    #     compiled = re.compile(pattern)
    #     result = compiled.search(output)
    #     if not result:
    #         result = "timeout"
    #     else:
    #         result = result.group(1).strip()

    #     # Compute the total time of execution
    #     pattern = "global::totalTime = (.*)ms"
    #     compiled = re.compile(pattern)
    #     ret = compiled.search(output)
    #     time_to_solve = ret.group(1).strip()

    #     return result, time_to_solve



class Rule:

    def __init__(self, name: str, nonterminal_type):
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


    def add_subrule(self, subrule, is_active: bool = True):
        self.subrules.append(subrule)

        # By default rule is activiated
        for i in range(self.num_nonterminals):
            self.active_rules[i].append(is_active)

        self.num_rules += 1


    def to_string_format(self) -> str:
        ret = ""
        for i in str(self.num_nonterminals):
            for r in self.active_rules:
                if r:
                    ret += "1"
                else:
                    ret += "0"
        return ret


    def generate_grammar(self, p: SyGuSProblem):
        ret = []
        for i in range(self.num_nonterminals):
            print(self.name + str(i))
            tmp = [create_symbol(self.name + str(i)), self.nonterminal_type, []]
            for rule, is_active in zip(self.subrules, self.active_rules[i]):
                if is_active:
                    for r in rule(p):
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


if __name__ == "__main__":
    print("> Starting Program.")

    # Create parameters
    p = SyGuSProblem("inv0.sl")
    p.read_sygus_problem("benchmarks/lib/General_Track/bv-conditional-inverses/", "find_inv_bvsge_bvadd_4bit.sl")
    print(p)
    print("Constants:", p.get_constants())
    print("Variables:", p.get_variables())

    # Change to BitVec of all types
    r = Rule("BitVec", [create_symbol("_"), create_symbol("BitVec"), 4])
    r.add_subrule(lambda x: [create_symbol("BitVec0")])
    r.add_subrule(lambda x: [create_symbol("BitVec1")])
    r.add_subrule(lambda x: [create_symbol("BitVec2")])
    combinations = [
        [Symbol("BitVec0"), Symbol("BitVec0")],
        [Symbol("BitVec0"), Symbol("BitVec1")],
        [Symbol("BitVec0"), Symbol("BitVec2")],
        [Symbol("BitVec1"), Symbol("BitVec0")],
        [Symbol("BitVec1"), Symbol("BitVec1")],
        [Symbol("BitVec1"), Symbol("BitVec2")],
        [Symbol("BitVec2"), Symbol("BitVec0")],
        [Symbol("BitVec2"), Symbol("BitVec1")],
        [Symbol("BitVec2"), Symbol("BitVec2")]
    ]
    for a, b in combinations:
        r.add_subrule(lambda x: [[Symbol("bvneg"), a]])
        # r.add_rule(lambda x: [[Symbol("bvnot"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvadd"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvsub"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvand"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvadd"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvshlr"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvor"), a, b]])
        # r.add_rule(lambda x: [[Symbol("bvshl"), a, b]])
    r.add_subrule(lambda x: [create_symbol(c) for c in x.get_constants()])
    r.add_subrule(lambda x: [create_symbol(v) for v in x.get_variables()])
    # print(r.to_string_format())
    # print(r.generate_grammar(p))

    r1 = Rule("Int", create_symbol("Int"))
    r1.add_subrule(lambda x: [create_symbol("Int0")])
    r1.add_subrule(lambda x: [create_symbol("Int1")])
    r1.add_subrule(lambda x: [create_symbol("Int2")])
    r1.add_subrule(lambda x: [create_symbol(c) for c in x.get_constants()])
    r1.add_subrule(lambda x: [create_symbol(v) for v in x.get_variables()])


    m = Metagrammar()
    m.add_rule(r1)
    m.add_rule(r)

    # for a in r.generate_grammar(p):
    #     print(a)

    m.write_problem_with_grammar(p, "results/", "test.sl")

    # # Try getting output from metagrammar
    # m = Metagrammar()
    # generated_terminals, generated_non_terminals = m.apply(p)[0], m.apply(p)[1]
    # print("GENERATED TERMINALS: ", generated_terminals)
    # print("GENERATED NON TERMINALS: ", generated_non_terminals)

    # p.write_sygus_problem("results/", "test.sl")
    
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

    print("> Ending Program.")

