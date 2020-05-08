import requests
from datetime import date, timedelta
import os


def load_pitch_fx_day_data(day):
    games = find_games(day)
    for i, game in enumerate(games):
        __fill_data(game)


def refresh_pitch_fx_data(day):
    for file in os.listdir(os.path.join(os.getcwd(), "PitchFX")):
        if file.endswith(str(day.year) + ".csv"):
            os.remove(os.path.join(os.getcwd(), "PitchFX", file))
    games = refresh_season_stats(day)
    for i, game in enumerate(games):
        __fill_data(game)


def refresh_season_stats(day):
    game_pks = []
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    for year in range(day.year - 2, day.year + 1):
        params = {
            "sportId": 1,
            "season": year,
            "startDate": str(year) + "-1-1",
        }
        if year == day.year:
            params["endDate"] = str(day)
        else:
            params["endDate"] = str(year) + "-12-31"
        schedule = requests.get(schedule_url, params).json()["dates"]
        for game_day in schedule:
            game_date = game_day["date"]
            game_date = date(int(game_date[:game_date.find("-")]),
                             int(game_date[game_date.find("-") + 1:game_date.rfind("-")]),
                             int(game_date[game_date.rfind("-") + 1:]))
            for game in game_day["games"]:
                if game["gameType"] == "R" and game["status"]["codedGameState"] == "F":
                    game_pks.append((game_date, game["gamePk"]))
    return game_pks


def find_games(day):
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "season": day.year,
        "startDate": str(day - timedelta(1)),
        "endDate": str(day - timedelta(1))
    }
    schedule = requests.get(schedule_url, params).json()["dates"]
    game_pks = []
    for day in schedule:
        for game in day["games"]:
            if game["gameType"] == "R" and game["status"]["codedGameState"] == "F":
                game_pks.append((day, game["gamePk"]))
    return game_pks


def __fill_data(game):
    game_date, game_key = game
    url = f"https://statsapi.mlb.com/api/v1/game/{game_key}/playByPlay"
    game_data = __connect(url)
    current_pitchers = ["", ""]
    current_files = [None, None]
    baserunners = ["", "", ""]
    inning = 1
    half = "top"
    outs = 0
    for play in game_data["allPlays"]:
        new_inning, new_half = play["about"]["inning"], play["about"]["halfInning"]
        if inning != new_inning or half != new_half:
            baserunners = ["", "", ""]
            outs = 0
            inning = new_inning
            half = new_half

        new_baserunners, outs_on_play, runs = __get_new_baserunners(play["runners"])
        run_difference = __compute_run_difference(play["result"], half, runs)
        current_index = int(half == "bottom")
        current_pitcher, file = __process_pitcher_file(play["matchup"]["pitcher"], current_pitchers, current_files,
                                                       current_index, game_date.year)

        current_batter = play["matchup"]["batter"]["id"]
        total_pitches = len(play["pitchIndex"])
        ab_index = play["about"]["atBatIndex"]
        des = play["result"].get("event", "")
        stand = play["matchup"]["batSide"]["code"]
        p_throws = play["matchup"]["pitchHand"]["code"]
        ab_count = 1
        for pitch in [play["playEvents"][i] for i in play["pitchIndex"]]:
            if pitch["isPitch"] and pitch["details"]["description"] != "Automatic Ball" and "pfxId" in pitch:
                data = pitch["pitchData"]
                coordinates = data["coordinates"]
                if "startSpeed" in data and "pX" in coordinates:
                    pfx_id = pitch["pfxId"]
                    play_id = pitch["playId"]
                    code = pitch["details"]["call"]["code"]
                    strikes = pitch["count"]["strikes"]
                    balls = pitch["count"]["balls"]
                    if code == "B":
                        balls -= 1
                    elif code == "S":
                        strikes -= 1
                    pdes = pitch["details"]["description"].replace(",", "-")
                    pitch_name = pitch["details"].get("type", {}).get("code", "U")

                    data_stats_file = ",".join([data.get(key, "") for key in data_keys])
                    coordinates_stats_file = ",".join([coordinates[key] for key in coordinates_keys])
                    breaks = data["breaks"]
                    break_stats_file = ",".join([breaks.get(key, "") for key in break_keys])
                    file_baserunners, file_new_baserunners = ",".join(baserunners), ",".join(new_baserunners)

                    file.write(f"{game_date},{game_key},{inning},{current_pitcher},{p_throws},")
                    file.write(f"{current_batter},{stand},{ab_index},{des},{total_pitches},{ab_count},{pfx_id},")
                    file.write(f"{play_id},{balls},{strikes},{outs},{code},{pdes},{pitch_name},{data_stats_file},")
                    file.write(f"{coordinates_stats_file},{break_stats_file},{file_baserunners},{file_new_baserunners}")
                    file.write(f",{runs},{outs_on_play},{run_difference},{half}\n")
                    ab_count += 1
                else:
                    continue
        baserunners = new_baserunners
        outs += outs_on_play


