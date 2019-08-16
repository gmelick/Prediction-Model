import numpy as np
import os
from scipy import stats


def compute_edm_similarity(pitch_stats, cmp_stats, covariances):
    distances = []
    for pitch in pitch_stats:
        pitch_min = 1000000
        pitch_array = np.array(pitch_stats[pitch])
        for cmp_pitch in cmp_stats:
            cmp_pitch_array = np.array(cmp_stats[cmp_pitch])
            difference = np.subtract(pitch_array, cmp_pitch_array)
            g = np.matmul(np.matmul(difference, np.linalg.inv(covariances)), difference.T) ** 1/2
            if g < pitch_min:
                pitch_min = g
        distances.append(pitch_min)
    return distances


def compute_mus(statistics, population_mus):
    new_stats = {}
    for batter_hand in statistics[0]:
        new_stats[batter_hand] = {}
        for pitch_type in statistics[0][batter_hand]:
            mus = []
            for i in range(4):
                entries = statistics[i][batter_hand][pitch_type]
                mean = np.mean(entries)
                if not np.isnan(mean):
                    mus.append(mean)
                    if i == 3:
                        new_stats[batter_hand][pitch_type] = mus
                        population_mus[batter_hand].append(mus)
    return [new_stats, statistics[-1]], population_mus


def clean_stats(statistics):
    total_pitches_clean = 0
    for i, stat in enumerate(statistics):
        if i < 4:
            total_pitches_clean = 0
            for batter_hand in stat:
                for pitch_type in stat[batter_hand]:
                    stat_line = np.array(stat[batter_hand][pitch_type])
                    z = np.abs(stats.zscore(stat_line))
                    stat_line = stat_line[np.where(z < 3)[0]]
                    statistics[i][batter_hand][pitch_type] = stat_line
                    if len(stat_line) < 10:
                        statistics[i][batter_hand][pitch_type] = []
                    total_pitches_clean += len(statistics[i][batter_hand][pitch_type])
    return statistics, total_pitches_clean


def calc_release(stats_split):
    return np.arctan2(float(stats_split[26]), float(stats_split[28]) - 2.85)


def read_stats(stats_file):
    velocity = {}
    horizontal_break = {}
    vertical_break = {}
    release_points = {}
    lines = stats_file.readlines()
    righties = 0
    batter_total = 0
    if len(lines) > 100:
        handedness = lines[1].split(",")[4]
        for i, line in enumerate(lines):
            if i > 0:
                batter_total += 1
                stats_split = line.split(",")
                pitch_type = stats_split[18]
                batter_hand = stats_split[6]
                if batter_hand == "R":
                    righties += 1
                if batter_hand in velocity:
                    if pitch_type in pitch_types:
                        if pitch_type in velocity[batter_hand]:
                            velocity[batter_hand][pitch_type].append(float(stats_split[23]))
                            horizontal_break[batter_hand][pitch_type].append(float(stats_split[31]))
                            vertical_break[batter_hand][pitch_type].append(float(stats_split[32]))
                            release_points[batter_hand][pitch_type].append(calc_release(stats_split))
                        else:
                            velocity[batter_hand][pitch_type] = [float(stats_split[23])]
                            horizontal_break[batter_hand][pitch_type] = [float(stats_split[31])]
                            vertical_break[batter_hand][pitch_type] = [float(stats_split[32])]
                            release_points[batter_hand][pitch_type] = [calc_release(stats_split)]
                else:
                    velocity[batter_hand] = {pitch_type: [float(stats_split[23])]}
                    horizontal_break[batter_hand] = {pitch_type: [float(stats_split[31])]}
                    vertical_break[batter_hand] = {pitch_type: [float(stats_split[32])]}
                    release_points[batter_hand] = {pitch_type: [calc_release(stats_split)]}
    else:
        return None

    return [velocity, horizontal_break, vertical_break, release_points, handedness], righties, batter_total


def main():
    cwd = os.getcwd()
    for year in ["2019"]:
        print(year)
        pitchers = {}
        righties_vs_lefties_total = 0
        righties_vs_righties_total = 0
        lefties_total = 0
        righties_total = 0
        population_mus = {"R": [], "L": []}
        for file in os.listdir(os.path.join(cwd, "PitchFX")):
            if file.endswith(year + ".csv"):
                pitcher = file[:file.rfind(" ")]
                file = open(os.path.join(cwd, "PitchFX", pitcher + " " + year + ".csv"))
                statistics = read_stats(file)
                if statistics is not None:
                    righties = statistics[1]
                    total = statistics[2]
                    statistics = statistics[0]
                    if statistics[-1] == "L":
                        lefties_total += total
                        righties_vs_lefties_total += righties
                    else:
                        righties_total += total
                        righties_vs_righties_total += righties
                    statistics, count = clean_stats(statistics)
                    if count >= 100:
                        statistics, population_mus = compute_mus(statistics, population_mus)
                        pitchers[pitcher] = statistics

        right_handed_mus = np.array(population_mus["R"])
        right_handed_mu_covariance = np.cov(right_handed_mus.T)
        left_handed_mus = np.array(population_mus["L"])
        left_handed_mu_covariance = np.cov(left_handed_mus.T)

        similarity_scores = np.ones((len(pitchers), len(pitchers)))
        key_list = list(pitchers.keys())
        for i, pitcher in enumerate(pitchers):
            print(pitcher)
            similarity_scores[i][i] = 0
            for j in range(i + 1, len(key_list)):
                pitcher_stats = pitchers[pitcher][0]
                pitcher_hand = pitchers[pitcher][1]
                cmp_pitcher_stats = pitchers[key_list[j]][0]
                cmp_pitcher_hand = pitchers[key_list[j]][1]
                if pitcher_hand == cmp_pitcher_hand:
                    d_r = compute_edm_similarity(pitcher_stats["R"], cmp_pitcher_stats["R"], right_handed_mu_covariance)
                    d_l = compute_edm_similarity(pitcher_stats["L"], cmp_pitcher_stats["L"], left_handed_mu_covariance)
                    if pitcher_hand == "R":
                        f_r_r = righties_vs_righties_total / righties_total
                        score = f_r_r * np.mean(d_r) + (1 - f_r_r) * np.mean(d_l)
                    else:
                        f_l_r = righties_vs_lefties_total / lefties_total
                        score = f_l_r * np.mean(d_r) + (1 - f_l_r) * np.mean(d_l)
                    similarity_scores[i][j] = score
                    similarity_scores[j][i] = score
                else:
                    similarity_scores[i][j] = -1
                    similarity_scores[j][i] = -1

        file = open(os.path.join(cwd, "Similarity Scores", year + " Pitcher Similarity Scores.csv"), "w+")
        file.write(",")
        for i, pitcher in enumerate(pitchers):
            if i != len(pitchers) - 1:
                file.write(pitcher + ",")
            else:
                file.write(pitcher + "\n")
        for i, pitcher in enumerate(pitchers):
            file.write(pitcher + ",")
            for j in range(len(pitchers)):
                if j != len(pitchers) - 1:
                    file.write(str(similarity_scores[i][j]) + ",")
                else:
                    file.write(str(similarity_scores[i][j]) + "\n")
        file.close()


pitch_types = ["FF", "CU", "CH", "SL", "FT", "FC", "SI", "EP", "FS", "KC", "FO", "SC", "KN"]
