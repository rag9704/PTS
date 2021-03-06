#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.plotting.maps Contains the MapsPlotter class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from .component import PlottingComponent
from ..maps.component import MapsComponent
from ...core.tools import filesystem as fs
from ...core.basics.log import log
from ...magic.core.frame import Frame
from ...magic.plot.imagegrid import StandardImageGridPlotter

# -----------------------------------------------------------------

class MapsPlotter(PlottingComponent, MapsComponent):
    
    """
    This class...
    """

    # The load functions
    load_functions = dict()

    # The plot functions
    plot_functions = dict()

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructors of the base classes
        PlottingComponent.__init__(self, *args, **kwargs)
        MapsComponent.__init__(self, *args, **kwargs)

        # -- Attributes --

        # The dictionary of image frames
        self.images = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Load the images
        self.load_images()

        # 3. Plot
        self.plot()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(MapsPlotter, self).setup()

    # -----------------------------------------------------------------

    def load_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the maps ...")

        for name in ["dust", "ionizing_stars", "old_stars", "young_stars"]:

            # Determine the path to the image
            path = fs.join(self.maps_path, name + ".fits")

            # Debugging
            log.debug("Loading the " + name + " image ...")

            # Open the map
            image = Frame.from_file(path)

            # Add the image to the dictionary
            self.images[name] = image

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting ...")

        # Create the image plotter
        plotter = StandardImageGridPlotter()

        # Add the images
        for label in self.images: plotter.add_image(self.images[label], label)

        # Determine the path to the plot file
        path = fs.join(self.plot_maps_path, "maps.pdf")

        plotter.colormap = "hot"
        plotter.vmin = 0.0

        plotter.set_title("Input maps")

        # Make the plot
        plotter.run(path)

# -----------------------------------------------------------------
