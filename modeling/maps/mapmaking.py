#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.maps.mapmaking Contains the MapMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import copy
import numpy as np

# Import astronomical modules
from astropy.units import Unit
from photutils import detect_sources

# Import the relevant PTS classes and modules
from ...magic.basics.mask import Mask
from ...magic.core.image import Image
from ...magic.core.frame import Frame
from .component import MapsComponent
from ...core.tools import time, filesystem
from ..decomposition.decomposition import load_parameters

# -----------------------------------------------------------------

# Solar luminosity
Lsun = 3.846e26 * Unit("Watt")

# -----------------------------------------------------------------

class MapMaker(MapsComponent):

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
        super(MapMaker, self).__init__(config)

        # -- Attributes --

        # The structural galaxy parameters
        self.parameters = None
        self.distance_mpc = None

        # Input images
        self.images = dict()

        # Bulge and disk
        self.disk = None
        self.bulge = None

        # Set the low signal-to-noise mask to None initially
        self.mask = None

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new MapMaker instance
        maker = cls(arguments.config)

        # Set the input and output path
        maker.config.path = arguments.path

        # A single map name can be specified so the procedure is only run for that map
        maker.config.single_map = arguments.map

        # Return the new instance
        return maker

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Load the input images
        self.load_images()

        # 3. Cut-off the low signal-to-noise pixels
        #self.cutoff_low_snr()

        # 4. If requested, save the maps with masked
        #if self.config.save_cutoff_maps: self.save_cutoff_maps()

        # 5. Convert maps to solar luminosity units
        self.convert_units()

        # Make the dust map
        self.make_dust_map()

        # Make the old stars map
        self.make_old_stars_map()

        # Make the non-ionizing young stars map
        self.make_non_ionizing_stars_map()

        # Make the ionizing young stars map
        self.make_ionizing_stars_map()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(MapMaker, self).setup()

        # Determine the path to the parameters file
        path = filesystem.join(self.components_path, "parameters.dat")

        # Load the structural parameters
        self.parameters = load_parameters(path)

        # Get the galaxy distance
        self.distance_mpc = self.parameters.distance.to("Mpc").value

    # -----------------------------------------------------------------

    def load_images(self):

        """
        This function ...
        :return:
        """

        # Load the SDSS i image
        self.load_image("SDSS i", "i")

        # Load the GALEX FUV image
        self.load_image("GALEX FUV", "FUV")

        # Load the H-alpha image
        self.load_image("Mosaic Halpha", "Halpha")

        # Load the 24 micron image
        self.load_image("MIPS 24mu", "24mu")

        # Load the IRAC 3.6 image
        self.load_image("IRAC I1", "3.6mu")

        # Load the PACS 70 image
        self.load_image("Pacs blue", "70mu")

        # load the PACS 160 image
        self.load_image("Pacs red", "160mu")

        # Load the disk image
        self.load_disk()

        # Load the bulge image
        self.load_bulge()

    # -----------------------------------------------------------------

    def load_disk(self):

        """
        This function ...
        """

        # Determine the path to the disk image
        path = filesystem.join(self.components_path, "disk.fits")

        # Load the disk image
        self.disk = Frame.from_file(path)

    # -----------------------------------------------------------------

    def load_bulge(self):

        """
        This function ...
        """

        # Determine the path to the bulge image
        path = filesystem.join(self.components_path, "bulge.fits")

        # Load the bulge image
        self.bulge = Frame.from_file(path)

    # -----------------------------------------------------------------

    def load_image(self, image_name, image_id):

        """
        This function ...
        :param image_name:
        :param image_id:
        """

        # Determine the full path to the image
        path = filesystem.join(self.trunc_path, image_name + ".fits")

        # Check whether the image is present
        if not filesystem.is_file(path): raise IOError("Could not find the " + image_name + " image")

        # Open the image
        image = Image.from_file(path)

        # Assert that the units are MJy/sr
        if not "Halpha" in image_name: assert image.unit == Unit("MJy/sr")

        # Add the image to the dictionary
        self.images[image_id] = image

    # -----------------------------------------------------------------

    def cutoff_low_snr(self):

        """
        This function ...
        :return:
        """

        # Check whether the reference image is present
        if os.path.isfile(self.config.cutoff.reference_path):

            # Open the reference image
            reference = Image.from_file(self.config.cutoff.reference_path)

            # Check whether the errors frame is present
            assert self.config.errors in reference.frames, "An error map could not be found for the reference image"

            # Create a mask for the pixels with a signal-to-noise ratio of 5 or less
            data = reference.frames[self.config.primary] < self.config.cutoff.level*reference.frames[self.config.errors]
            self.mask = Mask(data)

            # If requested, remove holes from the cut-off mask
            if self.config.cutoff.remove_holes:

                # Save the mask as a FITS file
                Frame(self.mask.astype(float)).save(self.config.saving.cutoff_mask_with_holes_path)

                # Perform the segmentation
                segments = detect_sources(self.mask.astype(float), 0.5, 1).data

                # Save segments
                Frame(segments.astype(float)).save(self.config.saving.cutoff_mask_segments_path)

                # Find the label of the largest segment (=the background)
                label_counts = np.bincount(segments.flatten())
                background_label = np.argmax(label_counts)

                # Create a mask for the holes identified as background
                holes = copy.deepcopy(self.mask)
                holes[segments == background_label] = False

                # Save holes mask
                Frame(holes.astype(float)).save(self.config.saving.cutoff_mask_holes_path)

                # Remove holes from the mask
                self.mask[holes] = False

            # Save the mask as a FITS file
            Frame(self.mask.astype(float)).save(self.config.saving.cutoff_mask_path)

        # If not, raise an error
        else: raise IOError("The prepared reference image could not be found")

        # Cut-off the input images at the same contour level
        self.h[self.mask] = 0.0
        self.fuv[self.mask] = 0.0
        self.ha[self.mask] = 0.0
        self.irac[self.mask] = 0.0
        self.mips[self.mask] = 0.0
        self.pacsblue[self.mask] = 0.0
        self.pacsred[self.mask] = 0.0

        # Cut-off the error maps at the same contour level
        self.fuv_errors[self.mask] = 0.0
        self.ha_errors[self.mask] = 0.0
        self.irac_errors[self.mask] = 0.0
        self.mips_errors[self.mask] = 0.0

        # Cut-off the bulge and disk images at the same contour level
        self.disk[self.mask] = 0.0
        self.bulge[self.mask] = 0.0

    # -----------------------------------------------------------------

    def save_cutoff_maps(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Saving input images set to zero outside the low signal-to-noise contour level")

        # Save each of the frames
        self.h.save(self.config.saving.h_cutoff_path)
        self.fuv.save(self.config.saving.fuv_cutoff_path)
        self.ha.save(self.config.saving.ha_cutoff_path)
        self.irac.save(self.config.saving.irac_cutoff_path)
        self.mips.save(self.config.saving.mips_cutoff_path)
        self.pacsblue.save(self.config.saving.pacsblue_cutoff_path)
        self.pacsred.save(self.config.saving.pacsred_cutoff_path)
        self.disk.save(self.config.saving.disk_cutoff_path)
        self.bulge.save(self.config.saving.bulge_cutoff_path)

    # -----------------------------------------------------------------

    def convert_units(self):

        """
        This function ...
        :return:
        """

        # FUV is not converted to Lsun

        # Convert the H-alpha image to solar luminosities
        self.convert_halpha_to_solar()

        # Convert the MIPS image to solar luminosities
        self.convert_mips_to_solar()

        # Convert the PACS images to solar luminosities
        self.convert_pacs_to_solar()

    # -----------------------------------------------------------------

    def convert_halpha_to_solar(self):

        """
        This function converts the H alpha image from
        :return:
        """

        # Convert from erg/s to Lsun
        self.images["Halpha"].convert_to("Lsun")

    # -----------------------------------------------------------------

    def convert_mips_to_solar(self):

        """
        This function ...
        :return:
        """

        # Calculate conversion factors from MJy/sr to solar luminosities
        exponent = (2.0*np.log10(2.85/206264.806247)) - 20.0 + np.log10(3e8/24e-6) + np.log10(4.0*np.pi) + (2.0*np.log10(self.distance_mpc*3.08567758e22)) - np.log10(3.846e26)

        # Multiply the image
        self.images["24mu"] *= 10.**exponent

        # Set the new unit
        self.images["24mu"].unit = "Lsun"

    # -----------------------------------------------------------------

    def convert_pacs_to_solar(self):

        """
        This function ...
        :return:
        """

        # Calculate the conversion factors
        exponent_70 = (2.0*np.log10(2.85/206264.806247)) - 20.0 + np.log10(3e8/70e-6) + np.log10(4.0*np.pi) + (2.0*np.log10(self.distance_mpc*3.08567758e22)) - np.log10(3.846e26)
        exponent_160 = (2.0*np.log10(2.85/206264.806247)) - 20.0 + np.log10(3e8/160e-6) + np.log10(4.0*np.pi) + (2.0*np.log10(self.distance_mpc*3.08567758e22)) - np.log10(3.846e26)

        # Convert the units of the 70 micron and 160 micron images from MJy/sr to solar luminosities
        self.images["70mu"] *= 10.0**exponent_70
        self.images["160mu"] *= 10.0**exponent_160

        # Set the new unit
        self.images["70mu"].unit = "Lsun"
        self.images["160mu"].unit = "Lsun"

    # -----------------------------------------------------------------

    def make_dust_map(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Creating the dust attenuation map ...")

        # Dust = FUV attenuation = ratio of TIR and FUV luminosity


        ### CALCULATE FUV AND TIR MAP IN W/M2 UNIT

        # Convert the FUV map from MJy/sr to W/m2
        factor = - 20.0 + np.log10(3e8) - np.log10(0.153e-6) + (2*np.log10(2.85/206264.806247))
        fuv_converted = self.images["FUV"] * 10.0**factor

        # Get the TIR map in solar units
        tir_map = self.get_tir_map()

        # Convert the TIR frame from solar units to W/m2
        exponent = np.log10(3.846e26) - np.log10(4*np.pi) - (2.0*np.log10(self.distance_mpc*3.08567758e22))
        tir_map *= 10.0**exponent


        # CALCULATE TIR TO FUV RATIO (AND POWERS THEREOF)

        # The ratio of TIR and FUV
        tir_to_fuv = np.log10(tir_map/fuv_converted)

        # Calculate powers of tir_to_fuv
        tir_to_fuv2 = np.power(tir_to_fuv, 2.0)
        tir_to_fuv3 = np.power(tir_to_fuv, 3.0)
        tir_to_fuv4 = np.power(tir_to_fuv, 4.0)

        # Ouput TIR to FUV ratio
        tir_to_fuv.save(self.config.dust.tir_to_fuv_output_path)

        ### CREATE FUV ATTENUATION MAP

        #a_fuv_buat = (-0.0333*x3) + (0.3522*x2) + (1.1960*x) + 0.4967

        # Create an empty image
        a_fuv_cortese = Frame.zeros_like(tir_to_fuv)

        limits = []
        a = []
        b = []
        c = []
        d = []
        e = []

        limits.append((None, 4.0))
        a.append(0.50994)
        b.append(0.88311)
        c.append(0.53315)
        d.append(0.04004)
        e.append(0.04883)

        limits.append((4.0, 4.2))
        a.append(0.49867)
        b.append(0.86377)
        c.append(0.51952)
        d.append(0.04038)
        e.append(0.04624)

        limits.append((4.2, 4.6))
        a.append(0.49167)
        b.append(0.85201)
        c.append(0.51152)
        d.append(0.04060)
        e.append(0.04475)

        limits.append((4.6, 5.0))
        a.append(0.48223)
        b.append(0.83642)
        c.append(0.50127)
        d.append(0.04092)
        e.append(0.04288)

        limits.append((5.0, 5.4))
        a.append(0.46909)
        b.append(0.81520)
        c.append(0.48787)
        d.append(0.04138)
        e.append(0.04050)

        limits.append((5.4, 5.8))
        a.append(0.45013)
        b.append(0.78536)
        c.append(0.47009)
        d.append(0.04210)
        e.append(0.03745)

        limits.append((5.8, 6.3))
        a.append(0.42168)
        b.append(0.74191)
        c.append(0.44624)
        d.append(0.04332)
        e.append(0.03362)

        limits.append((6.3, 6.6))
        a.append(0.40210)
        b.append(0.71272)
        c.append(0.43139)
        d.append(0.04426)
        e.append(0.03140)

        limits.append((6.6, 6.9))
        a.append(0.37760)
        b.append(0.67674)
        c.append(0.41420)
        d.append(0.04555)
        e.append(0.02900)

        limits.append((6.9, 7.2))
        a.append(0.34695)
        b.append(0.63224)
        c.append(0.39438)
        d.append(0.04739)
        e.append(0.02650)

        limits.append((7.2, 7.5))
        a.append(0.30899)
        b.append(0.57732)
        c.append(0.37157)
        d.append(0.05000)
        e.append(0.02399)

        limits.append((7.5, 7.8))
        a.append(0.26302)
        b.append(0.51013)
        c.append(0.34522)
        d.append(0.05377)
        e.append(0.02164)

        limits.append((7.8, 8.1))
        a.append(0.20982)
        b.append(0.42980)
        c.append(0.31431)
        d.append(0.05909)
        e.append(0.01957)

        limits.append((8.1, 8.4))
        a.append(0.15293)
        b.append(0.33799)
        c.append(0.27713)
        d.append(0.06638)
        e.append(0.01792)

        limits.append((8.4, 8.8))
        a.append(0.09944)
        b.append(0.24160)
        c.append(0.23161)
        d.append(0.07580)
        e.append(0.01671)

        limits.append((8.8, 9.2))
        a.append(0.05822)
        b.append(0.15524)
        c.append(0.17801)
        d.append(0.08664)
        e.append(0.01593)

        limits.append((9.2, 9.6))
        a.append(0.03404)
        b.append(0.09645)
        c.append(0.12452)
        d.append(0.09679)
        e.append(0.01548)

        limits.append((9.6, 10.0))
        a.append(0.02355)
        b.append(0.06934)
        c.append(0.08725)
        d.append(0.10339)
        e.append(0.01526)

        limits.append((10.0, 10.5))
        a.append(0.02025)
        b.append(0.06107)
        c.append(0.07212)
        d.append(0.10588)
        e.append(0.01517)

        # Calculate the specific star formation map
        ssfr = self.get_ssfr_map()

        # Create the FUV attenuation map
        for i in range(len(limits)):

            if limits[i][0] is None: where = ssfr < limits[i][1]
            elif limits[i][1] is None: where = ssfr > limits[i][0]
            else: where = (ssfr >= limits[i][0]) * (ssfr < limits[i][1])

            # Set the appropriate pixels
            a_fuv_cortese[where] = a[i] + b[i]*tir_to_fuv[where] + c[i]*tir_to_fuv2[where] + d[i]*tir_to_fuv3[where] - e[i]*tir_to_fuv4[where]

        # Set attenuation to zero where sSFR is smaller than zero
        a_fuv_cortese[ssfr < 0.0] = 0.0

        # Set attenuation to zero where sSFR is greater than 10.5
        a_fuv_cortese[ssfr >= 10.5] = 0.0

        # Set attenuation to zero where the original FUV map is smaller than zero
        a_fuv_cortese[self.fuv <= 0.0] = 0.0

        # Mask pixels outside of the low signal-to-noise contour
        a_fuv_cortese[self.mask] = 0.0

        # Make sure all pixel values are larger than or equal to zero
        a_fuv_cortese[a_fuv_cortese < 0.0] = 0.0

        # Save the dust (FUV attenuation) map as a FITS file
        a_fuv_cortese.save(self.config.dust.output_path)

    # -----------------------------------------------------------------

    def make_old_stars_map(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Creating old stars map")

        # Old stars = IRAC3.6 - bulge
        # From the IRAC 3.6 micron map, we must subtract the bulge component to only retain the disk emission

        # Calculate factor
        flux3_6 = 60541.038
        factor = 0.54 * flux3_6 / self.bulge.sum()

        # Create the old stars map
        old_stars = self.irac - factor*self.bulge

        # Set the old stars map zero for pixels with low signal-to-noise in the 3.6 micron image
        old_stars[self.irac < self.config.old_stars.irac_snr_level*self.irac_errors] = 0.0

        # Make sure all pixel values are larger than or equal to zero
        old_stars[old_stars < 0.0] = 0.0

        # Mask pixels outside of the low signal-to-noise contour
        old_stars[self.mask] = 0.0

        # Save the old stars map as a FITS file
        old_stars.save(self.config.old_stars.output_path)

    # -----------------------------------------------------------------

    def make_non_ionizing_stars_map(self):

        """
        This function ...
        :return:
        """

        # Calculate the non ionizing young stars map from the FUV data
        non_ionizing_stars = self.fuv_young_stars

        # Save the non-ionizing stars map as a FITS file
        non_ionizing_stars.save(self.config.non_ionizing_stars.output_path)

    # -----------------------------------------------------------------

    def make_ionizing_stars_map(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Creating the ionizing young stars map")

        ## HA HAS BEEN CONVERTED TO LSUN (ABOVE)

        #Young ionizing stars = Ha + 0.031 x MIPS24

        ### CALCULATE THE IONIZING STARS MAP BASED ON THE CONVERTED H ALPHA AND THE DISK-SUBTRACTED 24 MICRON IMAGE

        # Calculate the young stellar contribution to the 24 micron image
        mips_young_stars = self.mips_young_stars

        # Save the mips_young_stars map
        mips_young_stars.save(self.config.ionizing_stars.mips_young_stars.output_path)

        # Calculate ionizing stars map and ratio
        ionizing = self.ha + 0.031*mips_young_stars
        #ionizing_ratio = self.ha / (0.031*mips_young_stars)


        ### MASK NEGATIVE AND LOW SIGNAL-TO-NOISE PIXELS

        # Set pixels to zero with low signal-to-noise in the H Alpha image
        ionizing[self.ha < self.config.ionizing_stars.ha_snr_level*self.ha_errors] = 0.0
        #ionizing_ratio[self.ha < self.config.ionizing_stars.ha_snr_level*self.ha_errors] = 0.0

        # Set pixels to zero with low signal-to-noise in the 24 micron image
        ionizing[self.mips < self.config.ionizing_stars.mips_snr_level*self.mips_errors] = 0.0
        #ionizing_ratio[self.mips < self.config.ionizing_stars.mips_snr_level*self.mips_errors] = 0.0

        # Make sure all pixel values are larger than or equal to zero
        ionizing[ionizing < 0.0] = 0.0
        #ionizing_ratio[ionizing < 0.0] = 0.0

        # Save the ionizing stars map
        ionizing.save(self.config.ionizing_stars.output_path)

    # -----------------------------------------------------------------

    def get_ssfr_map(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Creating the specific star formation map")

        # Young non-ionizing stars (specific star formation rate) = GALEXFUV - H
        #fuv_h = -2.5*(np.log10(self.fuv) - np.log10(self.h))

        ratio = self.fuv / self.h

        # Save ...
        ratio.save(self.config.dust.ssfr.color_output_path)

        fuv_h = -2.5*np.log10(self.fuv/self.h)

        # Save ...
        fuv_h.save(self.config.dust.ssfr.with_nans_output_path)

        # Mask nans in the sSFR map
        fuv_h.replace_nans(0.0)

        # Mask pixels outside of the low signal-to-noise contour
        fuv_h[self.mask] = 0.0

        # Set negative pixels to zero
        fuv_h[fuv_h < 0.0] = 0.0

        # Mask low sigal-to-noise pixels in the fuv map, if requested
        if self.config.ssfr.mask_low_fuv_snr: fuv_h[self.fuv < self.config.ssfr.fuv_snr_level*self.fuv_errors] = 0.0

        # Save the resulting sSFR map
        fuv_h.save(self.config.dust.ssfr.output_path)

        return fuv_h

    # -----------------------------------------------------------------

    def get_tir_map(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Creating the TIR map")

        ### MIPS, PACSBLUE AND PACSRED CONVERTED TO LSUN (ABOVE)

        # Galametz (2013) formula for Lsun units
        tir_data = (2.133*self.mips) + (0.681*self.pacsblue) + (1.125*self.pacsred)

        # Return the TIR map  (in solar units)
        return tir_data

    # -----------------------------------------------------------------

    def get_fuv_young_stars_map(self):

        """
        This function ...
        :return:
        """

        ## Subtract old stellar contribution from FUV and MIPS 24 emission

        #     From the FUV and 24 micron maps we must subtract the diffuse radiation (old stellar contribution),
        #     for this we typically use an exponential disk
        #     (scale length detemermined by GALFIT)

        # TODO: calculate this flux value
        flux_fuv = 855.503

        self_flux_fuv = self.fuv.sum()

        # Assert flux calculation is correct
        #assert int(flux_fuv) == int(self_flux_fuv), "FLUX FUV DOES NOT MATCH: " + str(flux_fuv) + " =/= " + str(self_flux_fuv)
        #self.log.warning("Flux FUV = " + str(flux_fuv) + " <> " + str(self_flux_fuv))

        #typisch 20% en 35% respectievelijk
        #48% voor MIPS 24 komt van Lu et al. 2014

        factor = 0.2 * flux_fuv/self.disk.sum()

        #print("factor=", factor)

        # Subtract the disk contribution to the FUV image
        new_fuv = self.fuv - factor * self.disk

        # Make sure all pixels of the disk-subtracted maps are larger than or equal to zero
        new_fuv[new_fuv < 0.0] = 0.0

        # Set zero where low signal-to-noise ratio
        new_fuv[self.fuv < self.config.non_ionizing_stars.fuv_snr_level*self.fuv_errors] = 0.0

        # Return the new FUV frame
        return new_fuv

    # -----------------------------------------------------------------

    def get_mips_young_stars_map(self):

        """
        This function ...
        :return:
        """

        ## Subtract old stellar contribution from FUV and MIPS 24 emission

        #     From the FUV and 24 micron maps we must subtract the diffuse radiation (old stellar contribution),
        #     for this we typically use an exponential disk
        #     (scale length detemermined by GALFIT)

        ## MIPS HAS BEEN CONVERTED TO LSUN (ABOVE)

        # TODO: calculate this flux value
        flux_mips = 27790.448

        self_flux_mips = self.mips.sum()

        # Assert flux calculation is correct
        #assert int(flux_mips) == int(self_flux_mips), "FLUX MIPS DOES NOT MATCH: " + str(flux_mips) + " =/= " + str(self_flux_mips)
        #self.log.warning("Flux 24 micron = " + str(flux_mips) + " <> " + str(self_flux_mips))

        #typisch 20% en 35% respectievelijk
        #48% voor MIPS 24 komt van Lu et al. 2014

        factor = 0.48*flux_mips/self.disk.sum()

        # Subtract the disk contribution to the 24 micron image
        new_mips = self.mips - factor*self.disk

        # Make sure all pixels of the disk-subtracted maps are larger than or equal to zero
        new_mips[new_mips < 0.0] = 0.0

        # Set zero where low signal-to-noise ratio
        new_mips[self.mips < self.config.ionizing_stars.mips_young_stars.mips_snr_level*self.mips_errors] = 0.0

        # Return the new 24 micron frame
        return new_mips

# -----------------------------------------------------------------
