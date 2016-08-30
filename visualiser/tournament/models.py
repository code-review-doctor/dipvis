# Diplomacy Tournament Visualiser
# Copyright (C) 2014 Chris Brand
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models import Max, Min, Sum, Q
from django.utils.translation import ugettext as _

from tournament.background import *

import urllib2, random

SPRING = 'S'
FALL = 'F'
SEASONS = (
    (SPRING, _('spring')),
    (FALL, _('fall')),
)
MOVEMENT = 'M'
RETREATS = 'R'
# Use X for adjustments to simplify sorting
ADJUSTMENTS = 'X'
PHASES = (
    (MOVEMENT, _('movement')),
    (RETREATS, _('retreats')),
    (ADJUSTMENTS, _('adjustments')),
)
phase_str = {
    MOVEMENT: 'M',
    RETREATS: 'R',
    ADJUSTMENTS: 'A',
}

FIRST_YEAR = 1901

TOTAL_SCS = 34
WINNING_SCS = ((TOTAL_SCS/2)+1)

# These happen to co-incide with the coding used by the WDD
GAME_RESULT = (
    ('W', _('Win')),
    ('D2', _('2-way draw')),
    ('D3', _('3-way draw')),
    ('D4', _('4-way draw')),
    ('D5', _('5-way draw')),
    ('D6', _('6-way draw')),
    ('D7', _('7-way draw')),
    ('L', _('Loss')),
)

# Default initial position image
S1901M_IMAGE = u's1901m.gif'

# Power assignment methods
RANDOM = 'R'
FRENCH_METHOD = 'F'
POWER_ASSIGNS =  (
    (RANDOM, _('Random')),
    (FRENCH_METHOD, _('French method')),
)

# Mask values to choose which background strings to include
MASK_TITLES = 1<<0
MASK_TOURNEY_COUNT = 1<<1
MASK_FIRST_TOURNEY = 1<<2
MASK_LAST_TOURNEY = 1<<3
MASK_BEST_TOURNEY_RESULT = 1<<4
MASK_GAMES_PLAYED = 1<<5
MASK_BEST_SC_COUNT = 1<<6
MASK_SOLO_COUNT = 1<<7
MASK_ELIM_COUNT = 1<<8
MASK_BOARD_TOP_COUNT = 1<<9
MASK_ROUND_ENDPOINTS = 1<<10
MASK_ALL_BG = (1<<11)-1

# Mask values to choose which news strings to include
MASK_BOARD_TOP = 1<<0
MASK_GAINERS = 1<<1
MASK_LOSERS = 1<<2
MASK_DRAW_VOTES = 1<<3
MASK_ELIMINATIONS = 1<<4
MASK_ALL_NEWS = (1<<5)-1

TITLE_MAP = {
    'World Champion' : 1,
    'North American Champion' : 1,
    'Winner' : 1,
    'European Champion' : 1,
    'Second' : 2,
    'Third' : 3,
}

class InvalidScoringSystem(Exception):
    pass

class GameScoringSystem():
    # TODO This doesn't deal with multiple players playing one power
    """
    A scoring system for a Game.
    Provides a method to calculate a score for each player of one game.
    """
    name = u''
    # True for classes that provide building blocks rather than full scoring systems
    is_abstract = True

    def _the_game(self, centre_counts):
        """Returns the game in question."""
        return centre_counts.first().game

    def _final_year(self, centre_counts):
        """Returns the most recent year we have centre counts for."""
        return centre_counts.order_by('-year')[0].year

    def _final_year_scs(self, centre_counts):
        """Returns the CentreCounts for the most recent year only, ordered largest-to-smallest."""
        return centre_counts.filter(year=self._final_year(centre_counts)).order_by('-count')

    def _survivor_count(self, centre_counts):
        """Returns the number of surviving powers"""
        return self._final_year_scs(centre_counts).filter(count__gt=0).count()

    def scores(self, centre_counts):
        """
        Takes the set of CentreCount objects for one Game.
        Returns a dict, indexed by power id, of scores.
        """
        return {}

class GScoringSolos(GameScoringSystem):
    """
    Solos score 100 points.
    Other results score 0.
    """
    def __init__(self):
        self.is_abstract = False
        self.name = _(u'Solo or bust')

    def scores(self, centre_counts):
        """
        If any power soloed, they get 100 points.
        Otherwise, they get 0.
        Return a dict, indexed by power id, of scores.
        """
        retval = {}
        # We only care about the most recent centrecounts
        for sc in self._final_year_scs(centre_counts):
            retval[sc.power] = 0
            if sc.count >= WINNING_SCS:
                retval[sc.power] = 100.0
        return retval

class GScoringDrawSize(GameScoringSystem):
    """
    Solos score 100 points.
    Draw sharers split 100 points between them.
    """
    def __init__(self):
        self.is_abstract = False
        self.name = _(u'Draw size')

    def scores(self, centre_counts):
        """
        If any power soloed, they get 100 points.
        Otherwise, if a draw passed, all powers in the draw equally shared 100 points between them.
        Otherwise, all surviving powers equally share 100 points between them.
        Return a dict, indexed by power id, of scores.
        """
        retval = {}
        the_game = self._the_game(centre_counts)
        is_dias = the_game.is_dias()
        draw = the_game.passed_draw()
        survivors = self._survivor_count(centre_counts)
        soloed = the_game.soloer() != None
        # We only care about the most recent centrecounts
        for sc in self._final_year_scs(centre_counts):
            retval[sc.power] = 0
            if sc.count >= WINNING_SCS:
                retval[sc.power] = 100.0
            elif soloed:
                # Leave the score at zero
                pass
            elif draw and sc.power in draw.powers():
                retval[sc.power] = 100.0 / draw.draw_size()
            elif sc.count > 0:
                retval[sc.power] = 100.0 / survivors
        return retval

def adjust_rank_score(centre_counts, rank_points):
    """
    Takes a list of CentreCounts for one year of one game, ordered highest-to-lowest
    and a list of ranking points for positions, ordered from first place to last.
    Returns a list of ranking points for positions, ordered to correspond to the centre counts,
    having made adjustments for any tied positions.
    Where two or more powers have the same score, the ranking points for their positions
    are shared eveny between them.
    """
    if len(rank_points) == 0:
        # The rest of them get zero points
        return [] + [0.0] * len(centre_counts)
    # First count up how many powers tied at the top
    i = 0
    count = 0
    points = 0
    scs = centre_counts[0].count
    while (i < len(centre_counts)) and (centre_counts[i].count == scs):
        count += 1
        if i < len(rank_points):
            points += rank_points[i]
        i += 1
    # Now share the points between those tied players
    for j in range(0,i):
        if j < len(rank_points):
            rank_points[j] = points / count
        else:
            rank_points.append(points / count)
    # And recursively continue
    return rank_points[0:i] + adjust_rank_score(centre_counts[i:], rank_points[i:])

