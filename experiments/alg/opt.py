import argparse
import math
import multiprocessing as mp
import os
import random
from copy import deepcopy
from itertools import permutations
from typing import List

from utils import *


def annealing(chain) -> List[Element]:
    imax = 20
    global_min_cost = cost(chain)
    global_min_chain = deepcopy(chain)
    for _ in range(imax):
        cur_chain = deepcopy(chain)
        random.shuffle(cur_chain)
        cur_cost = cost(cur_chain)
        temp = 100
        while temp > 0.01:
            new_chain = deepcopy(cur_chain)
            i = random.randint(0, len(new_chain) - 1)
            element = new_chain[i]
            new_chain = new_chain[:i] + new_chain[i + 1 :]
            j = random.randint(0, len(new_chain))
            new_chain.insert(j, element)
            if is_valid(new_chain):
                new_cost = cost(new_chain)
                if new_cost < global_min_cost:
                    global_min_cost = new_cost
                    global_min_chain = deepcopy(new_chain)
                if math.exp(-(new_cost - cur_cost) / temp) > random.random():
                    cur_chain = new_chain
                    cur_cost = new_cost
            temp *= 0.97
    # return global_min_chain
    return global_min_cost


def dummy(chain: List[Element]):
    global_min_cost = cost(chain)
    global_min_chain = chain
    for c in list(permutations(chain)):
        if is_valid(c) and cost(c) < global_min_cost:
            global_min_cost = cost(c)
            global_min_chain = c
    # return global_min_cost
    return global_min_chain


def dummy_subtask(chain):
    header, tail = chain[:2], chain[2:]
    local_min_cost = 1000
    for c in list(permutations(tail)):
        cc = header + list(c)
        if is_valid(cc):
            local_min_cost = min(local_min_cost, cost(cc))
    return local_min_cost


def dummy_parallel(chain: List[Element]):
    tasks = []
    for i in range(len(chain)):
        for j in range(i + 1, len(chain)):
            cc = [chain[i], chain[j]] + chain[:i] + chain[i + 1 : j] + chain[j + 1 :]
            tasks.append(deepcopy(cc))
            tasks.append(deepcopy([cc[1], cc[0]] + cc[2:]))

    with mp.Pool(64) as pool:
        results = pool.map(dummy_subtask, tasks)

    return min(results)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--alg", "-a", type=str)
    args = p.parse_args()
    assert os.path.exists("graph"), "input graph not exist"
    graph_raw = open("graph").read()
    chain = parse(graph_raw)
    if args.alg == "dummy":
        optimized_chain = dummy_parallel(chain)
    else:
        optimized_chain = annealing(chain)
    print(optimized_chain)
