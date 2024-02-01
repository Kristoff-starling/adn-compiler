import argparse
import random
import subprocess
import time

from utils import *


def execute_command(cmd):
    res = subprocess.run(cmd, capture_output=True)
    return float(res.stdout.decode("utf-8").strip())


element_pool = [
    "acl",
    "logging",
    "metrics",
    "mutation",
    "ratelimit",
    "bandwidthlimit",
    "circuitbreaker",
    "lbsticky",
    "cache",
    "fault",
    "admissioncontrol",
]


def gen_random_graph(num):
    res = ""
    meet_network = False
    npos = random.randint(0, num)
    for _ in range(num):
        if npos == _:
            res += "network(N)->"
            meet_network = True
        ename = random.choice(element_pool)
        if not meet_network:
            pos = random.choice(["C", "C/S"])
        else:
            pos = random.choice(["S", "C/S"])
        res += f"{ename}({pos})->"
    if npos == num:
        res += "network(N)->"
    return res[:-2]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", "-n", type=int, default=5)
    args = parser.parse_args()
    count = 0
    # while True:
    dummy_time = 0
    anneal_time = 0
    wrong = 0
    for _ in range(100):
        original = gen_random_graph(args.num)
        with open("graph", "w") as f:
            f.write(original)
        timestamp = time.time()
        c1 = execute_command(["python3", "opt.py", "-a", "dummy"])
        duration = round(time.time() - timestamp, 3)
        dummy_time += duration
        timestamp = time.time()
        c2 = execute_command(["python3", "opt.py", "-a", "annealing"])
        duration = round(time.time() - timestamp, 3)
        anneal_time += duration
        count = count + 1
        print(f"{count}(wrong: {wrong}):")
        print(original)
        print(cost(parse(original)), c1, c2)
        print(round(dummy_time / count, 3), round(anneal_time / count, 3))
        print("")
        if c1 != c2:
            wrong += 1
        # assert cost(c1) == cost(c2)
    print(wrong)
