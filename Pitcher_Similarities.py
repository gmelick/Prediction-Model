import numpy as np
import os
from scipy import stats


def compute_pitcher_similarities(year):
    pitchers = {}
    righties_vs_lefties_total = 0
    righties_vs_righties_total = 0
    lefties_total = 0
    righties_total = 0
    population_mus = {"R": [], "L": []}
    for file in os.listdir(os.path.join(cwd, "PitchFX")):
        if file.endswith(f"{year}.csv") or file.endswith(f"{year - 1}.csv") or file.endswith(f"{year - 2}.csv"):
            pitcher_name = file[:file.rfind(" ")]
            statistics, handedness, pitches_to_righties, total_pitches = __read_stats(file)
            if statistics is not None:
                if handedness == "L":
                    lefties_total += total_pitches
                    righties_vs_lefties_total += pitches_to_righties
                else:
                    righties_total += total_pitches
                    righties_vs_righties_total += pitches_to_righties
                statistics, count = __clean_stats(statistics)
                if count >= 100:
                    statistics, population_mus = __compute_mus(statistics, population_mus)
                    if pitcher_name in pitchers:
                        pitchers[pitcher_name] = [__combine_stats(pitchers[pitcher_name][0], statistics), handedness]
                    else:
                        pitchers[pitcher_name] = [statistics, handedness]

    right_handed_mus = np.array(population_mus["R"])
    right_handed_mu_covariance = np.cov(right_handed_mus.T)
    left_handed_mus = np.array(population_mus["L"])
    left_handed_mu_covariance = np.cov(left_handed_mus.T)

    similarity_scores = np.ones((len(pitchers), len(pitchers)))
    key_list = list(pitchers.keys())
    for i, pitcher_name in enumerate(pitchers):
        similarity_scores[i][i] = 0
        for j in range(i + 1, len(key_list)):
            pitcher_stats = pitchers[pitcher_name][0]
            cmp_pitcher_stats = pitchers[key_list[j]][0]
            # Compare the handedness of the pitchers, if they match compute the score, otherwise score is -1
            if pitchers[pitcher_name][1] == pitchers[key_list[j]][1]:
                similarity_scores[i][j] = __compute_scores(pitcher_stats, cmp_pitcher_stats, right_handed_mu_covariance,
                                                           left_handed_mu_covariance, pitchers, pitcher_name,
                                                           righties_vs_righties_total, righties_total,
                                                           righties_vs_lefties_total, lefties_total)
                similarity_scores[j][i] = similarity_scores[i][j]
            else:
                similarity_scores[i][j] = -1
                similarity_scores[j][i] = -1

    with open(os.path.join(cwd, "Similarity Scores", f"{year} Pitcher Similarity Scores.csv"), "w+") as file:
        for pitcher_name in pitchers:
            file.write(f",{pitcher_name}")
        file.write("\n")
        for i, pitcher_name in enumerate(pitchers):
            file.write(pitcher_name)
            for j in range(len(pitchers)):
                file.write(f",{similarity_scores[i][j]}")
            file.write("\n")


def __read_stats(stats_file):
    # Statistics are velocity, horizontal break, vertical break, and release point
    # Each dictionary keeps track of pitches thrown to each handedness of batter, pitch type, and the statistics
    statistics = {"R": {}, "L": {}}
    pitches_to_righties = 0
    lines = open(os.path.join(cwd, "PitchFX", stats_file)).readlines()
    if len(lines) > 1:
        total_pitches = len(lines) - 1
        handedness = lines[1].split(",")[4]
        if total_pitches >= 100:
            for line in lines[1:]:
                pitch = line.split(",")
                pitch_type = pitch[18]
                batter_hand = pitch[6]
                pitch_statistics = [float(pitch[23]), float(pitch[31]), float(pitch[32]), __calc_release(pitch)]
                pitches_to_righties += 1 if batter_hand == "R" else 0
                __process_pitch(pitch_type, batter_hand, pitch_statistics, statistics)
        else:
            return None, None, None, None
    else:
        return None, None, None, None
    return statistics, handedness, pitches_to_righties, total_pitches


