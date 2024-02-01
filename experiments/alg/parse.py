if __name__ == "__main__":
    dummy = []
    annealing = []
    with open("result10", "r") as f:
        for line in f:
            info = line.strip().split(" ")
            if len(info) == 3:
                dummy.append(float(info[1]))
                annealing.append(float(info[2]))
    print(dummy)
    print(annealing)
