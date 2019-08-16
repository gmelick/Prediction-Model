import numpy as np
import os


def get_bullpens():
    bullpens = {}
    for file in os.listdir(os.path.join(cwd, "Bullpens")):
        if file.endswith("Bullpen.csv"):
            team_name = file[file.find(" ") + 1:file.rfind(" ")]
            bullpens[team_name] = [{}, []]
            team_bullpen = open(os.path.join(cwd, "Bullpens", file))
            curr_pitcher = ""
            current = []
            for i, line in enumerate(team_bullpen.readlines()):
                if i % 8 == 0:
                    if i != 0:
                        bullpens[team_name][0][curr_pitcher] = current
                    current = np.zeros((7, 11))
                    curr_pitcher = line.split(",")[0].strip()
                else:
                    inning = line.split(",")
                    for j, appearances in enumerate(inning):
                        current[i % 8 - 1][j] = int(float(appearances))
            bullpens[team_name][1] = current
    return bullpens


def get_pitches():
    file = open(os.path.join(cwd, "Pitcher Pitches.csv"))
    pitches = {}
    for line in file.readlines():
        pitcher_pitches = line.split(",")
        pitcher = pitcher_pitches[0].strip()
        pitches[pitcher] = []
        for pitch in pitcher_pitches[1:]:
            if pitch != "":
                pitches[pitcher].append(int(pitch))
            else:
                break
    return pitches


def new_pitcher(lead, inning, bullpen, bullpen_pitchers):
    if lead < -4:
        lead = -5
    elif lead > 4:
        lead = 5

    if inning <= 4:
        inning = 4
    elif inning >= 10:
        inning = 10

    if bullpen[inning - 4][lead + 5] > 1:
        rand_int = np.random.randint(1, bullpen[inning - 4][lead + 5])
        count = 0
        for pitcher in bullpen_pitchers:
            count += bullpen_pitchers[pitcher][inning - 4][lead + 5]
            if count >= rand_int:
                bullpen = np.subtract(bullpen, bullpen_pitchers[pitcher])
                del bullpen_pitchers[pitcher]
                return pitcher, bullpen, bullpen_pitchers
    else:
        total = bullpen.sum()
        if total == 0:
            return None, None, None
        rand_int = np.random.randint(1, total + 1)
        count = 0
        for pitcher in bullpen_pitchers:
            for p_inning in bullpen_pitchers[pitcher]:
                for p_runs in p_inning:
                    count += p_runs
            if count >= rand_int:
                bullpen = np.subtract(bullpen, bullpen_pitchers[pitcher])
                del bullpen_pitchers[pitcher]
                return pitcher, bullpen, bullpen_pitchers
    return None, None, None


cwd = os.getcwd()
