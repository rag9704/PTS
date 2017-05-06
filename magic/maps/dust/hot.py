#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.maps.dust.hot Contains the HotDustMapsMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ....core.tools.logging import log
from ....core.basics.configurable import Configurable

# -----------------------------------------------------------------

def make_map(mips24, old, factor):

    """
    This function ...
    :return: 
    """

    # Create the map maker
    maker = HotDustMapsMaker()

    # Set input
    factors = [factor]

    # Run the map maker
    maker.run(mips24=mips24, old=old, factors=factors)

    # Return the map
    return maker.single_map

# -----------------------------------------------------------------

def make_maps(mips24, old, factors):

    """
    This fucntion ...
    :return: 
    """

    # Create the map maker
    maker = HotDustMapsMaker()

    # Run the map maker
    maker.run(mips24=mips24, old=old, factors=factors)

    # Return the maps
    return maker.maps

# -----------------------------------------------------------------

class HotDustMapsMaker(Configurable):

    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(HotDustMapsMaker, self).__init__(*args, **kwargs)

        # -- Attributes --

        # THe mips 24 frame and error map
        self.mips24 = None
        self.mips24_errors = None

        # THe map of the old stellar disk
        self.old = None

        # Factors
        self.factors = None

        # The maps
        self.maps = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs: 
        :return: 
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Make the maps
        self.make_maps()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ....
        :param kwargs: 
        :return: 
        """

        # Call the setup function of the base class
        super(HotDustMapsMaker, self).setup(**kwargs)

        # Get the input
        self.mips24 = kwargs.pop("mips24")
        self.mips24_errors = kwargs.pop("mips24_errors")
        self.old = kwargs.pop("old")

        # Set factors
        self.factors = kwargs.pop("factors")

    # -----------------------------------------------------------------

    def load_mips(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the MIPS 24 micron image and converting to solar units ...")

        # Get MIPS 24 micron frame and error map
        #self.mips24 = self.dataset.get_frame("MIPS 24mu")  # in original MJy/sr units
        #self.mips24_errors = self.dataset.get_errormap("MIPS 24mu")  # in original MJy/sr units

        ## CONVERT TO LSUN

        # Get the galaxy distance
        distance = self.galaxy_properties.distance

        # Get pixelscale and wavelength
        pixelscale = self.mips24.average_pixelscale
        wavelength = self.mips24.filter.pivot

        # Conversion from MJy / sr to Jy / sr
        conversion_factor = 1e6

        # Conversion from Jy / sr to Jy / pix(2)
        conversion_factor *= (pixelscale ** 2).to("sr/pix2").value

        # Conversion from Jy / pix to W / (m2 * Hz) (per pixel)
        conversion_factor *= 1e-26

        # Conversion from W / (m2 * Hz) (per pixel) to W / (m2 * m) (per pixel)
        conversion_factor *= (speed_of_light / wavelength ** 2).to("Hz/m").value

        # Conversion from W / (m2 * m) (per pixel) [SPECTRAL FLUX] to W / m [SPECTRAL LUMINOSITY]
        conversion_factor *= (4. * np.pi * distance ** 2).to("m2").value

        # Conversion from W / m [SPECTRAL LUMINOSITY] to W [LUMINOSITY]
        conversion_factor *= wavelength.to("m").value

        # Conversion from W to Lsun
        conversion_factor *= 1. / solar_luminosity.to("W").value

        ## DO THE CONVERSION

        self.mips24 *= conversion_factor
        self.mips24_errors *= conversion_factor

    # -----------------------------------------------------------------

    def make_maps(self):

        """
        This function ...
        :return:
        """

        # H-ALPHA HAS BEEN CONVERTED TO LSUN (ABOVE)

        # Inform the user
        log.info("Making the maps of hot dust ...")

        # Normalize the old map
        normalized_old = self.old.normalized()

        # Loop over the different factors
        for factor in self.factors:

            # Calculate the corrected 24 micron image
            corrected = make_corrected_24mu_map(self.mips24, normalized_old, factor)

            # Determine name
            name = str(factor)

            # Add the attenuation map to the dictionary
            self.maps[name] = corrected

    # -----------------------------------------------------------------

    def make_distributions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making distributions of the pixel values of the corrected 24 micron maps ...")

        # Create mask
        #mask = self.distribution_region.to_mask(self.map.xsize, self.map.ysize)

        # NEW: TODO

        # Loop over the different maps
        for factor in self.corrected_24mu_maps:

            # Get the values
            values = self.corrected_24mu_maps[factor][mask]

            # Make a distribution of the pixel values indicated by the mask
            distribution = Distribution.from_values(values, bins=self.config.histograms_nbins)

            # Add the distribution to the dictionary
            self.corrected_24mu_distributions[factor] = distribution

    # -----------------------------------------------------------------

    @property
    def single_map(self):

        """
        This function ...
        :return: 
        """

        if len(self.maps) != 1: raise ValueError("Not a single map")
        return self.maps[self.maps.keys()[0]]

# -----------------------------------------------------------------

def make_corrected_24mu_map(mips24, disk, factor):

    """
    This function ...
    :return:
    """

    # Inform the user
    log.info("Subtracting the old stellar contribution from the 24 micron emission map with a factor of " + str(factor) + " ...")

    ## Subtract old stellar contribution from FUV and MIPS 24 emission

    #     From the FUV and 24 micron maps we must subtract the diffuse radiation (old stellar contribution),
    #     for this we typically use an exponential disk
    #     (scale length detemermined by GALFIT)

    ## MIPS HAS BEEN CONVERTED TO LSUN (ABOVE)

    # typisch 20% en 35% respectievelijk
    # 48% voor MIPS 24 komt van Lu et al. 2014

    # Total contribution in solar units
    total_contribution = factor * mips24.sum()

    # Subtract the disk contribution to the 24 micron image
    new_mips = mips24 - total_contribution * disk # disk image is normalized

    # Make sure all pixels of the disk-subtracted maps are larger than or equal to zero
    #new_mips[new_mips < 0.0] = 0.0

    # Set zero where low signal-to-noise ratio
    # new_mips[self.mips < self.config.ionizing_stars.mips_young_stars.mips_snr_level*self.mips_errors] = 0.0

    # Return the new 24 micron frame
    return new_mips

# -----------------------------------------------------------------