import requests
from bs4 import BeautifulSoup
import numpy as np
from datetime import date, timedelta
import PitchFX
import os


def create_roster():
    cur_date = date.today() - timedelta(1)
    base_url = "https://www.mlb.com/starting-lineups/"
    file = open(os.path.join(cwd, "Master Roster.csv"))
    roster = {}
    for line in file.readlines():
        roster[line.split(",")[0].strip()] = line.split(",")[1].strip()
    file.close()

    url = base_url + str(cur_date)
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    lineup_class = "starting-lineups__teams starting-lineups__teams--sm starting-lineups__teams--xl"
    games = soup.find_all("div", {"class": lineup_class})
    for i, game in enumerate(games):
        print("Roster Game " + str(i + 1) + " of " + str(len(games)))
        for player in game.find_all("a", {"class": "starting-lineups__player--link"}):
            if player.text not in roster:
                href = player["href"]
                player_number = href[href.rfind("-") + 1:]
                roster[player.text] = player_number

    file = open(os.path.join(cwd, "Master Roster.csv"), 'w+')
    for player in roster:
        file.write(player + "," + roster[player] + "\n")
    return roster


def bullpens_to_file():
    for i, team in enumerate(__teams):
        print(team + ": " + str(i + 1) + " of 30")
        composite, bullpen = get_bullpen(team)
        file = open(os.path.join(cwd, "Bullpens", "2019 " + team + " Bullpen.csv"), 'w+')
        for pitcher in bullpen:
            if pitcher in name_corrections:
                file.write(name_corrections[pitcher.strip()] + "\n")
            else:
                file.write(pitcher.strip() + "\n")
            for row in bullpen[pitcher]:
                for i, column in enumerate(row):
                    if i != len(row) - 1:
                        file.write(str(column) + ",")
                    else:
                        file.write(str(column) + "\n")
        file.write("Composite\n")
        for row in composite:
            for i, column in enumerate(row):
                if i != len(row) - 1:
                    file.write(str(column) + ",")
                else:
                    file.write(str(column) + "\n")
        file.close()


def get_bullpen(team_name):
    __pitchers = {}
    __comp_matrix = np.zeros((7, 11))
    base_url = "https://www.baseball-reference.com"
    url = base_url + "/teams/" + __teams[team_name] + "/2019-pitching.shtml"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    table = soup.find("table", {"id": "team_pitching"})
    body = table.find("tbody")
    relievers = False
    for i, row in enumerate(body.find_all("tr")):
        position = row.find("td", {"data-stat": "pos"})
        innings = row.find("td", {"data-stat": "IP"})
        if position is not None:
            if position.text == "CL":
                relievers = True
            if relievers:
                if float(innings.text) < 15:
                    break
                link = row.find("a")["href"]
                __pitchers[row.find("a").text] = __compute_pitcher_matrix(link, base_url, __comp_matrix, __pitchers)
    return __comp_matrix, __pitchers


def __compute_pitcher_matrix(link, base_url, __composite_matrix, __pitchers):
    pitcher_matrix = np.zeros((7, 11))
    player_id = link[link.rfind("/") + 1: link.rfind(".")]
    params = {"id": player_id, "t": "p", "year": 2019}
    url = base_url + "/players/gl.fcgi"
    soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
    game_log = soup.find("table", {"id": "pitching_gamelogs"})
    situations = game_log.find_all("td", {"data-stat": "pitcher_situation_in"})
    for j, situation in enumerate(situations):
        if j != len(situations) - 1 and "1b start" not in situation.text and "1t start" not in situation.text:
            inning = int(situation.text[:2])
            score = situation.text[situation.text.rfind("out") + 4:]
            pitcher_matrix = __fill_matrix(inning, score, pitcher_matrix, __composite_matrix, __pitchers)
    return pitcher_matrix


def __fill_matrix(inning, score, pitcher_matrix, __composite_matrix, __pitchers):
    if inning <= 4:
        pitcher_matrix = __fill_runs(0, score, pitcher_matrix, __composite_matrix, __pitchers)
    elif inning >= 10:
        pitcher_matrix = __fill_runs(6, score, pitcher_matrix, __composite_matrix, __pitchers)
    else:
        pitcher_matrix = __fill_runs(inning - 4, score, pitcher_matrix, __composite_matrix, __pitchers)
    return pitcher_matrix


