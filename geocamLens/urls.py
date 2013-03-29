# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls.defaults import patterns

from geocamUtil.FileUtil import importModuleByName

from geocamLens import settings

views = importModuleByName(settings.GEOCAM_LENS_VIEW_MODULE).viewSingleton

urlpatterns = patterns(
    '',

    # kml
    (r'^kml/startSession.kml(?:\?[^/]*)?$', views.kmlStartSession,
     {'readOnly': True}, 'geocamLens_kmlStartSession'),
    (r'^kml/([^/]+)/([^/]+)\.kml$', views.kmlGetSessionResponse,
     # google earth can't handle django challenge
     {'challenge': 'basic',
      'readOnly': True},
     'geocamLens_kmlGetSessionResponse'),
    (r'^feed\.kml$', views.kmlFeed,
     {'readOnly': True},
     'geocamLens_kml'),

    # features
    (r'^features.json', views.featuresJson, {'readOnly': True}),
    (r'^featuresJson.js', views.featuresJsonJs, {'readOnly': True}),
    (r'^galleryDebug.html', views.galleryDebug, {'readOnly': True}),

    (r'^photo/(?P<imgId>[^/]+)/(?:[^/]+)?$', views.viewPhoto,
     {'readOnly': True}),

    (r'^upload/$', views.uploadImageAuth),
    # alternate URL that accepts http basic authentication, used by newer versions of GeoCam Mobile
    (r'^upload-m/$', views.uploadImageAuth,
     {'challenge': 'basic'}),

    (r'^edit/photo/(?P<imgId>[^/]+)/$', views.editImageWrapper),
    (r'^editWidget/photo/(?P<imgId>[^/]+)/$', views.editImage),

    # legacy URLs, compatible with the old version of GeoCam
    # Mobile *if* user authentication is off (not recommended!).
    (r'^upload/(?P<userName>[^/]+)/$', views.uploadImage),

    )
