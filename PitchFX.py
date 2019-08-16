import requests
from datetime import date, timedelta
import os


def refresh_season_stats():
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "season": year,
        "startDate": str(year) + "-1-1",
        "endDate": str(year) + "-12-31"
    }
    schedule = requests.get(schedule_url, params).json()["dates"]
    game_pks = []
    for day in schedule:
        for GAME in day["games"]:
            if GAME["gameType"] == "R" and GAME["status"]["codedGameState"] == "F":
                game_pks.append(GAME["gamePk"])
    return game_pks


def find_games():
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "season": year,
        "startDate": str(date.today() - timedelta(1)),
        "endDate": str(date.today() - timedelta(1))
    }
    schedule = requests.get(schedule_url, params).json()["dates"]
    game_pks = []
    for day in schedule:
        for GAME in day["games"]:
            if GAME["gameType"] == "R" and GAME["status"]["codedGameState"] == "F":
                game_pks.append(GAME["gamePk"])
    return game_pks


def fill_data(game_key):
    url = "https://statsapi.mlb.com/api/v1/game/" + str(game_key) + "/playByPlay"
    connecting = True
    game_data = None
    while connecting:
        try:
            game_data = requests.get(url).json()
            connecting = False
        except requests.exceptions.ConnectionError:
            continue
    current_pitchers = []
    current_files = []
    baserunners = ["", "", ""]
    new_baserunners = ["", "", ""]
    inning = 1
    half = "top"
    runs = 0
    outs = 0
    outs_on_play = 0
    for play in game_data["allPlays"]:
        if inning != play["about"]["inning"] or half != play["about"]["halfInning"]:
            baserunners = ["", "", ""]
            outs = 0
            inning = play["about"]["inning"]
            half = play["about"]["halfInning"]
        for runner in play["runners"]:
            start = runner["movement"]["start"]
            end = runner["movement"]["end"]
            if runner["movement"]["isOut"]:
                outs_on_play += 1
            if end == "score":
                runs += 1
            if start != end and start != "4B":
                if start is not None:
                    new_baserunners[int(start[0]) - 1] = ""
                if end != "score" and end is not None and end != "4B":
                    new_baserunners[int(end[0]) - 1] = runner["details"]["runner"]["id"]
        if half == "top":
            run_difference = int(play["result"]["homeScore"]) - int(play["result"]["awayScore"]) + runs
        else:
            run_difference = int(play["result"]["awayScore"]) - int(play["result"]["homeScore"]) + runs
        current_pitcher = play["matchup"]["pitcher"]["id"]
        full_name = play["matchup"]["pitcher"]["fullName"]
        current_index = int(play["about"]["halfInning"] == "bottom")
        if len(current_pitchers) < 2 and current_pitcher not in current_pitchers:
            current_pitchers.append(current_pitcher)
            file = check_new_pitcher(full_name)
            current_files.append(file)
        elif current_pitcher not in current_pitchers:
            file = check_new_pitcher(full_name)
            current_pitchers[current_index] = current_pitcher
            current_files[current_index] = file
        else:
            file = current_files[current_index]

        current_batter = play["matchup"]["batter"]["id"]
        total_pitches = len(play["pitchIndex"])
        ab_index = play["about"]["atBatIndex"]
        if "event" in play["result"]:
            des = play["result"]["event"]
        else:
            des = ""
        stand = play["matchup"]["batSide"]["code"]
        p_throws = play["matchup"]["pitchHand"]["code"]
        pitch_indices = play["pitchIndex"]
        ab_count = 1
        for pitch in [play["playEvents"][i] for i in pitch_indices]:
            if pitch["isPitch"] and pitch["details"]["description"] != "Automatic Ball" and "pfxId" in pitch:
                pfx_id = pitch["pfxId"]
                play_id = pitch["playId"]
                code = pitch["details"]["call"]["code"]
                pdes = pitch["details"]["description"]
                pdes = pdes.replace(",", "-")

                strikes = pitch["count"]["strikes"]
                balls = pitch["count"]["balls"]
                if code == "B":
                    balls -= 1
                elif code == "S":
                    strikes -= 1

                if "type" not in pitch["details"]:
                    pitch_name = "U"
                else:
                    pitch_name = pitch["details"]["type"]["code"]

                if "typeConfidence" in pitch["pitchData"]:
                    confidence = pitch["pitchData"]["typeConfidence"]
                else:
                    confidence = ""

                if "zone" in pitch["pitchData"]:
                    location = pitch["pitchData"]["zone"]
                else:
                    location = ""
                
                data = pitch["pitchData"]
                coordinates = data["coordinates"]
                breaks = data["breaks"]
                sz_top = data["strikeZoneTop"]
                sz_bot = data["strikeZoneBottom"]
                if "startSpeed" in data and "pX" in coordinates:
                    start_speed = data["startSpeed"]
                    end_speed = data["endSpeed"]
                    x0 = coordinates["x0"]
                    y0 = coordinates["y0"]
                    z0 = coordinates["z0"]
                    px = coordinates["pX"]
                    pz = coordinates["pZ"]
                    pfxX = coordinates["pfxX"]
                    pfxZ = coordinates["pfxZ"]
                    vX0 = coordinates["vX0"]
                    vY0 = coordinates["vY0"]
                    vZ0 = coordinates["vZ0"]
                    ax = coordinates["aX"]
                    ay = coordinates["aY"]
                    az = coordinates["aZ"]
                    break_angle = breaks["breakAngle"]
                    break_length = breaks["breakLength"]
                    break_y = breaks["breakY"]
                    spin_direction = breaks["spinDirection"]
                else:
                    continue

                if "nastyFactor" in data:
                    nasty_factor = data["nastyFactor"]
                else:
                    nasty_factor = ""

                if "spinRate" in breaks:
                    spin_rate = breaks["spinRate"]
                else:
                    spin_rate = ""

                file.write(str(date.today() - timedelta(1)) + "," + str(game_key) + "," + str(inning) + ",")
                file.write(str(current_pitcher) + "," + p_throws + "," + str(current_batter) + "," + stand + ",")
                file.write(str(ab_index) + "," + des + "," + str(total_pitches) + "," + str(ab_count) + "," + pfx_id)
                file.write("," + play_id + "," + str(balls) + "," + str(strikes) + "," + str(outs) + "," + code + ",")
                file.write(pdes + "," + pitch_name + "," + str(location) + ",")
                file.write(str(confidence) + "," + str(sz_top) + "," + str(sz_bot) + "," + str(start_speed) + ",")
                file.write(str(end_speed) + "," + str(nasty_factor) + "," + str(x0) + "," + str(y0) + "," + str(z0))
                file.write("," + str(px) + "," + str(pz) + "," + str(pfxX) + "," + str(pfxZ) + "," + str(vX0) + ",")
                file.write(str(vY0) + "," + str(vZ0) + "," + str(ax) + "," + str(ay) + "," + str(az) + ",")
                file.write(str(break_angle) + "," + str(break_length) + "," + str(break_y) + "," + str(spin_rate) + ",")
                file.write(str(spin_direction) + ",")
                for i, runner in enumerate(baserunners):
                    file.write(str(runner) + ",")
                for i, runner in enumerate(new_baserunners):
                    file.write(str(runner) + ",")
                file.write(str(runs) + "," + str(outs_on_play) + "," + str(run_difference) + "," + half + "\n")
                ab_count += 1
        baserunners = new_baserunners
        new_baserunners = ["", "", ""]
        runs = 0
        outs += outs_on_play
        outs_on_play = 0


