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

NUM_NONTERMINALS = 3
NUM_SUBRULES = 70
NUM_EPOCHS = 10

def rand_bool_list(x, y):
    ret = []
    for i in range(x):
        ret.append(random.choices([True, False], k = y))
    return ret

def print_pool(pool):
    for [rules, score, num_unsolved, num_solved] in pool:
        s = ""
        for row in rules:
            for v in row:
                s += str(int(v))
            s += " "
        print(s, score, num_unsolved, num_solved)


def mutate(ind1, ind2):
    new_ind = []
    for i in range(len(ind1)):
        new_ind.append(random.choices([ind1[i][j], ind2[i][j], True, False], weights=[4, 4, 1, 1], k = len(ind1[0])))
    return new_ind

if __name__ == "__main__":
    print("> Starting Program.")
    random.seed(100)

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

    # Set up metagrammar and add the generated bitvector rules
    best_str = "0" * 210
    best_score = float("inf")
    best_unsolved = float("inf")
    best_solved = 0
    r.from_string(best_str)

    m = Metagrammar()
    m.add_rule(r)


    # Get all problem files from the directory of problems.
    problem_dir = "benchmarks/lib/General_Track/bv-conditional-inverses/"
    all_problems = [f for f in listdir(problem_dir) if isfile(join(problem_dir, f))]

    random.shuffle(all_problems)
    train_problems, test_problems = all_problems[:len(all_problems)//3], all_problems[len(all_problems)//3:]
    assert(len(test_problems) + len(train_problems) == len(all_problems))

    # print("Total Number of Test Files: ", len(all_problems))
    # print("Base Case (All): ", m.base_score(problem_dir, all_problems))
    # print("Base Case (Test): ", m.base_score(problem_dir, test_problems))
    # print("Base Case (Train): ", m.base_score(problem_dir, train_problems))

    pool = []
    for individual in range(5):
        new_rules = rand_bool_list(NUM_NONTERMINALS, NUM_SUBRULES)
        r.set_active_rules(new_rules)
        new_score, num_unsolved, num_solved = m.score(problem_dir, train_problems)
        pool.append([new_rules, new_score, num_unsolved, num_solved])

    pool.sort(reverse=False, key=lambda x: x[1])
    print_pool(pool)

    # print(pool[0])
    # r.set_active_rules(pool[0])
    # new_score, num_unsolved, num_solved = m.score(problem_dir, train_problems)

    # for epoch in range(NUM_EPOCHS):
    for epoch in range(1):
        print("EPOCH: ", epoch)
        # At each epoch, take each combination and add to new pool

        for i in range(5):
            for j in range(5):

                # Mutate
                new_ind = mutate(pool[i][0], pool[j][0])
                r.set_active_rules(new_ind)
                new_score, num_unsolved, num_solved = m.score(problem_dir, train_problems)
                pool.append([new_ind, new_score, num_unsolved, num_solved])


        # Take only the best 5 from that pool
        pool.sort(reverse=False, key=lambda x: x[1])
        pool = pool[:5]
        print_pool(pool)


    for [rules, score, num_unsolved, num_solved] in pool:
        s = ""
        for row in rules:
            for v in row:
                s += str(int(v))
            s += " "
        print(s, score, num_unsolved, num_solved)
        r.set_active_rules(rules)
        print("[DEBUG] Score on Test Set: ", m.score(problem_dir, test_problems))


    # TODO: Add in check for logic type to determine which nonterminals to use
    # r1 = Rule("Int", create_symbol("Int"))
    # r1.add_subrule(lambda x: [create_symbol("Int0")])
    # r1.add_subrule(lambda x: [create_symbol("Int1")])
    # r1.add_subrule(lambda x: [create_symbol("Int2")])
    # r1.add_subrule(lambda x: [create_symbol(c) for c in x.get_constants()])
    # r1.add_subrule(lambda x: [create_symbol(v) for v in x.get_variables()])


    print("> Ending Program.")

