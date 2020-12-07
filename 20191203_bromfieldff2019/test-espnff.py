from espnff import League

# league info
league_id = 775166
season = 2018

# from browser cookie, 181227
swid = '{9F7C3455-C43D-42A6-9D1A-AEB707CB5F0B}'
espn_s2 = 'AEBSDwG1acaXBt31ap4LjKGjSaGd%2BBoXbFs59oEpoGUWCwjIcmEmxmEb%2F8asDxSz705IwB9HrGVBAgjZiFZ8m3aRY%2BHDEtG1lR1%2F%2BDrjkF1wqoeQaVfeeVzQE05y2HOJwEoT4Ojn1%2FHJQ3cjMqmHdUmdt70MX0zSjvjwnl15%2BCHnkVMEhX%2B7dTGidNtTmilvKlCFiO237AV%2FICfGA%2FcY9t1vGdesiEnJyDv6WEX6OGuWI%2FwkrjR%2BGUoAa7HM4U4kNIIEovl0FKG3bTRLoSHwFtDOVNUdfDnkOMoGiPCw82W0mA%3D%3D'

# initialize league object
l = League(league_id, season, espn_s2=espn_s2, swid=swid)

# create list of teams
team_power_ranks = {}
for t in range(8):
    team_power_ranks.update({l.teams[t].team_name: []})
    

# get power rankings for each week
for w in range(1, 17):
    for t in range(8):
        power_rank = l.power_rankings(w)[t]
        
        # append power ranking to list via indexing with team name
        team_power_ranks[power_rank[1].team_name].append(power_rank[0])
        

# set xvals
xvals = [x for x in range(1, 17)]

# make figure
ax = plt.subplot(121)

# plot
for t in range(0, 8):
    
    # get name
    name = l.teams[t].team_name
    
    # plot
    ax.plot(xvals, scores[t], linewidth=3, label=name)

# decorate and plot

ax.set_ylim((0, 200))
plt.legend(loc='right', bbox_to_anchor = plt.subplot(122).bbox)
plt.show()