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

from django.conf.urls import patterns, include, url
from django.contrib import admin

import tournament

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'visualiser.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^tournaments/', include('tournament.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^players/$', tournament.views.PlayerIndexView.as_view()),
    url(r'^players/(?P<pk>\d+)/$', tournament.views.PlayerDetailView.as_view(), name='player_detail'),
)
