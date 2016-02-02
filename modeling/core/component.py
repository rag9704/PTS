#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.core.component Contains the ModelingComponent class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ...core.tools import inspection, filesystem

# -----------------------------------------------------------------

class ModelingComponent(Configurable):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(ModelingComponent, self).__init__(config, "modeling")

        # Attributes
        self.galaxy_name = None

        self.data_path = None
        self.prep_path = None
        self.maps_path = None
        self.phot_path = None

        self.kernels_path = None

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(ModelingComponent, self).setup()

        # -- Attributes --

        # Get the name of the galaxy (the name of the base directory)
        self.galaxy_name = os.path.basename(self.config.path)

        # Get the full path to the 'data', 'prep' and 'in' directories
        self.data_path = os.path.join(self.config.path, "data")
        self.prep_path = os.path.join(self.config.path, "prep")
        self.maps_path = os.path.join(self.config.path, "maps")
        self.phot_path = os.path.join(self.config.path, "phot")

        # Determine the path to the kernels user directory
        self.kernels_path = os.path.join(inspection.pts_user_dir, "kernels")

        # Create the prep path if it does not exist yet
        filesystem.create_directories([self.prep_path, self.maps_path, self.phot_path])

# -----------------------------------------------------------------
