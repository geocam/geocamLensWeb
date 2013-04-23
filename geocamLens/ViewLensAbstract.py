# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

# Create your views here.

import sys
import os
import tempfile

import PIL.Image
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from geocamUtil import anyjson as json
from geocamUtil.icons import cacheIcons
from geocamUtil.models.UuidField import makeUuid

from geocamLens.models import Image
from geocamLens.forms import UploadImageForm, EditImageForm
from geocamLens.ViewKml import ViewKml
from geocamLens.SearchAbstract import BadQuery
from geocamLens import settings

cacheIcons(os.path.join(settings.STATIC_ROOT, 'geocamLens', 'icons', 'map'))
cacheIcons(os.path.join(settings.STATIC_ROOT, 'geocamLens', 'icons', 'mapr'))


class ViewLensAbstract(ViewKml):
    # override in derived classes
    search = None
    defaultImageModel = None

    def getMatchingFeaturesForQuery(self, query):
        allFeatures = self.search.getAllFeatures()
        features = self.search.searchFeatures(allFeatures, query)
        return features

    def getMatchingFeatures(self, request):
        query = request.REQUEST.get('q', '')
        return self.getMatchingFeaturesForQuery(query)

    def dumps(self, obj):
        if 1:
            return json.dumps(obj, indent=4, sort_keys=True)  # pretty print for debugging
        else:
            return json.dumps(obj, separators=(',', ':'))  # compact

    def getFeaturesGeoJson(self, request):
        try:
            matches = self.getMatchingFeatures(request)
            errorMessage = None
        except BadQuery, e:
            errorMessage = e.message

        numFeaturesParam = request.GET.get('n')
        if numFeaturesParam:
            if numFeaturesParam == 'all':
                numFeatures = None
            else:
                numFeatures = int(numFeaturesParam)
        else:
            numFeatures = settings.GEOCAM_LENS_DEFAULT_NUM_FEATURES
        if numFeatures != None:
            matches = matches[:numFeatures]

        if errorMessage:
            response = {'error': {'code': -32099,
                                  'message': errorMessage}}
        else:
            gjFeatures = [f.getGeoJson() for f in matches]
            featureCollection = dict(type='FeatureCollection',
                                     crs=dict(type='name',
                                              properties=dict(name='urn:ogc:def:crs:OGC:1.3:CRS84')),
                                     features=gjFeatures)
            response = dict(result=featureCollection)
        return self.dumps(response)

    def featuresJson(self, request):
        return HttpResponse(self.getFeaturesGeoJson(request),
                            mimetype='application/json')

    def featuresJsonJs(self, request):
        response = self.getFeaturesGeoJson(request)
        return HttpResponse('geocamAware.handleNewFeatures(%s);\n' % response,
                            mimetype='text/javascript')

    def galleryDebug(self, request):
        return HttpResponse('<body><pre>%s</pre></body>' % self.getFeaturesGeoJson(request))

    def getExportSettings(self):
        exportedVars = ['SCRIPT_NAME',
                        'STATIC_URL',
                        'DATA_URL',
                        'GEOCAM_AWARE_GALLERY_PAGE_COLS',
                        'GEOCAM_AWARE_GALLERY_PAGE_ROWS',
                        'GEOCAM_AWARE_GALLERY_THUMB_SIZE',
                        'GEOCAM_AWARE_DESC_THUMB_SIZE',
                        'GEOCAM_AWARE_MAP_BACKEND',
                        'GEOCAM_AWARE_USE_MARKER_CLUSTERING',
                        'GEOCAM_AWARE_USE_TRACKING',
                        'GEOCAM_AWARE_DEFAULT_MAP_BOUNDS']
        exportDict = dict(((f, getattr(settings, f, None))
                           for f in exportedVars))
        return json.dumps(exportDict)

    def editImage0(self, request, imgId, template):
        img = self.defaultImageModel.objects.get(id=imgId)
        ajax = 'ajax' in request.POST
        if request.method == 'POST':
            form = EditImageForm(request.POST, instance=img)
            if form.is_valid():
                updatedObject = form.save()
                if ajax:
                    return HttpResponse(json.dumps({'result': updatedObject.getGeoJson()}),
                                        mimetype='application/json')
            else:
                if ajax:
                    return HttpResponse(json.dumps({'error': {'code': -32099,
                                                              'message': 'invalid value in form field',
                                                              'data': form._get_errors()}
                                                    }),
                                        mimetype='application/json')
        else:
            form = EditImageForm(instance=img)
        return (render_to_response
                (template,
                 dict(img=img,
                      form=form),
                 context_instance=RequestContext(request)))

    def editImage(self, request, imgId):
        return self.editImage0(request, imgId, 'editImage.html')

    def editImageWrapper(self, request, imgId):
        return self.editImage0(request, imgId, 'editImageWrapper.html')

    @csrf_exempt
    def uploadImageAuth(self, request):
        return self.uploadImage(request, request.user.username)

    def uploadImage(self, request, userName):
        author = User.objects.get(username=userName)
        if request.method == 'POST':
            print >> sys.stderr, 'upload image start'
            form = UploadImageForm(request.POST, request.FILES)
            print >> sys.stderr, 'FILES:', request.FILES.keys()
            if form.is_valid():
                incoming = request.FILES['photo']

                # store image data in temp file
                fd, tempStorePath = tempfile.mkstemp('-uploadImage.jpg')
                os.close(fd)
                storeFile = file(tempStorePath, 'wb')
                for chunk in incoming.chunks():
                    storeFile.write(chunk)
                storeFile.close()
                print >> sys.stderr, 'upload: saved image data to temp file:', tempStorePath

                # create image db record
                uuid = form.cleaned_data.setdefault('uuid', makeUuid())
                form.cleaned_data['name'] = incoming.name
                form.cleaned_data['author'] = author
                uuidMatches = self.defaultImageModel.objects.filter(uuid=uuid)
                sameUuid = (uuidMatches.count() > 0)
                if sameUuid:
                    # if the incoming uuid matches an existing uuid, this is
                    # either (1) a duplicate upload of the same image or (2)
                    # the next higher resolution level in an incremental
                    # upload.
                    img = uuidMatches.get()
                    print >> sys.stderr, 'upload: photo %s with same uuid %s posted' % (img.name, img.uuid)
                    newVersion = img.version + 1
                else:
                    # create Image db record
                    img = self.defaultImageModel()  # pylint: disable=E1102
                    img.readImportVals(storePath=tempStorePath,
                                       uploadImageFormData=form.cleaned_data)

                    # set version
                    newVersion = 0

                # check the new image file on disk to get the dimensions
                im = PIL.Image.open(tempStorePath, 'r')
                newRes = im.size
                del im

                if sameUuid:
                    oldRes = (img.widthPixels, img.heightPixels)
                    if newRes > oldRes:
                        print >> sys.stderr, 'upload: resolution increased from %d to %d' % (oldRes[0], newRes[0])
                        img.widthPixels, img.heightPixels = newRes
                        img.processed = False
                    else:
                        print >> sys.stderr, 'upload: ignoring dupe, but telling the client it was received so it stops trying'
                else:
                    img.widthPixels, img.heightPixels = newRes

                if not img.processed:
                    # generate thumbnails and any other processing
                    # (better to do this part in the background, but we
                    # don't have that set up yet)
                    img.version = newVersion
                    # make sure the image gets an id if it doesn't already have one --
                    # the id will be used in process() to calculate the storage path
                    img.save()
                    img.process(importFile=tempStorePath)
                    img.save()

                # after import by process(), can delete redundant temp copy
                os.unlink(tempStorePath)

                print >> sys.stderr, 'upload image end'

                # swfupload requires non-empty response text.
                # also added a text pattern (in html comment) for clients to check against to make sure
                # photo has actually arrived in share.  we also put a matching line in the error log so we
                # never again run into the issue that the phone thinks it successfully uploaded but there
                # is no record of the http post on the server.
                print >> sys.stderr, 'GEOCAM_SHARE_POSTED %s' % img.name
                return HttpResponse('file posted <!--\nGEOCAM_SHARE_POSTED %s\n-->' % img.name)

            else:
                print >> sys.stderr, "form is invalid"
                print >> sys.stderr, "form errors: ", form._errors
                userAgent = request.META.get('HTTP_USER_AGENT', '')
                # swfupload user can't see errors in form response, best return an error code
                if 'Flash' in userAgent:
                    return HttpResponseBadRequest('<h1>400 Bad Request</h1>')
        else:
            form = UploadImageForm()
            #print 'form:', form
        resp = render_to_response('upload.html',
                                  dict(form=form,
                                       author=author,
                                       ),
                                  context_instance=RequestContext(request))
        print >> sys.stderr, 'upload image end'
        return resp

    def viewPhoto(self, request, imgId):
        # this is not very efficient
        img = Image.objects.get(id=imgId)
        imgData = file(img.getImagePath(), 'r').read()
        return HttpResponse(imgData, mimetype='image/jpeg')
