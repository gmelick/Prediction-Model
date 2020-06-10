from datetime import date
from calculate_game import calculate_game
import requests
from bs4 import BeautifulSoup
import Game
from pitching import get_pitches
import numpy as np
import scipy.stats
import time
import os
from bullpen_from_api import load_bullpen, get_team_list, get_roster_player_keys


def simulate_day(cur_date):
    id_to_name = get_roster_player_keys(cur_date, True)
    name_to_id = get_roster_player_keys(cur_date, False)
    bullpens = create_team_bullpens(load_bullpen()[0], get_rosters(cur_date), id_to_name)
    pitches_matrix = get_pitches()
    predicted_total, actual_total = adjust(cur_date.year)
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
            if "no games scheduled" in games[0].text:
                break
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
            home_pitchers = [home_starter] + list(bullpens[home_team][0].keys())
            away_pitchers = [away_starter] + list(bullpens[away_team][0].keys())
            home_pitcher_bootstraps = create_bootstraps(home_pitchers, away_lineup, cur_date, name_to_id,
                                                        bullpens[home_team])
            away_pitcher_bootstraps = create_bootstraps(away_pitchers, home_lineup, cur_date, name_to_id,
                                                        bullpens[away_team])
            bootstraps = [home_pitcher_bootstraps, away_pitcher_bootstraps]

            for j in range(game_sims):
                if j % 10 == 9:
                    print(j + 1)
                game_sim = Game.Game(cur_date, param_teams, starters, lineups, pitches_matrix, param_bullpens,
                                     bootstraps)
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
                file.write(f"The simulations took {end - start:.2f} seconds for the {game_sims} simulations\n")
                prob_away_win, prob_home_fav_cover, prob_away_fav_cover = \
                    __write_statistics(total_score, home_scores, away_scores, home_wins, adjustment, home_team,
                                       away_team, file)

            with open(os.path.join(cwd, "Predictions", f"{cur_date.year} Betting Tracker.csv"), 'a') as file:
                home_score = float(f"{total_score[1] * adjustment / game_sims: .2f}")
                away_score = float(f"{total_score[0] * adjustment / game_sims: .2f}")
                file.write(f"{cur_date},{home_team},{away_team},{home_score},{away_score}")
                double_header_game = 0
                if away_team + " @ " + home_team in doubleheader_tracking and \
                        doubleheader_tracking[away_team + " @ " + home_team] == 1:
                    double_header_game = 1
                home_team = teams_dict[home_team] if home_team in teams_dict else teams_dict[translate[home_team]]
                away_team = teams_dict[away_team] if away_team in teams_dict else teams_dict[translate[away_team]]
                home_score = float(f"{total_score[1] * adjustment / game_sims: .2f}")
                away_score = float(f"{total_score[0] * adjustment / game_sims: .2f}")
                money, betting_stats = calculate_game("MLB", home_team, away_team, home_score, away_score, cur_date.day,
                                                      cur_date.month, cur_date.year, double_header_game)
                if money is None:
                    file.write("\n")
                    continue

                for stat in betting_stats:
                    file.write(f",{stat}")
                for amount in money:
                    for dollars in amount:
                        file.write(f",{dollars}")
                file.write("\n")

            spread_money, ml_money, total_money = money
            home_actual, away_actual, home_spread, home_spread_odds, away_spread, away_spread_odds, home_ml, away_ml, \
                total, over_odds, under_odds = betting_stats
            pred_odds_winner, rel_risk_ml, rel_tw_ml, rel_res_ml, rel_home_cover, rel_away_cover, rel_spd_risk, \
                rel_spd_tw, rel_spd_res = calc_relative_bets(home_score, away_score, 1 - prob_away_win,
                                                             prob_home_fav_cover, prob_away_fav_cover, home_actual,
                                                             away_actual, int(home_ml), int(away_ml), home_spread,
                                                             int(home_spread_odds), int(away_spread_odds))
            with open(os.path.join(cwd, "Predictions", f"{cur_date.year} Relative Betting Tracker.csv"), 'a') as file:
                file.write(f"{cur_date},{home_team},{away_team},{home_score},{away_score},{home_actual},{away_actual},")
                file.write(f"{home_ml},{away_ml},{ml_money[0]},{ml_money[1]},{ml_money[2]},{pred_odds_winner:.2f},")
                file.write(f"{rel_risk_ml},{rel_tw_ml},{rel_res_ml},{home_spread},{home_spread_odds},")
                file.write(f"{away_spread_odds},{spread_money[0]},{spread_money[1]},{spread_money[2]},")
                file.write(f"{rel_home_cover:.2f},{rel_away_cover:.2f},{rel_spd_risk},{rel_spd_tw},{rel_spd_res},")
                file.write(f"{total},{over_odds},{under_odds},{total_money[0]},{total_money[1]},{total_money[2]}\n")

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

    if not os.path.exists(os.path.join(cwd, "Predictions", f"{year} Relative Betting Tracker.csv")):
        with open(os.path.join(cwd, "Predictions", f"{year} Relative Betting Tracker.csv"), 'w+') as file:
            file.write("Date,Home,Away,Home Pred,Away Pred,Home Act,Away Act,ML (H),ML (A),Risk,To Win,$,Pred % ML,")
            file.write("Risk (Rel),To Win,$,Home Spread,Odds (H),Odds (A),Risk,To Win,$,Pred Home Cover,")
            file.write("Pred Away Cover,Risk (Rel),To Win,$,Total,Over,Under,Risk,To Win,$\n")


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
        away_team = translate[away_team] if away_team in translate else away_team
        home_team = translate[home_team] if home_team in translate else home_team
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
    away_team = translate[away_team] if away_team in translate else away_team
    home_team = translate[home_team] if home_team in translate else home_team
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
        winning_score = total_score[0] * adjustment / game_sims
        losing_score = total_score[1] * adjustment / game_sims
        winner_percentage = prob_away_win * 100
        favorite_cover = prob_away_fav_win * 100
        dog_cover = (1 - prob_home_fav_win) * 100
    f_str = f"The {winning_team} beat the {losing_team} {percentage:.1f}% of the games by an average score of "
    f_str += f"{winning_score:.2f} to {losing_score:.2f}\nThe {winning_team} have a {winner_percentage:.1f}% chance of "
    f_str += f"winning, a {favorite_cover:.1f}% chance of covering -1.5, and a {dog_cover:.1f}% chance of covering +1.5"
    file.write(f_str + "\n\n")
    return prob_away_win, prob_home_fav_win, prob_away_fav_win


