#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.maps.dust.attenuation Contains the AttenuationDustMapsMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
from copy import copy

# Import the relevant PTS classes and modules
from ....magic.core.frame import Frame
from ....core.basics.log import log
from ....core.basics.configurable import Configurable
from ...calibrations.cortese import CorteseAttenuationCalibration
from .tir_to_uv import make_tir_to_uv
from ....core.filter.filter import parse_filter
from ....core.tools import sequences
from ...core.list import NamedFrameList

# -----------------------------------------------------------------

def make_map(fuv, tir, ssfr, ssfr_colour):

    """
    This function ...
    :param fuv:
    :param tir:
    :param ssfr:
    :param ssfr_colour:
    :return: 
    """

    # Create the attenuation map maker
    maker = CorteseAttenuationMapsMaker()

    # Set input
    tirs = {"standard": tir}
    ssfrs = {ssfr_colour: ssfr}

    # Run
    maker.run(fuv=fuv, tirs=tirs, ssfrs=ssfrs)

    # Get the map
    return maker.single_map

# -----------------------------------------------------------------

class CorteseAttenuationMapsMaker(Configurable):

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
        super(CorteseAttenuationMapsMaker, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The FUV map
        self.fuv = None

        # The TIR maps
        self.tirs = None

        # The ssfr maps
        self.ssfrs = None

        # Origins
        self.tirs_origins = None
        self.ssfrs_origins = None

        # Methods
        self.tirs_methods = None
        self.ssfrs_methods = None

        # The table describing the calibration parameters from Cortese et. al 2008
        # Title of table: Relations to convert the TIR/FUV ratio in A(FUV) for different values of tau and
        # FUV − NIR/optical colours.
        self.cortese = None

        # The SSFR maps (the FUV/optical-NIR colour maps)
        self.ssfrs = dict()

        # The attenuation maps (for different FUV/optical-NIR colours)
        self.maps = dict()

        # The origins
        self.origins = dict()

        # The methods
        self.methods = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Make the dust map
        self.make_maps()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(CorteseAttenuationMapsMaker, self).setup(**kwargs)

        # Get input
        self.fuv = kwargs.pop("fuv")
        self.tirs = kwargs.pop("tirs")
        self.ssfrs = kwargs.pop("ssfrs")

        # Get origins
        self.tirs_origins = kwargs.pop("tirs_origins", None)
        self.ssfrs_origins = kwargs.pop("ssfrs_origins", None)

        # Get methods
        self.tirs_methods = kwargs.pop("tirs_methods", None)
        self.ssfrs_methods = kwargs.pop("ssfrs_methods", None)

        # Get method name
        self.method_name = kwargs.pop("method_name", None)
        if self.has_methods and self.method_name is None: raise ValueError("Method name should be specified when methods are given")

        # Get already calculated maps
        self.maps = kwargs.pop("maps", dict())

        # Create the Cortese instance
        self.cortese = CorteseAttenuationCalibration()

    # -----------------------------------------------------------------

    @property
    def has_origins(self):

        """
        This function ...
        :return: 
        """

        return self.tirs_origins is not None and self.ssfrs_origins is not None

    # -----------------------------------------------------------------

    @property
    def has_methods(self):

        """
        This function ...
        :return:
        """

        return self.tirs_methods is not None and self.ssfrs_methods is not None

    # -----------------------------------------------------------------

    @property
    def has_all_maps(self):

        """
        This function ...
        :return:
        """

        # Loop over the different TIR maps
        for name in self.tirs:

            # Loop over the different colour options
            for ssfr_colour in self.ssfrs:

                # Determine name
                key = name + "__" + ssfr_colour

                # If map is not yet present, return False
                if key not in self.maps: return False

        # ALl maps are already present
        return True

    # -----------------------------------------------------------------

    def make_maps(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the attenuation maps ...")

        # Dust = FUV attenuation = function of (ratio of TIR and FUV luminosity)

        # CHECK if ALL MAPS ARE ALREADY PRESENT: IN THAT CASE, WE DON'T HAVE TO CREATE THE TIR_TO_FUV MAP!
        if self.has_all_maps:
            log.debug("All maps are already present. Not creating the TIR to FUV map and the attenuation maps but setting origins and methods.")
            need_any = False
        else: need_any = True

        # Loop over the different TIR maps
        for name in self.tirs:

            #print(name, self.tirs[name])

            # Make the TIR to FUV map
            if need_any: tir_to_fuv = make_tir_to_uv(self.tirs[name], self.fuv)
            #log_tir_to_fuv = Frame(np.log10(tir_to_fuv), wcs=tir_to_fuv.wcs) # unit is lost: cannot do rebinning because 'frame.unit.is_per_pixelsize' is not accessible ...
            else: tir_to_fuv = None

            # Loop over the different colour options
            for ssfr_colour in self.ssfrs:

                # Determine name
                key = name + "__" + ssfr_colour

                # Set origins
                if self.has_origins:

                    origins = copy(self.tirs_origins[name])
                    origins_ssfr = copy(self.ssfrs_origins[ssfr_colour])
                    sequences.extend_unique(origins, origins_ssfr)
                    sequences.append_unique(origins, parse_filter("FUV"))
                    self.origins[key] = origins

                # Set methods
                if self.has_methods:

                    methods = copy(self.tirs_methods[name])
                    methods_ssfr = copy(self.ssfrs_methods[ssfr_colour])
                    sequences.extend_unique(methods, methods_ssfr)
                    methods.append(self.method_name)
                    self.methods[key] = methods

                # Check whether a map is already present
                if key in self.maps:
                    log.warning("The " + name + " attenuation map is already created: not creating it again")
                    continue

                # Get the ssfr map
                ssfr = self.ssfrs[ssfr_colour]

                # Rebin and convolve the TIR-to-FUV, FUV and the sSFR maps
                frames = NamedFrameList(fuv=self.fuv, ssfr=ssfr, tirtofuv=tir_to_fuv)
                frames.convolve_and_rebin()
                
                # Get frames
                log_tir_to_fuv = Frame(np.log10(frames["tirtofuv"]), wcs=frames["tirtofuv"].wcs)

                # Create the FUV attenuation map according to the calibration in Cortese et. al 2008
                fuv_attenuation = make_fuv_attenuation_map(self.cortese, ssfr_colour, log_tir_to_fuv, frames["ssfr"])

                # Set properties
                fuv_attenuation.unit = None # no unit for attenuation
                fuv_attenuation.filter = None # no filter for attenuation
                fuv_attenuation.wcs = frames.wcs
                fuv_attenuation.distance = frames.distance
                fuv_attenuation.pixelscale = frames.pixelscale
                fuv_attenuation.psf_filter = frames.psf_filter
                fuv_attenuation.fwhm = frames.fwhm

                # Set attenuation to zero where the original FUV map is smaller than zero
                fuv_attenuation[frames["fuv"] < 0.0] = 0.0

                # Make positive: replace NaNs and negative pixels by zeros
                # Set negatives and NaNs to zero
                fuv_attenuation.replace_nans(0.0)
                fuv_attenuation.replace_negatives(0.0)

                # Add the attenuation map to the dictionary
                self.maps[key] = fuv_attenuation

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

def make_fuv_attenuation_map(cortese, ssfr_colour, log_tir_to_fuv, ssfr):

    """
    This function ...
    :param cortese:
    :param ssfr_colour:
    :param log_tir_to_fuv:
    :param ssfr:
    :return:
    """

    # Inform the user
    log.info("Creating the A(FUV) map according to the relation to the TIR/FUV ratio as described in Cortese et. al 2008 ...")

    # Calculate powers of log(tir_to_fuv)
    log_tir_to_fuv2 = np.power(log_tir_to_fuv.data, 2.0)
    log_tir_to_fuv3 = np.power(log_tir_to_fuv.data, 3.0)
    log_tir_to_fuv4 = np.power(log_tir_to_fuv.data, 4.0)

    # Create an empty image
    a_fuv_cortese = Frame.zeros_like(log_tir_to_fuv)

    # Create the FUV attenuation map
    for tau, colour_range, parameters in cortese.taus_ranges_and_parameters(ssfr_colour):
        # Debugging
        log.debug("Setting FUV attenuation values for tau = " + str(tau) + " ...")

        # Set mask
        where = (ssfr >= colour_range.min) * (ssfr < colour_range.max)

        # Set the appropriate pixels
        a_fuv_cortese[where] = parameters[0] + parameters[1] * log_tir_to_fuv[where] + parameters[2] * log_tir_to_fuv2[where] + \
                               parameters[3] * log_tir_to_fuv3[where] + parameters[4] * log_tir_to_fuv4[where]

    # Get absolute upper limit
    absolute_upper_limit = cortese.get_upper_limit(ssfr_colour)

    # Set attenuation to zero where tir_to_fuv is NaN
    a_fuv_cortese[np.isnan(log_tir_to_fuv)] = 0.0

    # Set attenuation to zero where sSFR is smaller than zero
    a_fuv_cortese[ssfr < 0.0] = 0.0

    # Set attenuation to zero where sSFR is greater than the absolute upper limit for the FUV-IR/optical colour
    a_fuv_cortese[ssfr >= absolute_upper_limit] = 0.0

    # Return the A(FUV) map
    return a_fuv_cortese

# -----------------------------------------------------------------