class GScoringCDiplo(GameScoringSystem):
    """
    If there is a solo:
    - Soloers score a set number of points (soloer_pts).
    - Losers to a solo may optionally also score some set number of points (loss_pts).
    Otherwise:
    - Participants get some points (played_pts).
    - Everyone gets one point per centre owned.
    - Power with the most centres gets a set number of points (first_pts).
    - Power with the second most centres gets a set number of points (second_pts).
    - Power with the third most centres gets a set number of points (third_pts).
    - if powers are tied for rank, they split the points for their ranks.
    """
    def __init__(self, name, soloer_pts, played_pts, first_pts, second_pts, third_pts, loss_pts=0):
        self.is_abstract = False
        self.name = name
        self.soloer_pts = soloer_pts
        self.played_pts = played_pts
        self.position_pts = [first_pts, second_pts, third_pts]
        self.loss_pts = loss_pts

    def scores(self, centre_counts):
        retval = {}
        final_scs = self._final_year_scs(centre_counts)
        # Tweak the ranking points to allow for ties
        rank_pts = adjust_rank_score(list(final_scs), self.position_pts)
        i = 0
        for sc in final_scs:
            if final_scs[0].count >= WINNING_SCS:
                retval[sc.power] = self.loss_pts
                if sc.count >= WINNING_SCS:
                    retval[sc.power] = self.soloer_pts
            else:
                retval[sc.power] = self.played_pts + sc.count + rank_pts[i]
            i += 1
        return retval

class GScoringSumOfSquares(GameScoringSystem):
    """
    Soloer gets 100 points, everyone else gets zero.
    If there is no solo, square each power's final centre-count and normalize those numbers to
    sum to 100 points.
    """
    def __init__(self):
        self.name = _(u'Sum of Squares')
        self.is_abstract = False

    def scores(self, centre_counts):
        retval = {}
        retval_solo = {}
        solo_found = False
        final_scs = self._final_year_scs(centre_counts)
        sum_of_squares = 0
        for sc in final_scs:
            retval_solo[sc.power] = 0
            retval[sc.power] = sc.count * sc.count * 100.0
            sum_of_squares += sc.count * sc.count
            if sc.count >= WINNING_SCS:
                # Overwrite the previous totals we came up with
                retval_solo[sc.power] = 100.0
                solo_found = True
        if solo_found:
            return retval_solo
        for sc in final_scs:
            retval[sc.power] /= sum_of_squares
        return retval

# All the game scoring systems we support
G_SCORING_SYSTEMS = [
    GScoringSolos(),
    GScoringDrawSize(),
    GScoringCDiplo(_('CDiplo 100'), 100.0, 1.0, 38.0, 14.0, 7.0),
    GScoringCDiplo(_('CDiplo 80'), 80.0, 0.0, 25.0, 14.0, 7.0),
    GScoringSumOfSquares(),
]

class RoundScoringSystem():
    """
    A scoring system for a Round.
    Provides a method to calculate a score for each player of one round.
    """
    name = u''
    # True for classes that provide building blocks rather than full scoring systems
    is_abstract = True

    def scores(self, game_players):
        """
        Takes the set of GamePlayer objects of interest.
        Returns a dict, indexed by player key, of scores.
        """
        return {}

class RScoringBest(RoundScoringSystem):
    """
    Take the best of any game scores for that round.
    """
    def __init__(self):
        self.is_abstract = False
        self.name = _(u'Best game counts')

    def scores(self, game_players):
        """
        If any player played multiple games, take the best game score.
        Otherwise, just take their game score.
        Return a dict, indexed by player key, of scores.
        """
        retval = {}
        # First retrieve all the scores of all the games that are involved
        # This will give us the "if the game ended now" score for in-progress games
        game_scores = {}
        for g in Game.objects.filter(gameplayer__in=game_players):
            game_scores[g] = g.scores()
        # for each player who played any of the specified games
        for p in Player.objects.filter(gameplayer__in=game_players):
            # For some reason, if a player is in game_players more than once, we'll hit this
            # TODO Investigate and fix the need for this
            if p in retval:
                continue
            # Find just their games
            player_games = game_players.filter(player=p)
            # Find the highest score
            retval[p] = max(game_scores[g.game][g.power] for g in player_games)
        return retval

# All the round scoring systems we support
R_SCORING_SYSTEMS = [
    RScoringBest(),
]

class TournamentScoringSystem():
    """
    A scoring system for a Tournament.
    Provides a method to calculate a score for each player of tournament.
    """
    name = u''
    # True for classes that provide building blocks rather than full scoring systems
    is_abstract = True

    def scores(self, round_players):
        """
        Takes the set of RoundPlayer objects of interest.
        Combines the score attribute of ones for each player into an overall score for that player.
        Returns a dict, indexed by player key, of scores.
        """
        return {}

class TScoringSum(TournamentScoringSystem):
    """
    Just add up the best N round scores.
    """
    scored_rounds = 0

    def __init__(self, name, scored_rounds):
        self.is_abstract = False
        self.name = name
        self.scored_rounds = scored_rounds

    def scores(self, round_players):
        """
        If a player played more than N rounds, sum the best N round scores.
        Otherwise, sum all their round scores.
        Return a dict, indexed by player key, of scores.
        """
        retval = {}
        # Retrieve all the scores for all the rounds involved.
        # This will give us "if the round ended now" scores for in-progress round(s)
        round_scores = {}
        for r in Round.objects.filter(roundplayer__in=round_players):
            round_scores[r] = r.scores()
        # for each player who played any of the specified rounds
        for p in Player.objects.filter(roundplayer__in=round_players):
            if p in retval:
                continue
            score = 0
            # Find just their rounds
            player_rounds = round_players.filter(player=p)
            # Extract the scores into a sorted list, highest first
            player_scores = []
            for r in player_rounds:
                try:
                    player_scores.append(round_scores[r.the_round][r.player])
                except KeyError:
                    pass
            player_scores.sort(reverse=True)
            # Add up the first N
            for s in player_scores[:self.scored_rounds]:
                score += s
            retval[p] = score
        return retval

# All the tournament scoring systems we support
T_SCORING_SYSTEMS = [
    TScoringSum(_('Sum best 2 rounds'), 2),
    TScoringSum(_('Sum best 3 rounds'), 3),
    TScoringSum(_('Sum best 4 rounds'), 4),
]

def find_scoring_system(name, the_list):
    """
    Searches through the_list for a scoring system with the specified name.
    Returns either the ScoringSystem object or None.
    """
    for s in the_list:
        # There shouldn't be any abstract systems in here, but just in case...
        if not s.is_abstract and s.name == name:
            return s
    return None

def find_game_scoring_system(name):
    return find_scoring_system(name, G_SCORING_SYSTEMS)

def find_round_scoring_system(name):
    return find_scoring_system(name, R_SCORING_SYSTEMS)

def find_tournament_scoring_system(name):
    return find_scoring_system(name, T_SCORING_SYSTEMS)

