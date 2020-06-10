import numpy as np
import os
from scipy import stats


def compute_pitcher_similarities(year):
    score_list = []
    pitchers = {}
    pitcher_vs_righties = [0, 0]
    pitch_totals = [0, 0]
    population_mus = {"R": [], "L": []}
    for file in os.listdir(os.path.join(cwd, "PitchFX")):
        if file.endswith(tuple(f"{y}.csv" for y in range(year - 2, year + 1))):
            pitcher_name = file[:file.rfind(" ")]
            statistics, handedness, pitches_to_righties, total_pitches = __read_stats(file)
            if statistics is not None:
                pitch_totals[handedness] += total_pitches
                pitcher_vs_righties[handedness] += pitches_to_righties
                count = __clean_stats(statistics)
                if count >= 100:
                    __compute_mus(statistics, population_mus)
                    pitchers[pitcher_name] = (__combine_stats(pitchers.get(pitcher_name, [{}])[0], statistics),
                                              handedness)

    mus = [np.array(population_mus["R"]), np.array(population_mus["L"])]
    covs = [np.cov(mus[0].T), np.cov(mus[1].T)]
    fraction_r_v_r = pitcher_vs_righties[0] / pitch_totals[0]
    fraction_l_v_r = pitcher_vs_righties[1] / pitch_totals[1]
    matchup_fractions = [[fraction_r_v_r, 1 - fraction_r_v_r], [fraction_l_v_r, 1 - fraction_l_v_r]]

    similarity_scores = np.ones((len(pitchers), len(pitchers)))
    key_list = list(pitchers.keys())
    for i, pitcher_name in enumerate(pitchers):
        print(f"Finding similarity scores for {pitcher_name}: {i + 1} of {len(key_list)}")
        similarity_scores[i][i] = 0
        for j in range(i + 1, len(key_list)):
            pitcher_stats = pitchers[pitcher_name]
            cmp_pitcher_stats = pitchers[key_list[j]]
            # Compare the handedness of the pitchers, if they match compute the score, otherwise score is -1
            if pitcher_stats[1] == cmp_pitcher_stats[1]:
                score = __compute_scores(pitcher_stats, cmp_pitcher_stats, covs, matchup_fractions)
                if np.isnan(score):
                    similarity_scores[i][j] = -1
                    similarity_scores[j][i] = -1
                else:
                    similarity_scores[i][j] = score
                    similarity_scores[j][i] = score
                    score_list.append(score)
            else:
                similarity_scores[i][j] = -1
                similarity_scores[j][i] = -1

    percent_different = np.array(score_list) / (max(score_list) / 100)
    ind = 0
    for i in range(len(pitchers)):
        for j in range(i + 1, len(pitchers)):
            if similarity_scores[i][j] != -1:
                similarity_scores[i][j] = percent_different[ind]
                similarity_scores[j][i] = percent_different[ind]
                ind += 1

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
    total_pitches = len(lines) - 1
    if total_pitches <= 0:
        return None, None, None, None
    else:
        handedness = 0 if lines[1].split(",")[4] == "R" else 1
        for line in lines[1:]:
            pitch = line.split(",")
            pitch_type = pitch[18]
            batter_hand = pitch[6]
            pitch_statistics = [float(pitch[23]), float(pitch[31]), float(pitch[32]), __calc_release(pitch)]
            pitches_to_righties += 1 if batter_hand == "R" else 0
            __process_pitch(pitch_type, batter_hand, pitch_statistics, statistics)
        return statistics, handedness, pitches_to_righties, total_pitches


def __calc_release(stats_split):
    return np.arctan2(float(stats_split[26]), float(stats_split[28]) - 2.85)


def __process_pitch(pitch_type, batter_hand, pitch_statistics, statistics):
    if pitch_type in pitch_types:
        statistics[batter_hand][pitch_type] = statistics[batter_hand].get(pitch_type, []) + [pitch_statistics]


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
    for batter_hand, pitch_type in for_deletion:
        del statistics[batter_hand][pitch_type]
    return total_pitches


def __compute_mus(statistics, population_mus):
    for batter_hand in statistics:
        for pitch_type in statistics[batter_hand]:
            mus = np.mean(np.array(statistics[batter_hand][pitch_type]), axis=0)
            statistics[batter_hand][pitch_type] = mus
            population_mus[batter_hand] += [mus]


def __combine_stats(old_stats, new_stats):
    if not bool(old_stats):
        return new_stats
    for batter_hand in old_stats:
        for pitch_type in old_stats[batter_hand]:
            old = old_stats[batter_hand][pitch_type]
            new_stats[batter_hand][pitch_type] = old if pitch_type not in new_stats[batter_hand] \
                else new_stats[batter_hand][pitch_type] + old
    return new_stats


def __compute_scores(pitcher_stats, cmp_pitcher_stats, covariances, matchup_fractions):
    d_r = __compute_edm_similarity(pitcher_stats[0]["R"], cmp_pitcher_stats[0]["R"], covariances[0])
    d_l = __compute_edm_similarity(pitcher_stats[0]["L"], cmp_pitcher_stats[0]["L"], covariances[1])
    d_r = d_l if not d_r else d_r
    d_l = d_r if not d_l else d_l
    pitcher_hand = pitcher_stats[1]
    return matchup_fractions[pitcher_hand][0] * np.mean(d_r) + matchup_fractions[pitcher_hand][1] * np.mean(d_l)


def __compute_edm_similarity(pitch_stats, cmp_stats, covariances):
    if not bool(cmp_stats):
        return []
    distances = []
    for pitch in pitch_stats:
        pitch_array = np.array(pitch_stats[pitch])
        cmp_arr = np.array([cmp_stats[cmp_pitch] for cmp_pitch in cmp_stats])
        diff = np.subtract(pitch_array, cmp_arr)
        dist = np.matmul(np.matmul(diff, np.linalg.inv(covariances)), diff.T).diagonal()
        distances.append(np.amin(dist) ** 1/2)
    return distances


pitch_types = ["FF", "CU", "CH", "SL", "FT", "FC", "SI", "EP", "FS", "KC", "FO", "SC", "KN"]
cwd = os.getcwd()
