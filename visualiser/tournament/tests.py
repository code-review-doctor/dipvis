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

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from tournament.models import *

class TournamentModelTests(TestCase):
    def setUp(self):
        s1 = ScoringSystem.objects.create(name='s1')
        t1 = Tournament.objects.create(name='t1', start_date=timezone.now(), end_date=timezone.now())
        t2 = Tournament.objects.create(name='t2', start_date=timezone.now(), end_date=timezone.now())
        t3 = Tournament.objects.create(name='t3', start_date=timezone.now(), end_date=timezone.now())
        r11 = Round.objects.create(tournament=t1, number=1, scoring_system=s1, dias=True)
        r12 = Round.objects.create(tournament=t1, number=2, scoring_system=s1, dias=True)
        r13 = Round.objects.create(tournament=t1, number=3, scoring_system=s1, dias=True)
        r21 = Round.objects.create(tournament=t2, number=1, scoring_system=s1, dias=True)
        r22 = Round.objects.create(tournament=t2, number=2, scoring_system=s1, dias=True)
        r31 = Round.objects.create(tournament=t3, number=1, scoring_system=s1, dias=True)
        r32 = Round.objects.create(tournament=t3, number=2, scoring_system=s1, dias=True)
        g11 = Game.objects.create(name='g1', started_at=timezone.now(), the_round=r11)
        g12 = Game.objects.create(name='g2', started_at=timezone.now(), the_round=r11)
        g13 = Game.objects.create(name='g3', started_at=timezone.now(), the_round=r12, is_finished=True)
        g14 = Game.objects.create(name='g4', started_at=timezone.now(), the_round=r12)
        g15 = Game.objects.create(name='g5', started_at=timezone.now(), the_round=r13, is_finished=True)
        g16 = Game.objects.create(name='g6', started_at=timezone.now(), the_round=r13, is_finished=True)
        g21 = Game.objects.create(name='g1', started_at=timezone.now(), the_round=r21)
        g22 = Game.objects.create(name='g2', started_at=timezone.now(), the_round=r22)
        g31 = Game.objects.create(name='g1', started_at=timezone.now(), the_round=r31, is_finished=True)
        g32 = Game.objects.create(name='g2', started_at=timezone.now(), the_round=r32, is_finished=True)

    def test_validate_year_negative(self):
        self.assertRaises(ValidationError, validate_year, -1)

    def test_validate_year_1899(self):
        self.assertRaises(ValidationError, validate_year, 1899)

    def test_validate_sc_count_negative(self):
        self.assertRaises(ValidationError, validate_sc_count, -1)

    def test_validate_sc_count_35(self):
        self.assertRaises(ValidationError, validate_sc_count, 35)
    
    def test_round_is_finished_no_games_over(self):
        t = Tournament.objects.get(name='t1')
        r1 = t.round_set.get(number=1)
        self.assertEqual(r1.is_finished(), False)

    def test_round_is_finished_some_games_over(self):
        t = Tournament.objects.get(name='t1')
        r2 = t.round_set.get(number=2)
        self.assertEqual(r2.is_finished(), False)

    def test_round_is_finished_all_games_over(self):
        t = Tournament.objects.get(name='t1')
        r3 = t.round_set.get(number=3)
        self.assertEqual(r3.is_finished(), True)

    def test_tourney_is_finished_some_rounds_over(self):
        t = Tournament.objects.get(name='t1')
        self.assertEqual(t.is_finished(), False)

    def test_tourney_is_finished_no_rounds_over(self):
        t = Tournament.objects.get(name='t2')
        self.assertEqual(t.is_finished(), False)

    def test_tourney_is_finished_all_rounds_over(self):
        t = Tournament.objects.get(name='t3')
        self.assertEqual(t.is_finished(), True)