def get_scoring_systems(systems):
    return sorted([(s.name, s.name) for s in systems if not s.is_abstract])

def validate_year(value):
    """
    Checks for a valid game year
    """
    if value < FIRST_YEAR:
        raise ValidationError(_(u'%(value)d is not a valid game year'), params = {'value': value})

def validate_year_including_start(value):
    """
    Checks for a valid game year, allowing 1900, too
    """
    if value < FIRST_YEAR-1:
        raise ValidationError(_(u'%(value)d is not a valid game year'), params = {'value': value})

def validate_sc_count(value):
    """
    Checks for a valid SC count
    """
    if value < 0 or value > TOTAL_SCS:
        raise ValidationError(_(u'%(value)d is not a valid SC count'), params = {'value': value})

# TODO Not used
def validate_wdd_id(value):
    """
    Checks a WDD id
    """
    url = u'http://world-diplomacy-database.com/php/results/player_fiche.php?id_player=%d' % value
    p = urllib2.urlopen(url)
    if p.geturl() != url:
        raise ValidationError(_(u'%(value)d is not a valid WDD Id'), params = {'value': value})

class GreatPower(models.Model):
    """
    One of the seven great powers that can be played
    """
    name = models.CharField(max_length=20, unique=True)
    abbreviation = models.CharField(max_length=1, unique=True)
    starting_centres = models.PositiveIntegerField()

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

class GameSet(models.Model):
    """
    A Diplomacy board game set.
    Over the years, different sets have been produced with different pieces, maps, etc.
    The main purpose of separating this out is so that we can display SC counts with power
    colours matching those of any photos of the board.
    """
    name = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.name

class SetPower(models.Model):
    """
    A single GreatPower in a given GameSet.
    """
    the_set = models.ForeignKey(GameSet, verbose_name=_(u'set'))
    power = models.ForeignKey(GreatPower)
    colour = models.CharField(max_length=20)

    class Meta:
        unique_together = ('the_set', 'power')

    def __unicode__(self):
        return _(u'%(power)s in %(the_set)s' % {'power': self.power.name, 'the_set': self.the_set.name})

def add_player_bg(player):
    """
    Cache background data for the player
    """
    wdd = player.wdd_player_id
    if wdd:
        try:
            bg = Background(wdd)
        except WDDNotAccessible:
            return
        # Titles won
        titles = bg.titles()
        for title in titles:
            pos = None
            the_title = None
            for key,val in TITLE_MAP.iteritems():
                try:
                    if title[key] == unicode(player):
                        pos = val
                        if key.find('Champion') != -1:
                            the_title = key
                except KeyError:
                    pass
            if pos:
                i, created = PlayerRanking.objects.get_or_create(player=player,
                                                                 tournament=title['Tournament'],
                                                                 position=pos,
                                                                 year=title['Year'])
                if the_title:
                    i.title = the_title
                i.save()
        # Podium finishes
        finishes = bg.finishes()
        for finish in finishes:
            d = finish['Date']
            i,created = PlayerRanking.objects.get_or_create(player=player,
                                                            tournament=finish['Tournament'],
                                                            position=finish['Position'],
                                                            year=d[:4])
            i.date = d
            i.save()
        # Tournaments
        tournaments = bg.tournaments()
        for t in tournaments:
            d = t['Date']
            try:
                i,created = PlayerRanking.objects.get_or_create(player=player,
                                                                tournament=t['Name of the tournament'],
                                                                position=t['Rank'],
                                                                year=d[:4])
                i.date = d
                i.save()
            except KeyError:
                # No rank implies they were the TD or similar - just ignore that tournament
                print("Ignoring %s for %s" % (t['Name of the tournament'], player))
                pass
        # Boards
        boards = bg.boards()
        for b in boards:
            try:
                power = b['Country']
                p=GreatPower.objects.get(name__contains=power)
            except GreatPower.DoesNotExist:
                # Apparently not a Standard game
                continue
            i,created = PlayerGameResult.objects.get_or_create(tournament_name=b['Name of the tournament'],
                                                               game_name=b['Round / Board'],
                                                               player=player,
                                                               power=p,
                                                               date = b['Date'],
                                                               position = b['Position'])
            # If there's no 'Position sharing', they were alone at that position
            try:
                i.position_equals = b['Position sharing']
            except KeyError:
                i.position_equals = 1
            # Ignore any of these that aren't present
            try:
                i.score = b['Score']
            except KeyError:
                pass
            try:
                i.final_sc_count = b['Final SCs']
            except KeyError:
                pass
            try:
                i.result = b['Game end']
            except KeyError:
                pass
            try:
                i.year_eliminated = b['Elimination year']
            except KeyError:
                pass
            i.save()

def position_str(position):
    """
    Returns the string version of the position e.g. '1st', '12th'.
    """
    # TODO translation support ?
    result = unicode(position)
    pos = position % 100
    if pos > 3 and pos < 21:
        result += u'th'
    elif pos % 10 == 1:
        result += u'st'
    elif pos % 10 == 2:
        result += u'nd'
    elif pos % 10 == 3:
        result += u'rd'
    else:
        result += u'th'
    return _(result)