def __calc_release(stats_split):
    return np.arctan2(float(stats_split[26]), float(stats_split[28]) - 2.85)


def __process_pitch(pitch_type, batter_hand, pitch_statistics, statistics):
    if pitch_type in pitch_types:
        if pitch_type in statistics[batter_hand]:
            statistics[batter_hand][pitch_type].append(pitch_statistics)
        else:
            statistics[batter_hand][pitch_type] = [pitch_statistics]


def __clean_stats(statistics):
    total_pitches = 0
    for_deletion = []
    for batter_hand in statistics:
        for pitch_type in statistics[batter_hand]:
            stat_matrix = np.array(statistics[batter_hand][pitch_type])
            z = np.abs(stats.zscore(stat_matrix))
            statistics[batter_hand][pitch_type] = stat_matrix[np.all(z <= 3, axis=1)]
            if len(statistics[batter_hand][pitch_type]) < 10:
                for_deletion.append((batter_hand, pitch_type))
            else:
                total_pitches += len(statistics[batter_hand][pitch_type])
    for combination in for_deletion:
        del statistics[combination[0]][combination[1]]
    return statistics, total_pitches


def __compute_mus(statistics, population_mus):
    for batter_hand in statistics:
        for pitch_type in statistics[batter_hand]:
            entries = np.array(statistics[batter_hand][pitch_type])
            mus = np.mean(entries, axis=0)
            statistics[batter_hand][pitch_type] = mus
            population_mus[batter_hand].append(mus)
    return statistics, population_mus


def __combine_stats(old_stats, new_stats):
    aggr = {"R": {}, "L": {}}
    for batter_hand in old_stats:
        for pitch_type in old_stats[batter_hand]:
            if pitch_type in new_stats[batter_hand]:
                aggr[batter_hand][pitch_type] = old_stats[batter_hand][pitch_type] + new_stats[batter_hand][pitch_type]
            else:
                aggr[batter_hand][pitch_type] = old_stats[batter_hand][pitch_type]
        for pitch_type in new_stats[batter_hand]:
            if pitch_type not in old_stats[batter_hand]:
                aggr[batter_hand][pitch_type] = new_stats[batter_hand][pitch_type]
    return aggr


def __compute_scores(pitcher_stats, cmp_pitcher_stats, right_cov, left_cov, pitchers, pitcher_name, r_v_r_tot, r_tot,
                     r_v_l_tot, l_tot):
    d_r = __compute_edm_similarity(pitcher_stats["R"], cmp_pitcher_stats["R"], right_cov)
    d_l = __compute_edm_similarity(pitcher_stats["L"], cmp_pitcher_stats["L"], left_cov)
    if pitchers[pitcher_name][1] == "R":
        f_r_r = r_v_r_tot / r_tot
        return f_r_r * np.mean(d_r) + (1 - f_r_r) * np.mean(d_l)
    else:
        f_l_r = r_v_l_tot / l_tot
        return f_l_r * np.mean(d_r) + (1 - f_l_r) * np.mean(d_l)


def __compute_edm_similarity(pitch_stats, cmp_stats, covariances):
    distances = []
    for pitch in pitch_stats:
        pitch_min = np.inf
        pitch_array = np.array(pitch_stats[pitch])
        for cmp_pitch in cmp_stats:
            cmp_pitch_array = np.array(cmp_stats[cmp_pitch])
            difference = np.subtract(pitch_array, cmp_pitch_array)
            g = np.matmul(np.matmul(difference, np.linalg.inv(covariances)), difference.T) ** 1/2
            if g < pitch_min:
                pitch_min = g
        distances.append(pitch_min)
    return distances


pitch_types = ["FF", "CU", "CH", "SL", "FT", "FC", "SI", "EP", "FS", "KC", "FO", "SC", "KN"]
cwd = os.getcwd()
