import os


def create_from_file():
    roster = {}
    file = open(os.path.join(cwd, "Master Roster.csv"))
    for line in file.readlines():
        stats = line.split(",")
        roster[stats[0]] = stats[1].strip()
    return roster


def create_reverse():
    roster = {}
    file = open(os.path.join(cwd, "Master Roster.csv"))
    for line in file.readlines():
        stats = line.split(",")
        roster[stats[1].strip()] = stats[0]
    return roster


cwd = os.getcwd()
