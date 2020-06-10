from pitching import get_new_pitcher
import numpy as np
import copy
import warnings


class Game:
    def __init__(self, game_date, teams, starters, lineups, pitches_matrix, bullpens, bootstraps):
        self.game_date = game_date
        self.teams = teams
        self.current_pitcher = copy.deepcopy(starters)
        self.used_pitchers = [[], []]
        self.lineups = copy.deepcopy(lineups)
        self.inning = 0
        self.score = [0, 0]
        self.pitch_counts = [0, 0]
        self.batting_indices = [0, 0]
        self.outs = 0
        self.strikes = 0
        self.balls = 0
        self.foul_count = 0
        self.runners = ["", "", ""]
        self.bootstraps = bootstraps
        if starters[0] in self.bootstraps[0] and starters[1] in self.bootstraps[1]:
            self.curr_bootstraps = [self.bootstraps[0][starters[0]], self.bootstraps[1][starters[1]]]
        else:
            self.curr_bootstraps = [{}, {}]
        self.linescore = []
        self.boxscore = [{batter: [0] * 7 for batter in lineup} for lineup in lineups]
        self.pitches_matrix = pitches_matrix
        self.pitch_limits = [-1, -1]
        if starters[0] in self.pitches_matrix:
            home_pitcher_pitches = self.pitches_matrix[starters[0]]
            self.pitch_limits[0] = np.random.normal(np.mean(home_pitcher_pitches), np.abs(np.std(home_pitcher_pitches)))
        if starters[1] in self.pitches_matrix:
            away_pitcher_pitches = self.pitches_matrix[starters[1]]
            self.pitch_limits[1] = np.random.normal(np.mean(away_pitcher_pitches), np.abs(np.std(away_pitcher_pitches)))
        bullpens_copy = copy.deepcopy(bullpens)
        self.bullpens = [bullpens_copy[0][1], bullpens_copy[1][1]]
        self.bullpen_pitchers = [bullpens_copy[0][0], bullpens_copy[1][0]]

    def simulate_game(self):
        if self.pitch_limits[0] == -1 or self.pitch_limits[1] == -1:
            warnings.warn("Could Not Generate Pitching Limits", RuntimeWarning)
            return None, None, None
        if not bool(self.curr_bootstraps[0]) or not bool(self.curr_bootstraps[1]):
            warnings.warn("Could Not Generate a Bootstrap for one of the starters", RuntimeWarning)
            return None, None, None

        # Simulate the next half inning if it is the first nine innings, or it is tied, or the visiting team has taken
        # the lead in extra innings with the home team coming up
        while self.inning < 18 or self.score[0] == self.score[1] or \
                (self.inning >= 18 and self.score[0] != self.score[1] and self.inning % 2 == 1):
            self.simulate_inning()
        return self.score, self.linescore, self.boxscore

    def simulate_inning(self):
        self.linescore.append(0)
        while self.outs < 3:
            self.simulate_at_bat()
        self.outs = 0
        self.runners = ["", "", ""]
        self.inning += 1

    def substitute_pitcher(self, curr_index):
        self.__replace_pitcher_in_batting_lineup(curr_index)
        lead = self.score[curr_index] - self.score[np.abs(curr_index - 1)]
        inning = int(self.inning / 2) + 1
        new_pitcher, bullpen, bullpen_pitchers = get_new_pitcher(lead, inning, self.bullpens[curr_index],
                                                                 self.bullpen_pitchers[curr_index])

        # If there are no pitchers left in the bullpen, just coin flip the winner of the game
        if new_pitcher is None:
            self.coin_flip()
            return

        self.__substitute_pitcher(curr_index, new_pitcher, bullpen, bullpen_pitchers)

    def simulate_at_bat(self):
        curr_index = self.inning % 2
        if self.pitch_counts[curr_index] > self.pitch_limits[curr_index]:
            self.substitute_pitcher(curr_index)
        batter = self.lineups[curr_index][self.batting_indices[curr_index]]
        curr_batter_bootstrap = np.array(self.curr_bootstraps[curr_index][batter])
        if len(curr_batter_bootstrap) == 0:
            curr_batter_bootstrap = np.array(self.curr_bootstraps[curr_index]["Generic"])
        while self.strikes < 3 and self.balls < 4:
            if self.simulate_pitch(curr_index, curr_batter_bootstrap, batter) == -1:
                break
        self.batting_indices[curr_index] += 1
        self.batting_indices[curr_index] %= 9
        self.strikes = 0
        self.balls = 0
        self.foul_count = 0

    def simulate_pitch(self, curr_index, curr_batter_bootstrap, batter):
        criteria_pitches = self.create_criteria(curr_batter_bootstrap)
        if criteria_pitches.shape[0] > 5:
            pitch = criteria_pitches[np.random.randint(len(criteria_pitches))]
        else:
            pitch = curr_batter_bootstrap[np.random.randint(len(curr_batter_bootstrap))]
        self.pitch_counts[curr_index] += 1

        if pitch[16] not in in_play:
            self.mid_at_bat_pitch(pitch, batter, curr_index)
        else:
            self.outs += int(pitch[51])
            runs = int(pitch[50])
            result = pitch[8]
            self.score[curr_index] += runs
            self.__fill_in_boxscore(curr_index, batter, result, runs)
            if int(pitch[51]) + int(pitch[15]) < 3:
                self.__advance_runners(pitch, batter)
            return -1

    def mid_at_bat_pitch(self, pitch, batter, curr_index):
        if pitch[16] in strike_codes:
            if self.strikes < 2 or pitch[16] != "F" or self.foul_count >= 3:
                self.strikes += 1
                if self.strikes == 3:
                    self.outs += 1
                    self.boxscore[curr_index][batter][0] += 1
                    self.boxscore[curr_index][batter][5] += 1
                    self.__find_left_on_base(curr_index, batter)
            elif pitch[16] == "F" and self.strikes == 2:
                self.foul_count += 1
        elif pitch[16] in ball_codes:
            self.balls += 1
            if self.balls == 4:
                self.walk(batter, curr_index)
                self.boxscore[curr_index][batter][4] += 1

    def walk(self, batter, curr_index):
        if self.runners[0] == "":
            self.runners[0] = batter
        elif self.runners[1] == "":
            self.runners[1] = self.runners[0]
            self.runners[0] = batter
        elif self.runners[2] == "":
            self.runners[2] = self.runners[1]
            self.runners[1] = self.runners[0]
            self.runners[0] = batter
        else:
            self.score[curr_index] += 1
            self.linescore[-1] += 1
            self.boxscore[curr_index][self.runners[2]][1] += 1
            self.boxscore[curr_index][batter][3] += 1
            self.runners[2] = self.runners[1]
            self.runners[1] = self.runners[0]
            self.runners[0] = batter

    def coin_flip(self):
        result = np.random.uniform()
        if result >= .5:
            self.score = [self.score[0] + 1, self.score[1]]
        else:
            self.score = [self.score[0], self.score[1] + 1]

    def create_criteria(self, current_bootstrap):
        # Creates the matrix of all the pitches that have been thrown in similar situations based on baserunners, count
        # and run differential.
        aggregate = self.create_baserunner_criteria(self.create_count_criteria(
            self.create_run_diff_criteria(current_bootstrap)))
        if aggregate is not None and aggregate.shape[0] > 5:
            return aggregate
        else:
            aggregate = self.create_baserunner_criteria(self.create_count_criteria(current_bootstrap))
            if aggregate is not None and aggregate.shape[0] > 5:
                return aggregate
            else:
                aggregate = self.create_baserunner_criteria(self.create_run_diff_criteria(current_bootstrap))
                aggregate = np.concatenate((aggregate, self.create_count_criteria(
                    self.create_run_diff_criteria(current_bootstrap))))
                if aggregate is not None and aggregate.shape[0] > 5:
                    return aggregate
                else:
                    aggregate = self.create_baserunner_criteria(current_bootstrap)
                    aggregate = np.concatenate((aggregate, self.create_count_criteria(current_bootstrap)))
                    if aggregate is not None and aggregate.shape[0] > 5:
                        return aggregate
                    else:
                        aggregate = np.concatenate((aggregate, self.create_run_diff_criteria(current_bootstrap)))
        return aggregate

    def create_count_criteria(self, current):
        if len(current) > 0:
            criteria_pitches = current[np.where(current[:, 14] == str(self.strikes))[0]]
            criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 13] == str(self.balls))[0]]
            criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 15] == str(self.outs))]
            return criteria_pitches
        return np.empty(0)

    def create_baserunner_criteria(self, current):
        if len(current) > 0:
            criteria_pitches = current
            for i, runner in enumerate(self.runners):
                if runner != "":
                    criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 44 + i] != "")]
                else:
                    criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 44 + i] == "")]
            return criteria_pitches
        return np.empty(0)

    def create_run_diff_criteria(self, current):
        if len(current) > 0:
            run_diff = self.score[(self.inning + 1) % 2] - self.score[self.inning % 2]
            criteria_pitches = current[np.where(current[:, 52] == str(-run_diff))]
            return criteria_pitches
        return np.empty(0)

    def __replace_pitcher_in_batting_lineup(self, curr_index):
        opp_index = np.abs(curr_index - 1)
        if self.current_pitcher[curr_index] in self.lineups[opp_index]:
            pitcher_lineup_position = self.lineups[opp_index].index(self.current_pitcher[curr_index])
            self.lineups[opp_index][pitcher_lineup_position] = "Generic"
            self.boxscore[opp_index]["Generic"] = [0] * 7

    def __substitute_pitcher(self, curr_index, new_pitcher, bullpen, bullpen_pitchers):
        self.used_pitchers[curr_index].append(self.current_pitcher[curr_index])
        self.current_pitcher[curr_index] = new_pitcher
        self.curr_bootstraps[curr_index] = self.bootstraps[curr_index][new_pitcher]
        self.bullpens[curr_index] = bullpen
        self.bullpen_pitchers[curr_index] = bullpen_pitchers
        self.pitch_counts[curr_index] = 0
        self.pitch_limits[curr_index] = np.random.normal(np.mean(self.pitches_matrix[new_pitcher]),
                                                         np.abs(np.std(self.pitches_matrix[new_pitcher])))

    def __fill_in_boxscore(self, curr_index, batter, result, runs):
        self.linescore[-1] += runs
        if result not in no_ab:
            self.boxscore[curr_index][batter][0] += 1
        for i in range(3):
            if self.runners[2 - i] != "" and runs > 0:
                self.boxscore[curr_index][self.runners[2 - i]][1] += 1
                runs -= 1
        if runs > 0:
            self.boxscore[curr_index][batter][1] += 1
        if result in hits:
            self.boxscore[curr_index][batter][2] += 1
        if result not in no_rbi:
            self.boxscore[curr_index][batter][3] += runs
        if result in walk:
            self.boxscore[curr_index][batter][4] += 1
        if "Strikeout" in result:
            self.boxscore[curr_index][batter][5] += 1
        if result not in hits and result not in walk:
            self.__find_left_on_base(curr_index, batter)

    def __find_left_on_base(self, curr_index, batter):
        for runner in self.runners:
            if runner != "":
                self.boxscore[curr_index][batter][6] += 1

    def __advance_runners(self, pitch, batter):
        res = pitch[8]
        outs_on_play = int(pitch[51])
        runs_on_play = int(pitch[50])
        runners_on_before = sum(np.array(self.runners) != "")
        if self.find_if_baserunners_match(pitch[44:47]):
            for i in range(49, 46, -1):
                if pitch[i] == "":
                    self.runners[i - 47] = ""
                else:
                    for j in range(44, 47):
                        if pitch[i] == pitch[j]:
                            self.runners[i - 47] = self.runners[j - 44]
                if pitch[i] == pitch[5]:
                    self.runners[i - 47] = batter
        elif res in hits:
            bases = 1 if res == "Single" else 2 if res == "Double" else 3 if res == "Triple" else \
                4 if res == "Home Run" else 0
            if 0 < bases:
                for i in range(3):
                    runner = self.runners[i]
                    self.runners[i] = ""
                    if i + bases <= 2:
                        self.runners[i + bases] = runner
                if bases < 4:
                    self.runners[bases - 1] = batter
        else:
            bases = 0
            batter_reaches = False
            for i in range(47, 50):
                if pitch[i] == pitch[5]:
                    batter_reaches = True
                    bases = i - 46
                    break
            if batter_reaches:
                for i in range(3):
                    runner = self.runners[i]
                    self.runners[i] = ""
                    if runner == "" and i >= bases - 1:
                        break
                    elif i + bases <= 2:
                        self.runners[i + bases] = runner
                self.runners[bases - 1] = batter
        runners_on_after = sum(np.array(self.runners) != "")
        runs_by_runners = runners_on_before + 1 - runners_on_after - outs_on_play - runs_on_play
        if runs_by_runners != 0:
            if runs_by_runners < 0:
                if np.abs(runs_by_runners) > runs_on_play:
                    adjusted_outs = np.abs(runs_by_runners) - runs_on_play
                    self.score[self.inning % 2] += adjusted_outs
                    self.linescore[-1] += adjusted_outs
                    self.outs -= adjusted_outs
            self.score[self.inning % 2] += runs_by_runners
            self.linescore[-1] += runs_by_runners

    def find_if_baserunners_match(self, baserunners):
        baserunner_match = True
        for i in range(3):
            if not ((baserunners[i] != "" and self.runners[i] != "") or (baserunners[i] == self.runners[i])):
                baserunner_match = False
        return baserunner_match


no_ab = ["Caught Stealing", "Hit By Pitch", "Intent Walk", "Sac Bunt", "Sac Fly", "Walk"]
hits = ["Single", "Double", "Triple", "Home Run"]
no_rbi = ["Field Error", "Grounded Into DP"]
walk = ["Walk", "Intent Walk"]
ball_codes = ["*B", "B"]
strike_codes = ["C", "F", "L", "S", "T", "W"]
in_play = ["D", "E", "X", "H"]
