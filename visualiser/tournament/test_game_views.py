# Diplomacy Tournament Visualiser
# Copyright (C) 2019 Chris Brand
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

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tournament.diplomacy import GameSet, GreatPower, SupplyCentre
from tournament.game_scoring import G_SCORING_SYSTEMS
from tournament.models import Tournament, Round, Game
from tournament.models import CentreCount, SupplyCentreOwnership
from tournament.models import R_SCORING_SYSTEMS, T_SCORING_SYSTEMS
from tournament.models import SPRING
from tournament.models import TournamentPlayer, RoundPlayer, GamePlayer
from tournament.players import Player

HOURS_8 = timedelta(hours=8)

class GameViewTests(TestCase):
    fixtures = ['game_sets.json']

    @classmethod
    def setUpTestData(cls):
        # Easy access to all the GreatPowers
        cls.austria = GreatPower.objects.get(abbreviation='A')
        cls.england = GreatPower.objects.get(abbreviation='E')
        cls.france = GreatPower.objects.get(abbreviation='F')
        cls.germany = GreatPower.objects.get(abbreviation='G')
        cls.italy = GreatPower.objects.get(abbreviation='I')
        cls.russia = GreatPower.objects.get(abbreviation='R')
        cls.turkey = GreatPower.objects.get(abbreviation='T')

        # A superuser
        cls.USERNAME1 = 'superuser'
        cls.PWORD1 = 'l33tPw0rd'
        u1 = User.objects.create_user(username=cls.USERNAME1,
                                      password=cls.PWORD1,
                                      is_superuser=True)
        u1.save()

        now = timezone.now()
        # Published Tournament so it's visible to all
        # This one has Secret draw votes
        cls.t1 = Tournament.objects.create(name='t1',
                                           start_date=now,
                                           end_date=now,
                                           round_scoring_system=R_SCORING_SYSTEMS[0].name,
                                           tournament_scoring_system=T_SCORING_SYSTEMS[0].name,
                                           draw_secrecy=Tournament.SECRET,
                                           is_published=True)
        # One DIAS round, with 1 game
        cls.r1 = Round.objects.create(tournament=cls.t1,
                                      scoring_system=G_SCORING_SYSTEMS[0].name,
                                      dias=True,
                                      start=cls.t1.start_date)
        cls.g1 = Game.objects.create(name='Game1',
                                     started_at=cls.r1.start,
                                     the_round=cls.r1,
                                     the_set=GameSet.objects.first())
        # And one non-DIAS round, with 1 game
        r = Round.objects.create(tournament=cls.t1,
                                 scoring_system=G_SCORING_SYSTEMS[0].name,
                                 dias=False,
                                 start=cls.t1.start_date + HOURS_8)
        cls.g2 = Game.objects.create(name='Game2',
                                     started_at=r.start,
                                     the_round=r,
                                     the_set=GameSet.objects.first())
        # Published Tournament so it's visible to all
        # This one has Count draw votes
        cls.t2 = Tournament.objects.create(name='t2',
                                           start_date=now,
                                           end_date=now,
                                           round_scoring_system=R_SCORING_SYSTEMS[0].name,
                                           tournament_scoring_system=T_SCORING_SYSTEMS[0].name,
                                           draw_secrecy=Tournament.COUNTS,
                                           is_published=True)
        # One DIAS round, with 1 game
        r = Round.objects.create(tournament=cls.t2,
                                 scoring_system=G_SCORING_SYSTEMS[0].name,
                                 dias=True,
                                 start=cls.t2.start_date)
        cls.g3 = Game.objects.create(name='Game3',
                                     started_at=r.start,
                                     the_round=r,
                                     the_set=GameSet.objects.first())
        # And one non-DIAS round, with 1 game
        r = Round.objects.create(tournament=cls.t2,
                                 scoring_system=G_SCORING_SYSTEMS[0].name,
                                 dias=False,
                                 start=cls.t2.start_date + HOURS_8)
        cls.g4 = Game.objects.create(name='Game4',
                                     started_at=r.start,
                                     the_round=r,
                                     the_set=GameSet.objects.first())

        # Add SO ownerships for Game1, but skip 1901
        #for sco in cls.g1.supplycentreownership_set.filter(year=1900):
        #    SupplyCentreOwnership.objects.create(game=sco.game, year=1902, sc=sco.sc, owner=sco.owner)
        #cls.g1.create_or_update_sc_counts_from_ownerships(1902)
        #print(len(cls.g1.years_played()))
        #print(cls.g1.years_played()[0])
        #print(cls.g1.years_played()[-1])

        # Default SC ownerships, used to test post of sc ownerships
        cls.default_owners = {'Ankara': cls.turkey,
                              'Belgium': cls.france,
                              'Berlin': cls.germany,
                              'Brest': cls.france,
                              'Budapest': cls.austria,
                              'Bulgaria': cls.turkey,
                              'Constantinople': cls.turkey,
                              'Denmark': cls.germany,
                              'Edinburgh': cls.england,
                              'Greece': cls.austria,
                              'Holland': cls.germany,
                              'Kiel': cls.germany,
                              'Liverpool': cls.england,
                              'London': cls.england,
                              'Marseilles': cls.france,
                              'Moscow': cls.russia,
                              'Munich': cls.germany,
                              'Naples': cls.italy,
                              'Norway': cls.england,
                              'Paris': cls.france,
                              'Portugal': cls.france,
                              'Rome': cls.italy,
                              'Rumania': cls.russia,
                              'Serbia': cls.austria,
                              'Sevastapol': cls.russia,
                              'Smyrna': cls.turkey,
                              'Spain': cls.france,
                              'St.Petersburg': cls.russia,
                              'Sweden': cls.russia,
                              'Trieste': cls.austria,
                              'Tunis': cls.italy,
                              'Venice': cls.italy,
                              'Vienna': cls.austria,
                              'Warsaw': cls.russia}

    def test_detail(self):
        response = self.client.get(reverse('game_detail', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_detail_non_existant_game(self):
        response = self.client.get(reverse('game_detail', args=(self.t1.pk, 'Game42')))
        self.assertEqual(response.status_code, 404)

    def test_detail_no_aar_link(self):
        # Add a GamePlayer without an AAR
        p = Player.objects.create(first_name='Thor', last_name='Odinson')
        TournamentPlayer.objects.create(tournament=self.t1, player=p)
        RoundPlayer.objects.create(the_round=self.r1, player=p)
        GamePlayer.objects.create(game=self.g1, player=p, power=self.italy)
        response = self.client.get(reverse('game_detail', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'After Action Report', response.content)
        # Clean up
        p.delete()

    def test_detail_aar_link(self):
        # Add a GamePlayer with an AAR
        p = Player.objects.create(first_name='Thor', last_name='Odinson')
        TournamentPlayer.objects.create(tournament=self.t1, player=p)
        RoundPlayer.objects.create(the_round=self.r1, player=p)
        GamePlayer.objects.create(game=self.g1,
                                  player=p,
                                  power=self.italy,
                                  after_action_report='I died')
        response = self.client.get(reverse('game_detail', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'After Action Report', response.content)
        # Clean up
        p.delete()

    def test_aar(self):
        # Add a GamePlayer with an AAR
        p = Player.objects.create(first_name='Thor', last_name='Odinson')
        TournamentPlayer.objects.create(tournament=self.t1, player=p)
        RoundPlayer.objects.create(the_round=self.r1, player=p)
        GamePlayer.objects.create(game=self.g1, player=p, after_action_report='I died')
        response = self.client.get(reverse('aar', args=(self.t1.pk, self.g1.name, p.pk)))
        self.assertEqual(response.status_code, 200)
        # Clean up
        p.delete()

    def test_non_existant_aar(self):
        # Add a GamePlayer without an AAR
        p = Player.objects.create(first_name='Thor', last_name='Odinson')
        TournamentPlayer.objects.create(tournament=self.t1, player=p)
        RoundPlayer.objects.create(the_round=self.r1, player=p)
        GamePlayer.objects.create(game=self.g1, player=p)
        response = self.client.get(reverse('aar', args=(self.t1.pk, self.g1.name, p.pk)))
        self.assertEqual(response.status_code, 404)
        # Clean up
        p.delete()

    def test_aar_non_player(self):
        # Try to retrieve an AAR from somebody who didn't play the Game
        p = Player.objects.create(first_name='Thor', last_name='Odinson')
        response = self.client.get(reverse('aar', args=(self.t1.pk, self.g1.name, p.pk)))
        self.assertEqual(response.status_code, 404)
        # Clean up
        p.delete()

    def test_sc_chart(self):
        response = self.client.get(reverse('game_sc_chart', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_sc_chart_refresh(self):
        response = self.client.get(reverse('game_sc_chart_refresh', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_enter_scs_not_logged_in(self):
        response = self.client.get(reverse('enter_scs', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 302)

    def test_enter_scs(self):
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        response = self.client.get(reverse('enter_scs', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_post_enter_scs(self):
        self.assertFalse(self.g1.is_finished)
        counts = {1907: {self.austria: 5,
                         self.england: 5,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 5,
                         self.russia: 4,
                         self.turkey: 5},
                  1909: {self.austria: 6,
                         self.england: 6,
                         self.france: 4,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 9,
                         self.turkey: 0},
                  1910: {self.austria: 7,
                         self.england: 7,
                         self.france: 4,
                         self.germany: 4,
                         self.italy: 4,
                         self.russia: 8,
                         self.turkey: 0},
                  1912: {self.austria: 9,
                         self.england: 9,
                         self.france: 3,
                         self.germany: 3,
                         self.italy: 3,
                         self.russia: 7,
                         self.turkey: 0}}
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'scs-TOTAL_FORMS': '4',
                'scs-INITIAL_FORMS': '0',
                'scs-MAX_NUM_FORMS': '1000',
                'scs-MIN_NUM_FORMS': '0',
                'death-%s' % str(self.austria): '',
                'death-%s' % str(self.england): '',
                'death-%s' % str(self.france): '',
                'death-%s' % str(self.germany): '',
                'death-%s' % str(self.italy): '',
                'death-%s' % str(self.russia): '',
                'death-%s' % str(self.turkey): '1908',
                'end-is_finished': 'ok'}
        for n, (y, dots) in enumerate(counts.items()):
            data['scs-%d-year' % n] = str(y)
            for p, c in dots.items():
                data['scs-%d-%s' % (n, str(p))] = str(c)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_scs', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the SC Chart page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('game_sc_chart', args=(self.t1.pk, self.g1.name)))
        # And the CentreCounts should be added
        for year, dots in counts.items():
            with self.subTest(year=year):
                ccs = CentreCount.objects.filter(game=self.g1, year=year)
                self.assertEqual(ccs.count(), 7)
                for p, c in dots.items():
                    with self.subTest(year=year, power=p):
                        self.assertEqual(ccs.get(power=p).count, c)
        # Turkey should be eliminated in 1908
        cc = CentreCount.objects.get(game=self.g1, year=1909, power=self.turkey)
        self.assertEqual(cc.count, 0)
        # Game should now be finished
        self.g1.refresh_from_db()
        self.assertTrue(self.g1.is_finished)
        # Clean up
        for year in counts.keys():
            ccs = CentreCount.objects.filter(game=self.g1, year=year)
            ccs.delete()
        cc.delete()
        self.g1.is_finished = False
        self.g1.save()

    def test_post_enter_scs_modify(self):
        self.assertEqual(CentreCount.objects.filter(game=self.g1, year=1907).count(), 0)
        self.assertEqual(CentreCount.objects.filter(game=self.g1, year=1908).count(), 0)
        # Add some pre-existing CentreCounts for Game1, including an elimination
        CentreCount.objects.create(game=self.g1, year=1907, power=self.austria, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.england, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.france, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.germany, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.italy, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.russia, count=5)
        CentreCount.objects.create(game=self.g1, year=1907, power=self.turkey, count=4)

        CentreCount.objects.create(game=self.g1, year=1908, power=self.austria, count=6)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.england, count=0)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.france, count=6)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.germany, count=6)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.italy, count=6)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.russia, count=4)
        CentreCount.objects.create(game=self.g1, year=1908, power=self.turkey, count=6)
        counts = {1901: {self.austria: 5,
                         self.england: 4,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 5,
                         self.turkey: 4},
                  1907: {self.austria: 5,
                         self.england: 5,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 5,
                         self.russia: 5,
                         self.turkey: 4},
                  1908: {self.austria: 5,
                         self.england: 0,
                         self.france: 6,
                         self.germany: 6,
                         self.italy: 7,
                         self.russia: 4,
                         self.turkey: 6}}
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'scs-TOTAL_FORMS': '6',
                'scs-INITIAL_FORMS': '2',
                'scs-MAX_NUM_FORMS': '1000',
                'scs-MIN_NUM_FORMS': '0',
                'death-%s' % str(self.austria): '',
                'death-%s' % str(self.england): '1908',
                'death-%s' % str(self.france): '',
                'death-%s' % str(self.germany): '',
                'death-%s' % str(self.italy): '',
                'death-%s' % str(self.russia): '',
                'death-%s' % str(self.turkey): ''}
        for n, (y, dots) in enumerate(counts.items()):
            data['scs-%d-year' % n] = str(y)
            for p, c in dots.items():
                data['scs-%d-%s' % (n, str(p))] = str(c)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_scs', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the SC Chart page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('game_sc_chart', args=(self.t1.pk, self.g1.name)))
        # And the CentreCounts should be updated
        for year, dots in counts.items():
            with self.subTest(year=year):
                ccs = CentreCount.objects.filter(game=self.g1, year=year)
                self.assertEqual(ccs.count(), 7)
                for p, c in dots.items():
                    with self.subTest(year=year, power=p):
                        self.assertEqual(ccs.get(power=p).count, c)
        # Clean up
        for year in counts.keys():
            ccs = CentreCount.objects.filter(game=self.g1, year=year)
            ccs.delete()

    def test_post_enter_scs_too_many(self):
        counts = {1907: {self.austria: 5,
                         self.england: 5,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 5,
                         self.russia: 4,
                         self.turkey: 5},
                  1909: {self.austria: 6,
                         self.england: 6,
                         self.france: 4,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 5,
                         self.turkey: 4},
                  1910: {self.austria: 7,
                         self.england: 7,
                         self.france: 4,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 4,
                         self.turkey: 4},
                  1911: {self.austria: 8,
                         self.england: 8,
                         self.france: 3,
                         self.germany: 4,
                         self.italy: 3,
                         self.russia: 4,
                         self.turkey: 4},
                  1912: {self.austria: 9,
                         self.england: 9,
                         self.france: 3,
                         self.germany: 3,
                         self.italy: 3,
                         self.russia: 3,
                         self.turkey: 4}}
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'scs-TOTAL_FORMS': '4',
                'scs-INITIAL_FORMS': '0',
                'scs-MAX_NUM_FORMS': '1000',
                'scs-MIN_NUM_FORMS': '0',
                'death-%s' % str(self.austria): '',
                'death-%s' % str(self.england): '',
                'death-%s' % str(self.france): '',
                'death-%s' % str(self.germany): '',
                'death-%s' % str(self.italy): '',
                'death-%s' % str(self.russia): '',
                'death-%s' % str(self.turkey): ''}
        for n, (y, dots) in enumerate(counts.items()):
            data['scs-%d-year' % n] = str(y)
            for p, c in dots.items():
                data['scs-%d-%s' % (n, str(p))] = str(c)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_scs', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # Should get an error for the year with too many total SCs
        self.assertEqual(response.status_code, 200)
        # One form-wide error in the 1910 form, because the SC total is 35
        self.assertEqual(response.context['formset'].total_error_count(), 1)

    def test_post_enter_scs_zombie(self):
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1907).exists())
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1908).exists())
        counts = {1907: {self.austria: 5,
                         self.england: 5,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 5,
                         self.russia: 4,
                         self.turkey: 5},
                  1908: {self.austria: 6,
                         self.england: 6,
                         self.france: 4,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 5,
                         self.turkey: 4}}
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'scs-TOTAL_FORMS': '4',
                'scs-INITIAL_FORMS': '0',
                'scs-MAX_NUM_FORMS': '1000',
                'scs-MIN_NUM_FORMS': '0',
                'death-%s' % str(self.austria): '',
                'death-%s' % str(self.england): '',
                'death-%s' % str(self.france): '',
                'death-%s' % str(self.germany): '',
                'death-%s' % str(self.italy): '1908',
                'death-%s' % str(self.russia): '',
                'death-%s' % str(self.turkey): ''}
        for n, (y, dots) in enumerate(counts.items()):
            data['scs-%d-year' % n] = str(y)
            for p, c in dots.items():
                data['scs-%d-%s' % (n, str(p))] = str(c)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_scs', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # Should get an error for the year with too many total SCs
        self.assertEqual(response.status_code, 200)
        # Italy died in 1908, but also had 4 SCs
        self.assertIn(str(self.italy), response.context['death_form'].errors.keys())
        # No new CentreCounts should have been created
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1907).exists())
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1908).exists())

    def test_post_enter_scs_zombie_2(self):
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1907).exists())
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1908).exists())
        counts = {1907: {self.austria: 5,
                         self.england: 5,
                         self.france: 5,
                         self.germany: 5,
                         self.italy: 5,
                         self.russia: 0,
                         self.turkey: 9},
                  1908: {self.austria: 6,
                         self.england: 6,
                         self.france: 4,
                         self.germany: 5,
                         self.italy: 4,
                         self.russia: 1,
                         self.turkey: 8}}
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'scs-TOTAL_FORMS': '4',
                'scs-INITIAL_FORMS': '0',
                'scs-MAX_NUM_FORMS': '1000',
                'scs-MIN_NUM_FORMS': '0',
                'death-%s' % str(self.austria): '',
                'death-%s' % str(self.england): '',
                'death-%s' % str(self.france): '',
                'death-%s' % str(self.germany): '',
                'death-%s' % str(self.italy): '',
                'death-%s' % str(self.russia): '',
                'death-%s' % str(self.turkey): ''}
        for n, (y, dots) in enumerate(counts.items()):
            data['scs-%d-year' % n] = str(y)
            for p, c in dots.items():
                data['scs-%d-%s' % (n, str(p))] = str(c)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_scs', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # Should get an error for Russia recovering from an elimination
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['formset'].total_error_count(), 1)
        # No new CentreCounts should have been created
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1907).exists())
        self.assertFalse(CentreCount.objects.filter(game=self.g1, year=1908).exists())

    def test_sc_owners(self):
        response = self.client.get(reverse('game_sc_owners', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_sc_owners_refresh(self):
        response = self.client.get(reverse('game_sc_owners_refresh', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_enter_sc_owners_not_logged_in(self):
        response = self.client.get(reverse('enter_sc_owners', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 302)

    def test_enter_sc_owners(self):
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        response = self.client.get(reverse('enter_sc_owners', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_post_enter_sc_owners(self):
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 0)
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'form-TOTAL_FORMS': '5',
                'form-INITIAL_FORMS': '1',
                'form-MAX_NUM_FORMS': '1000',
                'form-MIN_NUM_FORMS': '0'}
        for n, year in enumerate([1907]):
            data['form-%d-year' % n] = str(year)
            for sc, p in self.default_owners.items():
                data['form-%d-%s' % (n, sc)] = str(p.id)
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_sc_owners', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the SC Owners page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('game_sc_owners', args=(self.t1.pk, self.g1.name)))
        # TODO And the appropriate SupplyCentreOwnerships should have been created
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 34)
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 7)
        # Clean up
        self.g1.supplycentreownership_set.filter(year=1907).delete()
        self.g1.centrecount_set.filter(year=1907).delete()

    def test_post_enter_sc_owners_modify(self):
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 0)
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 0)
        # Add 1907 SupplyCentreOwnerships
        # Serbia and Rumania neutral, remainder as listed above
        for sc, p in self.default_owners.items():
            if (sc != 'Serbia') and (sc != 'Rumania'):
                SupplyCentreOwnership.objects.create(game=self.g1,
                                                     sc=SupplyCentre.objects.get(name=sc),
                                                     owner=p,
                                                     year=1907)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'form-TOTAL_FORMS': '5',
                'form-INITIAL_FORMS': '1',
                'form-MAX_NUM_FORMS': '1000',
                'form-MIN_NUM_FORMS': '0'}
        for n, year in enumerate([1907]):
            data['form-%d-year' % n] = str(year)
            for sc, p in self.default_owners.items():
                data['form-%d-%s' % (n, sc)] = str(p.id)
        # Include a blank row
        n += 1
        data['form-%d-year' % n] = ''
        for sc, p in self.default_owners.items():
            data['form-%d-%s' % (n, sc)] = ''
        # Now change the ownership of Trieste
        data['form-0-Trieste'] = str(self.italy.id)
        # And make Greece and Rumania neutral
        data['form-0-Greece'] = ''
        data['form-0-Rumania'] = ''
        # Serbia will be changed from neutral to Austrian
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_sc_owners', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the SC Owners page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('game_sc_owners', args=(self.t1.pk, self.g1.name)))
        # And the appropriate SupplyCentreOwnerships should have been updated/deleted
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 32)
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 7)
        sc=SupplyCentre.objects.get(name='Serbia')
        self.assertEqual(self.g1.supplycentreownership_set.get(year=1907, sc=sc).owner, self.austria)
        sc=SupplyCentre.objects.get(name='Trieste')
        self.assertEqual(self.g1.supplycentreownership_set.get(year=1907, sc=sc).owner, self.italy)
        sc=SupplyCentre.objects.get(name='Greece')
        self.assertFalse(self.g1.supplycentreownership_set.filter(year=1907, sc=sc).exists())
        sc=SupplyCentre.objects.get(name='Rumania')
        self.assertFalse(self.g1.supplycentreownership_set.filter(year=1907, sc=sc).exists())
        # Clean up
        self.g1.supplycentreownership_set.filter(year=1907).delete()
        self.g1.centrecount_set.filter(year=1907).delete()

    def test_post_enter_sc_owners_all_neutral(self):
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 0)
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 0)
        # Create some CentreCounts for 1907
        CentreCount.objects.create(game=self.g1,
                                   power=self.austria,
                                   year=1907,
                                   count=6)
        CentreCount.objects.create(game=self.g1,
                                   power=self.italy,
                                   year=1907,
                                   count=16)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = {'form-TOTAL_FORMS': '5',
                'form-INITIAL_FORMS': '1',
                'form-MAX_NUM_FORMS': '1000',
                'form-MIN_NUM_FORMS': '0'}
        for n, year in enumerate([1907]):
            data['form-%d-year' % n] = str(year)
            for sc, p in self.default_owners.items():
                data['form-%d-%s' % (n, sc)] = ''
        data_enc = urlencode(data)
        response = self.client.post(reverse('enter_sc_owners', args=(self.t1.pk, self.g1.name)),
                                    data_enc,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the SC Owners page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('game_sc_owners', args=(self.t1.pk, self.g1.name)))
        # There should still be no SupplyCentreOwnerships
        self.assertEqual(self.g1.supplycentreownership_set.filter(year=1907).count(), 0)
        # and the two CentreCounts we added at the start
        self.assertEqual(self.g1.centrecount_set.filter(year=1907).count(), 2)
        # Clean up
        self.g1.centrecount_set.filter(year=1907).delete()

    def test_current_game_image(self):
        response = self.client.get(reverse('current_game_image', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_game_image(self):
        response = self.client.get(reverse('game_image', args=(self.t1.pk, self.g1.name, 'S1901M')))
        self.assertEqual(response.status_code, 200)

    def test_timelapse(self):
        response = self.client.get(reverse('game_timelapse', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_game_image_seq(self):
        response = self.client.get(reverse('game_image_seq', args=(self.t1.pk, self.g1.name, 'S1901M')))
        self.assertEqual(response.status_code, 200)

    def test_add_position_not_logged_in(self):
        response = self.client.get(reverse('add_game_image', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 302)

    def test_add_position(self):
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        response = self.client.get(reverse('add_game_image', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_news(self):
        response = self.client.get(reverse('game_news', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_news_ticker(self):
        response = self.client.get(reverse('game_news_ticker', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_background(self):
        response = self.client.get(reverse('game_background', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_background_ticker(self):
        response = self.client.get(reverse('game_background_ticker', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_ticker(self):
        response = self.client.get(reverse('game_ticker', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_draw_vote_not_logged_in(self):
        response = self.client.get(reverse('draw_vote', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 302)

    def test_post_secret_dias_draw_vote(self):
        self.assertEqual(self.g1.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'passed': False,
                          'proposer': str(self.austria)})
        response = self.client.post(reverse('draw_vote', args=(self.t1.pk, self.g1.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g1.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g1.drawproposal_set.count(), 1)
        dp = self.g1.drawproposal_set.get()
        self.assertEqual(dp.game, self.g1)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertFalse(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 7)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                self.assertIn(power, powers)
        # Draws in this tournament are secret
        self.assertIsNone(dp.votes_in_favour)
        self.assertFalse(self.g1.is_finished)
        # Clean up
        dp.delete()

    def test_post_secret_non_dias_draw_vote(self):
        self.assertEqual(self.g2.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'passed': False,
                          'powers': [str(self.england), str(self.turkey)],
                          'proposer': str(self.england)}, True)
        response = self.client.post(reverse('draw_vote', args=(self.t1.pk, self.g2.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g2.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g2.drawproposal_set.count(), 1)
        dp = self.g2.drawproposal_set.get()
        self.assertEqual(dp.game, self.g2)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertFalse(dp.passed)
        self.assertEqual(dp.proposer, self.england)
        # Draws in this round are non-DIAS
        self.assertEqual(dp.draw_size(), 2)
        powers = dp.powers()
        for power in [self.england, self.turkey]:
            with self.subTest(power=power):
                self.assertIn(power, powers)
        for power in [self.austria, self.france, self.germany, self.italy, self.russia]:
            with self.subTest(power=power):
                self.assertNotIn(power, powers)
        # Draws in this tournament are secret
        self.assertIsNone(dp.votes_in_favour)
        self.assertFalse(self.g2.is_finished)
        # Clean up
        dp.delete()

    def test_post_secret_dias_draw_vote_passed(self):
        self.assertEqual(self.g1.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1903',
                          'season': SPRING,
                          'passed': True,
                          'proposer': str(self.austria)})
        response = self.client.post(reverse('draw_vote', args=(self.t1.pk, self.g1.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g1.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g1.drawproposal_set.count(), 1)
        dp = self.g1.drawproposal_set.get()
        self.assertEqual(dp.game, self.g1)
        self.assertEqual(dp.year, 1903)
        self.assertEqual(dp.season, SPRING)
        self.assertTrue(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 7)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                self.assertIn(power, powers)
        # Draws in this tournament are secret
        self.assertIsNone(dp.votes_in_favour)
        self.g1.refresh_from_db()
        self.assertTrue(self.g1.is_finished)
        # Clean up
        dp.delete()
        self.g1.is_finished = False
        self.g1.save()
        self.g1.refresh_from_db()

    def test_post_secret_non_dias_draw_vote_passed(self):
        self.assertEqual(self.g2.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'passed': True,
                          'powers': [str(self.england), str(self.turkey)],
                          'proposer': str(self.austria)}, True)
        response = self.client.post(reverse('draw_vote', args=(self.t1.pk, self.g2.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g2.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g2.drawproposal_set.count(), 1)
        dp = self.g2.drawproposal_set.get()
        self.assertEqual(dp.game, self.g2)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertTrue(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are non-DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 2)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                if power in [self.england, self.turkey]:
                    self.assertIn(power, powers)
                else:
                    self.assertNotIn(power, powers)
        # Draws in this tournament are secret
        self.assertIsNone(dp.votes_in_favour)
        self.g2.refresh_from_db()
        self.assertTrue(self.g2.is_finished)
        # Clean up
        dp.delete()
        self.g2.is_finished = False
        self.g2.save()
        self.g2.refresh_from_db()

    def test_post_counts_dias_draw_vote(self):
        self.assertEqual(self.g3.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'votes_in_favour': 4,
                          'proposer': str(self.austria)})
        response = self.client.post(reverse('draw_vote', args=(self.t2.pk, self.g3.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g3.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g3.drawproposal_set.count(), 1)
        dp = self.g3.drawproposal_set.get()
        self.assertEqual(dp.game, self.g3)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertFalse(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 7)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                self.assertIn(power, powers)
        # Draws in this tournament reveal the for/against counts
        self.assertEqual(dp.votes_in_favour, 4)
        self.assertFalse(self.g3.is_finished)
        # Clean up
        dp.delete()

    def test_post_counts_non_dias_draw_vote(self):
        self.assertEqual(self.g4.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'powers': [str(self.england), str(self.turkey)],
                          'votes_in_favour': 4,
                          'proposer': str(self.england)}, True)
        response = self.client.post(reverse('draw_vote', args=(self.t2.pk, self.g4.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g4.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g4.drawproposal_set.count(), 1)
        dp = self.g4.drawproposal_set.get()
        self.assertEqual(dp.game, self.g4)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertFalse(dp.passed)
        self.assertEqual(dp.proposer, self.england)
        # Draws in this round are non-DIAS
        self.assertEqual(dp.draw_size(), 2)
        powers = dp.powers()
        for power in [self.england, self.turkey]:
            with self.subTest(power=power):
                self.assertIn(power, powers)
        for power in [self.austria, self.france, self.germany, self.italy, self.russia]:
            with self.subTest(power=power):
                self.assertNotIn(power, powers)
        # Draws in this tournament reveal the for/against counts
        self.assertEqual(dp.votes_in_favour, 4)
        self.assertFalse(self.g4.is_finished)
        # Clean up
        dp.delete()

    def test_post_counts_dias_draw_vote_passed(self):
        self.assertEqual(self.g3.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'votes_in_favour': 7,
                          'proposer': str(self.austria)})
        response = self.client.post(reverse('draw_vote', args=(self.t2.pk, self.g3.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g3.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g3.drawproposal_set.count(), 1)
        dp = self.g3.drawproposal_set.get()
        self.assertEqual(dp.game, self.g3)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertTrue(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 7)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                self.assertIn(power, powers)
        # Draws in this tournament reveal the for/against counts
        self.assertEqual(dp.votes_in_favour, 7)
        self.g3.refresh_from_db()
        self.assertTrue(self.g3.is_finished)
        # Clean up
        dp.delete()
        self.g3.is_finished = False
        self.g3.save()
        self.g3.refresh_from_db()

    def test_post_counts_non_dias_draw_vote_passed(self):
        self.assertEqual(self.g4.drawproposal_set.count(), 0)
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        data = urlencode({'year': '1902',
                          'season': SPRING,
                          'powers': [str(self.england), str(self.turkey)],
                          'votes_in_favour': 7,
                          'proposer': str(self.austria)}, True)
        response = self.client.post(reverse('draw_vote', args=(self.t2.pk, self.g4.name)),
                                    data,
                                    content_type='application/x-www-form-urlencoded')
        # It should redirect to the Game page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.g4.get_absolute_url())
        # And the DrawProposal should be added
        self.assertEqual(self.g4.drawproposal_set.count(), 1)
        dp = self.g4.drawproposal_set.get()
        self.assertEqual(dp.game, self.g4)
        self.assertEqual(dp.year, 1902)
        self.assertEqual(dp.season, SPRING)
        self.assertTrue(dp.passed)
        self.assertEqual(dp.proposer, self.austria)
        # Draws in this round are non-DIAS, and all powers are still alive
        self.assertEqual(dp.draw_size(), 2)
        powers = dp.powers()
        for power in GreatPower.objects.all():
            with self.subTest(power=power):
                if power in [self.england, self.turkey]:
                    self.assertIn(power, powers)
                else:
                    self.assertNotIn(power, powers)
        # Draws in this tournament reveal the for/against counts
        self.assertEqual(dp.votes_in_favour, 7)
        self.g4.refresh_from_db()
        self.assertTrue(self.g4.is_finished)
        # Clean up
        dp.delete()
        self.g4.is_finished = False
        self.g4.save()
        self.g4.refresh_from_db()

    def test_draw_vote(self):
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        response = self.client.get(reverse('draw_vote', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    # TODO check initial value for year and season in draw vote page with and without game images

    # TODO check errors from DrawProposal.clean() get displayed
    # - Second passed DrawProposal for one game
    # - Passed DrawProposal with SC counts afterwards
    # - Dead power in non-DIAS DP

    # TODO what about a DrawProposal for a game that was won outright?

    def test_views(self):
        response = self.client.get(reverse('game_views', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_overview(self):
        response = self.client.get(reverse('game_overview', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_overview2(self):
        response = self.client.get(reverse('game_overview_2', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_overview3(self):
        response = self.client.get(reverse('game_overview_3', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)

    def test_scrape_backstabbr_not_logged_in(self):
        response = self.client.get(reverse('enter_scs', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 302)

    def test_scrape_backstabbr_no_url(self):
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        self.assertEqual(len(self.g1.notes), 0)
        response = self.client.get(reverse('scrape_backstabbr', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 404)

    def test_scrape_backstabbr_success(self):
        self.assertEqual(len(self.g1.notes), 0)
        self.assertEqual(self.g1.centrecount_set.count(), 7)
        # Give g1 a backstabbr URL
        self.g1.notes = 'https://www.backstabbr.com/game/4917371326693376'
        self.g1.save()
        self.client.login(username=self.USERNAME1, password=self.PWORD1)
        response = self.client.get(reverse('scrape_backstabbr', args=(self.t1.pk, self.g1.name)))
        self.assertEqual(response.status_code, 200)
        # TODO Check the information displayed on the page
        self.assertIn(b'1912', response.content)
        # We should have added CentreCounts and SupplyCentreOwnerships for 1912
        ccs = self.g1.centrecount_set.filter(year=1912)
        self.assertEqual(len(ccs), 7)
        scos = self.g1.supplycentreownership_set.filter(year=1912)
        self.assertEqual(len(scos), 34)
        # Clean up
        self.g1.notes = ''
        ccs.delete()
        scos.delete()
        self.g1.save()
        self.g1.refresh_from_db()
