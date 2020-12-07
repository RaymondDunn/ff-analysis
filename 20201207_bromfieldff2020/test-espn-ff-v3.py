# install api interface at https://github.com/cwendt94/ff-espn-api/

import requests

# get hardcoded cookies from browser


# helper function from ff-espn-api
def checkRequestStatus(status: int) -> None:
    if 500 <= status <= 503:
            raise Exception(status)
    if status == 401:
        raise Exception("Access Denied")

    elif status == 404:
        raise Exception("Invalid League")

    elif status != 200:
        raise Exception('Unknown %s Error' % status)


year = 2019
league_id = 83174673


# fetch league
swid = '{9F7C3455-C43D-42A6-9D1A-AEB707CB5F0B}'
espn_s2 = 'AEAbG0EULx3Zj%2BBXRnR2huemCue3imODGQzS2bFsC6ldc6oK7WFCyVHIDa71t3AAsVCbaCAGI6AfRJv8Efy15OXnp3zMO5bMcfk%2F2ZFNhJ2Su3GMo2agzCWBVLfebZwx6afUlLoCNHndmRunHYkbcfHoZgz%2FNSZlep0G9UHXKXzazUs03JV5nSspxiymkMSFgdIvZjPrhxfQL5H4WH34S3iIrCgOUxyO%2BXQUxv3dtDzvgO3fxbdp3BPGhNBlDBPZk70U4sEttyWJXds5p2pDlhS7QYXRQYVwh6jpQy29%2FP6ZOQ%3D%3D'
cookies = {
    'espn_s2': espn_s2,
    'SWID': swid
}
ENDPOINT = "https://fantasy.espn.com/apis/v3/games/FFL/seasons/" + str(year) + "/segments/0/leagues/" + str(league_id)
params = ''

r = requests.get(ENDPOINT, params=params, cookies=cookies)
status = r.status_code
checkRequestStatus(status)
data = r.json()


# fetch players, get general data about players
params = {
    'scoringPeriodId': 0,
    'view': 'players_wl',
}

endpoint = 'https://fantasy.espn.com/apis/v3/games/ffl/seasons/' + str(year) + '/players'
r = requests.get(endpoint, params=params, cookies=cookies)
status = r.status_code
checkRequestStatus(status)
data = r.json()

# fetch players, get scoring data
params = {
    'scoringPeriodId': 1
}
endpoint = 'https://fantasy.espn.com/apis/v3/games/ffl/seasons/' + str(year) + '/segments/0/leagues/' + str(league_id) + '?view=mMatchup&view=mMatchupScore'
r = requests.get(endpoint, params=params, cookies=cookies)
status = r.status_code
checkRequestStatus(status)
data = r.json()


# get player scoring data for all weeks
import pandas as pd

slotcodes = {
    0 : 'QB', 2 : 'RB', 4 : 'WR',
    6 : 'TE', 16: 'Def', 17: 'K',
    20: 'Bench', 21: 'IR', 23: 'Flex'
}

week = 1
d = r.json()
data = []

for tm in d['teams']:
    tmid = tm['id']
    for p in tm['roster']['entries']:
        name = p['playerPoolEntry']['player']['fullName']
        slot = p['lineupSlotId']
        pos  = slotcodes[slot]

        # injured status (need try/exc bc of D/ST)
        inj = 'NA'
        try:
            inj = p['playerPoolEntry']['player']['injuryStatus']
        except:
            pass

        # projected/actual points
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
print('\nComplete.')

data = pd.DataFrame(data, 
                columns=['Week', 'Team', 'Player', 'Slot', 
                             'Pos', 'Status', 'Proj', 'Actual'])

# display just for my team aka index by column value
teamndx = 4
ndxs = np.where(data['Team'] == team)[0]
data.loc(ndxs)

# what about get data for free agents?
# api V2 free agent data can be accessed following something like https://github.com/mkreiser/ESPN-Fantasy-Football-API
# api v3 data... 