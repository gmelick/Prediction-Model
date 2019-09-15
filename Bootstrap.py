from datetime import date
import requests
from bs4 import BeautifulSoup
import Game
import pitching
import numpy as np
import scipy.stats
import time
import Master_Roster_Creation
import os


def main():
    game_sims = 250
    teams_ = ["Rockies", "Yankees", "Red Sox", "Orioles", "D-backs", "Reds", "White Sox", "Rays", "Blue Jays", "Braves",
              "Tigers", "Royals", "Indians", "Phillies", "Pirates", "Rangers", "Astros", "Athletics", "Twins", "Padres",
              "Cubs", "Mets", "Giants", "Brewers", "Cardinals", "Angels", "Mariners", "Marlins", "Dodgers", "Nationals"]
    roster = Master_Roster_Creation.create_reverse()
    pitches_matrix = pitching.get_pitches()
    bullpens = pitching.get_bullpens()
    cur_date = date.today()
    predicted_total, actual_total = adjust()
    if predicted_total != 0:
        adjustment = actual_total / predicted_total
    else:
        adjustment = 1
    base_url = "https://www.mlb.com/starting-lineups/"
    url = base_url + str(cur_date.year) + "-" + str(cur_date.month) + "-" + str(cur_date.day)
    iteration = 0
    predicted_games = {}
    doubleheader_tracking = {}
    no_change = False
    while True:
        if no_change:
            time.sleep(180)
        soup = None
        connected = False
        no_change = True
        while not connected:
            try:
                soup = BeautifulSoup(requests.get(url).content, 'html.parser')
                connected = True
            except requests.exceptions.ConnectionError:
                continue
        games = soup.find_all("div", {"class": "starting-lineups__matchup"})
        if iteration == 0:
            for game in games:
                teams = game.find_all("a", {"class": "starting-lineups__team-name--link"})
                away_team = teams[0].text.strip()
                home_team = teams[1].text.strip()
                if away_team + " @ " + home_team in predicted_games:
                    predicted_games[away_team + " @ " + home_team] += 1
                    doubleheader_tracking[away_team + " @ " + home_team] = 0
                else:
                    predicted_games[away_team + " @ " + home_team] = 1
            iteration += 1
        for i, game in enumerate(games):
            teams = game.find_all("a", {"class": "starting-lineups__team-name--link"})
            away_team = teams[0].text.strip()
            home_team = teams[1].text.strip()
            postponed_class = "starting-lineups__game-state starting-lineups__game-state--postponed"
            postponed = game.find("span", {"class": postponed_class})
            if postponed is not None:
                if predicted_games[away_team + " @ " + home_team] > 0:
                    predicted_games[away_team + " @ " + home_team] -= 1
                continue
            if away_team not in teams_ or home_team not in teams_:
                continue
            if predicted_games[away_team + " @ " + home_team] == 0:
                continue
            pitchers = game.find_all("div", {"class": "starting-lineups__pitcher-name"})
            away_starter = pitchers[0].text.strip()
            home_starter = pitchers[1].text.strip()
            if away_starter == 'TBD' or home_starter == 'TBD':
                continue
            if game.find("li", {"class": "starting-lineups__player--TBD"}) is not None:
                continue

            if away_team + " @ " + home_team in doubleheader_tracking:
                if doubleheader_tracking[away_team + " @ " + home_team] == 1:
                    continue
                elif doubleheader_tracking[away_team + " @ " + home_team] == 0:
                    doubleheader_tracking[away_team + " @ " + home_team] = away_starter + home_starter
                elif doubleheader_tracking[away_team + " @ " + home_team] != away_starter + home_starter:
                    doubleheader_tracking[away_team + " @ " + home_team] = 1
                else:
                    continue
            away_lineup = []
            home_lineup = []
            for a, player in enumerate(game.find_all("a", {"class": "starting-lineups__player--link"})):
                if a < 9:
                    away_lineup.append(player.text)
                elif a < 18:
                    home_lineup.append(player.text)
                else:
                    break
            print(home_team)
            print(away_team)
            print(home_starter)
            print(away_starter)
            print(home_lineup)
            print(away_lineup)

            param_teams = [home_team, away_team]
            starters = [home_starter, away_starter]
            lineups = [away_lineup, home_lineup]
            param_bullpens = [bullpens[home_team], bullpens[away_team]]
            home_wins = 0
            total_score = [0, 0]
            home_scores = []
            away_scores = []
            total_box = [{}, {}]
            for a, lineup in enumerate(lineups):
                for batter in lineup:
                    total_box[a][batter] = [0] * 7
                total_box[a]["Generic"] = [0] * 7
            start = time.time()
            home_pitcher_bootstraps = create_bootstraps(home_team, home_starter, away_lineup)
            away_pitcher_bootstraps = create_bootstraps(away_team, away_starter, home_lineup)
            for j in range(game_sims):
                if j % 10 == 9:
                    print(j + 1)
                bootstraps = [home_pitcher_bootstraps, away_pitcher_bootstraps]
                game_sim = Game.Game(cur_date, param_teams, starters, lineups, pitches_matrix, param_bullpens,
                                     bootstraps, roster)
                score, linescore, boxscore = game_sim.simulate_game()
                if score is None:
                    break
                away_scores.append(score[0])
                home_scores.append(score[1])
                away_str = away_team.ljust(13) + " "
                count = 0
                while count < len(linescore):
                    away_str += str(linescore[count]) + " "
                    count += 2
                away_str += "  " + str(score[0])
                count = 1
                home_str = home_team.ljust(13) + " "
                while count < len(linescore):
                    home_str += str(linescore[count]) + " "
                    count += 2
                home_str += "  " + str(score[1])
                print(away_str)
                print(home_str + "\n")
                home_keys = list(boxscore[1].keys())
                for k, away_key in enumerate(boxscore[0]):
                    for a in range(7):
                        total_box[0][away_key][a] += boxscore[0][away_key][a]
                    if k < len(home_keys):
                        for a in range(7):
                            total_box[1][home_keys[k]][a] += boxscore[1][home_keys[k]][a]
                total_score = np.add(total_score, score)
                if score[1] > score[0]:
                    home_wins += 1
            end = time.time()
            predicted_games[away_team + " @ " + home_team] -= 1
            no_change = False
            if total_score[0] == 0:
                continue
            box_score = ""
            home_keys = list(total_box[1].keys())
            for j, away_key in enumerate(total_box[0]):
                box_score += away_key.ljust(30)
                for a in range(7):
                    box_score += str(total_box[0][away_key][a] / game_sims).ljust(5)
                if j < len(home_keys):
                    box_score += "     " + home_keys[j].ljust(30)
                    for a in range(7):
                        box_score += str(total_box[1][home_keys[j]][a] / game_sims).ljust(5)
                box_score += "\n"
            file = open(os.path.join(cwd, "Predictions", "Tracking Reference " + str(cur_date) + ".txt"), 'a+')
            file.write(box_score)
            combined_mean = (np.mean(home_scores) - np.mean(away_scores)) * adjustment
            combined_var = (np.var(home_scores) + np.var(away_scores)) * (adjustment ** 2)
            var = scipy.stats.norm(combined_mean, combined_var ** (1 / 2))
            prob_away_win = var.cdf(0)
            prob_away_fav_win = var.cdf(-1.5)
            prob_home_fav_win = 1 - var.cdf(1.5)
            file.write("The simulations took " + str(end - start) + " seconds for the " + str(game_sims))
            file.write(" simulations\n")
            divisor = game_sims / 100
            if total_score[1] >= total_score[0]:
                victory = "The " + home_team + " beat the " + away_team + " "
                victory += str(home_wins / divisor) + "% of the games by an average score of "
                victory += str(total_score[1] * adjustment / game_sims) + " to "
                victory += str(total_score[0] * adjustment / game_sims)
                file.write(victory + "\n")

                probabilities = "The " + home_team + " have a " + str((1 - prob_away_win) * 100) + "% chance of winning"
                probabilities += ", a " + str(prob_home_fav_win * 100) + "% chance of covering -1.5,"
                probabilities += " and a " + str((1 - prob_away_fav_win) * 100) + "% chance of covering +1.5"
                file.write(probabilities + "\n")
            else:
                victory = "The " + away_team + " beat the " + home_team + " "
                victory += str((game_sims - home_wins) / divisor) + "% of the games by an average score of "
                victory += str(total_score[0] * adjustment / game_sims) + " to "
                victory += str(total_score[1] * adjustment / game_sims)
                file.write(victory + "\n")

                probabilities = "The " + away_team + " have a " + str(prob_away_win * 100) + "% chance of winning,"
                probabilities += " a " + str(prob_away_fav_win * 100) + "% chance of covering -1.5,"
                probabilities += " and a " + str((1 - prob_home_fav_win) * 100) + "% chance of covering +1.5"
                file.write(probabilities + "\n")
            file.write("\n")
            file.close()
        finished = True
        for matchup in predicted_games:
            if predicted_games[matchup] != 0:
                finished = False
        if finished:
            break


