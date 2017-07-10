#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.html.all Contains the AllPagesGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import webbrowser

# Import the relevant PTS classes and modules
from pts.modeling.html.status import StatusPageGenerator
from pts.modeling.html.data import DataPageGenerator
from pts.modeling.html.preparation import PreparationPageGenerator
from pts.modeling.html.maps import MapsPageGenerator
from pts.modeling.html.model import ModelPageGenerator
from pts.core.tools.logging import log
from ..component.galaxy import GalaxyModelingComponent

# -----------------------------------------------------------------

class AllPagesGenerator(GalaxyModelingComponent):

    """
    This function ...
    """

    def __init__(self, *args, **kwargs):

        """
        This function ...
        """

        # Call the constructor of the base class
        super(AllPagesGenerator, self).__init__(*args, **kwargs)

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Setup
        self.setup(**kwargs)

        # Generate the status page
        if self.history.finished("fetch_properties"): self.generate_status()

        # Generate the data page
        if self.history.finished("fetch_images"): self.generate_data()

        # Generate the preparation page
        if self.history.finished("prepare_data"): self.generate_preparation()

        # Generate the maps page
        if self.history.finished_maps: self.generate_maps()

        # GEnerate the model page
        if self.history.finished("configure_fit"): self.generate_model()

        # Write
        self.write()

        # Show
        if self.config.show: self.show()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(AllPagesGenerator, self).setup(**kwargs)

    # -----------------------------------------------------------------

    def generate_status(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generate the status page ...")

        # Generate
        generator = StatusPageGenerator()
        generator.config.path = self.config.path
        generator.run()

    # -----------------------------------------------------------------

    def generate_data(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the data page ...")

        # Generate
        generator = DataPageGenerator()
        generator.config.path = self.config.path
        generator.run()

    # -----------------------------------------------------------------

    def generate_preparation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the preparation page ...")

        # Generate
        generator = PreparationPageGenerator()
        generator.config.path = self.config.path
        generator.run()

    # -----------------------------------------------------------------

    def generate_maps(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the maps page ...")

        # Generate
        generator = MapsPageGenerator()
        generator.config.path = self.config.path
        generator.run()

    # -----------------------------------------------------------------

    def generate_model(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the model page ...")

        # Generate the model page
        generator = ModelPageGenerator()
        generator.config.path = self.config.path
        generator.run()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the pages ...")

        # Open
        webbrowser._tryorder = ["safari"]
        webbrowser.open(self.environment.html_status_path, new=2)

# -----------------------------------------------------------------
