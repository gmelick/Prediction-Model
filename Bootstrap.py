from datetime import date
from calculate_game import calculate_game
import requests
from bs4 import BeautifulSoup
import Game
from pitching import get_pitches, get_bullpens
import numpy as np
import scipy.stats
import time
import Master_Roster_Creation
import os


def simulate_day(cur_date):
    roster = Master_Roster_Creation.create_reverse()
    pitches_matrix = get_pitches()
    if cur_date.month > 4:
        bullpens = get_bullpens(cur_date.year)
    else:
        bullpens = get_bullpens(cur_date.year - 1)
    predicted_total, actual_total = adjust()
    adjustment = actual_total / predicted_total if predicted_total != 0 else 1
    iteration = 0
    predicted_games = {}
    doubleheader_tracking = {}
    no_change = False
    while True:
        if no_change:
            time.sleep(180)
        __create_tracker(cur_date.year)
        url = f"https://www.mlb.com/starting-lineups/{cur_date.year}-{cur_date.month}-{cur_date.day}"
        soup = __connect(url)
        games = soup.find_all("div", {"class": "starting-lineups__matchup"})
        if iteration == 0:
            predicted_games, doubleheader_tracking = __iterate_games(games)
            iteration += 1

        for i, game in enumerate(games):
            processed = __process_game(game, predicted_games, doubleheader_tracking)
            if processed == -1:
                continue
            home_team, away_team, home_starter, away_starter, home_lineup, away_lineup = processed
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
                total_box[a] = {batter: [0] * 7 for batter in lineup}
                total_box[a]["Generic"] = [0] * 7
            start = time.time()
            home_pitcher_bootstraps = create_bootstraps(home_team, home_starter, away_lineup, cur_date)
            away_pitcher_bootstraps = create_bootstraps(away_team, away_starter, home_lineup, cur_date)
            bootstraps = [home_pitcher_bootstraps, away_pitcher_bootstraps]

            for j in range(game_sims):
                if j % 10 == 9:
                    print(j + 1)
                game_sim = Game.Game(cur_date, param_teams, starters, lineups, pitches_matrix, param_bullpens,
                                     bootstraps, roster)
                score, linescore, boxscore = game_sim.simulate_game()
                if score is None:
                    break
                away_scores.append(score[0])
                home_scores.append(score[1])
                __write_linescore(home_team, away_team, score, linescore)
                __add_boxscore_to_total(boxscore, total_box)
                total_score = np.add(total_score, score)
                if score[1] > score[0]:
                    home_wins += 1
            end = time.time()

            predicted_games[away_team + " @ " + home_team] -= 1
            no_change = False
            if total_score[0] == 0:
                continue
            box_score = __create_file_boxscore(total_box)
            with open(os.path.join(cwd, "Predictions", "Tracking Reference " + str(cur_date) + ".txt"), 'a+') as file:
                file.write(box_score)
                file.write(f"The simulations took {end - start} seconds for the {game_sims} simulations\n")
                __write_statistics(total_score, home_scores, away_scores, home_wins, adjustment, home_team, away_team,
                                   file)

            with open(os.path.join(cwd, "Predictions", f"{cur_date.year} Betting Tracker.csv"), 'a') as file:
                file.write(f"{cur_date},{home_team},{away_team},{total_score[1]},{total_score[0]}")
                double_header_game = 0
                if away_team + " @ " + home_team in doubleheader_tracking:
                    double_header_game = doubleheader_tracking[away_team + " @ " + home_team]
                home_team = teams_dict[home_team] if home_team in teams_dict else translate[home_team]
                away_team = teams_dict[away_team] if away_team in teams_dict else translate[away_team]
                result = calculate_game("MLB", home_team, away_team, total_score[1], total_score[0], cur_date.day,
                                        cur_date.month, cur_date.year, double_header_game)
                if result is None:
                    file.write("\n")
                    continue
                else:
                    money, betting_stats = result
                for stat in betting_stats:
                    file.write(f",{stat}")
                for amount in money:
                    for dollars in amount:
                        file.write(f",{dollars}")
                file.write("\n")
        finished = True
        for matchup in predicted_games:
            if predicted_games[matchup] != 0:
                finished = False
        if finished:
            break


def __create_tracker(year):
    if not os.path.exists(os.path.join(cwd, "Predictions", f"{year} Betting Tracker.csv")):
        with open(os.path.join(cwd, "Predictions", f"{year} Betting Tracker.csv"), 'w+') as write_header_file:
            write_header_file.write("Date,Home Team,Away Team,Predicted Score Home,Predicted Score Away,")
            write_header_file.write("Actual Home Score,Actual Away Score,Home Spread,Home Spread Odds,Away Spread,")
            write_header_file.write("Away Spread Odds,Home Moneyline,Away Moneyline,Total,Over Odds,Under Odds,")
            write_header_file.write("Spread Risk,Spread To Win,Spread $,Moneyline Risk,Moneyline To Win,Moneyline $,")
            write_header_file.write("Total Risk,Total To Win,Total $\n")


