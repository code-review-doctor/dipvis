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

from django.conf.urls import patterns, url, include

from tournament import views

urlpatterns = patterns('',
    url(r'^$', views.TourneyIndexView.as_view(), name='index'),
    url(r'^(?P<pk>\d+)/$', views.TourneyDetailView.as_view(), name='tournament_detail'),
    url(r'^(?P<tournament_id>\d+)/', include([
        url(r'^scores/$', views.tournament_scores, name='tournament_scores'),
        url(r'^enter_scores/$', views.round_scores, name='enter_scores'),
        url(r'^roll_call/$', views.roll_call, name='roll_call'),
        url(r'^current_round/$', views.tournament_round, name='tournament_round'),
        url(r'^news/$', views.tournament_news, name='tournament_news'),
        url(r'^background/$', views.tournament_background, name='tournament_background'),
        url(r'^rounds/$', views.round_index, name='round_index'),
        url(r'^rounds/(?P<round_num>\d+)/', include([
            url(r'^$', views.round_detail, name='round_detail'),
            url(r'^create_games/$', views.create_games, name='create_games'),
            url(r'^game_scores/$', views.game_scores, name='game_scores'),
            url(r'^games/$', views.game_index, name='game_index'),
        ])),
        url(r'^games/(?P<game_name>\w+)/', include([
            url(r'^$', views.game_detail, name='game_detail'),
            url(r'^sc_chart/$', views.game_sc_chart, name='game_sc_chart'),
            url(r'^enter_scs/$', views.sc_counts, name='enter_scs'),
            url(r'^news/$', views.game_news, name='game_news'),
            url(r'^background/$', views.game_background, name='game_background'),
            url(r'^draw_vote/$', views.draw_vote, name='draw_vote'),
        ])),
    ])),
)
