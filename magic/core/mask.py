#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.mask Contains the Mask class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import astronomical modules
from astropy.io import fits
from reproject import reproject_exact, reproject_interp

# Import the relevant PTS classes and modules
from ...core.basics.log import log
from ..basics.mask import MaskBase
from ..basics.mask import Mask as oldMask

# -----------------------------------------------------------------

class Mask(MaskBase):
    
    """
    This class ...
    """

    def __init__(self, data, **kwargs):

        """
        The constructor ...
        :param data:
        :param kwargs:
        """

        # Call the constructor of the base class
        super(Mask, self).__init__(data, **kwargs)

        # Set the WCS
        self.wcs = kwargs.pop("wcs", None)

        # The path
        self.path = None

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, index=None, plane=None, hdulist_index=None):

        """
        This function ...
        :param path:
        :param index:
        :param plane:
        :param hdulist_index:
        :return:
        """

        name = None
        description = None
        no_filter = True
        fwhm = None
        add_meta = False

        from . import fits as pts_fits  # Import here because io imports SegmentationMap

        try:
            # PASS CLS TO ENSURE THIS CLASSMETHOD WORKS FOR ENHERITED CLASSES!!
            mask = pts_fits.load_frame(cls, path, index, name, description, plane, hdulist_index, no_filter, fwhm, add_meta=add_meta)
        except TypeError: raise IOError("The file is possibly damaged")

        # Set the path
        mask.path = path

        # Return the mask
        return mask

    # -----------------------------------------------------------------

    @property
    def has_wcs(self):

        """
        This function ...
        :return:
        """

        return self.wcs is not None

    # -----------------------------------------------------------------

    @property
    def header(self):

        """
        This function ...
        :return:
        """

        # If the WCS for this frame is defined, use it to create a header
        if self.wcs is not None: header = self.wcs.to_header()

        # Else, create a new empty header
        else: header = fits.Header()

        # Add properties to the header
        header['NAXIS'] = 2
        header['NAXIS1'] = self.xsize
        header['NAXIS2'] = self.ysize

        # Return the header
        return header

    # -----------------------------------------------------------------

    def rebin(self, reference_wcs, exact=False, parallel=True, threshold=0.5):

        """
        This function ...
        :param reference_wcs:
        :param exact:
        :param parallel:
        :param threshold:
        :return:
        """

        # Check whether the frame has a WCS
        if not self.has_wcs: raise RuntimeError("Cannot rebin a mask without coordinate system")

        # Calculate rebinned data and footprint of the original image
        if exact: new_data, footprint = reproject_exact((self._data.astype(int), self.wcs), reference_wcs, shape_out=reference_wcs.shape, parallel=parallel)
        else: new_data, footprint = reproject_interp((self._data.astype(int), self.wcs), reference_wcs, shape_out=reference_wcs.shape)

        #print(new_data)
        #print(np.sum(np.isnan(new_data)))
        #print(new_data > threshold)

        #print(np.isnan(new_data))
        mask_data = np.logical_or(new_data > threshold, np.isnan(new_data))
        #print(mask_data)

        # Replace the data and WCS
        self._data = mask_data
        self._wcs = reference_wcs.copy()

        # Return the footprint
        from .frame import Frame
        return Frame(footprint, wcs=reference_wcs.copy())

    # -----------------------------------------------------------------

    def rebinned(self, reference_wcs, exact=False, parallel=True):

        """
        This function ...
        :param reference_wcs:
        :return:
        """

        new = self.copy()
        new.rebin(reference_wcs, exact=exact, parallel=parallel)
        return new

    # -----------------------------------------------------------------

    def to_rgb(self, colour="black", background_color="white"):

        """
        This function ...
        :param colour:
        :param background_color:
        :return:
        """

        from .rgb import RGBImage
        return RGBImage.from_mask(self, colour=colour, background_color=background_color)

    # -----------------------------------------------------------------

    def to_rgba(self, colour="black"):

        """
        This function ...
        :param colour:
        :return:
        """

        from .rgba import RGBAImage
        return RGBAImage.from_mask(self, colour=colour)

    # -----------------------------------------------------------------

    def save(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Saving the mask ...")

        # Check whether the path is valid
        if self.path is None: raise RuntimeError("Path is not defined")

        # Save
        self.saveto(self.path)

    # -----------------------------------------------------------------

    def saveto(self, path, header=None, update_path=True, colour="black", background_color="white"):

        """
        This function ...
        :param path:
        :param header:
        :param update_path:
        :param colour:
        :param background_color:
        :return:
        """

        # FITS format
        if path.endswith(".fits"): self.saveto_fits(path, header=header, update_path=update_path)

        # ASDF format
        elif path.endswith(".asdf"): self.saveto_asdf(path, header=header, update_path=update_path)

        # PNG format
        elif path.endswith(".png"): self.saveto_png(path, colour=colour, background_color=background_color)

        # Invalid
        else: raise ValueError("Invalid file format")

    # -----------------------------------------------------------------

    def saveto_fits(self, path, header=None, update_path=True):

        """
        This function ...
        :param path:
        :param header:
        :param update_path:
        :return:
        """

        # If a header is not specified, created it from the WCS
        if header is None: header = self.header

        from .fits import write_frame  # Import here because io imports Mask

        # Write to a FITS file
        write_frame(self._data.astype(int), header, path)

        # Update the path
        if update_path: self.path = path

    # -----------------------------------------------------------------

    def saveto_asdf(self, path, header=None, update_path=True):

        """
        This function ...
        :param path:
        :param header:
        :param update_path:
        :return:
        """

        # If a header is not specified, created it from the WCS
        if header is None: header = self.header

        # Import
        from asdf import AsdfFile

        # Create the tree
        tree = dict()

        tree["data"] = self._data
        tree["header"] = header

        # Create the asdf file
        ff = AsdfFile(tree)

        # Write
        ff.write_to(path)

        # Update the path
        if update_path: self.path = path

    # -----------------------------------------------------------------

    def saveto_png(self, path, colour="black", background_color="white", alpha=False):

        """
        This function ...
        :param path:
        :param colour:
        :param background_color:
        :param alpha:
        :return:
        """

        # Get RGB image
        if alpha: image = self.to_rgba(colour=colour)
        else: image = self.to_rgb(colour=colour, background_color=background_color)

        # Save RGB image
        image.saveto(path)

# -----------------------------------------------------------------

def union(*args):

    """
    This function ...
    :param args:
    :return:
    """

    # UNION = 0 + first + second + ... (0 is neutral element for sum)
    # so for one mask, union = 0 + mask = mask

    if len(args) == 1: return Mask(args[0])

    #arrays = [arg.data for arg in args]
    arrays = []
    for arg in args:
        if isinstance(arg, MaskBase): arrays.append(arg.data)
        elif isinstance(arg, oldMask): arrays.append(arg)
        else: arrays.append(arg)
    return Mask(np.sum(arrays, axis=0))

# -----------------------------------------------------------------

def intersection(*args):

    """
    This function ...
    :param args:
    :return:
    """

    # INTERSECTION = 1 * first * second * ... (1 is neutral element for multiplication)
    # so for one mask, intersection = 1 * mask = mask

    if len(args) == 1: return Mask(args[0])

    #arrays = [arg.data for arg in args]
    arrays = []
    for arg in args:
        if isinstance(arg, MaskBase): arrays.append(arg.data)
        elif isinstance(arg, oldMask): arrays.append(arg)
        else: arrays.append(arg)
    return Mask(np.product(arrays, axis=0))

# -----------------------------------------------------------------
