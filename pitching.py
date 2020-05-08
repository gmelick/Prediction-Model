import numpy as np
import os


def get_bullpens(year):
    bullpens = {}
    for file in os.listdir(os.path.join(cwd, "Bullpens")):
        if file.startswith(f"{year}") and file.endswith("Bullpen.csv"):
            team_name = file[file.find(" ") + 1:file.rfind(" ")]
            bullpens[team_name] = [{}, np.zeros((7, 11))]
            with open(os.path.join(cwd, "Bullpens", file)) as team_bullpen:
                lines = team_bullpen.readlines()
                for i in range(int(len(lines) / 8)):
                    curr_pitcher = lines[i * 8].split(",")[0].strip()
                    __create_bullpen(team_name, curr_pitcher, lines[i * 8 + 1:i * 8 + 8], bullpens)
    return bullpens


def __create_bullpen(team_name, curr_pitcher, appearances_matrix, bullpens):
    if curr_pitcher != "Composite":
        bullpens[team_name][0][curr_pitcher] = [[int(float(appearances)) for appearances in line.split(",")]
                                                for line in appearances_matrix]
    else:
        bullpens[team_name][1] = [[int(float(appearances)) for appearances in line.split(",")]
                                  for line in appearances_matrix]


def get_pitches():
    with open(os.path.join(cwd, "Pitcher Pitches.csv")) as file:
        return {line.split(",")[0].strip(): [int(pitch) for pitch in line.split(",")[1:]] for line in file.readlines()}


def get_new_pitcher(lead, inning, bullpen, bullpen_pitchers):
    lead = -5 if lead < -4 else 5 if lead > 4 else lead
    inning = 4 if inning <= 4 else 10 if inning >= 10 else inning
    if bullpen[inning - 4][lead + 5] > 1:
        rand_int = np.random.randint(1, bullpen[inning - 4][lead + 5])
        for pitcher in bullpen_pitchers:
            rand_int -= bullpen_pitchers[pitcher][inning - 4][lead + 5]
            if 0 > rand_int:
                return __replace_pitcher(pitcher, bullpen, bullpen_pitchers)
    else:
        total = np.array(bullpen).sum()
        if total == 0:
            return None, None, None
        rand_int = np.random.randint(1, total + 1)
        for pitcher in bullpen_pitchers:
            rand_int -= sum([sum([p_runs for p_runs in p_inning]) for p_inning in bullpen_pitchers[pitcher]])
            if 0 > rand_int:
                return __replace_pitcher(pitcher, bullpen, bullpen_pitchers)
    return None, None, None


def __replace_pitcher(pitcher, bullpen, bullpen_pitchers):
    bullpen = np.subtract(bullpen, bullpen_pitchers[pitcher])
    del bullpen_pitchers[pitcher]
    return pitcher, bullpen, bullpen_pitchers


cwd = os.getcwd()