def __connect(url):
    while True:
        try:
            return BeautifulSoup(requests.get(url).content, 'html.parser')
        except requests.exceptions.ConnectionError:
            continue


def __iterate_games(games):
    predicted_games = {}
    doubleheader_tracking = {}
    for game in games:
        teams = game.find_all("a", {"class": "starting-lineups__team-name--link"})
        away_team = teams[0].text.strip()
        home_team = teams[1].text.strip()
        if away_team + " @ " + home_team in predicted_games:
            predicted_games[away_team + " @ " + home_team] += 1
            doubleheader_tracking[away_team + " @ " + home_team] = 0
        else:
            predicted_games[away_team + " @ " + home_team] = 1
    return predicted_games, doubleheader_tracking


def __process_game(game, predicted_games, doubleheader_tracking):
    teams = game.find_all("a", {"class": "starting-lineups__team-name--link"})
    away_team = teams[0].text.strip()
    home_team = teams[1].text.strip()
    postponed_class = "starting-lineups__game-state starting-lineups__game-state--postponed"
    postponed = game.find("span", {"class": postponed_class})
    if postponed is not None:
        if predicted_games[away_team + " @ " + home_team] > 0:
            predicted_games[away_team + " @ " + home_team] -= 1
        return -1
    if away_team not in teams_ or home_team not in teams_:
        return -1
    if predicted_games[away_team + " @ " + home_team] == 0:
        return -1
    pitchers = game.find_all("div", {"class": "starting-lineups__pitcher-name"})
    away_starter = pitchers[0].text.strip()
    home_starter = pitchers[1].text.strip()
    if away_starter == 'TBD' or home_starter == 'TBD':
        return -1
    if game.find("li", {"class": "starting-lineups__player--TBD"}) is not None:
        return -1

    if away_team + " @ " + home_team in doubleheader_tracking:
        if doubleheader_tracking[away_team + " @ " + home_team] == 1:
            return -1
        elif doubleheader_tracking[away_team + " @ " + home_team] == 0:
            doubleheader_tracking[away_team + " @ " + home_team] = away_starter + home_starter
        elif doubleheader_tracking[away_team + " @ " + home_team] != away_starter + home_starter:
            doubleheader_tracking[away_team + " @ " + home_team] = 1
        else:
            return -1
    away_lineup = []
    home_lineup = []
    for a, player in enumerate(game.find_all("a", {"class": "starting-lineups__player--link"})):
        if a < 9:
            away_lineup.append(player.text)
        elif a < 18:
            home_lineup.append(player.text)
        else:
            break
    return home_team, away_team, home_starter, away_starter, home_lineup, away_lineup


def __write_linescore(home_team, away_team, score, linescore):
    away_str = f"{away_team.ljust(13)} "
    away_str += " ".join([str(linescore[i]) for i in range(0, len(linescore), 2)])
    away_str += f"  {score[0]}"
    home_str = home_team.ljust(13) + " "
    home_str += " ".join([str(linescore[i]) for i in range(1, len(linescore), 2)])
    home_str += f"  {score[1]}"
    print(away_str)
    print(home_str + "\n")


def __add_boxscore_to_total(boxscore, total_box):
    home_keys = list(boxscore[1].keys())
    for k, away_key in enumerate(boxscore[0]):
        for a in range(7):
            total_box[0][away_key][a] += boxscore[0][away_key][a]
        if k < len(home_keys):
            for a in range(7):
                total_box[1][home_keys[k]][a] += boxscore[1][home_keys[k]][a]


def __create_file_boxscore(total_box):
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
    return box_score


def __write_statistics(total_score, home_scores, away_scores, home_wins, adjustment, home_team, away_team, file):
    combined_mean = (np.mean(home_scores) - np.mean(away_scores)) * adjustment
    combined_var = (np.var(home_scores) + np.var(away_scores)) * (adjustment ** 2)
    var = scipy.stats.norm(combined_mean, combined_var ** (1 / 2))
    prob_away_win = var.cdf(0)
    prob_away_fav_win = var.cdf(-1.5)
    prob_home_fav_win = 1 - var.cdf(1.5)
    divisor = game_sims / 100
    if total_score[1] >= total_score[0]:
        winning_team = home_team
        losing_team = away_team
        percentage = home_wins / divisor
        winning_score = total_score[1] * adjustment / game_sims
        losing_score = total_score[0] * adjustment / game_sims
        winner_percentage = (1 - prob_away_win) * 100
        favorite_cover = prob_home_fav_win * 100
        dog_cover = (1 - prob_away_fav_win) * 100
    else:
        winning_team = away_team
        losing_team = home_team
        percentage = (game_sims - home_wins) / divisor
        winning_score = total_score[1] * adjustment / game_sims
        losing_score = total_score[0] * adjustment / game_sims
        winner_percentage = prob_away_win * 100
        favorite_cover = prob_away_fav_win * 100
        dog_cover = (1 - prob_home_fav_win) * 100
    f_str = f"The {winning_team} beat the {losing_team} {percentage}% of the games by an average score of "
    f_str += f"{winning_score} to {losing_score}\nThe {winning_team} have a {winner_percentage}% chance of winning, a "
    f_str += f"{favorite_cover}% chance of covering -1.5, and a {dog_cover}% chance of covering +1.5\n\n"
    file.write(f_str)