class Player(models.Model):
    """
    A person who played Diplomacy
    """
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    wdd_player_id = models.PositiveIntegerField(unique=True, verbose_name=_(u'WDD player id'), blank=True, null=True)
    # TODO Would be nice to support a picture of the player, too

    class Meta:
        ordering = ['last_name', 'first_name']

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)

    def save(self, *args, **kwargs):
        super(Player, self).save(*args, **kwargs)
        add_player_bg(self)

    def clean(self):
        if not self.wdd_player_id:
            return
        # Check that the WDD id seems to match the name
        try:
            bg = Background(self.wdd_player_id)
        except WDDNotAccessible:
            # Not much we can do in this case
            return
        except InvalidWDDId:
            raise ValidationError(_(u'WDD Id %(wdd_id)d is invalid'), params = {'wdd_id': self.wdd_player_id})
        # TODO This may be too strict
        wdd_name = bg.name()
        if wdd_name != self.__unicode__():
            raise ValidationError(_(u'WDD Id %(wdd_id)d is for %(wdd_name)s, not %(first_name)s %(last_name)s'),
                                  params = {'wdd_id': self.wdd_player_id,
                                            'wdd_name': wdd_name,
                                            'first_name': self.first_name,
                                            'last_name': self.last_name})

    def _rankings(self, mask=MASK_ALL_BG):
        """ List of titles won and tournament rankings"""
        results = []
        ranking_set = self.playerranking_set.order_by('year')
        plays = ranking_set.count()
        if plays == 0:
            return results
        if (mask & MASK_TOURNEY_COUNT) != 0:
            results.append(_(u'%(name)s has competed in %(number)d tournament(s).') % {'name': self, 'number': plays})
        if (mask & MASK_TITLES) != 0:
            # Add summaries of actual titles
            titles = {}
            for ranking in ranking_set:
                if ranking.title:
                    if ranking.title not in titles:
                        titles[ranking.title] = []
                    titles[ranking.title].append(ranking.year)
            for key, lst in titles.iteritems():
                results.append(str(self) + ' was ' + key + ' in ' + ', '.join(map(str, lst)) + '.')
        if (mask & MASK_FIRST_TOURNEY) != 0:
            first = ranking_set.first()
            results.append(_(u'%(name)s first competed in a tournament (%(tournament)s) in %(year)d.') % {'name': self,
                                                                                                          'tournament': first.tournament,
                                                                                                          'year': first.year})
        if (mask & MASK_LAST_TOURNEY) != 0:
            last = ranking_set.last()
            results.append(_(u'%(name)s most recently competed in a tournament (%(tournament)s) in %(year)d.') % {'name': self,
                                                                                                                  'tournament': last.tournament,
                                                                                                                  'year': last.year})
        if (mask & MASK_BEST_TOURNEY_RESULT) != 0:
            wins = ranking_set.filter(position=1).count()
            if wins > 1:
                results.append(_(u'%(name)s has won %(wins)d tournaments.') % {'name': self, 'wins': wins})
            elif wins > 0:
                results.append(_(u'%(name)s has won %(wins)d tournament.') % {'name': self, 'wins': wins})
            else:
                best = ranking_set.aggregate(Min('position'))['position__min']
                pos = position_str(best)
                results.append(_(u'The best tournament result for %(name)s is %(position)s.') % {'name': self, 'position': pos})
        return results

    def _results(self, power=None, mask=MASK_ALL_BG):
        """ List of tournament game achievements, optionally with one Great Power """
        results = []
        results_set = self.playergameresult_set.order_by('year')
        if power:
            results_set = results_set.filter(power=power)
            c_str = _(u' as %(power)s') % {'power': power}
        else:
            c_str = u''
        games = results_set.count()
        if games == 0:
            if (mask & MASK_GAMES_PLAYED) != 0:
                results.append(_(u'%(name)s has never played%(power)s in a tournament before.') % {'name': self,
                                                                                                   'power': c_str})
            return results
        if (mask & MASK_GAMES_PLAYED) != 0:
            results.append(_(u'%(name)s has played %(games)d tournament games%(power)s.') % {'name': self,
                                                                                             'games': games,
                                                                                             'power': c_str})
        if (mask & MASK_BEST_SC_COUNT) != 0:
            best = results_set.aggregate(Max('final_sc_count'))['final_sc_count__max']
            results.append(_(u'%(name)s has finished with as many as %(dots)d centres%(power)s in tournament games.') % {'name': self,
                                                                                                                         'dots': best,
                                                                                                                         'power': c_str})
            solo_set = results_set.filter(final_sc_count__gte=WINNING_SCS)
        if (mask & MASK_SOLO_COUNT) != 0:
            solos = solo_set.count()
            if solos > 0:
                results.append(_(u'%(name)s has soloed %(solos)d of %(games)d tournament games played%(power)s (%(percentage).2f%%).') % {'name': self,
                                                                                                                                          'solos': solos,
                                                                                                                                          'games': games,
                                                                                                                                          'power': c_str,
                                                                                                                                          'percentage': 100.0*float(solos)/float(games)})
            else:
                results.append(_(u'%(name)s has yet to solo%(power)s at a tournament.') % {'name': self,
                                                                                           'power': c_str})
        if (mask & MASK_ELIM_COUNT) != 0:
            query = Q(year_eliminated__isnull=False) | Q(final_sc_count=0)
            eliminations_set = results_set.filter(query)
            eliminations = eliminations_set.count()
            if eliminations > 0:
                results.append(_(u'%(name)s was eliminated in %(deaths)d of %(games)d tournament games played%(power)s (%(percentage).2f%%).') % {'name': self,
                                                                                                                                                  'deaths': eliminations,
                                                                                                                                                  'games': games,
                                                                                                                                                  'power': c_str,
                                                                                                                                                  'percentage': 100.0*float(eliminations)/float(games)})
            else:
                results.append(_(u'%(name)s has yet to be eliminated%(power)s in a tournament.') % {'name': self,
                                                                                                   'power': c_str})
        if (mask & MASK_BOARD_TOP_COUNT) != 0:
            query = Q(result='W') | Q(position=1)
            victories_set = results_set.filter(query)
            board_tops = victories_set.count()
            if board_tops > 0:
                results.append(_(u'%(name)s topped the board in %(tops)d of %(games)d tournament games played%(power)s (%(percentage).2f%%).') % {'name': self,
                                                                                                                                                  'tops': board_tops,
                                                                                                                                                  'games': games,
                                                                                                                                                  'power': c_str,
                                                                                                                                                  'percentage': 100.0*float(board_tops)/float(games)})
            else:
                results.append(_(u'%(name)s has yet to top the board%(power)s at a tournament.') % {'name': self,
                                                                                                   'power': c_str})
        return results

    def background(self, power=None, mask=MASK_ALL_BG):
        """
        List of background strings about the player, optionally as a specific Great Power
        """
        if not power:
            return self._rankings(mask=mask) + self._results(mask=mask)
        return self._results(power, mask=mask)

class Tournament(models.Model):
    """
    A Diplomacy tournament
    """
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    # How do we combine round scores to get an overall player tournament score ?
    # This is the name of a TournamentScoringSystem object
    tournament_scoring_system = models.CharField(max_length=40,
                                                 choices=get_scoring_systems(T_SCORING_SYSTEMS),
                                                 help_text=_(u'How to combine round scores into a tournament score'))
    # How do we combine game scores to get an overall player score for a round ?
    # This is the name of a RoundScoringSystem object
    round_scoring_system = models.CharField(max_length=40,
                                            choices=get_scoring_systems(R_SCORING_SYSTEMS),
                                            help_text=_(u'How to combine game scores into a round score'))

    class Meta:
        ordering = ['-start_date']

    def scores(self, force_recalculation=False):
        """
        Returns the scores for everyone who played in the tournament.
        """
        # If the tournament is over, report the stored scores unless we're told to recaclulate
        if self.is_finished() and not force_recalculation:
            retval = {}
            for p in self.tournamentplayer_set.all():
                retval[p.player] = p.score
            return retval

        # Find the scoring system to combine round scores into a tournament score
        system = find_tournament_scoring_system(self.tournament_scoring_system)
        if not system:
            raise InvalidScoringSystem(self.tournament_scoring_system)
        return system.scores(RoundPlayer.objects.filter(the_round__tournament=self))

    def background(self, mask=MASK_ALL_BG):
        """
        Returns a list of background strings for the tournament
        """
        players = Player.objects.filter(tournamentplayer__tournament = self)
        results = []
        for p in players:
            results += p.background(mask=mask)
        # Shuffle the resulting list
        random.shuffle(results)
        return results

    def news(self):
        """
        Returns a list of news strings for the tournament
        """
        results = []
        # TODO This should probably just call through to the current round's news() method
        current_round = self.current_round()
        if current_round:
            for g in current_round.game_set.all():
                results += g.news(include_game_name=True)
        else:
            # TODO list top few scores in previous round, perhaps ?
            pass
        # Shuffle the resulting list
        random.shuffle(results)
        return results

    def current_round(self):
        """
        Returns the Round in progress, or None
        """
        # Rely on the default ordering
        rds = self.round_set.all()
        for r in rds:
            if not r.is_finished():
                return r
        return None

    def is_finished(self):
        for r in self.round_set.all():
            if not r.is_finished():
                return False
        return True

    def get_absolute_url(self):
        return reverse('tournament_detail', args=[str(self.id)])

    def __unicode__(self):
        return self.name

