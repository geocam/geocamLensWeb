# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import logging
import os
from glob import glob

from django.core.management.base import NoArgsCommand

from geocamUtil.Builder import Builder
from geocamUtil.icons import svg, rotate, halo
from geocamUtil.Installer import Installer

from geocamLens import settings


class Command(NoArgsCommand):
    help = 'Prep geocamLens app'

    def handle_noargs(self, **options):
        up = os.path.dirname
        appDir = up(up(up(os.path.abspath(__file__))))
        print 'appDir:', appDir
        builder = Builder()

        # render svg to png
        svgOutput = '%s/build/media/geocamLens/icons/map/' % appDir
        if settings.GEOCAM_LENS_RENDER_SVG_ICONS:
            svgGlob = '%s/media_src/icons/*.svg' % appDir
            logging.debug('svgIcons %s %s', svgGlob, svgOutput)
            for imPath in glob(svgGlob):
                svg.buildIcon(builder, imPath, outputDir=svgOutput)

        # link static stuff into build/media
        inst = Installer(builder)
        inst.installRecurseGlob('%s/static/*' % appDir,
                                '%s/build/media' % appDir)

        # make highlighted versions of icons
        dstGlob = svgOutput + '*.png'
        logging.debug('highlightIcons %s', dstGlob)
        for dst in glob(dstGlob):
            if 'Highlighted' in dst:
                continue
            dstHighlighted = os.path.splitext(dst)[0] + 'Highlighted.png'
            halo.addHalo(builder, dst, dstHighlighted)

        # rotate pngs
        rotGlob = '%s/build/media/geocamLens/icons/map/*Point*.png' % appDir
        rotOutput = '%s/build/media/geocamLens/icons/mapr' % appDir
        logging.debug('rotateIcons %s %s', rotGlob, rotOutput)
        for imPath in glob(rotGlob):
            rotate.buildAllDirections(builder, imPath, outputDir=rotOutput)
