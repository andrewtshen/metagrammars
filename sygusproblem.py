from sexp_utils import *

class SyGuSProblem:
    def __init__(self, name: str):
        """
        Creates an empty SyGuS problem. In order to use, load a SyGuS problem with the
        read_sygus_problem function. This will load the proper
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
        all_symbols = self.combine()
        return " ".join(map(str, all_symbols))


    def combine(self):
        """
        Combines the problem back into one large nested list
        """
        return [self.logic +
                [self.synth_fun + self.synth_fun_name + [self.synth_fun_parameters] + self.synth_fun_ret_type +
                 [self.synth_fun_terminals] + [self.synth_fun_non_terminals]] +
                self.defines_and_declares +
                self.constraints +
                self.check_synth][0] # TODO: Less janky way to combine list together


    """
    =============
    |SET Methods|
    =============
    """


    def create_with_new_grammar(
        self, 
        new_grammar: list
    ) -> list:
        """
        Set a new grammar by replacing the old one. A new list of symbols is created by slicing out the old
        grammar and inserting the new grammar.

        """
        grammar_idx = 0
        for s in self.symbols:
            if type(s) == list and dumps(s[0]) == "synth-fun":
                break
            grammar_idx += 1

        return self.symbols[:grammar_idx] + [self.synth_fun + self.synth_fun_name + [self.synth_fun_parameters] + self.synth_fun_ret_type + new_grammar] + self.symbols[grammar_idx+1:]


    """
    =============
    |GET Methods|
    =============
    """


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
        """
        Gets the synthesis function parameters
        """
        return self.synth_fun_parameters


    def get_symbols(self):
        """
        Gets all of the symbols from the problem
        """
        return self.symbols


    def get_constants(self):
        """
        Gets a set of constants used in the function definitions
        """
        ret = set()
        for d in self.defines_and_declares:
            definition = d[0]
            if dumps(definition) == "define-fun":
                fn_name, fn_args, fn_ret = d[1], d[2], d[3]
                # We wish to ignore the first 4 arguments in the function tuple:
                # the define-fun, function name, args, return value
                if fn_ret == self.synth_fun_ret_type[0]:
                    for r in SyGuSProblem.get_constants_helper(d[4:]):
                        ret.add(r)
                # # TODO: See if this case should be included. If a function does not take arguments, treat as constant
                # if fn_args == []:
                #     ret.add(dumps(fn_name))
                # If fn does have arguments, remove them from the ret since it is not a constant
                for args in fn_args:
                    ret.discard(dumps(args[0]))
        return list(ret)


    def get_return_type(self):
        """
        Gets the return type of the problem
        """
        return self.synth_fun_ret_type[0]


    def get_constants_helper(d):
        """
        Helper function that recusively finds any constants within the a single function
        """
        ret = set()
        for d1 in d:
            if type(d1) == list:
                # Since this is a function, ignore the first value (function call)
                for r in SyGuSProblem.get_constants_helper(d1[1:]):
                    # See if value starts with #, if so then it is a BV number
                    # TODO: ensure that this works with numbers (ILA) as well
                    if len(r) >= 2 and r[0] == "\\" and r[1] == "#":
                        ret.add(r)
            else:
                # This is just a constant
                ret.add(dumps(d1))
        return ret


    def get_variables(self):
        """
        Get all the variables from the problem
        """
        ret = set()
        for d in self.defines_and_declares:
            definition = d[0]
            if dumps(definition) == "declare-var":
                var_name = d[1]
                ret.add(dumps(var_name))
        return list(ret)


    """
    =========================================
    |READ/WRITE SyGuS Problem from/to a file|
    =========================================
    """


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
