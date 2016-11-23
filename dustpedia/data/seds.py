#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.dustpedia.data.seds Contains the SEDFetcher class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ..core.photometry import DustPediaPhotometry
from ...core.tools import filesystem as fs
from ..core.sample import DustPediaSample
from ...core.tools.logging import log

# -----------------------------------------------------------------

class SEDFetcher(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        """

        # Call the constructor of the base class
        super(SEDFetcher, self).__init__(config)

        # The DustPediaSample object
        self.sample = DustPediaSample()

        # The DustPediaPhotometry object
        self.photometry = DustPediaPhotometry()

        # The SED
        self.sed = None

        # The NGC ID
        self.ngc_id = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Get the SED
        self.get_sed()

        # 3. Write
        if self.config.write: self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup of the base class
        super(SEDFetcher, self).setup(**kwargs)

        # Get the NGC ID
        self.ngc_id = self.sample.get_name(self.config.galaxy_name)

    # -----------------------------------------------------------------

    def get_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Getting the SED ...")

        # Get the SED for the galaxy
        self.sed = self.photometry.get_sed(self.ngc_id, add_iras=self.config.iras, add_planck=self.config.planck)

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the SED
        self.write_sed()

    # -----------------------------------------------------------------

    def write_sed(self):

        """
        This function ...
        :return:
        """

        # Determine the path
        path = fs.join(self.config.path, self.config.galaxy_name + ".dat")

        # Save the SED
        self.sed.save(path)

# -----------------------------------------------------------------