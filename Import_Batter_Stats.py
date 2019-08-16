import requests
from bs4 import BeautifulSoup
import os
import time


def main():
    name_corrections = {
        "Peter Alonso": "Pete Alonso",
        "Giovanny Urshela": "Gio Urshela",
        "Steve Wilkerson": "Stevie Wilkerson",
        "J.T. Riddle": "JT Riddle",
        "Dwight Smith Jr.": "Dwight Smith Jr",
        "Richie Martin Jr.": "Richie Martin"
    }
    stats = {}
    types = [1, 2, 5]
    url = "https://www.fangraphs.com/leaders.aspx"
    params = {
        "pos": "all",
        "stats": "bat",
        "lg": "all",
        "qual": 100,
        "season": 2019,
        "page": "1_50",
        "type": 8
    }

    print(1)
    handedness_file = False
    handedness_reference = None
    if os.path.exists("Batter Hand Reference.csv"):
        handedness_file = True
        handedness_reference = create_handedness_from_file()
        file = open(os.path.join(cwd, "Batter Hand Reference.csv"), 'a+')
    else:
        file = open(os.path.join(cwd, "Batter Hand Reference.csv"), 'w+')
    soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
    time.sleep(1)
    pages = int(soup.find("div", {"class": "rgWrap rgInfoPart"}).find_all("strong")[1].text)
    table = soup.find("table", {"class": "rgMasterTable"})
    table_body = table.find("tbody")
    for row in table_body.find_all("tr"):
        data = row.find_all("td")
        name = data[1].text
        if handedness_file and name in handedness_reference:
            stats[name] = [handedness_reference[name]]
        else:
            handedness_extension = row.find("a")["href"]
            handedness_url = "https://www.fangraphs.com/" + handedness_extension
            soup = BeautifulSoup(requests.get(handedness_url).content, 'html.parser')
            time.sleep(1)
            bats_throws = soup.find_all("div", {"class": "player-info-box-item"})[1].text
            start = bats_throws.find(":") + 2
            stats[name] = [bats_throws[start:start + 1]]
            file.write(name + "," + bats_throws[start:start + 1] + "\n")
    for page in range(1, pages):
        print(str(page + 1))
        params["page"] = str(page + 1) + "_50"
        soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
        time.sleep(1)
        table = soup.find("table", {"class": "rgMasterTable"})
        table_body = table.find("tbody")
        for row in table_body.find_all("tr"):
            data = row.find_all("td")
            name = data[1].text
            if handedness_file and name in handedness_reference:
                stats[name] = [handedness_reference[name]]
            else:
                handedness_extension = row.find("a")["href"]
                handedness_url = "https://www.fangraphs.com/" + handedness_extension
                soup = BeautifulSoup(requests.get(handedness_url).content, 'html.parser')
                time.sleep(1)
                bats_throws = soup.find_all("div", {"class": "player-info-box-item"})[1].text
                start = bats_throws.find(":") + 2
                stats[name] = [bats_throws[start:start + 1]]
                file.write(name + "," + bats_throws[start:start + 1] + "\n")
    file.close()

    params["season1"] = 2017
    for stat_type in types:
        print(1)
        params["page"] = "1_50"
        params["type"] = stat_type
        soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
        time.sleep(1)
        pages = int(soup.find("div", {"class": "rgWrap rgInfoPart"}).find_all("strong")[1].text)
        table = soup.find("table", {"class": "rgMasterTable"})
        table_body = table.find("tbody")
        for row in table_body.find_all("tr"):
            data = row.find_all("td")
            name = data[1].text
            if name in stats:
                if stat_type == 1:
                    for i in [4, 5]:
                        text = data[i].text
                        stats[name].append(text[:text.find(" ")])
                elif stat_type == 2:
                    for i in [5, 6, 7, 9, 14, 15, 16, 17, 18, 19]:
                        text = data[i].text
                        stats[name].append(text[:text.find(" ")])
                elif stat_type == 5:
                    for i in [3, 4, 5, 6, 7, 8, 11]:
                        text = data[i].text
                        stats[name].append(text[:text.find(" ")])

        for page in range(1, pages):
            print(str(page + 1))
            params["page"] = str(page + 1) + "_50"
            soup = BeautifulSoup(requests.get(url, params).content, 'html.parser')
            time.sleep(1)
            table = soup.find("table", {"class": "rgMasterTable"})
            table_body = table.find("tbody")
            for row in table_body.find_all("tr"):
                data = row.find_all("td")
                name = data[1].text
                if name in stats:
                    if stat_type == 1:
                        for i in [4, 5]:
                            text = data[i].text
                            stats[name].append(text[:text.find(" ")])
                    elif stat_type == 2:
                        for i in [5, 6, 7, 9, 14, 15, 16, 17, 18, 19]:
                            text = data[i].text
                            stats[name].append(text[:text.find(" ")])
                    elif stat_type == 5:
                        for i in [3, 4, 5, 6, 7, 8, 11]:
                            text = data[i].text
                            stats[name].append(text[:text.find(" ")])

    file = open(os.path.join(cwd, "2019 Batter Stats.csv"), 'w+')
    for player in stats:
        if player in name_corrections:
            file.write(name_corrections[player] + ",")
        else:
            file.write(player + ",")
        for i, stat in enumerate(stats[player]):
            if i != len(stats[player]) - 1:
                file.write(stat + ",")
            else:
                file.write(stat + "\n")
    file.close()


def create_handedness_from_file():
    file = open(os.path.join(cwd, "Batter Hand Reference.csv"))
    ref = {}
    for line in file.readlines():
        ref[line.split(",")[0]] = line.split(",")[1].strip()
    return ref


cwd = os.getcwd()