def __fill_runs(index, score, pitcher_matrix, __composite_matrix, __pitchers):
    if score == "tie":
        pitcher_matrix[index][5] += 1
        __composite_matrix[index][5] += 1
    elif score[0] == "a":
        lead = int(score[1:])
        if lead > 4:
            pitcher_matrix[index][10] += 1
            __composite_matrix[index][10] += 1
        else:
            pitcher_matrix[index][lead + 5] += 1
            __composite_matrix[index][lead + 5] += 1
    else:
        deficit = int(score[1:])
        if deficit > 4:
            pitcher_matrix[index][0] += 1
            __composite_matrix[index][0] += 1
        else:
            pitcher_matrix[index][np.abs(deficit - 5)] += 1
            __composite_matrix[index][np.abs(deficit - 5)] += 1
    return pitcher_matrix


def pitches_to_file(yesterday_games):
    file = open(os.path.join(cwd, "Pitcher Pitches.csv"))
    pitches = {}
    for line in file.readlines():
        name = line.split(",")[0].strip()
        pitches[name] = []
        for pc in line.split(",")[1:]:
            pitches[name].append(pc.strip())
    file.close()

    for i, game in enumerate(yesterday_games):
        print("Pitches Game " + str(i + 1) + " of " + str(len(yesterday_games)))
        box = requests.get("https://statsapi.mlb.com/api/v1/game/" + str(game) + "/boxscore").json()
        for team_des in box["teams"]:
            team = box["teams"][team_des]
            for player_id in team["players"]:
                player = team["players"][player_id]
                if "numberOfPitches" in player["stats"]["pitching"]:
                    if player["person"]["fullName"] in pitches:
                        pitches[player["person"]["fullName"]].append(player["stats"]["pitching"]["numberOfPitches"])
                    else:
                        pitches[player["person"]["fullName"]] = [player["stats"]["pitching"]["numberOfPitches"]]

    file = open(os.path.join(cwd, "Pitcher Pitches.csv"), 'w+')
    for pitcher in pitches:
        print(pitcher)
        file.write(pitcher + ",")
        for pitch_total in pitches[pitcher][:len(pitches[pitcher]) - 1]:
            file.write(str(pitch_total) + ",")
        file.write(str(pitches[pitcher][-1]) + "\n")
    file.close()


def pitches_to_file_alt(games):
    pitches = {}
    for i, game in enumerate(games):
        print("Pitches Game " + str(i + 1) + " of " + str(len(games)))
        box = requests.get("https://statsapi.mlb.com/api/v1/game/" + str(game) + "/boxscore").json()
        for team_des in box["teams"]:
            team = box["teams"][team_des]
            for player_id in team["players"]:
                player = team["players"][player_id]
                if "numberOfPitches" in player["stats"]["pitching"]:
                    if player["person"]["fullName"] in pitches:
                        pitches[player["person"]["fullName"]].append(player["stats"]["pitching"]["numberOfPitches"])
                    else:
                        pitches[player["person"]["fullName"]] = [player["stats"]["pitching"]["numberOfPitches"]]

    file = open(os.path.join(cwd, "Pitcher Pitches.csv"), 'w+')
    for pitcher in pitches:
        print(pitcher)
        file.write(pitcher + ",")
        for pitch_total in pitches[pitcher][:len(pitches[pitcher]) - 1]:
            file.write(str(pitch_total) + ",")
        file.write(str(pitches[pitcher][-1]) + "\n")
    file.close()


def main():
    yesterday_games = PitchFX.find_games()
    create_roster()
    bullpens_to_file()
    pitches_to_file(yesterday_games)


def main_alt():
    games = PitchFX.refresh_season_stats()
    pitches_to_file_alt(games)


__teams = {"Braves": "ATL",
           "Marlins": "MIA",
           "Mets": "NYM",
           "Phillies": "PHI",
           "Nationals": "WSN",
           "Cubs": "CHC",
           "Reds": "CIN",
           "Brewers": "MIL",
           "Pirates": "PIT",
           "Cardinals": "STL",
           "D-backs": "ARI",
           "Rockies": "COL",
           "Dodgers": "LAD",
           "Padres": "SDP",
           "Giants": "SFG",
           "Orioles": "BAL",
           "Red Sox": "BOS",
           "Yankees": "NYY",
           "Rays": "TBR",
           "Blue Jays": "TOR",
           "White Sox": "CHW",
           "Indians": "CLE",
           "Tigers": "DET",
           "Royals": "KCR",
           "Twins": "MIN",
           "Astros": "HOU",
           "Angels": "LAA",
           "Athletics": "OAK",
           "Mariners": "SEA",
           "Rangers": "TEX"
           }
name_corrections = {
    "J.D. Hammer": "JD Hammer",
    "Josh Smith": "Josh A. Smith"
}
cwd = os.getcwd()
