import requests
import matplotlib.pyplot as plt
import numpy as np
import scipy
import seaborn as sns
import pandas as pd
import json
from datetime import datetime
import os
from espn_api.football import League
from espn_api.football import Player

class FF:
    def __init__(self, league_id='83174673', swid='{9F7C3455-C43D-42A6-9D1A-AEB707CB5F0B}', espn_s2='AEAy3mkAv%2FsnK2YbgEVRFKpOw6%2ByQVeXH5BDBOlzgAiBg646ZtRuneInbY1z9QYrt1Ws8r6Cc8pS0g%2BVi7HmU0b%2F0lxgkP9csOvk9S01pusHVMJOZ9GfMZblZ01U9NjD46R2N%2BI21guim1Lga4TfVKqE6rCLMJvQszv5ZKdFgjngR98gxiClp9R3ZxzJ7cTLJufuir4JGnzKZ9RwOCL1%2BOaFy8qFEGwEVNGkuMY4Hj4zSR%2BL9a5fatMYEWNXvk4muhbgckHixSZiqvSnL6pyniu98SRFEpigMIkWgSJ%2FTfNvCg%3D%3D', year='2021'):

        # set league vars for requests
        self.league_id = league_id
        self.espn_s2 = espn_s2
        self.swid = swid
        self.year = year
        self.cookies = {
            'espn_s2': self.espn_s2,
            'SWID': self.swid
        }
        self.league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

        # set useful internal vars
        self.num_weeks = self.get_num_weeks()

        # hardcoded lookups
        self.slotcodes = {
            0 : 'QB', 2 : 'RB', 4 : 'WR',
            6 : 'TE', 16: 'Def', 17: 'K',
            20: 'Bench', 21: 'IR', 23: 'Flex'
        }

    # getters
    def get_num_weeks(self):
        if self.year == '2019' or self.year == '2020':
            return 13
        else:
            return 14

    # helper function from ff-espn-api
    def checkRequestStatus(self, status) -> None:
        if 500 <= status <= 503:
                raise Exception(status)
        if status == 401:
            raise Exception("Access Denied")

        elif status == 404:
            raise Exception("Invalid League")

        elif status != 200:
            raise Exception('Unknown %s Error' % status)

    # fetch players, get scoring data
    def fetch_players_data_by_week(self, week):
        params = {
            'scoringPeriodId': week
        }
        endpoint = 'https://fantasy.espn.com/apis/v3/games/ffl/seasons/' + str(self.year) + '/segments/0/leagues/' + str(self.league_id) + '?view=mMatchup&view=mMatchupScore'
        r = requests.get(endpoint, params=params, cookies=self.cookies)
        status = r.status_code
        self.checkRequestStatus(status)
        d = r.json()
        return d


    # function to convert fetched player data into dataframe
    def fetch_regular_season_player_data(self):
                
        # iterate teams
        data = []
        for week in range(1, self.num_weeks+1):

            # get player data for that scoring period
            d = self.fetch_players_data_by_week(week)

            for tm in d['teams']:
                tmid = tm['id']

                # iterate players on teams
                for p in tm['roster']['entries']:
                    name = p['playerPoolEntry']['player']['fullName']
                    slot = p['lineupSlotId']
                    pos  = self.slotcodes[slot]

                    # injured status (need try/exc bc of D/ST)
                    inj = 'NA'
                    try:
                        inj = p['playerPoolEntry']['player']['injuryStatus']
                    except:
                        pass

                    # grab projected/actual points
                    proj, act = None, None
                    for stat in p['playerPoolEntry']['player']['stats']:
                        if stat['scoringPeriodId'] != week:
                            continue
                        if stat['statSourceId'] == 0:
                            act = stat['appliedTotal']
                        elif stat['statSourceId'] == 1:
                            proj = stat['appliedTotal']

                    data.append([
                        week, tmid, name, slot, pos, inj, proj, act
                    ])
            print('Week {} complete.'.format(week))

        return data

    def convert_espn_json_to_dataframe(self, data):
        return pd.DataFrame(data, columns=['Week', 'Team', 'Player', 'Slot', 'Pos', 'Status', 'Proj', 'Actual'])

    def save_dataframe(self, data):
        today = datetime.today().strftime('%Y-%m-%d')
        data.to_csv('FF{}_playerdata_pulled_{}.csv'.format(self.year, today))

    def pull_and_save_data(self):
        raw_data = self.fetch_regular_season_player_data()
        df = self.convert_espn_json_to_dataframe(raw_data)
        self.save_dataframe(df)

    def load_data(self):

        filelist = os.listdir()
        possible_fnames = []

        # we might have multiple data files so grab the most recent one
        for f in filelist:
            if "{}".format(self.year) in f:
                if '.csv' in f:
                    possible_fnames.append(f)

        possible_fnames.sort()

        if len(possible_fnames) == 0:
            raise(Exception('Error: no matching data found for this year. Have you pulled it yet?'))

        df = pd.read_csv(possible_fnames[-1])
        self.df = df

        return df

    # convenience functions
    def get_player_performance_rank(self, player, week, only_starters=True):
        """ function that evaluates the positional ranking of a player among players owned (or just starters) that week
        I think this metric has better insight into how good a player is. random waiver players or bench players who
        pop off are better thought of as noise, assuming we are rational managers """

        year = self.year

        # load data
        data = self.df
        if only_starters:
            data = data[data['Pos'] != 'Bench']
        
        # just work with data for that week
        week_data = data[data['Week'] == week]

        # get position of that player
        pos = week_data[week_data['Player'] == player]['Pos']

        # return nan if player didn't start that week
        # and the person had "only_starters" selected
        if pos.empty:
            print("Warning: player {} not in dataset for week {}. Returning NaN.".format(player, week))
            return np.NaN   

        # get scores of players of that position
        pos_data = week_data[week_data['Pos'] == pos.unique()[0]]

        # get scores and sort descending
        scores = pos_data['Actual'].unique()
        scores.sort()
        scores = scores[::-1]

        # get where player score is in rank of scores
        player_score = pos_data[pos_data['Player']==player]['Actual'].tolist()[0]
        rank = np.where(scores == player_score)[0][0]

        # increment cause zero indexing
        rank += 1

        return rank


    def get_player_score(self, player, week, projected=False):
        """ Convenience function to get score of a player given data and week
        """

        #year = self.year
        data = self.df

        data = data[data['Week'] == week]

        # get data for that player
        player_data = data[data['Player'] == player]

        # return nan if player didn't score in that dataset for whatever reason
        if player_data.empty:
            print("Warning: no player score for {} recorded for week {}.".format(player, week))
            return np.NaN

        # return score
        if projected:
            target = 'Proj'
        else:
            target = 'Actual'
        player_score = player_data[target].tolist()[0]

        # if player was on bye, score will be zero but there's no other indication
        if np.isnan(player_score):
            #print('Warning: getting score from player {} on bye week {}, returning 0'.format(player, week))
            player_score = 0

        return player_score


    def was_player_started(self, player, week):

        #year = self.year

        # just work with data for that week
        data = self.df
        data = data[data['Week'] == week]
        player_data = data[data['Player'] == player]

        # if player wasn't in dataset, he was in waivers
        if player_data.empty:
            return False

        # if player was in dataset as bench, he was on bench
        if player_data['Pos'] == 'Bench':
            return False

        # if player was on IR, he's basically on the bench
        if player_data['Pos'] == 'IR':
            return False

        # if not the above, then ya
        return True


    def was_player_on_bench(self, player, week):

        # just work with data for that week
        #year = self.year
        data = self.df
        data = data[data['Week'] == week]
        player_data = data[data['Player'] == player]

        # if player wasn't in dataset, he was in waivers
        if player_data.empty:
            return False

        # if player was in dataset as bench, he was on bench
        if player_data['Pos'] == 'Bench':
            return True

        # if player was on IR, he's basically on the bench
        if player_data['Pos'] == 'IR':
            return True
        
        # otherwise player started
        return False


    def was_player_on_waivers(self, player, week):

        #year = self.year

        # just work with data for that week
        data = self.df
        data = data[data['Week'] == week]
        player_data = data[data['Player'] == player]

        # if player wasn't in dataset, he was in waivers
        if player_data.empty:
            return True
        else:
            return False


    def get_team_id(self, nickname=None):
        """ get the team id given a nickname for convenience """

        year = str(self.year)

        if year == "2021":
            nicknames = {
                'Tyler': 1,
                'Ray': 4,
                'Blount': 8,
                'Bot': 7,
                'Poogz': 10,
                'Brian': 3,
                'Mitch': 2,
                'D\'vonne': 5,
                'Sam': 6,
                'Hogz': 9
            }
        elif year == '2020':
            nicknames = {
                'Tyler': 1,
                'Ray': 4,
                'Blount': 8,
                'Jack': 7,
                'Poogz': 10,
                'Brian': 3,
                'Mitch': 2,
                'D\'vonne': 5,
                'Sam': 6,
                'Hogz': 9
            }
        elif year == '2019':
            nicknames = {
                'Tyler': 1,
                'Ray': 4,
                'Blount': 8,
                'Jack': 7,
                'Brian': 3,
                'Mitch': 2,
                'D\'vonne': 5,
                'Sam': 6
            }

        # return nickname list if none argument
        if nickname is None:
            return nicknames

        if nickname not in nicknames.keys():
            print('Warning: nickname {} not recognized in list {}'.format(nickname, nicknames))
            return -1
        
        return nicknames[nickname]

    def get_team_nickname(self, teamid):

        year = self.year

        nicknames = self.get_team_id(None)

        # flip key-value pairs
        ids = dict([(value, key) for key, value in nicknames.items()]) 

        # return
        return ids[teamid]


    #def get_team_nicknames_list(year='2020'):
    #    nicknames = get_team_id(nickname=None, year=year).keys()
    #    return nicknames

    def get_team_starters(self, team, week, pos=None):
        """ get players a team started that week. team can be nickname or id. optional argument to get players of a certain position"""
        
        year = self.year

        if type(team) == str:
            team_ndx = self.get_team_id(team, year)
        else:
            team_ndx = team

        # load data and just get data for that week/team
        data = self.df
        data = data[data['Week'] == week]
        data = data[data['Team'] == team_ndx]

        # get players not on bench or IR
        data = data[data['Pos'] != 'Bench']
        starters = data[data['Pos'] != 'IR']

        if pos is not None:
            starters = starters[starters['Pos'] == pos]
            if starters.empty:
                print('Warning: position {} not found in starters for team {} week {}.'.format(pos, team, week))
                return []
        
        return starters['Player'].tolist()


    #def get_player_position(player, year='2020'):
    #    """ return position of player. heavy assumption player pos doesn't change """
    #
    #    data = load_data(year)
    #    pos = data[data['Player'] == player]['Pos'].tolist()[0]
    #    return pos


    def get_team_color(self, team):
        year = self.year
        if type(team) == str:
            team_ndx = self.get_team_id_from(team, year)
        else:
            team_ndx = team

        team_colors = np.array(plt.get_cmap('tab10').colors)
        return team_colors[team_ndx-1,:]


    def get_number_of_position_slots(self, pos=None):

        year = str(self.year)

        if year == '2020' or year == '2021':
            slots = 0
            if pos is None:
                slots = 10
            elif pos == 'QB':
                slots = 1
            elif pos == 'RB':
                slots = 2
            elif pos == 'WR':
                slots = 3
            elif pos == 'K':
                slots = 1
            elif pos == 'Def':
                slots = 1
            elif pos == 'TE':
                slots = 1
            else:
                print('Position {} not recognized.'.format(pos))
                slots = -1
        
        elif year == '2019':
            slots = 0
            if pos is None:
                slots = 10
            elif pos == 'QB':
                slots = 1
            elif pos == 'RB':
                slots = 2
            elif pos == 'WR':
                slots = 3
            elif pos == 'K':
                slots = 1
            elif pos == 'Def':
                slots = 1
            elif pos == 'TE':
                slots = 1
            else:
                print('Position {} not recognized.'.format(pos))
                slots = -1
        
        return slots
    

    def get_num_players_started(self, team, pos=None):
        """ function that returns the total number of different players started, optionally in a position """

        year = self.year

        if type(team) == str:
            team_ndx = self.get_team_id_from(team, year)
        else:
            team_ndx = team

        # load team data
        data = self.df
        data = data[data['Team'] == team_ndx]

        # get players not on bench or IR
        data = data[data['Pos'] != 'Bench']
        data = data[data['Pos'] != 'IR']

        if pos is None:
            num_players_started = len(data['Player'].unique())
        else:
            data = data[data['Pos'] == pos]
            num_players_started = len(data['Player'].unique())
        
        return num_players_started

    # return player ID given name
    def get_player_id(self, player_name):

        pid = self.league.player_map[player_name]

        return pid

    # get stats on player performance
    def get_player_object(self, player):

        year = self.year

        if type(player) == int:
            pid = player
        else:
            pid = self.get_player_id(player)

        # instantiate player object given player ID
        params = { 'view': 'kona_playercard' }
        filters = {'players':{'filterIds':{'value':[pid]}, 'filterStatsForTopScoringPeriodIds':{'value':16, "additionalValue":["00{}".format(year), "10{}".format(year)]}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}
        data = self.league.espn_request.league_get(params=params, headers=headers)
        p = Player(data['players'][0], year)

        return p

    def get_player_position(self, player):

        pid = self.get_player_id([player])
        p = self.get_player_object(pid)

        return p.position