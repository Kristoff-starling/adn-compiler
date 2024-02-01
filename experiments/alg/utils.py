from typing import List


class Element:
    def __init__(self, name: str, pos: str):
        self.name = name
        self.pos = pos

    @property
    def block_or_drop(self):
        return self.name in [
            "acl",
            "ratelimit",
            "bandwidthlimit",
            "cache",
            "fault",
            "circuitbreaker",
            "admissioncontrol",
        ]

    @property
    def strong_state(self):
        return self.name in [
            "cache",
            "acl",
            "lbsticky",
        ]


def parse(graph: str) -> List[Element]:
    graph = graph.strip()
    chain = []
    for e_str in graph.split("->"):
        ename, epos = e_str.split("(")
        element = Element(ename, epos[:-1])
        chain.append(element)
    return chain


def cost(chain: List[Element]) -> float:
    c = 0.0
    e, d, s, r = 1.0, 0.1, 5.0, 5.0
    workload = 1.0
    npos = -1
    for (i, element) in enumerate(chain):
        c += workload * e
        if element.block_or_drop:
            workload *= 1 - d
        if element.pos == "N":
            npos = i
    client_chain, server_chain = chain[:npos], chain[npos + 1 :]
    for element in client_chain:
        if element.strong_state:
            c += s
            break
    for element in server_chain:
        if element.strong_state:
            c += s
            break
    if len(client_chain) > 0:
        c += r
    if len(server_chain) > 0:
        c += r
    return c


def visualize(chain: List[Element]):
    return "->".join([f"{element.name}({element.pos})" for element in chain])


def is_valid(chain: List[Element]) -> bool:
    meet_network = False
    for element in chain:
        if element.pos == "N":
            meet_network = True
        if not meet_network and element.pos == "S":
            return False
        if meet_network and element.pos == "C":
            return False
    assert meet_network
    return True
