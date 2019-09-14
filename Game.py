import pitching
import numpy as np
import copy


class Game:
    def __init__(self, game_date, teams, starters, lineups, pitches_matrix, bullpens, bootstraps, roster):
        self.game_date = game_date
        self.teams = teams
        self.current_pitcher = copy.deepcopy(starters)
        self.used_pitchers = [[], []]
        copy_lineups = copy.deepcopy(lineups)
        self.lineups = copy_lineups
        self.inning = 0
        self.score = [0, 0]
        self.pitch_counts = [0, 0]
        self.batting_indices = [0, 0]
        self.outs = 0
        self.strikes = 0
        self.balls = 0
        self.runners = ["", "", ""]
        self.bootstraps = bootstraps
        self.curr_bootstraps = [self.bootstraps[0][starters[0]], self.bootstraps[1][starters[1]]]
        self.linescore = []
        self.boxscore = [{}, {}]
        for i, lineup in enumerate(lineups):
            for batter in lineup:
                self.boxscore[i][batter] = [0 for j in range(7)]
        self.roster = roster

        self.pitches_matrix = pitches_matrix
        home_pitcher_limit, away_pitcher_limit = -1, -1
        if starters[0] in self.pitches_matrix and starters[1] in self.pitches_matrix:
            home_pitcher_pitches = self.pitches_matrix[starters[0]]
            home_pitcher_limit = np.random.normal(np.mean(home_pitcher_pitches), np.abs(np.std(home_pitcher_pitches)))
            away_pitcher_pitches = self.pitches_matrix[starters[1]]
            away_pitcher_limit = np.random.normal(np.mean(away_pitcher_pitches), np.abs(np.std(away_pitcher_pitches)))
        self.pitch_limits = [home_pitcher_limit, away_pitcher_limit]

        bullpens_copy = copy.deepcopy(bullpens)
        self.bullpens = [bullpens_copy[0][1], bullpens_copy[1][1]]
        self.bullpen_pitchers = [bullpens_copy[0][0], bullpens_copy[1][0]]

    def simulate_game(self):
        if self.pitch_limits[0] == -1:
            print("Could Not Generate Pitching Limits")
            return None, None, None
        if len(self.curr_bootstraps[0]['Generic']) == 0 or len(self.curr_bootstraps[1]['Generic']) == 0:
            print("Could Not Generate A Generic Bootstrap")
            return None, None, None
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
        if self.current_pitcher[curr_index] in self.lineups[np.abs(curr_index - 1)]:
            self.lineups[np.abs(curr_index - 1)][self.lineups[np.abs(curr_index - 1)].index(self.current_pitcher[curr_index])] = "Generic"
            self.boxscore[np.abs(curr_index - 1)]["Generic"] = [0 for i in range(7)]
        lead = self.score[curr_index] - self.score[np.abs(curr_index - 1)]
        inning = int(self.inning / 2) + 1
        bullpen = self.bullpens[curr_index]
        bullpen_pitchers = self.bullpen_pitchers[curr_index]
        new_pitcher, bullpen, bullpen_pitchers = pitching.new_pitcher(lead, inning, bullpen, bullpen_pitchers)
        if new_pitcher is None:
            self.coin_flip()
            return
        self.used_pitchers[curr_index].append(self.current_pitcher[curr_index])
        self.current_pitcher[curr_index] = new_pitcher
        self.curr_bootstraps[curr_index] = self.bootstraps[curr_index][new_pitcher]
        self.bullpens[curr_index] = bullpen
        self.bullpen_pitchers[curr_index] = bullpen_pitchers
        self.pitch_counts[curr_index] = 0
        pitcher_pitches = self.pitches_matrix[new_pitcher]
        self.pitch_limits[curr_index] = np.random.normal(np.mean(pitcher_pitches), np.abs(np.std(pitcher_pitches)))

    def simulate_at_bat(self):
        curr_index = self.inning % 2
        if self.pitch_counts[curr_index] > self.pitch_limits[curr_index]:
            self.substitute_pitcher(curr_index)
        batter = self.lineups[curr_index][self.batting_indices[curr_index]]
        curr_bootstrap = self.curr_bootstraps[curr_index]
        curr_batter_bootstrap = np.array(curr_bootstrap[batter])
        if len(curr_batter_bootstrap) == 0 or batter == "Generic":
            curr_batter_bootstrap = np.array(self.curr_bootstraps[curr_index]["Generic"])
        while self.strikes < 3 and self.balls < 4:
            criteria_pitches = self.create_criteria(curr_batter_bootstrap)
            if criteria_pitches.shape[0] > 5:
                pitch = criteria_pitches[np.random.randint(len(criteria_pitches))]
            else:
                pitch = curr_batter_bootstrap[np.random.randint(len(curr_batter_bootstrap))]
            self.pitch_counts[curr_index] += 1
            if pitch[9] != pitch[10]:
                if pitch[16] == 'S':
                    self.strikes += 1
                    if self.strikes == 3:
                        self.outs += 1
                elif pitch[16] == 'B':
                    self.balls += 1
                    if self.balls == 4:
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
                            self.runners[2] = self.runners[1]
                            self.runners[1] = self.runners[0]
                            self.runners[0] = batter
            else:
                self.outs += int(pitch[51])
                runs = int(pitch[50])
                result = pitch[8]
                self.score[curr_index] += runs
                self.linescore[-1] += runs
                if result not in no_ab:
                    self.boxscore[curr_index][batter][0] += 1
                if result not in no_rbi:
                    self.boxscore[curr_index][batter][3] += runs
                i = 0
                while runs > 0 and i < 3:
                    if self.runners[i] != "":
                        self.boxscore[curr_index][self.runners[i]][1] += 1
                        runs -= 1
                    i += 1
                if runs > 0:
                    self.boxscore[curr_index][batter][1] += 1
                if result in hits:
                    self.boxscore[curr_index][batter][2] += 1
                if result in walk:
                    self.boxscore[curr_index][batter][4] += 1
                if "Strikeout" in result:
                    self.boxscore[curr_index][batter][5] += 1
                if result not in hits and result not in walk:
                    for runner in self.runners:
                        if runner != "":
                            self.boxscore[curr_index][batter][6] += 1

                if pitch[47] == "":
                    self.runners[0] = ""
                elif pitch[47] != pitch[44]:
                    self.runners[0] = batter

                if pitch[48] == "":
                    self.runners[1] = ""
                elif pitch[48] != pitch[45]:
                    if pitch[48] == pitch[44]:
                        self.runners[1] = self.runners[0]
                    else:
                        self.runners[1] = batter

                if pitch[49] == "":
                    self.runners[2] = ""
                elif pitch[49] == pitch[46]:
                    if pitch[49] == pitch[45]:
                        self.runners[2] = self.runners[1]
                    elif pitch[49] == pitch[44]:
                        self.runners[2] = self.runners[0]
                    else:
                        self.runners[2] = batter
                break
        self.batting_indices[curr_index] += 1
        self.batting_indices[curr_index] %= 9
        self.strikes = 0
        self.balls = 0

    def coin_flip(self):
        result = np.random.uniform()
        if result >= .5:
            self.score = [self.score[0] + 1, self.score[1]]
        else:
            self.score = [self.score[0], self.score[1] + 1]

    def create_criteria(self, current_bootstrap):
        aggregate = self.create_baserunner_criteria(self.create_count_criteria(self.create_run_diff_criteria(current_bootstrap)))
        if aggregate.shape[0] > 5:
            return aggregate
        else:
            aggregate = self.create_baserunner_criteria(self.create_count_criteria(current_bootstrap))
            if aggregate.shape[0] > 5:
                return aggregate
            else:
                aggregate = self.create_baserunner_criteria(self.create_run_diff_criteria(current_bootstrap))
                aggregate = np.concatenate((aggregate, self.create_count_criteria(self.create_run_diff_criteria(current_bootstrap))))
                if aggregate.shape[0] > 5:
                    return aggregate
                else:
                    aggregate = self.create_baserunner_criteria(current_bootstrap)
                    aggregate = np.concatenate((aggregate, self.create_count_criteria(current_bootstrap)))
                    if aggregate.shape[0] > 5:
                        return aggregate
                    else:
                        aggregate = np.concatenate((aggregate, self.create_run_diff_criteria(current_bootstrap)))
        return aggregate

    def create_count_criteria(self, current):
        if current is not None:
            criteria_pitches = current[np.where(current[:, 14] == str(self.strikes))[0]]
            criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 13] == str(self.balls))[0]]
            criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 15] == str(self.outs))]
            return criteria_pitches
        return None

    def create_baserunner_criteria(self, current):
        if current is not None:
            criteria_pitches = current
            for i, runner in enumerate(self.runners):
                if runner != "":
                    criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 44 + i] != "")]
                else:
                    criteria_pitches = criteria_pitches[np.where(criteria_pitches[:, 44 + i] == "")]
            return criteria_pitches
        return None

    def create_run_diff_criteria(self, current):
        if current is not None:
            run_diff = self.score[(self.inning + 1) % 2] - self.score[self.inning % 2]
            criteria_pitches = current[np.where(current[:, 52] == str(-run_diff))]
            return criteria_pitches
        return None


no_ab = ["Caught Stealing", "Hit By Pitch", "Intent Walk", "Sac Bunt", "Sac Fly", "Walk"]
hits = ["Single", "Double", "Triple", "Home Run"]
no_rbi = ["Field Error", "Grounded Into DP"]
walk = ["Walk", "Intent Walk"]
