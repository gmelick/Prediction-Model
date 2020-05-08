import numpy as np
import os


def compute_batter_similarities(year):
    """
    Computes the batter similarity scores for the year specified and writes them to a file
    :param year: The year to be processed
    :return: None
    """
    # Read the batter data from the file
    lines = open(os.path.join(cwd, f"{year} Batter Stats.csv")).readlines()
    player_stats = {}
    hands = []

    # Creates the array that will be populated with the population stats, there are 19 stats that are being tracked
    player_count = len(lines)
    stat_count = 19

    # Get the maximum and minimum values for each stat for use in standardization
    maximums, minimums = __calculate_maximums_minimums(lines, hands, player_stats, stat_count)

    # Standardize the player stats for each player
    player_stats = {player: [(player_stats[player][i] - minimums[i]) / (maximums[i] - minimums[i])
                             for i in range(stat_count)] for player in player_stats}

    # Create the similarity matrix
    key_list = list(player_stats.keys())
    similarity_matrix = __compute_similarity_matrix(player_stats, player_count, hands, stat_count, key_list)

    # Write the similarity matrix to the file
    __write_to_file(year, key_list, player_stats, similarity_matrix)


def __calculate_maximums_minimums(lines, hands, player_stats, stat_count):
    maximums = np.empty(19)
    maximums.fill(-1)
    minimums = np.empty(19)
    minimums.fill(np.inf)
    for i, line in enumerate(lines):
        stats = line.split(",")
        name = stats[0]
        hands.append(stats[1])
        player_stats[name] = [float(stats[j + 2].strip()) for j in range(stat_count)]
        for j in range(stat_count):
            stat = float(stats[j + 2].strip())
            if stat > maximums[j]:
                maximums[j] = stat
            if stat < minimums[j]:
                minimums[j] = stat
    return maximums, minimums


def __compute_similarity_matrix(player_stats, player_count, hands, stat_count, key_list):
    similarity_matrix = np.empty((player_count, player_count))
    for i, player in enumerate(player_stats):
        similarity_matrix[i][i] = 0
        for j in range(i + 1, player_count):
            if hands[i] == hands[j] or hands[i] == "B" or hands[j] == "B":
                batter_stats = player_stats[player]
                cmp_batter_stats = player_stats[key_list[j]]
                total = 0
                for k in range(stat_count):
                    total += (batter_stats[k] - cmp_batter_stats[k]) ** 2
                g = np.sqrt(total)
                similarity_matrix[i][j] = g
                similarity_matrix[j][i] = g
            else:
                similarity_matrix[i][j] = -1
                similarity_matrix[j][i] = -1
    return similarity_matrix


def __write_to_file(year, key_list, player_stats, similarity_matrix):
    with open(os.path.join(cwd, f"{year} Batter Similarity Scores.csv"), "w+") as file:
        for hitter in key_list:
            file.write(f",{hitter}")
        file.write("\n")
        for i, hitter in enumerate(player_stats):
            file.write(hitter)
            for j in range(len(player_stats)):
                file.write(f",{similarity_matrix[i][j]}")
            file.write("\n")


cwd = os.getcwd()