class TournamentPlayer(models.Model):
    """
    One player in a tournament
    """
    player = models.ForeignKey(Player)
    tournament = models.ForeignKey(Tournament)
    score = models.FloatField(default=0.0)

    class Meta:
        ordering = ['player']

    def __unicode__(self):
        return u'%s %s %f' % (self.tournament, self.player, self.score)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super(TournamentPlayer, self).save(*args, **kwargs)
        # Update background info when a player is added to the Tournament (only)
        if is_new:
            add_player_bg(self.player)

class Round(models.Model):
    """
    A single round of a Tournament
    """
    tournament = models.ForeignKey(Tournament)
    number = models.PositiveSmallIntegerField()
    # How do we combine game scores to get an overall player score for a round ?
    # This is the name of a GameScoringSystem object
    # There has at least been talk of tournaments using multiple scoring systems, one per round
    scoring_system = models.CharField(max_length=40,
                                      verbose_name=_(u'Game scoring system'),
                                      choices=get_scoring_systems(G_SCORING_SYSTEMS),
                                      help_text=_(u'How to calculate a score for one game'))
    dias = models.BooleanField(verbose_name=_(u'Draws Include All Survivors'))
    final_year = models.PositiveSmallIntegerField(blank=True, null=True, validators=[validate_year])
    earliest_end_time = models.DateTimeField(blank=True, null=True)
    latest_end_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['number']

    def scores(self, force_recalculation=False):
        """
        Returns the scores for everyone who played in the round.
        """
        # If the round is over, report the stored scores unless we're told to recaclulate
        if self.is_finished() and not force_recalculation:
            retval = {}
            for p in self.roundplayer_set.all():
                retval[p.player] = p.score
            return retval

        # Find the scoring system to combine game scores into a round score
        system = find_round_scoring_system(self.tournament.round_scoring_system)
        if not system:
            raise InvalidScoringSystem(self.tournament.round_scoring_system)
        return system.scores(GamePlayer.objects.filter(game__the_round=self))

    def is_finished(self):
        gs = self.game_set.all()
        if len(gs) == 0:
            # Rounds with no games can't have started
            return False
        for g in gs:
            if not g.is_finished:
                return False
        return True

    def background(self, mask=MASK_ALL_BG):
        """
        Returns a list of background strings for the round
        """
        results = []
        if (mask & MASK_ROUND_ENDPOINTS) & self.earliest_end_time:
            results.append(_(u'Round %(round)d could end as early as %(time)s.') % {'round': self.number,
                                                                                    'time': self.earliest_end_time.strftime("%H:%M")})
        if (mask & MASK_ROUND_ENDPOINTS) & self.latest_end_time:
            results.append(_(u'Round %(round)d could end as late as %(time)s.') % {'round': self.number,
                                                                                   'time': self.latest_end_time.strftime("%H:%M")})
        if (mask & MASK_ROUND_ENDPOINTS) & self.final_year:
            results.append(_(u'Round %(round)d will end after playing year %(year)d.') % {'round': self.number,
                                                                                          'year': self.final_year})
        # Shuffle the resulting list
        random.shuffle(results)
        return results

    def clean(self):
        # Must provide either both end times, or neither
        if self.earliest_end_time and not self.latest_end_time:
            raise ValidationError(_(u'Earliest end time specified without latest end time'))
        if self.latest_end_time and not self.earliest_end_time:
            raise ValidationError(_(u'Latest end time specified without earliest end time'))

    def get_absolute_url(self):
        return reverse('round_detail',
                       args=[str(self.tournament.id), str(self.number)])

    def __unicode__(self):
        return _(u'%(tournament)s Round %(round)d') % {'tournament': self.tournament, 'round': self.number}