def create_bootstraps(team, starter, lineup):
    pitchers = get_pitchers(team, starter)
    bootstraps = {}
    most_similar_lineup = []
    for hitter in lineup:
        most_similar_lineup.append(get_most_similar(hitter, "hitter"))
    for pitcher in pitchers:
        bootstraps[pitcher] = create_bootstrap(get_most_similar(pitcher, "pitcher"), most_similar_lineup, lineup)
    return bootstraps


def get_pitchers(team, starter):
    pitchers = [starter]
    bullpen = open(os.path.join(cwd, "Bullpens", "2019 " + team + " Bullpen.csv"))
    for i, line in enumerate(bullpen.readlines()):
        if i % 8 == 0:
            pitchers.append(line.split(",")[0].strip())
    return pitchers


def get_most_similar(player, identifier):
    if identifier == "hitter":
        file = open(os.path.join(cwd, "Similarity Scores", "2019 Batter Similarity Scores.csv"))
    else:
        file = open(os.path.join(cwd, "Similarity Scores", "2019 Pitcher Similarity Scores.csv"))
    lines = file.readlines()
    names = lines[0].split(",")[1:]
    names = list(map(lambda x: x.strip(), names))
    names_np = np.array(names)
    if player in names:
        ind = names.index(player)
        scores = np.array(lines[ind + 1].split(",")[1:]).astype(float)
        sorted_indices = np.argsort(scores)
        same_handed_similarity = scores[np.where(scores >= 0)]
        start_index = len(sorted_indices) - len(same_handed_similarity)
        return names_np[sorted_indices[start_index:start_index + 20]]
    return np.array([])


