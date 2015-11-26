#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       Astromagic -- the image editor for Astronomers        **
# *****************************************************************

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import AstroMagic modules
from .tools import configuration

# -----------------------------------------------------------------

class WCSFinder(object):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        ## Configuration

        self.config = configuration.set("wcsfinder", config)

    # -----------------------------------------------------------------

    def run(self, frame):

        """
        This function ...
        :return:
        """

        pass
        
# -----------------------------------------------------------------