import pandas as pd
import typing
import copy
import random
from os import listdir
from os.path import isfile, join
from sexp_utils import *
from metagrammar import Metagrammar
from sygusproblem import SyGuSProblem
from rule import Rule


"""
Things to do:
1. Create a function that can parse a SyGuS problem (.sl file)
2. Create a function that can replace a grammar using metagrammar rules
3. Create a function that can write back a modified SyGuS benchmark
4. Create a script to run solver on specific file
5. ???
6. Profit
"""


if __name__ == "__main__":
    print("> Starting Program.")

    # # Create parameters
    # p = SyGuSProblem("inv0.sl")
    # p.read_sygus_problem("benchmarks/lib/General_Track/bv-conditional-inverses/", "find_inv_bvsge_bvadd_4bit.sl")
    # print(p)

    # Change to BitVec of all types
    r = Rule("BitVec", [create_symbol("_"), create_symbol("BitVec"), 4], lambda x: create_symbol("#x0"))
    r.add_subrule(lambda x: [create_symbol("BitVec0")])
    r.add_subrule(lambda x: [create_symbol("BitVec1")])
    r.add_subrule(lambda x: [create_symbol("BitVec2")])

    combinations1 = [
        [Symbol("BitVec0"),
         Symbol("BitVec1"),
         Symbol("BitVec2")]
    ]

    combinations2 = [
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
    for a in combinations1:
        r.add_subrule(lambda x: [[Symbol("bvneg"), a]])
        r.add_subrule(lambda x: [[Symbol("bvnot"), a]])

    for a, b in combinations2:
        r.add_subrule(lambda x: [[Symbol("bvadd"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvsub"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvand"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvadd"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvlshr"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvor"), a, b]])
        r.add_subrule(lambda x: [[Symbol("bvshl"), a, b]])


    r.add_subrule(lambda x: [create_symbol(c) for c in x.get_constants()])
    r.add_subrule(lambda x: [create_symbol(v) for v in x.get_variables()])

    # Set up
    best_str = "1" * 210
    best_score = float("inf")
    r.from_string(best_str)

    m = Metagrammar()
    m.add_rule(r)


    # Get all problem files from the directory of problems.
    problem_dir = "benchmarks/lib/General_Track/bv-conditional-inverses/"
    all_problems = [f for f in listdir(problem_dir) if isfile(join(problem_dir, f))]
    print("Total Number of Test Files: ", len(all_problems))

    random.shuffle(all_problems)
    test_problems, train_problems = all_problems[:len(all_problems)//2], all_problems[len(all_problems)//2:]
    assert(len(test_problems) + len(train_problems) == len(all_problems))

    print("[DEBUG] Base String: ", r.to_string())
    for i in range(500):
        print("Iteration: ", i)
        # Try randomly swapping value, if better or equal score, then keep
        test_str = best_str
        for i in range(10):
            idx = random.randint(0, r.get_length()-1)
            if best_str[idx] == "0":
                test_str = test_str[:idx] + "1" + test_str[idx+1:]
            else:
                test_str = test_str[:idx] + "0" + test_str[idx+1:]

        # TODO: We will need to rewrite all of the nonterminals if there are multiple
        r.from_string(test_str)
        new_score, num_unsat = m.score(problem_dir, train_problems)
        print("[DEBUG] Current String: ", r.to_string())
        print("[DEBUG] Best Score: ", best_score, " | New Score: ", new_score, " | Number Unsat: ", num_unsat)
        if new_score <= best_score:
            best_str = test_str
            best_score = new_score

    print("[DEBUG] Best String: ", best_str, ", | Best String: ", best_str, " | Best Score", best_score)
    print("[DEBUG] Score on Test Set: ", m.score(problem_dir, test_problems))

    # test = ""
    # for i in range(210):
    #     test += str(random.randint(0, 1))
    # print(test)
    # r.from_string(test)


    # TODO: Add in check for logic type to determine which nonterminals to use
    # r1 = Rule("Int", create_symbol("Int"))
    # r1.add_subrule(lambda x: [create_symbol("Int0")])
    # r1.add_subrule(lambda x: [create_symbol("Int1")])
    # r1.add_subrule(lambda x: [create_symbol("Int2")])
    # r1.add_subrule(lambda x: [create_symbol(c) for c in x.get_constants()])
    # r1.add_subrule(lambda x: [create_symbol(v) for v in x.get_variables()])


    print("> Ending Program.")