class Game(models.Model):
    """
    A single game of Diplomacy, within a Round
    """
    # TODO Because we use game name in URLs, they must not contain spaces
    # TODO with our current URL scheme, we actually need game names to be unique
    # within the tournament - this is more restrictive than that
    name = models.CharField(max_length=20, unique=True, help_text='Must be unique. No spaces')
    started_at = models.DateTimeField()
    is_finished = models.BooleanField(default=False)
    is_top_board = models.BooleanField(default=False)
    the_round = models.ForeignKey(Round, verbose_name=_(u'round'))
    the_set = models.ForeignKey(GameSet, verbose_name=_(u'set'))
    # TODO Use this
    power_assignment = models.CharField(max_length=1,
                                        verbose_name=_(u'Power assignment method'),
                                        choices=POWER_ASSIGNS,
                                        default=RANDOM)

    class Meta:
        ordering = ['name']

    def scores(self, force_recalculation=False):
        """
        If the game has ended and force_recalculation is False, report the recorded scores.
        If the game has not ended or force_recalculation is True, calculate the scores if
        the game were to end now.
        Return value is a dict, indexed by power id, of scores.
        """
        if self.is_finished and not force_recalculation:
            # Return the stored scores for the game
            retval = {}
            players = self.gameplayer_set.all()
            for p in players:
                # TODO Need to combine scores if multiple players played a power
                retval[p.power] = p.score
            return retval

        # Calculate the scores for the game using the specified ScoringSystem
        system = find_game_scoring_system(self.the_round.scoring_system)
        if not system:
            raise InvalidScoringSystem(self.the_round.scoring_system)
        return system.scores(self.centrecount_set.all())

    def is_dias(self):
        """
        Returns whether the game is Draws Include All Survivors
        """
        return self.the_round.dias

    def years_played(self):
        """
        Returns a list of years for which there are SC counts for this game
        """
        scs = self.centrecount_set.all()
        return sorted(list(set([sc.year for sc in scs])))

    def players(self, latest=True):
        """
        Returns a dict, keyed by power, of lists of players of that power
        If latest is True, only include the latest player of each power
        """
        powers = GreatPower.objects.all()
        gps = self.gameplayer_set.all().order_by('-first_year')
        retval = {}
        for power in powers:
            ps = gps.filter(power=power)
            if latest:
                ps = ps[0:1]
            retval[power] = [gp.player for gp in ps]
        return retval

    def news(self, include_game_name=False, mask=MASK_ALL_NEWS):
        """
        Returns a list of strings the describe the latest events in the game
        """
        if include_game_name:
            gn_str = _(u' in game %(name)s') % {'name': self.name}
        else:
            gn_str = ''
        if self.is_finished:
            # Just report the final result
            return [self.result_str(include_game_name)]
        player_dict = self.players(latest=True)
        centres_set = self.centrecount_set.order_by('-year')
        last_year = centres_set[0].year
        current_scs = centres_set.filter(year=last_year)
        results = []
        if (mask & MASK_BOARD_TOP) != 0:
            # Who's topping the board ?
            max_scs = current_scs.order_by('-count')[0].count
            first = current_scs.order_by('-count').filter(count=max_scs)
            first_str = ', '.join(['%s (%s)' % (player_dict[scs.power][0],
                                                _(scs.power.abbreviation)) for scs in list(first)])
            results.append(_(u'Highest SC count%(game)s is %(dots)d, for %(player)s.') % {'game': gn_str,
                                                                                          'dots': max_scs,
                                                                                          'player': first_str})
        if last_year > 1900:
            prev_scs = centres_set.filter(year=last_year-1)
        else:
            # We only look for differences, so just force no differences
            prev_scs = current_scs
        for scs in current_scs:
            power = scs.power
            prev = prev_scs.get(power=power)
            # Who gained 2 or more centres in the last year ?
            if (mask & MASK_GAINERS) != 0:
                if scs.count - prev.count > 1:
                    results.append(_(u'%(player)s (%(power)s) grew from %(old)d to %(new)d centres%(game)s.') % {'player': player_dict[power][0],
                                                                                                                 'power': _(power.abbreviation),
                                                                                                                 'old': prev.count,
                                                                                                                 'new': scs.count,
                                                                                                                 'game': gn_str})
            # Who lost 2 or more centres in the last year ?
            if (mask & MASK_LOSERS) != 0:
                if prev.count - scs.count > 1:
                    results.append(_(u'%(player)s (%(power)s) shrank from %(old)d to %(new)d centres%(game)s.') % {'player': player_dict[power][0],
                                                                                                                   'power': _(power.abbreviation),
                                                                                                                   'old': prev.count,
                                                                                                                   'new': scs.count,
                                                                                                                   'game': gn_str})
        if (mask & MASK_DRAW_VOTES) != 0:
            # What draw votes failed recently ?
            # Note that it's fairly arbitrary where we draw the line here
            draws_set = self.drawproposal_set.order_by('-year').filter(year__gte=last_year)
            # TODO Lots of overlap with result_str()
            for d in draws_set:
                powers = d.powers()
                sz = len(powers)
                incl = []
                for power in powers:
                    # TODO This looks broken if there were replacements
                    game_player = self.gameplayer_set.filter(power=power).get()
                    incl.append(_(u'%(player)s (%(power)s)') % {'player': game_player.player,
                                                                'power': _(power.abbreviation)})
                incl_str = ', '.join(incl)
                if sz == 1:
                    d_str = _(u'Vote to concede to %(powers)s failed%(game)s.') % {'powers': incl_str, 'game': gn_str}
                else:
                    d_str = _(u'Draw vote for %(n)d-way between %(powers)s failed%(game)s.') % {'n': sz,
                                                                                                'powers': incl_str,
                                                                                                'game': gn_str}
                results.append(d_str)
        if (mask & MASK_ELIMINATIONS) != 0:
            # Who has been eliminated so far, and when ?
            zeroes = centres_set.filter(count=0).reverse()
            while len(zeroes):
                scs = zeroes[0]
                power = scs.power
                zeroes = zeroes.exclude(power=power)
                results.append(_(u'%(player)s (%(power)s) was eliminated in %(year)d%(game)s.') % {'player': player_dict[power][0],
                                                                                                   'power': _(power.abbreviation),
                                                                                                   'year': scs.year,
                                                                                                   'game': gn_str})
        # Shuffle the resulting list
        random.shuffle(results)
        return results

    def background(self, mask=MASK_ALL_BG):
        """
        Returns a list of strings that give background for the game
        """
        players_by_power = self.players(latest=True)
        results = []
        for c,players in players_by_power.iteritems():
            for p in players:
                results += p.background(c, mask=mask)
        # Shuffle the resulting list
        random.shuffle(results)
        return results

    def passed_draw(self):
        """
        Returns either a DrawProposal if a draw vote passed, or None.
        """
        # Did a draw proposal pass ?
        try:
            return self.drawproposal_set.filter(passed=True).get()
        except DrawProposal.DoesNotExist:
            return None

    def board_toppers(self):
        """
        Returns a list of CentreCounts for the current leader(s)
        """
        centres_set = self.centrecount_set.order_by('-year')
        last_year = centres_set[0].year
        current_scs = centres_set.filter(year=last_year)
        max_scs = current_scs.order_by('-count')[0].count
        first = current_scs.order_by('-count').filter(count=max_scs)
        return list(first)

    def neutrals(self, year=None):
        """How many neutral SCs are/were there ?"""
        if not year:
            year = self.final_year()
        scs = self.centrecount_set.filter(year=year)
        neutrals = TOTAL_SCS
        for sc in scs:
            neutrals -= sc.count
        return neutrals

    def final_year(self):
        """
        Returns the last complete year of the game, whether the game is completed or ongoing
        """
        return self.years_played()[-1]

    def soloer(self):
        """
        Returns either a GamePlayer if somebody soloed the game, or None
        """
        # Just order by SC count, and check the first (highest)
        scs = self.centrecount_set.order_by('-count')
        if scs[0].count >= WINNING_SCS:
            # TODO This looks like it fails if the soloer was a replacement player
            return self.gameplayer_set.filter(power=scs[0].power).get()
        return None

    def result_str(self, include_game_name=False):
        """
        Returns a string representing the game result, if any, or None
        """
        if include_game_name:
            gn_str = ' %s' % self.name
        else:
            gn_str = ''
        # Did a draw proposal pass ?
        draw = self.passed_draw()
        if draw:
            powers = draw.powers()
            sz = len(powers)
            if sz == 1:
                retval = _(u'Game%(game)s conceded to ') % {'game': gn_str}
            else:
                retval = _(u'Vote passed to end game%(game)s as a %(n)d-way draw between ') % {'game': gn_str, 'n': sz}
            winners = []
            for power in powers:
                # TODO This looks broken if there were replacements
                game_player = self.gameplayer_set.filter(power=power).get()
                winners.append(_(u'%(player)s (%(power)s)') % {'player': game_player.player,
                                                               'power': _(power.abbreviation)})
            return retval + ', '.join(winners)
        # Did a power reach 18 (or more) centres ?
        soloer = self.soloer()
        if soloer:
            # TODO would be nice to include their SC count
            return _(u'Game%(game)s won by %(player)s (%(power)s)') % {'game': gn_str,
                                                                       'player': soloer.player,
                                                                       'power': _(soloer.power.abbreviation)}
        # TODO Did the game get to the fixed endpoint ?
        if self.is_finished:
            player_dict = self.players(latest=True)
            toppers = self.board_toppers()
            first_str = ', '.join([_(u'%(player)s (%(power)s)') % {'player': player_dict[scs.power][0],
                                                                   'power': _(scs.power.abbreviation)} for scs in list(toppers)])
            return _(u'Game%(game)s ended. Board top is %(top)d centres, for %(player)s') % {'game': gn_str,
                                                                                             'top': scs.count,
                                                                                             'player': first_str}
        # Then it seems to be ongoing
        return None

    def save(self, *args, **kwargs):
        super(Game, self).save(*args, **kwargs)

        # Auto-create 1900 SC counts (unless they already exist)
        for power in GreatPower.objects.all():
            i, created = CentreCount.objects.get_or_create(power=power,
                                                           game=self,
                                                           year=FIRST_YEAR-1,
                                                           count=power.starting_centres)
            i.save()

        # Auto-create S1901M image (if it doesn't exist)
        i, created = GameImage.objects.get_or_create(game=self,
                                                     year=FIRST_YEAR,
                                                     season=SPRING,
                                                     phase=MOVEMENT,
                                                     image=S1901M_IMAGE)
        i.save()

        # If the game is (now) finished, store the player scores
        if self.is_finished:
            scores = self.scores(True)
            players = self.gameplayer_set.all()
            # TODO Need to split the score somehow if there were multiple players of a power
            for p in players:
                p.score = scores[p.power]
                p.save()

            # If the round is (now) finished, store the player scores
            r = self.the_round
            if r.is_finished():
                scores = r.scores(True)
                for p in r.roundplayer_set.all():
                    try:
                        p.score = scores[p.player]
                    except KeyError:
                        # Player was checked at rool call but didn't play
                        # TODO May want to add a way to give them some points
                        pass
                    p.save()

            # if the tournament is (now) finished, store the player scores
            t = self.the_round.tournament
            if t.is_finished():
                scores = t.scores(True)
                for p in t.tournamentplayer_set.all():
                    p.score = scores[p.player]
                    p.save()

    def get_absolute_url(self):
        return reverse('game_detail',
                       args=[str(self.the_round.tournament.id), self.name])

    def __unicode__(self):
        return self.name

