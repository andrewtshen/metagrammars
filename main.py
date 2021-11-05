import pandas as pd
from sexpdata import loads, dumps, Symbol # Everything we need to read SyGuS files (.sl)
import typing
import re
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
    with open(filename, 'r') as f:
        contents = f.readlines()
        return loads('(' + ''.join(remove_sexp_comments(contents)) + ')')


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


class SyGuSProblem:
    def __init__(self, name: str, symbols: list):
        self.symbols = symbols

    def __str__(self):
        return "SyGuS Problem expression" + " ".join(map(str, self.symbols))
    

def read_sygus_problem(
        problem_dir: str,
        problem_name: str,
    ) -> SyGuSProblem:
    """
    Reads a SyGuS problem from a given a file.
    Returns a SyGuSProblem instance.
    """
    SyGuS_sexp = get_sexp(problem_dir + problem_name)
    problem = SyGuSProblem(problem_name, SyGuS_sexp)
    return problem


def write_sygus_problem(
        problem: SyGuSProblem,
        destination_dir: str,
        problem_name: str,
    ):
    """
    Write a SyGus problem from a SyGuSProblem instance to a certain file.
    Return boolean value of if write succeeded.
    """
    data = export_sexp(problem.symbols)
    filename = destination_dir + problem_name
    # Create directory if path to filename does not already exist
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    with open(filename, 'w') as f:
        f.write(data)

if __name__ == "__main__":
    print("Starting Program")
    problem = read_sygus_problem("SyGuS_Benchmarks/tacas_benchmarks/bitvec_invariants/", "inv0.sl")
    print("DEBUG: Problem: ", problem)
    write_sygus_problem(problem, "results/", "test.txt")
    print("DEBUG: Successfully written back!")
    print("Ending Program")

