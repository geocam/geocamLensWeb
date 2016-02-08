# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls import url

from geocamUtil.FileUtil import importModuleByName

from django.conf import settings

views = importModuleByName(settings.GEOCAM_LENS_VIEW_MODULE).viewSingleton

urlpatterns = [
    # kml
    url(r'^kml/startSession.kml(?:\?[^/]*)?$', views.kmlStartSession,
     {'readOnly': True}, 'geocamLens_kmlStartSession'),
    url(r'^kml/([^/]+)/([^/]+)\.kml$', views.kmlGetSessionResponse,
     # google earth can't handle django challenge
     {'challenge': 'basic',
      'readOnly': True},
     'geocamLens_kmlGetSessionResponse'),
    url(r'^feed\.kml$', views.kmlFeed,
     {'readOnly': True},
     'geocamLens_kml'),

    # features
    url(r'^features.json', views.featuresJson, {'readOnly': True}),
    url(r'^featuresJson.js', views.featuresJsonJs, {'readOnly': True}),
    url(r'^galleryDebug.html', views.galleryDebug, {'readOnly': True}),

    url(r'^photo/(?P<imgId>[^/]+)/(?:[^/]+)?$', views.viewPhoto,
     {'readOnly': True}),

    url(r'^upload/$', views.uploadImageAuth),
    # alternate URL that accepts http basic authentication, used by newer versions of GeoCam Mobile
    url(r'^upload-m/$', views.uploadImageAuth,
     {'challenge': 'basic'}),

    url(r'^edit/photo/(?P<imgId>[^/]+)/$', views.editImageWrapper),
    url(r'^editWidget/photo/(?P<imgId>[^/]+)/$', views.editImage),

    # legacy URLs, compatible with the old version of GeoCam
    # Mobile *if* user authentication is off (not recommended!).
    url(r'^upload/(?P<userName>[^/]+)/$', views.uploadImage),

]