class DrawProposal(models.Model):
    """
    A single draw or concession proposal in a game
    """
    game = models.ForeignKey(Game)
    year = models.PositiveSmallIntegerField(validators=[validate_year])
    season = models.CharField(max_length=1, choices=SEASONS)
    passed = models.BooleanField()
    proposer = models.ForeignKey(GreatPower, related_name='+')
    power_1 = models.ForeignKey(GreatPower, related_name='+')
    power_2 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')
    power_3 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')
    power_4 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')
    power_5 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')
    power_6 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')
    power_7 = models.ForeignKey(GreatPower, blank=True, null=True, related_name='+')

    def draw_size(self):
        return len(self.powers())

    def powers(self):
        """
        Returns a list of powers included in the draw proposal.
        """
        retval = []
        for name, value in self.__dict__.iteritems():
            if name.startswith('power_'):
                if value:
                    retval.append(GreatPower.objects.get(pk=value))
        return retval

    def clean(self):
        # No skipping powers
        found_null = False
        for n in range(1,8):
            if not self.__dict__['power_%d_id' % n]:
                found_null = True
            elif found_null:
                raise ValidationError(_(u'Draw powers should go as early as possible'))
        # Each power must be unique
        powers = set()
        for name, value in self.__dict__.iteritems():
            if value and name.startswith('power_'):
                if value in powers:
                    power = GreatPower.objects.get(pk=value)
                    raise ValidationError(_(u'%(power)s present more than once'), params = {'power':  power})
                powers.add(value)
        # Only one successful draw proposal
        if self.passed:
            try:
                p = DrawProposal.objects.filter(game=self.game, passed=True).get()
                if p != self:
                    raise ValidationError(_(u'Game already has a successful draw proposal'))
            except DrawProposal.DoesNotExist:
                pass
        # No dead powers included
        # If DIAS, all alive powers must be included
        dias = self.game.is_dias()
        year = self.game.final_year()
        scs = self.game.centrecount_set.filter(year=year)
        for sc in scs:
            if sc.power in powers:
                if sc.count == 0:
                    raise ValidationError(_(u'Dead power %(power)s included in proposal'), params = {'power': sc.power})
            else:
                if dias and sc.count > 0:
                    raise ValidationError(_(u'Missing alive power %(power)s in DIAS game'), params = {'power': sc.power})

    def save(self, *args, **kwargs):
        super(DrawProposal, self).save(*args, **kwargs)
        # Does this complete the game ?
        if self.passed:
            self.game.is_finished = True
            self.game.save()

    def __unicode__(self):
        return u'%s %d%s' % (self.game, self.year, self.season)

class RoundPlayer(models.Model):
    """
    A person who played a round in a tournament
    """
    player = models.ForeignKey(Player)
    the_round = models.ForeignKey(Round, verbose_name=_(u'round'))
    score = models.FloatField(default=0.0)

    class Meta:
        ordering = ['player']

    def clean(self):
        # Player should already be in the tournament
        t = self.the_round.tournament
        tp = self.player.tournamentplayer_set.filter(tournament=t)
        if not tp:
            raise ValidationError(_(u'Player is not yet in the tournament'))

    def __unicode__(self):
        return _(u'%(player)s in %(round)s') % {'player': self.player, 'round': self.the_round}