def create_bootstraps(pitchers, lineup, sim_date, roster, bullpen):
    bootstraps = {}
    most_similar_lineup = [get_most_similar(roster[hitter], "hitter", sim_date.year, roster) for hitter in lineup]
    for pitcher in pitchers:
        pitcher_list = get_most_similar(pitcher, "pitcher", sim_date.year, roster)
        bootstrap = create_bootstrap(pitcher_list, most_similar_lineup, lineup, sim_date)
        if bootstrap is not None:
            bootstraps[pitcher] = bootstrap
        elif pitcher in bullpen[0]:
            bullpen[1] = np.subtract(bullpen[1], bullpen[0][pitcher])
            del (bullpen[0][pitcher])
    return bootstraps


def get_most_similar(player, identifier, year, roster):
    if identifier == "hitter":
        file = open(os.path.join(cwd, "Similarity Scores", f"{year} Batter Similarity Scores.csv"))
    else:
        file = open(os.path.join(cwd, "Similarity Scores", f"{year} Pitcher Similarity Scores.csv"))
    lines = file.readlines()
    if identifier == "hitter":
        names = np.array([roster[name.strip()] for name in lines[0].split(",")[1:]])
    else:
        names = np.array([name.strip() for name in lines[0].split(",")[1:]])
    if player in names:
        ind = np.where(names == player)[0][0]
        scores = np.array(lines[ind + 1].split(",")[1:]).astype(float)
        same_handed_ind = np.where(scores >= 0)
        same_handed_names = names[same_handed_ind]
        same_handed_scores = scores[same_handed_ind]
        return same_handed_names[np.argsort(same_handed_scores)[:20]]
    return np.array([])


def create_bootstrap(pitchers, hitters, lineup, sim_date):
    bootstrap = {hitter: [] for hitter in lineup}
    bootstrap["Generic"] = []
    for i, pitcher in enumerate(pitchers):
        for year in range(sim_date.year - 2, sim_date.year + 1):
            if not os.path.exists(os.path.join(cwd, "PitchFX", f"{pitcher.strip()} {year}.csv")):
                continue
            with open(os.path.join(cwd, "PitchFX", f"{pitcher.strip()} {year}.csv")) as current_pitcher_file:
                lines = current_pitcher_file.readlines()[1:]
                if i == 0:
                    batter_list = __create_full_batter_list(lineup, hitters)
                else:
                    batter_list = {batter: [batter] for batter in lineup}
                for line in lines:
                    pitch = line.split(",")
                    if get_date(pitch[0]) < sim_date:
                        if i == 0:
                            bootstrap["Generic"].append(pitch)
                        if int(pitch[5]) in batter_list:
                            for batter in batter_list[int(pitch[5])]:
                                bootstrap[batter].append(pitch)
    if len(bootstrap["Generic"]) < 25:
        return None
    return bootstrap


def __create_full_batter_list(lineup, hitters):
    batter_list = {}
    for batter, cmp_list in zip(lineup, hitters):
        for cmp_batter in cmp_list:
            if cmp_batter in batter_list:
                batter_list[cmp_batter].append(batter)
            else:
                batter_list[cmp_batter] = [batter]
    return batter_list


