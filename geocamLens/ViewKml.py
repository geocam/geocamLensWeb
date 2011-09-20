# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import urllib
import datetime
import sys

from django.core import urlresolvers

from geocamUtil import KmlUtil

from geocamLens.models import GoogleEarthSession
from geocamLens import settings

CACHED_CSS = None


class BogusRequest:
    def build_absolute_uri(self, text):
        return text


class ViewKml(object):
    search = None  # override in derived classes

    def kmlGetStartSessionKml(self, request, sessionId):
        urlPath = urlresolvers.reverse('geocamLens_kmlGetSessionResponse',
                                       args=[sessionId, 'initial'])
        absUrl = request.build_absolute_uri(urlPath)
        if settings.GEOCAM_LENS_KML_FLY_TO_VIEW:
            flyToView = '<flyToView>1</flyToView>'
        else:
            flyToView = ''
        return ("""
<NetworkLink>
  <name>%(GEOCAM_CORE_SITE_TITLE)s</name>
  <Link>
    <href>%(absUrl)s</href>
  </Link>
  %(flyToView)s
</NetworkLink>
""" % dict(GEOCAM_CORE_SITE_TITLE=settings.GEOCAM_CORE_SITE_TITLE,
           absUrl=absUrl,
           flyToView=flyToView))

    def kmlStartSession(self, request):
        searchQuery = request.REQUEST.get('q', None)
        sessionId = GoogleEarthSession.getSessionId(searchQuery)
        print >> sys.stderr, "ViewKml: started session %s" % sessionId
        return KmlUtil.wrapKmlDjango(self.kmlGetStartSessionKml(request, sessionId))

    def kmlGetAllFeaturesFolder(self, request, searchQuery, newUtime):
        allFeatures = self.search.getAllFeatures()
        features = self.search.searchFeatures(allFeatures, searchQuery)
        if 0:
            # FIX: update models so this filtering statement can work
            features = features.filter(mtime__lte=newUtime,
                                       deleted=False)
        featuresKml = '\n'.join([f.getKml(request) for f in features])
        return ("""
<Folder id="allFeatures">
  <name>All features</name>
  %s
</Folder>
""" % featuresKml)

    def kmlGetInitialKml(self, request, sessionId):
        newUtime = datetime.datetime.now()
        session, _created = GoogleEarthSession.objects.get_or_create(sessionId=sessionId,
                                                                     defaults=dict(utime=newUtime))
        session.utime = newUtime
        session.save()

        allFeaturesFolder = self.kmlGetAllFeaturesFolder(request,
                                                         session.getSearchQuery(),
                                                         newUtime)
        global CACHED_CSS
        if not CACHED_CSS:
            cssPath = '%sgeocamCore/css/share.css' % settings.MEDIA_ROOT
            CACHED_CSS = file(cssPath, 'r').read()
        result = ("""
<Document id="allFeatures">
  <name>%(GEOCAM_CORE_SITE_TITLE)s</name>
  <Style id="shareCss">
    <BalloonStyle>
      <text><![CDATA[
        <style type="text/css">
          %(CACHED_CSS)s
        </style>
        $[description]
      ]]></text>
    </BalloonStyle>
  </Style>
""" % dict(GEOCAM_CORE_SITE_TITLE=settings.GEOCAM_CORE_SITE_TITLE,
           CACHED_CSS=CACHED_CSS))
        if 0:
            quotedId = urllib.quote_plus(sessionId)
            updateUrl = request.build_absolute_uri('%skml/%s/update.kml' % (settings.SCRIPT_NAME, quotedId))
            result += ("""
  <NetworkLink>
    <name>Update</name>
    <Link>
      <href>%(updateUrl)s</href>
      <refreshMode>onInterval</refreshMode>
      <refreshInterval>30</refreshInterval>
    </Link>
  </NetworkLink>
""" % dict(updateUrl=updateUrl))

        result += ("""
  %(allFeaturesFolder)s

</Document>
""" % dict(allFeaturesFolder=allFeaturesFolder))
        return result

    def kmlGetUpdateKml(self, request, sessionId):
        # FIX: implement me -- can use old version of geocam for reference
        return ''

    def kmlGetSessionResponse(self, request, quotedId, method):
        sessionId = urllib.unquote_plus(quotedId)
        #print 'sessionId:', sessionId
        #print 'method:', method
        if method == 'initial':
            return KmlUtil.wrapKmlDjango(self.kmlGetInitialKml(request, sessionId))
        elif method == 'update':
            return KmlUtil.wrapKmlDjango(self.kmlGetUpdateKml(request, sessionId))
        else:
            raise Exception('method must be "initial" or "update"')