class GamePlayer(models.Model):
    """
    A person who played a Great Power in a Game
    """
    player = models.ForeignKey(Player)
    game = models.ForeignKey(Game)
    power = models.ForeignKey(GreatPower, related_name='+')
    first_year = models.PositiveSmallIntegerField(default=FIRST_YEAR, validators=[validate_year])
    first_season = models.CharField(max_length=1, choices=SEASONS, default=SPRING)
    last_year = models.PositiveSmallIntegerField(blank=True, null=True, validators=[validate_year])
    last_season = models.CharField(max_length=1, choices=SEASONS, blank=True)
    score = models.FloatField(default=0.0)
    # What order did this player choose their GreatPower ?
    # 1 => first, 7 => seventh, 0 => assigned rather than chosen
    # TODO Use this
    # TODO Add validators
    power_choice_order = models.PositiveSmallIntegerField(default=1)

    def clean(self):
        # Player should already be in the tournament
        t = self.game.the_round.tournament
        tp = self.player.tournamentplayer_set.filter(tournament=t)
        if not tp:
            raise ValidationError(_(u'Player is not yet in the tournament'))
        # Need either both or neither of last_year and last_season
        if self.last_season == '' and self.last_year:
            raise ValidationError(_(u'Final season played must also be specified'))
        if self.last_season != '' and not self.last_year:
            raise ValidationError(_(u'Final year must be specified with final season'))
        # Check for overlap with another player
        others = GamePlayer.objects.filter(game=self.game, power=self.power).exclude(player=self.player)
        # Ensure one player at a time
        for other in others:
            if self.first_year < other.first_year:
                we_were_first = True
            elif self.first_year == other.first_year:
                if self.first_season == other.first_season:
                    raise ValidationError(_(u'Overlap between players'))
                if self.first_season == SPRING:
                    we_were_first = True
                else:
                    we_were_first = False
            else:
                we_were_first = False
            if we_were_first:
                # Our term must finish before theirs started
                err_str = _(u'%(player)s is listed as playing %(power)s in game %(game)s from %(season)s %(year)')
                if not self.last_year or self.last_year > other.first_year:
                    raise ValidationError(err_str,
                                          params = {'player': other.player,
                                                    'power': power,
                                                    'game': XXX,
                                                    'season': other.first_season,
                                                    'year': other.first_year})
                if self.last_year == other.first_year:
                    if self.last_season != SPRING or other.first_season != FALL:
                        raise ValidationError(err_str,
                                              params = {'player': other.player,
                                                        'power': power,
                                                        'game': XXX,
                                                        'season': other.first_season,
                                                        'year': other.first_year})
            else:
                # Their term must finish before ours started
                err_str = _(u'%(player)s is listed as still playing %(power)s in game %(game)s from %(season)s %(year)')
                if not other.last_year or other.last_year > self.first_year:
                    raise ValidationError(err_str,
                                          params = {'player': other.player,
                                                    'power': power,
                                                    'game': self.game,
                                                    'season': self.first_season,
                                                    'year': self.first_year})
                if other.last_year == self.first_year:
                    if other.last_season != SPRING or self.first_season != FALL:
                        raise ValidationError(err_str,
                                              params = {'player': other.player,
                                                        'power': power,
                                                        'game': self.game,
                                                        'season': self.first_season,
                                                        'year': self.first_year})
        # TODO Ensure no gaps - may have to be done elsewhere

    def __unicode__(self):
        return u'%s %s %s' % (self.game, self.player, self.power)

def file_location(instance, filename):
    """
    Function that determines where to store the file.
    """
    # TODO Probably want a separate directory for each tournament,
    #      containing a directory per game
    return 'games'

class GameImage(models.Model):
    """
    An image depicting a Game at a certain point.
    The year, season, phase together indicate the phase that is about to played.
    """
    game = models.ForeignKey(Game)
    year = models.PositiveSmallIntegerField(validators=[validate_year])
    season = models.CharField(max_length=1, choices=SEASONS, default=SPRING)
    phase = models.CharField(max_length=1, choices=PHASES, default=MOVEMENT)
    image = models.ImageField(upload_to=file_location)

    class Meta:
        unique_together = ('game', 'year', 'season', 'phase')
        ordering = ['game', 'year', '-season', 'phase']

    def turn_str(self):
        """
        Short string version of season/year/phase
        e.g. 'S1901M'
        """
        return u'%s%d%s' % (self.season, self.year, phase_str[self.phase])

    def clean(self):
        if self.season == SPRING and self.phase == ADJUSTMENTS:
            raise ValidationError(_(u'No adjustment phase in spring'))

    def __unicode__(self):
        return _(u'%(game)s %(turn)s image') % {'game': self.game, 'turn': self.turn_str()}

class CentreCount(models.Model):
    """
    The number of centres owned by one power at the end of a given game year
    """
    power = models.ForeignKey(GreatPower, related_name='+')
    game = models.ForeignKey(Game)
    year = models.PositiveSmallIntegerField(validators=[validate_year_including_start])
    count = models.PositiveSmallIntegerField(validators=[validate_sc_count])

    class Meta:
        unique_together = ('power', 'game', 'year')

    def clean(self):
        # Is this for a year that is supposed to be played ?
        final_year = self.game.the_round.final_year
        if final_year and self.year > final_year:
                raise ValidationError(_(u'Games in this round end with %(year)d'), params = {'year': final_year})
        # Not possible to more than double your count in one year
        # or to recover from an elimination
        try:
            prev = CentreCount.objects.filter(power=self.power, game=self.game, year=self.year-1).get()
            if self.count > 2 * prev.count:
                raise ValidationError(_(u'SC count for a power cannot more than double in a year'))
            elif (prev.count == 0) and (self.count > 0):
                raise ValidationError(_(u'SC count for a power cannot increase from zero'))
        except CentreCount.DoesNotExist:
            # We're either missing a year, or this is the first year - let that go
            pass

    def save(self, *args, **kwargs):
        super(CentreCount, self).save(*args, **kwargs)
        # Does this complete the game ?
        final_year = self.game.the_round.final_year
        if final_year and self.year == final_year:
            # Final game year has been played
            self.game.is_finished = True
            self.game.save()
        if self.count >= WINNING_SCS:
            # Somebody won the game
            self.game.is_finished = True
            self.game.save()

    def __unicode__(self):
        return u'%s %d %s %d' % (self.game, self.year, _(self.power.abbreviation), self.count)

class PlayerRanking(models.Model):
    """
    A tournament ranking for a player.
    Used to import background information from the WDD.
    """
    player = models.ForeignKey(Player)
    tournament = models.CharField(max_length=30)
    position = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    date = models.DateField(blank=True, null=True)
    title = models.CharField(max_length=30, blank=True)

    def __unicode__(self):
        pos = position_str(self.position)
        s = _(u'%(player)s came %(position)s at %(tournament)s') % {'player': self.player,
                                                                    'position': pos,
                                                                    'tournament': self.tournament}
        if self.tournament[-4:] != unicode(self.year):
            s += _(u' in %(year)d') % {'year': self.year}
        return s

class PlayerGameResult(models.Model):
    """
    One player's result for a tournament game.
    Used to import background information from the WDD.
    """
    tournament_name = models.CharField(max_length=20)
    game_name = models.CharField(max_length=20)
    player = models.ForeignKey(Player)
    power = models.ForeignKey(GreatPower, related_name='+')
    date = models.DateField()
    position = models.PositiveSmallIntegerField()
    position_equals = models.PositiveSmallIntegerField(blank=True, null=True)
    score = models.FloatField(blank=True, null=True)
    final_sc_count = models.PositiveSmallIntegerField(blank=True, null=True)
    result = models.CharField(max_length=2, choices=GAME_RESULT, blank=True)
    year_eliminated = models.PositiveSmallIntegerField(blank=True, null=True, validators=[validate_year])

    class Meta:
        unique_together = ('tournament_name', 'game_name', 'player', 'power')

    def __unicode__(self):
        return _(u'%(player)s played %(power)s in %(game)s') % {'player': self.player,
                                                                'power': self.power,
                                                                'game': self.game_name}