def get_rosters(day):
    team_list, team_names = get_team_list(day.year)
    roster_params = {"rosterType": "40man", "date": day.strftime("%m/%d/%Y")}
    rosters = {}
    for team, team_name in zip(team_list, team_names):
        while True:
            roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team}/roster", params=roster_params).json()
            if bool(roster.get("roster", {})):
                break
        rosters[team_name] = [player["person"]["id"] for player in roster["roster"]]
    return rosters


def create_team_bullpens(bullpen, roster, id_to_name):
    team_bullpen = {}
    for team in roster:
        team_bullpen[team] = [{}, np.zeros((7, 11))]
        for player in roster[team]:
            if str(player) in bullpen and player in id_to_name:
                team_bullpen[team][0][id_to_name[player]] = bullpen[str(player)]
                team_bullpen[team][1] = np.add(team_bullpen[team][1], bullpen[str(player)])
    return team_bullpen


def get_date(date_str):
    first_ind = date_str.find("-")
    last_ind = date_str.rfind("-")
    year = date_str[:first_ind]
    month = date_str[first_ind + 1:last_ind]
    day = date_str[last_ind + 1:]
    return date(int(year), int(month), int(day))


def adjust(year):
    predicted_total = 0
    actual_total = 0
    if os.path.exists(os.path.join(cwd, "Predictions", f"{year} Betting Tracker.csv")):
        with open(os.path.join(cwd, "Predictions", f"{year} Betting Tracker.csv")) as file:
            for line in file.readlines()[1:]:
                elements = line.split(",")
                if len(elements) > 6:
                    predicted_total += float(elements[3]) + float(elements[4])
                    actual_total += int(elements[5]) + int(elements[6])
        return predicted_total, actual_total
    return 1, 1


# Returns the probability of the winning team winning (according to the score distribution), the results of betting on
# that outcome, then the odds of the home team covering, the odds of the away team covering, and the result of betting
# the spread based on those numbers
def calc_relative_bets(pred_home_score, pred_away_score, pred_odds_home_win, pred_odds_home_fav_cover,
                       pred_odds_home_dog_cover, home_score, away_score, home_odds, away_odds, home_spread,
                       home_spread_odds, away_spread_odds):
    if pred_home_score > pred_away_score:
        pred_prob_winner_win = pred_odds_home_win
        prob_winner_win, risk, to_win = calc_prob_from_odds(home_odds)
        act_winner_score = home_score
        act_loser_score = away_score
    else:
        pred_prob_winner_win = 1 - pred_odds_home_win
        prob_winner_win, risk, to_win = calc_prob_from_odds(away_odds)
        act_winner_score = away_score
        act_loser_score = home_score
    if pred_prob_winner_win > prob_winner_win:
        money = to_win if act_winner_score > act_loser_score else -risk if act_loser_score > act_winner_score else 0
    else:
        risk, to_win, money = 0, 0, 0
    results = [pred_prob_winner_win * 100, risk, to_win, money]
    if home_spread > 0:
        results += [pred_odds_home_dog_cover * 100, (1 - pred_odds_home_dog_cover) * 100]
        pred_odds_dog_cover = pred_odds_home_dog_cover
        odds_dog_cover, risk_dog, to_win_dog = calc_prob_from_odds(home_spread_odds)
        pred_odds_fav_cover = 1 - pred_odds_home_dog_cover
        odds_fav_cover, risk_fav, to_win_fav = calc_prob_from_odds(away_spread_odds)
        actual_fav_score, actual_dog_score, spread = away_score, home_score, -home_spread
    else:
        results += [pred_odds_home_fav_cover * 100, (1 - pred_odds_home_fav_cover) * 100]
        pred_odds_dog_cover = 1 - pred_odds_home_fav_cover
        odds_dog_cover, risk_dog, to_win_dog = calc_prob_from_odds(away_spread_odds)
        pred_odds_fav_cover = pred_odds_home_fav_cover
        odds_fav_cover, risk_fav, to_win_fav = calc_prob_from_odds(home_spread_odds)
        actual_fav_score, actual_dog_score, spread = home_score, away_score, home_spread
    if pred_odds_dog_cover > odds_dog_cover:
        money = to_win_dog if actual_fav_score + spread < actual_dog_score else \
            -risk_dog if actual_fav_score + spread > actual_dog_score else 0
        results += [risk_dog, to_win_dog, money]
    elif pred_odds_fav_cover > odds_fav_cover:
        money = to_win_fav if actual_fav_score + spread > actual_dog_score else \
            -risk_fav if actual_fav_score + spread < actual_dog_score else 0
        results += [risk_fav, to_win_fav, money]
    else:
        results += [0, 0, 0]
    return results


def calc_prob_from_odds(odds):
    if odds > 0:
        return 100 / (odds + 100), 10, odds / 10
    else:
        return odds / (odds - 100), odds / -10, 10


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
