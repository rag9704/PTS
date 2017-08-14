#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.truncation.html.significance Contains the SignificanceLevelsPageGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ....core.basics.log import log
from ..component import TruncationComponent
from ...html.component import stylesheet_url, page_style, table_class, hover_table_class, top_title_size, title_size
from ....core.tools.html import HTMLPage, SimpleTable, updated_footing
from ....core.tools import html
from ....magic.view.html import javascripts, css_scripts
from ....core.tools import browser
from ....core.tools.stringify import tostr
from ....core.tools.utils import lazyproperty
from ....magic.core.rgb import RGBImage
from ....core.tools import filesystem as fs
from ....magic.core.mask import Mask

# -----------------------------------------------------------------

significance_plots_name = "significance_plots"
ncolumns = 2
colour_map = "jet"

# -----------------------------------------------------------------

class SignificanceLevelsPageGenerator(TruncationComponent):

    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param interactive:
        :return:
        """

        # Call the constructor of the base class
        super(SignificanceLevelsPageGenerator, self).__init__(*args, **kwargs)

        # Plot paths for each filter
        self.filter_plot_paths = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # Make plots
        self.make_plots()

        # Generate the page
        self.generate_page()

        # 5. Writing
        self.write()

        # Show
        if self.config.show: self.show()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(SignificanceLevelsPageGenerator, self).setup(**kwargs)

        # Make directory to contain the plots
        self.plots_path = fs.join(self.truncation_html_path, "significance")
        if fs.is_directory(self.plots_path):
            if self.config.replot: fs.clear_directory(self.plots_path)
        else: fs.create_directory(self.plots_path)

        # Create directories for each filter
        for fltr in self.filters:
            fltr_path = fs.join(self.plots_path, str(fltr))
            self.filter_plot_paths[fltr] = fltr_path
            if not fs.is_directory(fltr_path): fs.create_directory(fltr_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def filters(self):

        """
        This function ...
        :return:
        """

        return self.dataset.filters

    # -----------------------------------------------------------------

    @property
    def title(self):

        """
        This function ...
        :return:
        """

        return "Significance maps"

    # -----------------------------------------------------------------

    @property
    def image_width(self):

        """
        This fucntion ...
        :return:
        """

        #return 150
        return None

    # -----------------------------------------------------------------

    @property
    def image_height(self):

        """
        This function ...
        :return:
        """

        return 300

    # -----------------------------------------------------------------

    def make_plots(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making plots ...")

        # Loop over the filters
        #for fltr in self.filters:
        # Loop over the frames
        for name in self.dataset.names: # FASTER

            # Get the filter
            fltr = self.dataset.get_filter(name)

            # Get plot path
            plot_path = self.filter_plot_paths[fltr]

            # Get frame
            #frame = self.dataset.get_frame_for_filter(fltr)
            frame = self.dataset.get_frame(name)

            # Get error map list
            #errormap = self.dataset.get_errormap_for_filter(fltr)
            errormap = self.dataset.get_errormap(name)

            # Create the significance map
            significance = frame / errormap

            # Create the plots
            for level in self.config.sigma_levels:

                # Create the mask
                mask = Mask(significance > level)

                # Fill holes
                mask.fill_holes()

                # Invert
                #mask.invert()

                # Create RGB image
                image = RGBImage.from_mask(mask)

                # Determine path
                path = fs.join(plot_path, str(level) + ".png")

                # Save the image
                image.saveto(path)

    # -----------------------------------------------------------------

    def generate_page(self):

        """
        Thisfunction ...
        :return:
        """

        # Inform the user
        log.info("Generating the page ...")

        css_paths = css_scripts[:]
        css_paths.append(stylesheet_url)

        # Create the page
        self.page = HTMLPage(self.title, style=page_style, css_path=css_paths, javascript_path=javascripts, footing=updated_footing())

        classes = dict()
        classes["JS9Menubar"] = "data-backgroundColor"
        self.page += html.center(html.make_theme_button(classes=classes))

        self.page += html.newline



    # -----------------------------------------------------------------

    @property
    def maps_sub_path(self):

        """
        This function ...
        :return:
        """

        return None

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the page
        self.write_page()

    # -----------------------------------------------------------------

    def write_page(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the page ...")

        # Save
        self.page.saveto(self.significance_maps_html_page_path)

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the page ...")

        # Open in browser
        browser.open_path(self.significance_maps_html_page_path)

# -----------------------------------------------------------------
