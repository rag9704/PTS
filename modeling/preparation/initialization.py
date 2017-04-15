#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.preparation.initialization Contains the PreparationInitializer class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from .component import PreparationComponent
from ...magic.sources.finder import SourceFinder
from ...core.tools import filesystem as fs
from ...core.tools.logging import log
from ...magic.misc.imageimporter import ImageImporter
from ...magic.core.frame import Frame
from ...magic.core.dataset import DataSet
from ...core.launch.pts import PTSRemoteLauncher
from ...core.filter.filter import parse_filter
from ...magic.convolution.kernels import get_fwhm, has_variable_fwhm

# -----------------------------------------------------------------

class PreparationInitializer(PreparationComponent):
    
    """
    This class...
    """

    def __init__(self, config=None, interactive=False):

        """
        The constructor ...
        :param config:
        :param interactive:
        :return:
        """

        # Call the constructor of the base class
        super(PreparationInitializer, self).__init__(config, interactive)

        # -- Attributes --

        # The frame paths
        self.paths = dict()
        self.error_paths = dict()

        # The source finder
        self.finder = None

        # The initial dataset
        self.set = DataSet()

        # Create the PTS remote launcher
        self.launcher = PTSRemoteLauncher()

        # The statistics
        self.statistics = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Get the image paths
        self.get_paths()

        # 3. Create the initialized images
        self.initialize_images()

        # 4. Create the dataset
        self.create_dataset()

        # 5. Find sources
        self.find_sources()

        # 6. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(PreparationInitializer, self).setup(**kwargs)

        # Setup the remote PTS launcher
        if self.config.remote is not None: self.launcher.setup(self.config.remote)
        else: self.finder = SourceFinder(self.config.sources) # Create the source finder

    # -----------------------------------------------------------------

    def get_paths(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Looking for images and error frames ...")

        # Loop over the different image origins
        for path, origin in fs.directories_in_path(self.data_images_path, returns=["path", "name"]):

            # Ignore the Planck data (for now)
            if origin == "Planck": continue

            # Loop over the FITS files in the current directory
            for image_path, image_name in fs.files_in_path(path, extension="fits", not_contains="poisson", returns=["path", "name"]):

                # Open the image frame
                frame = Frame.from_file(image_path)

                # Determine the preparation name
                if frame.filter is not None: prep_name = str(frame.filter)
                else: prep_name = image_name

                # Add the image path
                self.paths[prep_name] = image_path

                # Determine path to poisson error map
                poisson_path = fs.join(path, image_name + "_poisson.fits")

                # Set the path to the poisson error map
                if fs.is_file(poisson_path): self.error_paths[prep_name] = poisson_path

    # -----------------------------------------------------------------

    def initialize_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Processing the images ...")

        # Loop over all image paths
        for prep_name in self.paths:

            # Get the image path
            image_path = self.paths[prep_name]

            # Determine the output path for this image
            output_path = self.get_prep_path(prep_name)

            # Check whether this image already has an initialized image
            initialized_path = fs.join(output_path, "initialized.fits")
            if fs.is_file(initialized_path): continue

            # Debugging
            log.debug("Initializing image '" + image_path + "' ...")

            # Set the path to the region of bad pixels
            bad_region_path = fs.join(self.data_path, "bad", prep_name + ".reg")
            if not fs.is_file(bad_region_path): bad_region_path = None

            # Get the filter
            fltr = parse_filter(prep_name)

            # Set the FWHM if the instrument has a fixed PSF
            if has_variable_fwhm(fltr): fwhm = None
            else: fwhm = get_fwhm(fltr)

            # Debugging
            log.debug("Loading image " + image_path + " as " + prep_name + " ...")

            # Import the image
            importer = ImageImporter()
            importer.run(image_path, bad_region_path, fwhm=fwhm, find_error_frame=False) # don't look for error frames

            # Get the imported image
            image = importer.image

            # Set the image name
            image.name = prep_name

            # -----------------------------------------------------------------

            # Remove all frames except for the primary frame
            image.remove_frames_except("primary")

            # -----------------------------------------------------------------

            # If a poisson error map was found, add it to the image
            if prep_name in self.error_paths:

                error_map = Frame.from_file(self.error_paths[prep_name])
                image.add_frame(error_map, "errors")

            # Save the image
            image.saveto(initialized_path)

    # -----------------------------------------------------------------

    def create_dataset(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the initial dataset ...")

        # Loop over the image paths
        for prep_name in self.paths:

            # Add entry to the dataset
            self.set.add_path(prep_name, self.paths[prep_name])

            # Set the path to the poisson error map (included in the image now!)
            #if prep_name in self.error_paths: self.set.add_error_path(prep_name, self.error_paths[prep_name])

    # -----------------------------------------------------------------

    def find_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finding sources in the images ...")

        # Don't look for stars in the Halpha image
        ignore_stars = ["Mosaic Halpha"]

        # Don't look for other sources in the IRAC images
        ignore_other_sources = ["IRAC I1", "IRAC I2", "IRAC I3", "IRAC I4"]

        # Create an animation for the source finder
        #if self.config.visualise: animation = Animation()
        #else: animation = None

        ignore_images = []

        # Check for which images the source finding step has already been performed
        for prep_name in self.paths:

            # Get output path
            output_path = self.get_prep_path(prep_name)

            # Determine the path to the "sources" directory within the output path for this image
            sources_output_path = fs.join(output_path, "sources")

            # If the source finding step has already been performed on this image, don't do it again
            if fs.is_directory(sources_output_path):

                # Debugging
                log.debug("Source finder output has been found for this image, skipping source finding step")

                # Ignore this image for the source finder
                ignore_images.append(prep_name)

        # Find sources locally or remotely
        if self.config.remote is not None: self.find_sources_remote(ignore_images, ignore_stars, ignore_other_sources)
        else: self.find_sources_local(ignore_images, ignore_stars, ignore_other_sources)

        # Set FWHM of optical images
        self.set_fwhm()

    # -----------------------------------------------------------------

    def find_sources_local(self, ignore_images, ignore_stars, ignore_other_sources):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finding sources locally ...")

        # Run the source finder
        self.finder.run(dataset=self.set, ignore=ignore_images, ignore_stars=ignore_stars, ignore_other_sources=ignore_other_sources)

        # Get the statistics
        self.statistics = self.finder.statistics

    # -----------------------------------------------------------------

    def find_sources_remote(self, ignore_images, ignore_stars, ignore_other_sources):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finding sources remotely on host '" + self.config.remote + "'...")

        # Initialize the input dictionary
        input_dict = dict()

        # Set the input dataset
        input_dict["dataset"] = self.set
        input_dict["ignore_images"] = ignore_images
        input_dict["ignore_stars"] = ignore_stars
        input_dict["ignore_other_sources"] = ignore_other_sources

        # Run the PTS find_sources command remotely and get the output
        self.statistics = self.launcher.run_attached("find_sources", self.config.sources, input_dict, return_output_names=["statistics"], unpack=True)

    # -----------------------------------------------------------------

    def set_fwhm(self):

        """
        This function ...
        :return:
        """

        # Set the FWHM of the images
        for prep_name in self.set:

            if prep_name not in fwhms:

                image = self.set.get_image(prep_name)
                image.fwhm = self.statistics[prep_name].fwhm
                image.saveto(self.set.paths[prep_name])

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the dataset
        self.write_dataset()

    # -----------------------------------------------------------------

    def write_dataset(self):

        """
        This function ...
        :return:
        """

        # Save the dataset
        self.set.saveto(self.initial_dataset_path)

# -----------------------------------------------------------------
