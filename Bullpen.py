import requests
from bs4 import BeautifulSoup
import numpy as np


def new_pitcher(lead, inning, bullpen, bullpen_pitchers):
    if lead < -4:
        lead = -5
    elif lead > 4:
        lead = 5
    if inning <= 4:
        inning = 4
    elif inning >= 10:
        inning = 10
    rand_int = np.random.randint(1, bullpen[inning - 4][lead + 5])
    count = 0
    for pitcher in bullpen_pitchers:
        count += bullpen_pitchers[pitcher][inning - 4][lead + 5]
        if count > rand_int:
            return pitcher
    return None


def get_bullpen(team_name):
    base_url = "https://www.baseball-reference.com"
    url = base_url + "/teams/" + __teams[team_name] + "/2019-pitching.shtml"
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    table = soup.find("table", {"id": "team_pitching"})
    body = table.find("tbody")
    relievers = False
    rows = body.find_all("tr")
    for i, row in enumerate(rows):
        position = row.find("td", {"data-stat": "pos"})
        innings = row.find("td", {"data-stat": "IP"})
        if position is not None:
            if position.text == "CL":
                relievers = True
            if relievers:
                if float(innings.text) < 10:
                    break
                pitcher_matrix = np.zeros((7, 11))
                link = row.find("a")["href"]
                player_id = link[link.rfind("/") + 1: link.rfind(".")]
                params = {"id": player_id, "t": "p", "year": 2019}
                soup = BeautifulSoup(requests.get(base_url + "/players/gl.fcgi", params).content, 'html.parser')
                game_log = soup.find("table", {"id": "pitching_gamelogs"})
                situations = game_log.find_all("td", {"data-stat": "pitcher_situation_in"})
                for j, situation in enumerate(situations):
                    if j != len(situations) - 1 and "1b start" not in situation.text and "1t start" not in situation.text:
                        inning = int(situation.text[:2])
                        score = situation.text[situation.text.rfind("out") + 4:]
                        pitcher_matrix = __fill_matrix(inning, score, pitcher_matrix)
                __pitchers[row.find("a").text] = pitcher_matrix
    return __composite_matrix, __pitchers


def __fill_matrix(inning, score, pitcher_matrix):
    if inning <= 4:
        pitcher_matrix = __fill_runs(0, score, pitcher_matrix)
    elif inning >= 10:
        pitcher_matrix = __fill_runs(6, score, pitcher_matrix)
    else:
        pitcher_matrix = __fill_runs(inning - 4, score, pitcher_matrix)
    return pitcher_matrix


def __fill_runs(index, score, pitcher_matrix):
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


__pitchers = {}
__composite_matrix = np.zeros((7, 11))
__teams = {"Atlanta Braves": "ATL",
           "Miami Marlins": "FLA",
           "New York Mets": "NYM",
           "Philadelphia Phillies": "PHI",
           "Washington Nationals": "WSN",
           "Chicago Cubs": "CHC",
           "Cincinnati Reds": "CIN",
           "Milwaukee Brewers": "MIL",
           "Pittsburgh Pirates": "PIT",
           "St. Louis Cardinals": "STL",
           "Arizona Diamondbacks": "ARI",
           "Colorado Rockies": "COL",
           "Los Angeles Dodgers ": "LAD",
           "San Diego Padres": "SDP",
           "San Francisco Giants": "SFG",
           "Baltimore Orioles": "BAL",
           "Boston Red Sox": "BOS",
           "New York Yankees": "NYY",
           "Tampa Bay Rays": "TBR",
           "Toronto Blue Jays": "TOR",
           "Chicago White Sox": "CHW",
           "Cleveland Indians": "CLE",
           "Detroit Tigers": "DET",
           "Kansas City Royals": "KCR",
           "Minnesota Twins": "MIN",
           "Houston Astros": "HOU",
           "Los Angeles Angels": "LAA",
           "Oakland Athletics": "OAK",
           "Seattle Mariners": "SEA",
           "Texas Rangers": "TEX"
           }
