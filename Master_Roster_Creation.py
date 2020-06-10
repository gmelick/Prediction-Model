import os
from datetime import date, timedelta
from bs4 import BeautifulSoup
import requests


def create_roster(day):
    roster = {}
    start_date = date(day.year - 2, 1, 1)
    while start_date <= day:
        print(f"Creating Roster for {start_date}")
        url = f"https://www.mlb.com/starting-lineups/{start_date}"
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        games = soup.find_all("div", {"class": "starting-lineups__teams starting-lineups__teams--sm starting-lineups__teams--xl"})
        for i, game in enumerate(games):
            for player in game.find_all("a", {"class": "starting-lineups__player--link"}):
                if player.text not in roster:
                    href = player["href"]
                    player_number = href[href.rfind("-") + 1:]
                    roster[player.text] = player_number
        start_date += timedelta(1)

    # Write the roster to file
    with open(os.path.join(cwd, "Master Roster.csv"), 'w+') as file:
        for player in roster:
            file.write(f"{player},{roster[player]}\n")


def create_from_file():
    with open(os.path.join(cwd, "Master Roster.csv")) as file:
        return {line.split(",")[0]: line.split(",")[1].strip() for line in file.readlines()}


def create_reverse():
    with open(os.path.join(cwd, "Master Roster.csv")) as file:
        return {line.split(",")[1].strip(): line.split(",")[0] for line in file.readlines()}


cwd = os.getcwd()