def check_new_pitcher(name):
    cwd = os.getcwd()
    if os.path.exists(os.path.join(os.getcwd(), "PitchFX", name + " " + str(year) + ".csv")):
        file = open(os.path.join(cwd, "PitchFX", name + " " + str(year) + ".csv"), 'a')
    else:
        file = open(os.path.join(cwd, "PitchFX", name + " " + str(year) + ".csv"), 'a+')
        file.write("Date, Game, Inning, Pitcher, Hand, Batter, Stand, AB_ID, Result, AB_Total, AB_Count, Pfx_ID, ")
        file.write("Play_ID, Balls, Strikes, Outs, Code, Pdes, Type, Zone, Con, SZ_Top, SZ_Bot, Start_Speed, End_Speed")
        file.write(", Nasty_Factor, X0, Y0, Z0, PX, PZ, PfxX, PfxZ, VX0, VY0, VZ0, AX, AY, AZ, Break_Angle, ")
        file.write("Break_Length, Break_Y, Spin_Rate, Spin_Direction, Runner 1B, Runner 2B, Runner 3B, End 1B, End 2B,")
        file.write(" End 3B, Runs, Outs On Play, Run Diff, Half\n")
    return file


def main():
    games = find_games()
    for i, game in enumerate(games):
        print("Game " + str(i + 1) + " of " + str(len(games)))
        fill_data(game)


def main_alt():
    for file in os.listdir(os.path.join(os.getcwd(), "PitchFX")):
        if file.endswith(str(year) + ".csv"):
            os.remove(os.path.join(os.getcwd(), "PitchFX", file))
    games = refresh_season_stats()
    for i, game in enumerate(games):
        print("Game " + str(i + 1) + " of " + str(len(games)))
        fill_data(game)


year = 2019
