#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.preparation.datapreparation Contains the DataPreparer class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...magic.core.image import Image
from ...magic.region.list import PixelRegionList
from .component import PreparationComponent
from ...magic.prepare.batch import BatchImagePreparer
from ...core.tools import filesystem as fs
from ...core.tools.logging import log
from ...magic.region import tools as regions
from ...magic.misc.kernels import aniano_names
from ...magic.misc.calibration import CalibrationError
from ...core.launch.pts import PTSRemoteLauncher
from ...magic.core.dataset import DataSet
from ...magic.misc.kernels import AnianoKernels

# -----------------------------------------------------------------

class DataPreparer(PreparationComponent):

    """
    This class ...
    """

    # -----------------------------------------------------------------

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(DataPreparer, self).__init__(config)

        # -- Attributes --

        # The paths to the initialized images
        self.paths = []

        # The preparation dataset
        self.dataset = DataSet()

        # The FWHM of the reference image
        self.reference_fwhm = None

        # The Aniano kernels service
        self.aniano = None

        # Create the PTS remote launcher
        self.launcher = PTSRemoteLauncher()

        # The image preparer
        self.preparer = None

        # The image preparer configuration
        self.preparer_config = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function runs the data preparation ...
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Create the preparation dataset
        self.create_dataset()

        # 3. Prepare the images
        self.prepare_images()

        # 4. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(DataPreparer, self).setup(**kwargs)

        # Set options for the image preparer
        self.set_preparer_options()

        # Setup the remote PTS launcher
        if self.config.remote is not None: self.launcher.setup(self.config.remote)
        else: self.preparer = BatchImagePreparer(self.preparer_config)

    # -----------------------------------------------------------------

    def set_preparer_options(self):

        """
        This function ...
        :return:
        """

        # Create Aniano kernels instance
        aniano = AnianoKernels()

        # Write results of intermediate steps
        self.preparer_config["steps"] = True

        # We want to exclude the SPIRE images from the procedures that bring all images to the same resolution
        # Get the resolution and the FWHM of the SPIRE PSW image
        spire_fwhm = aniano.get_fwhm(self.spire_psw_filter)
        spire_pixelscale = self.initial_dataset.get_wcs("SPIRE PSW").average_pixelscale

        # Set the maximum FWHM and pixelscale for the image preparer
        self.preparer_config["max_fwhm"] = 0.99 * spire_fwhm
        self.preparer_config["max_pixelscale"] = 0.99 * spire_pixelscale

    # -----------------------------------------------------------------

    def create_dataset(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Checking the initialized images ...")

        # Loop over all images of the initial dataset
        for prep_name in self.initial_dataset.paths:

            # Get path of intial image
            image_path = self.initial_dataset.paths[prep_name]

            # Determine preparation directory for this image
            path = fs.directory_of(image_path)

            # Debugging
            log.debug("Checking " + path + " ...")

            # -----------------------------------------------------------------

            # Look if an initialized image file is present
            #image_path = fs.join(path, "initialized.fits")
            if not fs.is_file(image_path):

                log.warning("Initialized image could not be found for " + path)
                continue

            # Look if the 'sources' directory is present
            sources_path = fs.join(path, "sources")
            if not fs.is_directory(sources_path):

                log.warning("Sources directory could not be found for " + path)
                continue

            # -----------------------------------------------------------------

            # PATHS

            # Result path
            result_path = fs.join(path, "result.fits")

            # Check if the intermediate results have already been produced for this image and saved to the
            # corresponding preparation subdirectory
            extracted_path = fs.join(path, "extracted.fits")
            corrected_path = fs.join(path, "corrected_for_extinction.fits")
            converted_path = fs.join(path, "converted_unit.fits")
            convolved_path = fs.join(path, "convolved.fits")
            rebinned_path = fs.join(path, "rebinned.fits")
            subtracted_path = fs.join(path, "sky_subtracted.fits")

            sky_path = fs.join(path, "sky")

            # -----------------------------------------------------------------

            ## CURRENT ORDER OF STEPS IN IMAGEPREPARER:
            # 1. Setup
            # 2. Extract stars and galaxies from the image
            # 3. If requested, correct for galactic extinction
            # 4. If requested, convert the unit
            # 5. If requested, convolve
            # 6. If requested, rebin
            # 7. If requested, subtract the sky
            # 8. Calculate the calibration uncertainties
            # 9. If requested, set the uncertainties
            ##

            # -----------------------------------------------------------------

            # ALREADY COMPLETELY PREPARED

            # Check if a prepared image is already present
            if fs.is_file(result_path): continue

            # -----------------------------------------------------------------

            # ALREADY SKY-SUBTRACTED

            if fs.is_file(subtracted_path):

                # Check whether the sky directory is present
                if not fs.is_directory(sky_path): raise IOError("The sky subtraction output directory is not present for the '" + prep_name + "' image")

                # Add the path of the sky-subtracted image
                self.dataset.add_path(prep_name, subtracted_path)

                # Check whether keywords are set to True in image header ?

            # -----------------------------------------------------------------

            # ALREADY REBINNED

            # Check if the rebinned image is present
            elif fs.is_file(rebinned_path):

                # Add the path of the rebinned image
                self.dataset.add_path(prep_name, rebinned_path)

                # Check whether keywords are set to True in image header ?

            # -----------------------------------------------------------------

            # ALREADY CONVOLVED

            # Check if the convolved image is present
            elif fs.is_file(convolved_path):

                # Add the path of the convolved image
                self.dataset.add_path(prep_name, convolved_path)

            # -----------------------------------------------------------------

            # ALREADY UNIT-CONVERTED

            # Check if the converted image is present
            elif fs.is_file(converted_path):

                # Add the path of the unit-converted image
                self.dataset.add_path(prep_name, converted_path)

            # -----------------------------------------------------------------

            # ALREADY EXTINCTION CORRECTED

            # Check if the extinction-corrected image is present
            elif fs.is_file(corrected_path):

                # Add the path of the extinction-corrected image
                self.dataset.add_path(prep_name, corrected_path)

            # ALREADY SOURCE-EXTRACTED

            # Check if the source-extracted image is present
            elif fs.is_file(extracted_path):

                # Add the path of the source-extracted image
                self.dataset.add_path(prep_name, extracted_path)

            # -----------------------------------------------------------------

            # NO STEPS PERFORMED YET, START FROM INITIALIZED IMAGE

            else:

                # Add the path to the initialized image to the dataset
                self.dataset.add_path(prep_name, image_path)

            # -----------------------------------------------------------------

        # If all images have already been prepared
        if len(self.dataset) == 0: log.success("All images are already prepared")

    # -----------------------------------------------------------------

    def create_dataset_old(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the preparation dataset ...")

        # Loop over the image paths
        for image_path in self.paths:

            # Determine the path of the directory
            directory_path = fs.directory_of(image_path)

            # Check if the intermediate results have already been produced for this image and saved to the
            # corresponding preparation subdirectory
            extracted_path = fs.join(directory_path, "extracted.fits")
            corrected_path = fs.join(directory_path, "corrected_for_extinction.fits")
            converted_path = fs.join(directory_path, "converted_unit.fits")
            convolved_path = fs.join(directory_path, "convolved.fits")
            rebinned_path = fs.join(directory_path, "rebinned.fits")
            subtracted_path = fs.join(directory_path, "sky_subtracted.fits")

            ## CURRENT ORDER OF STEPS IN IMAGEPREPARER:
            # 1. Setup
            # 2. Extract stars and galaxies from the image
            # 3. If requested, correct for galactic extinction
            # 4. If requested, convert the unit
            # 5. If requested, convolve
            # 6. If requested, rebin
            # 7. If requested, subtract the sky
            # 8. Calculate the calibration uncertainties
            # 9. If requested, set the uncertainties
            ##

            # Check if the sky-subtracted image is present
            if fs.is_file(subtracted_path): pass

                # Disable all steps preceeding and including the sky subtraction
                #self.image_preparer.config.extract_sources = False
                #self.image_preparer.config.correct_for_extinction = False
                #self.image_preparer.config.convert_unit = False
                #self.image_preparer.config.convolve = False
                #self.image_preparer.config.rebin = False
                #self.image_preparer.config.subtract_sky = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(self.image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(self.image.wcs) if saturation_region is not None else None

                # Load the sky-subtracted image
                #image = Image.from_file(subtracted_path)
                #image.name = name

                # Add the path of the sky-subtracted image
                #self.dataset.add_path()

            # Check if the rebinned image is present
            elif fs.is_file(rebinned_path): pass

                # Disable all steps preceeding and including the rebinning
                #self.image_preparer.config.extract_sources = False
                #self.image_preparer.config.correct_for_extinction = False
                #self.image_preparer.config.convert_unit = False
                #self.image_preparer.config.convolve = False
                #self.image_preparer.config.rebin = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(
                #    image.wcs) if saturation_region is not None else None

                # Load the rebinned image
                #image = Image.from_file(rebinned_path)
                #image.name = name

            # Check if the convolved image is present
            elif fs.is_file(convolved_path): pass

                # Disable all steps preceeding and including the convolution
                #self.image_preparer.config.extract_sources = False
                #self.image_preparer.config.correct_for_extinction = False
                #self.image_preparer.config.convert_unit = False
                #self.image_preparer.config.convolve = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(image.wcs) if saturation_region is not None else None

                # Load the convolved image
                #image = Image.from_file(convolved_path)
                #image.name = name

            # Check if the converted image is present
            elif fs.is_file(converted_path): pass

                # Disable all steps preceeding and including the unit conversion
                #self.image_preparer.config.extract_sources = False
                #self.image_preparer.config.correct_for_extinction = False
                #self.image_preparer.config.convert_unit = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(image.wcs) if saturation_region is not None else None

                # Load the converted image
                #image = Image.from_file(converted_path)
                #image.name = name

            # Check if the extinction-corrected image is present
            elif fs.is_file(corrected_path): pass

                # Disable all steps preceeding and including the correction for extinction
                #self.image_preparer.config.extract_sources = False
                #self.image_preparer.config.correct_for_extinction = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(image.wcs) if saturation_region is not None else None

                # Load the extinction-corrected image
                #image = Image.from_file(corrected_path)
                #image.name = name

            # Check if the source-extracted image is present
            elif fs.is_file(extracted_path): pass

                # Disable all steps preceeding and including the source extraction
                #self.image_preparer.config.extract_sources = False

                # Set the principal ellipse and saturation region in sky coordinates
                #self.image_preparer.principal_ellipse_sky = regions.largest_ellipse(galaxy_region).to_sky(image.wcs)
                #self.image_preparer.saturation_region_sky = saturation_region.to_sky(image.wcs) if saturation_region is not None else None

                # Load the extracted image
                #image = Image.from_file(extracted_path)
                #image.name = name

            # -----------------------------------------------------------------

            # Write out sky annuli frames
            sky_path = fs.join(output_path, "sky")
            if not fs.is_directory(sky_path): fs.create_directory(sky_path)
            self.image_preparer.config.write_sky_apertures = True
            self.image_preparer.config.sky_apertures_path = sky_path

            # Set the visualisation path for the image preparer
            visualisation_path = self.visualisation_path if self.config.visualise else None

    # -----------------------------------------------------------------

    def prepare_images(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the images ...")

        # Prepare locally or remotely
        if self.config.remote is not None: self.prepare_images_remote()
        else: self.prepare_images_local()

    # -----------------------------------------------------------------

    def prepare_images_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the images remotely on host '" + self.config.remote + "'...")

        # Initialize the input dictionary
        input_dict = dict()

        # Set the input dataset
        input_dict["dataset"] = self.dataset

        # Run the PTS prepare_images command remotely and get the output
        frames, errormaps = self.launcher.run_attached("prepare_images", self.preparer_config, input_dict, return_output_names=["frames", "errormaps"], unpack=True)

    # -----------------------------------------------------------------

    def prepare_images_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the images remotely on host '" + self.config.remote + "'...")

        # Run the image preparer, pass the dataset
        self.preparer.run(dataset=self.dataset)

        # Get the frames
        frames = self.preparer.frames
        errormaps = self.preparer.errormaps

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        self.write_dataset()

    # -----------------------------------------------------------------

    def write_dataset(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def set_preparation_options(self, image, output_path):

        """
        This function ...
        :param image:
        :param output_path:
        :return:
        """

        # Set the attenuation value
        self.image_preparer.config.attenuation = self.attenuations[image.name]

        # If this image is not the reference image, set the appropriate options for rebinning and convolution
        # or this image does not need to be convolved (e.g. SPIRE images)
        if image.name == self.config.reference_image or aniano_names[image.name] is None:

            self.image_preparer.config.rebin = False
            self.image_preparer.config.convolve = False

        # Images that do need to be convolved
        else:

            # Debugging information
            log.debug("Setting the path to the convolution kernel ...")

            # Get the path to the local convolution kernel file
            this_aniano_name = aniano_names[image.name]
            reference_aniano_name = aniano_names[self.config.reference_image]
            kernel_file_path = self.aniano.get_kernel_path(this_aniano_name, reference_aniano_name)

            # Set the kernel path and FWHM
            self.image_preparer.config.convolution.kernel_path = kernel_file_path    # set kernel path
            self.image_preparer.config.convolution.kernel_fwhm = self.reference_fwhm # set kernel FWHM (is a quantity here)

            # Set flags to True
            self.image_preparer.config.rebin = True
            self.image_preparer.config.convolve = True

        # Convolve the SDSS images remotely
        if "SDSS" in image.name: self.image_preparer.config.convolution.remote = "nancy"
        else: self.image_preparer.config.convolution.remote = None

        # Check whether the image has to be sky subtracted
        if image.frames.primary.sky_subtracted:
            log.debug("The " + image.name + " image has already been sky subtracted")
            self.image_preparer.config.subtract_sky = False
        else: self.image_preparer.config.subtract_sky = True # Has yet to be sky subtracted

        # Set the calibration error
        self.image_preparer.config.uncertainties.calibration_error = CalibrationError.from_filter(image.filter)

        # Set the output directory
        self.image_preparer.config.output_path = output_path

        # -----------------------------------------------------------------

        # The units of the Halpha image don't have to be converted
        if "Halpha" in image.name: self.image_preparer.config.convert_unit = False
        else: self.image_preparer.config.convert_unit = True

# -----------------------------------------------------------------

def load_sources(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Load the galaxy region
    galaxy_region_path = fs.join(path, "galaxies.reg")
    galaxy_region = PixelRegionList.from_file(galaxy_region_path)

    # Load the star region (if present)
    star_region_path = fs.join(path, "stars.reg")
    star_region = PixelRegionList.from_file(star_region_path) if fs.is_file(star_region_path) else None

    # load the saturation region (if present)
    saturation_region_path = fs.join(path, "saturation.reg")
    saturation_region = PixelRegionList.from_file(saturation_region_path) if fs.is_file(saturation_region_path) else None

    # Load the region of other sources
    other_region_path = fs.join(path, "other_sources.reg")
    other_region = PixelRegionList.from_file(other_region_path) if fs.is_file(other_region_path) else None

    # Load the image with segmentation maps
    segments_path = fs.join(path, "segments.fits")
    segments = Image.from_file(segments_path, no_filter=True)

    # Get the different segmentation frames
    galaxy_segments = segments.frames.galaxies
    star_segments = segments.frames.stars if "stars" in segments.frames else None
    other_segments = segments.frames.other_sources if "other_sources" in segments.frames else None

    # Return the regions and segmentation maps
    return galaxy_region, star_region, saturation_region, other_region, galaxy_segments, star_segments, other_segments

# -----------------------------------------------------------------
