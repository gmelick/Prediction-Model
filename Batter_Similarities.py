import numpy as np
import os


def main():
    cwd = os.getcwd()
    file = open(os.path.join(cwd, "2019 Batter Stats.csv"))
    lines = file.readlines()
    player_stats = {}
    hands = []
    population_stats = np.zeros((19, len(lines) - 1))
    for i, line in enumerate(lines):
        if i > 0:
            stats = line.split(",")
            hands.append(stats[1])
            for j, stat in enumerate(line.split(",")):
                if j > 1:
                    population_stats[j - 2][i - 2] = stat
                    player_stats[stats[0]].append(float(stat.strip()))
                elif j == 0:
                    player_stats[stat] = []
    max_min = np.zeros((19, 2))
    for i, stat in enumerate(population_stats):
        max_min[i][0] = min(stat)
        max_min[i][1] = max(stat)
    for j, player in enumerate(player_stats):
        for i, stat in enumerate(player_stats[player]):
            population_stats[i][j] = (population_stats[i][j] - max_min[i][0]) / (max_min[i][1] - max_min[i][0])
            player_stats[player][i] = (stat - max_min[i][0]) / (max_min[i][1] - max_min[i][0])

    similarity_matrix = np.empty((len(player_stats), len(player_stats)))
    key_list = list(player_stats.keys())
    for i, stat in enumerate(player_stats):
        print(stat)
        similarity_matrix[i][i] = 0
        for j in range(i + 1, len(player_stats)):
            if hands[i] == hands[j] or hands[i] == "B" or hands[j] == "B":
                batter_stats = np.array(player_stats[stat])
                cmp_batter_stats = np.array(player_stats[key_list[j]])
                total = 0
                for k, entry in enumerate(batter_stats):
                    total += (batter_stats[k] - cmp_batter_stats[k]) ** 2
                g = np.sqrt(total)
                similarity_matrix[i][j] = g
                similarity_matrix[j][i] = g
            else:
                similarity_matrix[i][j] = -1
                similarity_matrix[j][i] = -1

    file = open(os.path.join(cwd, "2019 Batter Similarity Scores.csv"), "w+")
    file.write(",")
    for i, hitter in enumerate(key_list):
        if i != len(player_stats) - 1:
            file.write(hitter + ",")
        else:
            file.write(hitter + "\n")
    for i, hitter in enumerate(player_stats):
        print(hitter)
        file.write(hitter + ",")
        for j in range(len(player_stats)):
            if j != len(player_stats) - 1:
                file.write(str(similarity_matrix[i][j]) + ",")
            else:
                file.write(str(similarity_matrix[i][j]) + "\n")
    file.close()
