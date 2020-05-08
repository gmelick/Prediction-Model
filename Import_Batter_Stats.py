import requests
from bs4 import BeautifulSoup
import os
from datetime import date


def get_batter_stats(day):
    # These parameters get all players with at least 100 Plate Appearances
    starting_params = {
        "pos": "all",
        "stats": "bat",
        "lg": "all",
        "qual": 100,
        "season": day.year,
        "page": "1_50",
        "type": 8
    }

    # Initializes the array that will hold the batter statistics, loads just batter names and handedness
    stats = __create_handedness_from_file()

    file = __open_file("Batter Hand Reference.csv")
    # Adds any new players and their handedness to the statistics dictionary, and writes them to the reference file
    __process_pages(starting_params, stats, file)
    file.close()

    # Gets the desired player data from the last three years and adds it to the statistics dictionary
    starting_params["season1"] = day.year - 2
    starting_params["startdate"] = str(date(day.year - 2, 3, 1))
    starting_params["enddate"] = str(day)
    for stat_type in fields_by_type:
        starting_params["type"] = stat_type
        __process_pages(starting_params, stats, file, stat_type)

    # Writes the data from the statistics dictionary to a file
    __write_stats(day.year, stats)


def __create_handedness_from_file():
    if os.path.exists("Batter Hand Reference.csv"):
        file = open(os.path.join(cwd, "Batter Hand Reference.csv"))
        return {line.split(",")[0]: [line.split(",")[1].strip()] for line in file.readlines()}
    else:
        return {}


def __open_file(file_name):
    if os.path.exists(file_name):
        return open(os.path.join(cwd, file_name), 'a+')
    else:
        return open(os.path.join(cwd, file_name), 'w+')


def __process_pages(params, stats, file, stat_type=None):
    pages = __get_total_pages(params)
    for page in range(1, pages + 1):
        params["page"] = f"{page}_50"
        table_body = __get_table_body(params)
        __process_table(table_body, stats, file, stat_type)


def __get_total_pages(params):
    soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
    return int(soup.find("div", {"class": "rgWrap rgInfoPart"}).find_all("strong")[1].text)


def __get_table_body(params):
    soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
    return soup.find("table", {"class": "rgMasterTable"}).find("tbody")


def __process_table(table, stats, file, stat_type):
    for row in table.find_all("tr"):
        data = row.find_all("td")
        name = data[1].text
        if stat_type is None:
            if name not in stats:
                __get_handedness(row, name, stats, file)
        else:
            if name in stats:
                __get_stats(stat_type, data, stats, name)


def __get_handedness(row, name, stats, file):
    handedness_extension = row.find("a")["href"]
    handedness_url = "https://www.fangraphs.com/" + handedness_extension
    soup = BeautifulSoup(requests.get(handedness_url).content, 'html.parser')
    bats_throws = soup.find_all("div", {"class": "player-info-box-item"})[1].text
    start = bats_throws.find(":") + 2
    stats[name] = [bats_throws[start:start + 1]]
    file.write(name + "," + bats_throws[start:start + 1] + "\n")


def __get_stats(stat_type, data, stats, name):
    for i in fields_by_type[stat_type]:
        text = data[i].text
        stats[name].append(text[:text.find(" ")])


def __write_stats(year, stats):
    with open(os.path.join(cwd, f"{year} Batter Stats.csv"), 'w+') as file:
        for player in stats:
            if player in name_corrections:
                file.write(name_corrections[player])
            else:
                file.write(player)
            for stat in stats[player]:
                file.write(f",{stat}")
            file.write("\n")


# Differences in names between FanGraphs and the MLB Stats API
name_corrections = {
    "Peter Alonso": "Pete Alonso",
    "Giovanny Urshela": "Gio Urshela",
    "Steve Wilkerson": "Stevie Wilkerson",
    "J.T. Riddle": "JT Riddle",
    "Dwight Smith Jr.": "Dwight Smith Jr",
    "Richie Martin Jr.": "Richie Martin"
}

# The keys (1, 2, 5) are the different types on the FanGraphs leaderboard page:
#       1 - Advanced
#       2 - Batted Ball
#       5 - Plate Discipline
# The lists associated are the indices of the fields we want to pull from the given page:
#       Advanced - BB%, K%
#       Batted Ball - LD%, GB%, FB%, HR/FB, Pull%, Cent%, Oppo%, Soft%, Med%, Hard%
#       Plate Discipline - O-Swing%, Z-Swing%, Swing%, O-Contact%, Z-Contact%, Contact%, SwStr%
# For information on what these stats represent, see https://library.fangraphs.com/offense/offensive-statistics-list/
fields_by_type = {
    1: [4, 5],
    2: [5, 6, 7, 9, 14, 15, 16, 17, 18, 19],
    5: [3, 4, 5, 6, 7, 8, 11]
}
cwd = os.getcwd()
url = "https://www.fangraphs.com/leaders.aspx"
