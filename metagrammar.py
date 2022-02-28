import subprocess
import re
from os import listdir
from os.path import isfile, join
from pathlib import Path
from sygusproblem import SyGuSProblem
from sexp_utils import *


class Metagrammar:
    """
    A Metagrammar contains a list of rules that operate on a given problem.
    After applying each rule in the Metagrammar to a problem, the Metagrammar 
    outputs a list containing the new grammar which can be inserted into the
    problem.
    """

    def __init__(self):
        """
        Create a metagrammar with no rules initially
        """
        self.rules = []


    def generate_grammar_from_rules(
        self, 
        problem: SyGuSProblem,
    ) -> list:
        """
        Generates a grammar from the rules in the metagrammar based on the the
        problem and returns the grammar as a list
        """
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
            ret.append(r.generate_grammar(problem))

        # Insert the list of nonterminals at the beginning of the list as per SyGuS format
        ret.insert(0, nonterminals_list)
        return ret


    def add_rule(self, rule):
        """
        Add a rule (see rule.py) to the metagrammar
        """
        self.rules.append(rule)


    def write_problem_with_grammar(
        self,
        problem: SyGuSProblem,
        dest_dir: str,
        problem_name: str,
    ):
        """
        Writes a SyGuS problem to a specified file and returns boolean value of if 
        write succeeded
        """
        # Generate grammmar to export
        g = self.generate_grammar_from_rules(problem)
        data = export_sexp(problem.create_with_new_grammar(g))
        filename = dest_dir + problem_name

        # Create directory if path to filename does not already exist
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            f.write(data)


    def benchmark(
        self,
        src_dir: str,
        problem_name: str,
        use_stats: bool = True,
        timeout: int = 300,
        seed: int = 1,
    ) -> (int, int):
        """
        Runs benchmarks on a SyGuS problem and return the result (either a successful 
        solve or a "timeout or fail") as well as the time to solve the problem
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

        # Check if solved problem
        pattern = "(define-fun .*)"
        compiled = re.compile(pattern)
        result = compiled.search(output)
        if not result:
            result = "timeout or fail"
        else:
            result = result.group(1).strip()

        # Compute the total time of execution
        pattern = "global::totalTime = (.*)ms"
        compiled = re.compile(pattern)
        ret = compiled.search(output)
        time_to_solve = ret.group(1).strip()

        return result, time_to_solve


    def score(
        self, 
        problem_dir: str, 
        problems: list
    ) -> (int, int):
        """
        The score function receives a path to the problem directory as well as list
        of problems to score. Then, the scoring function applies the metagrammar to
        each problem and accumlates the total time to run as the score (note that 
        if the solver, CVC5, does not finish in time 600 will be added to the score).
        In addition to returning the score, the program also returns the number of 
        unsolved problems.
        """

        total_time_to_solve = 0
        num_unsat = 0
        # For each of the problems, write the problem with the new grammar to "results/test.sl"
        # then apply the benchmark function to retrieve the time to solve/whether it is solvable
        for fname in problems:
            p = SyGuSProblem(fname)
            p.read_sygus_problem(problem_dir, fname)
            self.write_problem_with_grammar(p, "results/", "test.sl")
            result, time_to_solve = self.benchmark("results/", "test.sl")

            if result == "timeout or fail":
                # TODO: Can change this value to a more fitting penalty.
                total_time_to_solve += 600
                num_unsat += 1
            else:
                total_time_to_solve += int(time_to_solve)

        return total_time_to_solve, num_unsat