def create_bootstrap(pitchers, hitters, lineup):
    roster = Master_Roster_Creation.create_from_file()
    bootstrap = {"Generic": []}
    for i, pitcher in enumerate(pitchers):
        for year in [2019, 2018, 2017]:
            try:
                current_pitcher_file = open(os.path.join(cwd, "PitchFX", pitcher.strip() + " " + str(year) + ".csv"))
            except FileNotFoundError:
                continue
            for line in current_pitcher_file.readlines()[1:]:
                pitch = line.split(",")
                if i == 0:
                    bootstrap["Generic"].append(pitch)
                for k, batter in enumerate(lineup):
                    if batter not in bootstrap:
                        bootstrap[batter] = []
                    if hitters[k].size != 0:
                        batter_list = [roster[batter.strip()].strip()]
                        if i == 0:
                            for comp_batter in hitters[k][1:]:
                                batter_list.append(roster[comp_batter.strip()].strip())
                        if pitch[6] in batter_list:
                            bootstrap[batter].append(pitch)
    return bootstrap


def adjust():
    file = open(os.path.join(cwd, "Prediction Tracking.csv"))
    predicted_total = 0
    actual_total = 0
    for line in file.readlines()[1:]:
        elements = line.split(",")
        predicted_total += float(elements[3]) + float(elements[4])
        actual_total += int(elements[5]) + int(elements[6])
    return predicted_total, actual_total


cwd = os.getcwd()