def create_bootstraps(team, starter, lineup, sim_date):
    pitchers = get_pitchers(team, starter, sim_date)
    bootstraps = {}
    most_similar_lineup = [get_most_similar(hitter, "hitter", sim_date.year) for hitter in lineup]
    for pitcher in pitchers:
        pitcher_list = get_most_similar(pitcher, "pitcher", sim_date.year)
        bootstraps[pitcher] = create_bootstrap(pitcher_list, most_similar_lineup, lineup, sim_date)
    return bootstraps


def get_pitchers(team, starter, sim_date):
    pitchers = [starter]
    if sim_date.month > 4:
        year = sim_date.year
    else:
        year = sim_date.year - 1
    bullpen = open(os.path.join(cwd, "Bullpens", f"{year} {team} Bullpen.csv"))
    for i, line in enumerate(bullpen.readlines()):
        if i % 8 == 0:
            pitchers.append(line.split(",")[0].strip())
    return pitchers


def get_most_similar(player, identifier, year):
    if identifier == "hitter":
        file = open(os.path.join(cwd, "Similarity Scores", f"{year} Batter Similarity Scores.csv"))
    else:
        file = open(os.path.join(cwd, "Similarity Scores", f"{year} Pitcher Similarity Scores.csv"))
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


def create_bootstrap(pitchers, hitters, lineup, sim_date):
    roster = Master_Roster_Creation.create_from_file()
    bootstrap = {"Generic": []}
    for i, pitcher in enumerate(pitchers):
        for year in range(sim_date.year - 3, sim_date.year + 1):
            try:
                current_pitcher_file = open(os.path.join(cwd, "PitchFX", f"{pitcher.strip()} {year}.csv"))
            except FileNotFoundError:
                continue
            for line in current_pitcher_file.readlines()[1:]:
                pitch = line.split(",")
                if get_date(pitch[0]) < sim_date:
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


def get_date(date_str):
    first_ind = date_str.find("-")
    last_ind = date_str.rfind("-")
    year = date_str[:first_ind]
    month = date_str[first_ind + 1:last_ind]
    day = date_str[last_ind + 1:]
    return date(int(year), int(month), int(day))


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
teams_ = ["Rockies", "Yankees", "Red Sox", "Orioles", "D-backs", "Reds", "White Sox", "Rays", "Blue Jays", "Braves",
          "Tigers", "Royals", "Indians", "Phillies", "Pirates", "Rangers", "Astros", "Athletics", "Twins", "Padres",
          "Cubs", "Mets", "Giants", "Brewers", "Cardinals", "Angels", "Mariners", "Marlins", "Dodgers", "Nationals"]
translate = {
    "Indios": "Indians",
    "Tigres": "Tigers",
    "Azulejos": "Blue Jays",
    "Rojos": "Reds",
    "Atléticos": "Athletics",
    "Nacionales": "Nationals",
    "Cardenales": "Cardinals",
    "Marineros": "Mariners",
    "Reales": "Royals",
    "Bravos": "Braves",
    "Gigantes": "Giants",
    "Cerveceros": "Brewers",
    "Piratas": "Pirates",
    "Cachorros": "Cubs"
}
teams_dict = {
    "Mets": "NYM",
    "Nationals": "WSH",
    "Orioles": "BAL",
    "Yankees": "NYY",
    "Indians": "CLE",
    "Twins": "MIN",
    "White Sox": "CWS",
    "Royals": "KC",
    "Tigers": "DET",
    "Blue Jays": "TOR",
    "Braves": "ATL",
    "Phillies": "PHI",
    "Astros": "HOU",
    "Rays": "TB",
    "Rockies": "COL",
    "Marlins": "MIA",
    "Cardinals": "STL",
    "Brewers": "MIL",
    "Cubs": "CHC",
    "Rangers": "TEX",
    "Giants": "SF",
    "Padres": "SD",
    "Angels": "LAA",
    "Athletics": "OAK",
    "Red Sox": "BOS",
    "Mariners": "SEA",
    "D-backs": "ARI",
    "Dodgers": "LAD",
    "Pirates": "PIT",
    "Reds": "CIN"
}
game_sims = 100