def __connect(url):
    while True:
        try:
            return requests.get(url).json()
        except requests.exceptions.ConnectionError:
            continue


def __get_new_baserunners(runners):
    new_baserunners = ["", "", ""]
    outs_on_play = 0
    runs = 0
    for runner in runners:
        start = runner["movement"]["start"]
        end = runner["movement"]["end"]
        if runner["movement"]["isOut"]:
            outs_on_play += 1
        if end == "score":
            runs += 1
        if start != end and start != "4B":
            if end != "score" and end is not None and end != "4B":
                new_baserunners[int(end[0]) - 1] = runner["details"]["runner"]["id"]
    return new_baserunners, outs_on_play, runs


def __compute_run_difference(scores, half, runs):
    home_score = int(scores["homeScore"])
    away_score = int(scores["awayScore"])
    if half == "top":
        return home_score - away_score + runs
    else:
        return away_score - home_score + runs


def __process_pitcher_file(pitcher, current_pitchers, current_files, current_index, year):
    current_pitcher = pitcher["id"]
    full_name = pitcher["fullName"]
    if current_pitcher not in current_pitchers:
        file = __check_new_pitcher(full_name, year)
        current_pitchers[current_index] = current_pitcher
        current_files[current_index] = file
    else:
        file = current_files[current_index]
    return file, current_pitcher


def __check_new_pitcher(name, year):
    path = os.path.join(cwd, "PitchFX", f"{name} {year}.csv")
    if os.path.exists(path):
        file = open(path, 'a')
    else:
        file = open(path, 'w+')
        file.write("Date,Game,Inning,Pitcher,Hand,Batter,Stand,AB_ID,Result,AB_Total,AB_Count,Pfx_ID,Play_ID,Balls,")
        file.write("Strikes,Outs,Code,Pdes,Type,Zone,Con,SZ_Top,SZ_Bot,Start_Speed,End_Speed,Nasty_Factor,X0,Y0,Z0,PX,")
        file.write("PZ,PfxX,PfxZ,VX0,VY0,VZ0,AX,AY,AZ,Break_Angle,Break_Length,Break_Y,Spin_Rate,Spin_Direction,")
        file.write("Runner 1B,Runner 2B,Runner 3B,End 1B,End 2B,End 3B,Runs,Outs On Play,Run Diff,Half\n")
    return file


cwd = os.getcwd()
data_keys = ["zone", "typeConfidence", "strikeZoneTop", "strikeZoneBottom", "startSpeed", "endSpeed", "nastyFactor"]
coordinates_keys = ["x0", "y0", "z0", "pX", "pZ", "pfxX", "pfxZ", "vX0", "vY0", "vZ0", "aX", "aY", "aZ"]
break_keys = ["breakAngle", "breakLength", "breakY", "spinRate", "spinDirection"]
