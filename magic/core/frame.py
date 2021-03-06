#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.frame Contains the Frame class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import copy
import numpy as np
import urllib
from scipy import ndimage
import tempfile
from sys import getsizeof

# Import astronomical modules
from reproject import reproject_exact, reproject_interp
from astropy.io import fits
from astropy.convolution import convolve, convolve_fft
from astropy.nddata import NDDataArray
from astropy.units import UnitConversionError
from astropy.coordinates import Angle

# Import the relevant PTS classes and modules
from .cutout import Cutout
from ..basics.vector import Position
from ..region.rectangle import SkyRectangleRegion, PixelRectangleRegion
from ..basics.coordinate import SkyCoordinate
from ..basics.stretch import SkyStretch
from ..tools import cropping
from ...core.basics.log import log
from ..basics.mask import Mask, MaskBase
from ...core.tools import filesystem as fs
from ...core.tools import archive
from ..basics.vector import Pixel
from ...core.units.unit import PhotometricUnit
from ...core.filter.filter import parse_filter
from .mask import Mask as newMask
from .alpha import AlphaMask
from ..convolution.kernels import get_fwhm, has_variable_fwhm
from ...core.tools import types
from ...core.units.parsing import parse_unit as u
from ..basics.vector import PixelShape
from ...core.tools.stringify import tostr
from ...core.units.stringify import represent_unit
from ..basics.pixelscale import Pixelscale
from ..dist_ellipse import distance_ellipse
from ..basics.vector import Pixel
from ..region.region import PixelRegion

# -----------------------------------------------------------------

nan_value = float("nan")
inf_value = float("inf")

# -----------------------------------------------------------------

nan_values = [float("nan"), np.NaN]
inf_values = [float("inf"), float("-inf"), np.Inf, -np.Inf]
zero_value = 0.0

# -----------------------------------------------------------------

def get_filter(frame_path):

    """
    Ths function allows getting the filter of a frame without loading the entire frame
    :param frame_path: 
    :return: 
    """

    from ..tools import headers
    header = fits.getheader(frame_path)
    fltr = headers.get_filter(fs.name(frame_path[:-5]), header)
    return fltr

# -----------------------------------------------------------------

def get_filter_name(frame_path):

    """
    This function ...
    :param frame_path:
    :return:
    """

    return str(get_filter(frame_path))

# -----------------------------------------------------------------

class Frame(NDDataArray):

    """
    This class ...
    """

    # Set the default extension
    default_extension = "fits"

    # -----------------------------------------------------------------

    def __init__(self, data, *args, **kwargs):

        """
        This function ...
        :param data:
        :param kwargs:
        """

        # Check the data
        #if data.dtype.type not in types.real_types:
        #    if data.dtype.type in types.integer_types: pass
        #    else: data = np.array(data, dtype=float)

        wcs = kwargs.pop("wcs", None)
        unit = kwargs.pop("unit", None)

        # Set general properties and flags
        self.name = kwargs.pop("name", None)
        self.description = kwargs.pop("description", None)
        self.zero_point = kwargs.pop("zero_point", None)
        self.source_extracted = kwargs.pop("source_extracted", False)
        self.extinction_corrected = kwargs.pop("extinction_corrected", False)
        self.sky_subtracted = kwargs.pop("sky_subtracted", False)

        # Set filter
        self.filter = kwargs.pop("filter", None)

        # Set FWHM
        self._fwhm = kwargs.pop("fwhm", None)

        # Set pixelscale
        self._pixelscale = kwargs.pop("pixelscale", None)
        if self._pixelscale is not None and not isinstance(self._pixelscale, Pixelscale): self._pixelscale = Pixelscale(self._pixelscale)

        # Set wavelength
        self._wavelength = kwargs.pop("wavelength", None)

        # Set meta data
        self.metadata = kwargs.pop("meta", dict())

        # Distance
        self.distance = kwargs.pop("distance", None)

        # PSF FILTER
        self._psf_filter = kwargs.pop("psf_filter", None)

        # The path
        self.path = kwargs.pop("path", None)
        self._from_multiplane = kwargs.pop("from_multiplane", False)

        # Call the constructor of the base class
        super(Frame, self).__init__(data, *args, **kwargs)

        # Set the WCS and unit
        self.wcs = wcs # go through the setter
        self.unit = unit # go through the setter

    # -----------------------------------------------------------------

    @property
    def shape(self):

        """
        This function ...
        :return:
        """

        return PixelShape.from_tuple(super(Frame, self).shape)

    # -----------------------------------------------------------------

    @property
    def filter_name(self):

        """
        This function ...
        :return: 
        """

        return str(self.filter) if self.filter is not None else None

    # -----------------------------------------------------------------

    @property
    def psf_filter(self):

        """
        This function ...
        :return: 
        """

        # FILTER CAN BE DIFFERENT FROM PSF FILTER !! E.G. FUV IMAGE CONVOLVED TO RESOLUTION OF HERSCHEL BAND

        # BUT: if PSFFLTR WAS NOT FOUND IN HEADER, AND THUS PRESENT AS _PSF_FILTER, ASSUME PSF_FILTER = FILTER (ORIGINAL IMAGE)
        if self._psf_filter is None: return self.filter
        else: return self._psf_filter

    # -----------------------------------------------------------------

    @psf_filter.setter
    def psf_filter(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        if types.is_string_type(value): value = parse_filter(value)
        self._psf_filter = value

    # -----------------------------------------------------------------

    @property
    def psf_filter_name(self):

        """
        This function ...
        :return: 
        """

        return str(self.psf_filter) if self.psf_filter is not None else None

    # -----------------------------------------------------------------

    @property
    def fwhm(self):

        """
        This function ...
        :return: 
        """

        # Find the FWHM for the filter
        if self._fwhm is not None: return self._fwhm
        elif self.psf_filter is not None and not has_variable_fwhm(self.psf_filter): return get_fwhm(self.psf_filter)
        else: return None

    # -----------------------------------------------------------------

    @fwhm.setter
    def fwhm(self, value):

        """
        This function ...
        :param value: 
        :return: 
        """

        self._fwhm = value

    # -----------------------------------------------------------------

    @property
    def data(self):

        """
        This function ...
        :return:
        """

        return self._data

    # -----------------------------------------------------------------

    @NDDataArray.wcs.setter
    def wcs(self, wcs):

        """
        This function ...
        :param wcs:
        :return:
        """

        self._wcs = wcs

    # -----------------------------------------------------------------

    @property
    def has_wcs(self):

        """
        This function ...
        :return:
        """

        return self.wcs is not None

    # -----------------------------------------------------------------

    @NDDataArray.unit.setter
    def unit(self, unit):

        """
        This function ...
        :param unit:
        :return:
        """

        # Convert string units to PhotometricUnit object
        if types.is_string_type(unit): unit = PhotometricUnit(unit)

        # Set the unit
        self._unit = unit

    # -----------------------------------------------------------------

    @property
    def has_unit(self):

        """
        This function ...
        :return:
        """

        return self.unit is not None

    # -----------------------------------------------------------------

    @property
    def filter(self):

        """
        This function ...
        :return:
        """

        return self._filter

    # -----------------------------------------------------------------

    @filter.setter
    def filter(self, fltr):

        """
        This function ...
        """

        if fltr is None: self._filter = None
        else: self._filter = parse_filter(fltr)

    # -----------------------------------------------------------------

    def __getitem__(self, item):

        """
        This function ...
        :param item:
        :return:
        """

        if isinstance(item, MaskBase): return self._data[item.data]
        elif isinstance(item, Pixel): return self._data[item.y, item.x]
        else: return self._data[item]

    # -----------------------------------------------------------------

    def __setitem__(self, item, value):

        """
        This function ...
        :param item:
        :return:
        """

        if isinstance(item, MaskBase): self._data[item.data] = value
        elif isinstance(item, Pixel): self._data[item.y, item.x] = value
        elif isinstance(item, tuple): self._data[item[0], item[1]] = value
        else: self._data[item] = value

    # -----------------------------------------------------------------

    def __eq__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__eq__(other)

    # -----------------------------------------------------------------

    def __ne__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__ne__(other)

    # -----------------------------------------------------------------

    def __gt__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__gt__(other)

    # -----------------------------------------------------------------

    def __ge__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__ge__(other)

    # -----------------------------------------------------------------

    def __lt__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__lt__(other)

    # -----------------------------------------------------------------

    def __le__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        return self._data.__le__(other)

    # -----------------------------------------------------------------

    def __mul__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.copy().__imul__(value)

    # -----------------------------------------------------------------

    def __rmul__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.__mul__(value)

    # -----------------------------------------------------------------

    def __imul__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self.__array__

        self._data *= value
        return self

    # -----------------------------------------------------------------

    def __add__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.copy().__iadd__(value)

    # -----------------------------------------------------------------

    def __radd__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.__add__(value)

    # -----------------------------------------------------------------

    def __iadd__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data += value
        return self

    # -----------------------------------------------------------------

    def __sub__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.copy().__isub__(value)

    # -----------------------------------------------------------------

    def __rsub__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        new = self.copy()
        new._data = value - new._data
        return new

    # -----------------------------------------------------------------

    def __isub__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data -= value
        return self

    # -----------------------------------------------------------------

    def __div__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.copy().__idiv__(value)

    # -----------------------------------------------------------------

    def __rdiv__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        new = self.copy()
        new._data = value / new._data
        return new

    # -----------------------------------------------------------------

    def __idiv__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data /= value
        return self

    # -----------------------------------------------------------------

    def __truediv__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.__div__(value)

    # -----------------------------------------------------------------

    def __itruediv__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.__idiv__(value)

    # -----------------------------------------------------------------

    def __pow__(self, power):

        """
        This function ...
        :param power:
        :return:
        """

        return self.copy().__ipow__(power)

    # -----------------------------------------------------------------

    def __ipow__(self, power):

        """
        This function ...
        :param power:
        :return:
        """

        self._data **= power
        return self

    # -----------------------------------------------------------------

    def __abs__(self):

        """
        This function ...
        :return:
        """

        new = self.copy()
        new._data = abs(self._data)
        return new

    # -----------------------------------------------------------------

    def log10(self):

        """
        This function ...
        :return: 
        """

        # Replace the data
        self._data = np.log10(self.data)

        # Set the unit to None
        self.unit = None

    # -----------------------------------------------------------------

    def get_log10(self):

        """
        This function ...
        :return: 
        """

        new = self.copy()
        new.log10()
        return new

    # -----------------------------------------------------------------

    def log(self):

        """
        This function ...
        :return: 
        """

        # Replace the data
        self._data = np.log(self.data)

        # Set the unit to None
        self.unit = None

    # -----------------------------------------------------------------

    def get_log(self):

        """
        THis function ...
        :return: 
        """

        new = self.copy()
        new.log10()
        return new

    # -----------------------------------------------------------------

    @classmethod
    def from_url(cls, url, index=None, name=None, description=None, plane=None, hdulist_index=None, no_filter=False,
                  fwhm=None, add_meta=True, distance=None):

        """
        This function ...
        :param url:
        :param index:
        :param name:
        :param description:
        :param plane:
        :param hdulist_index:
        :param no_filter:
        :param fwhm:
        :param add_meta:
        :param distance:
        :return:
        """

        # Inform the user
        log.info("Downloading file " + url + " ...")

        # Local path
        temp_path = tempfile.gettempdir()
        filename = fs.name(url)
        local_path = fs.join(temp_path, filename)

        # Download
        urllib.urlretrieve(url, local_path)

        if local_path.endswith(".fits"): fits_path = local_path
        else:

            # Inform the user
            log.info("Decompressing kernel file ...")

            # Fits path
            fits_path = fs.join(temp_path, fs.strip_extension(filename))

            # Decompress the kernel FITS file
            archive.decompress_file(local_path, fits_path)

            # Remove the compressed file
            fs.remove_file(local_path)

        # Open the FITS file
        return cls.from_file(fits_path, index, name, description, plane, hdulist_index, no_filter, fwhm, add_meta, distance=distance)

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, index=None, name=None, description=None, plane=None, hdulist_index=None, no_filter=False,
                  fwhm=None, add_meta=True, extra_meta=None, silent=False, distance=None):

        """
        This function ...
        :param path:
        :param index:
        :param name:
        :param description:
        :param plane:
        :param hdulist_index: if None, is automatically decided based on where the imageHDU is.
        :param no_filter:
        :param fwhm:
        :param add_meta:
        :param extra_meta:
        :param silent:
        :param distance:
        :return:
        """

        # Show which image we are importing
        if not silent: log.info("Reading in file '" + path + "' ...")

        from ..core.fits import load_frame
        # PASS CLS TO ENSURE THIS CLASSMETHOD WORKS FOR ENHERITED CLASSES!!
        try: return load_frame(cls, path, index, name, description, plane, hdulist_index, no_filter, fwhm, add_meta=add_meta, extra_meta=extra_meta, distance=distance)
        except TypeError: raise IOError("File is possibly damaged")

    # -----------------------------------------------------------------

    def copy(self):

        """
        This function ...
        :return:
        """

        return copy.deepcopy(self)

    # -----------------------------------------------------------------

    def apply_mask(self, mask, fill=0.0, invert=False):

        """
        This function ...
        :param mask:
        :param fill:
        :param invert:
        """

        if invert: self[mask.inverse()] = fill
        else: self[mask] = fill

    # -----------------------------------------------------------------

    def applied_mask(self, mask, fill=0.0, invert=False):

        """
        This function ...
        :param mask:
        :param fill:
        :param invert:
        :return:
        """

        new = self.copy()
        new.apply_mask(mask, fill=fill, invert=invert)
        return new

    # -----------------------------------------------------------------

    def apply_alpha_mask(self, mask, invert=False):

        """
        This function ...
        :param mask:
        :param invert:
        :return:
        """

        data = mask.as_real()
        #print(data)
        if invert: data = 1. - data

        # Multiply the data with the alpha mask
        self._data *= data

    # -----------------------------------------------------------------

    def applied_alpha_mask(self, mask, invert=False):

        """
        This function ...
        :param mask:
        :param invert:
        :return:
        """

        new = self.copy()
        new.apply_alpha_mask(mask, invert=invert)
        return new

    # -----------------------------------------------------------------

    @property
    def all_zero(self):

        """
        This function ...
        :return:
        """

        return np.all(np.equal(self._data, 0))

    # -----------------------------------------------------------------

    @property
    def all_nonzero(self):

        """
        This function ...
        :return:
        """

        return not np.any(np.equal(self._data, 0))

    # -----------------------------------------------------------------

    def where(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.equal(self._data, value), wcs=self.wcs.copy() if self.wcs is not None else None)
        #return newMask(self._data == value)

    # -----------------------------------------------------------------

    def where_not(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.not_equal(self._data, value), wcs=self.wcs.copy() if self.wcs is not None else None)

    # -----------------------------------------------------------------

    def where_smaller_than(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.less(self._data, value))

    # -----------------------------------------------------------------

    def where_smaller_than_or_equal(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.less_equal(self._data, value))

    # -----------------------------------------------------------------

    def where_greater_than(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.greater(self._data, value))

    # -----------------------------------------------------------------

    def where_greater_than_or_equal(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return newMask(np.greater_equal(self._data, value))

    # -----------------------------------------------------------------

    @property
    def nans(self):

        """
        This function ...
        :return:
        """

        #from .mask import union
        #return union(*[self.where(value) for value in nan_values])
        return newMask(np.isnan(self.data), wcs=self.wcs.copy() if self.wcs is not None else None)

    # -----------------------------------------------------------------

    @property
    def nans_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.where(self.nans))]

    # -----------------------------------------------------------------

    @property
    def nnans(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.nans.data)

    # -----------------------------------------------------------------

    @property
    def has_nans(self):

        """
        This function ...
        :return:
        """

        return np.any(self.nans.data)

    # -----------------------------------------------------------------

    @property
    def all_nans(self):

        """
        This function ...
        """

        return np.all(self.nans.data)

    # -----------------------------------------------------------------

    @property
    def infs(self):

        """
        This function ...
        :return:
        """

        #from .mask import union
        #return union(*[self.where(value) for value in inf_values])
        return newMask(np.isinf(self.data), wcs=self.wcs.copy() if self.wcs is not None else None)

    # -----------------------------------------------------------------

    @property
    def infs_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.where(self.infs))]

    # -----------------------------------------------------------------

    @property
    def all_infs(self):

        """
        This function ...
        :return:
        """

        return np.all(self.infs.data)

    # -----------------------------------------------------------------

    @property
    def ninfs(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.infs.data)

    # -----------------------------------------------------------------

    @property
    def has_infs(self):

        """
        This function ...
        :return:
        """

        return np.any(self.infs.data)

    # -----------------------------------------------------------------

    @property
    def zeroes(self):

        """
        This function ...
        :return:
        """

        return self.where(zero_value)

    # -----------------------------------------------------------------

    @property
    def zeroes_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.where(self.zeroes))]

    # -----------------------------------------------------------------

    @property
    def all_zeroes(self):

        """
        This function ...
        :return:
        """

        return np.all(self.zeroes.data)

    # -----------------------------------------------------------------

    @property
    def nzeroes(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.zeroes.data)

    # -----------------------------------------------------------------

    @property
    def has_zeroes(self):

        """
        This function ...
        :return:
        """

        return np.any(self.zeroes.data)

    # -----------------------------------------------------------------

    @property
    def nonzeroes(self):

        """
        This function ...
        :return:
        """

        return self.where_not(0.0)

    # -----------------------------------------------------------------

    @property
    def all_nonzeroes(self):

        """
        This function ...
        :return:
        """

        return np.all(self.nonzeroes.data)

    # -----------------------------------------------------------------

    @property
    def zeroes_x(self):

        """
        This function ...
        :return:
        """

        return np.where(self.zeroes)[1]

    # -----------------------------------------------------------------

    @property
    def zeroes_y(self):

        """
        This function ...
        :return:
        """

        return np.where(self.zeroes)[0]

    # -----------------------------------------------------------------

    @property
    def nonzeroes_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.nonzero(self._data))]

    # -----------------------------------------------------------------

    @property
    def nnonzeroes(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.nonzeroes.data)

    # -----------------------------------------------------------------

    @property
    def nonzeroes_x(self):

        """
        This function ...
        :return:
        """

        return np.nonzero(self._data)[1]

    # -----------------------------------------------------------------

    @property
    def nonzeroes_y(self):

        """
        This function ...
        :return:
        """

        return np.nonzero(self._data)[0]

    # -----------------------------------------------------------------

    @property
    def negatives(self):

        """
        This function ...
        :return:
        """

        return self.where_smaller_than(zero_value)

    # -----------------------------------------------------------------

    @property
    def negatives_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.where(self.negatives))]

    # -----------------------------------------------------------------

    @property
    def nnegatives(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.negatives.data)

    # -----------------------------------------------------------------

    @property
    def has_negatives(self):

        """
        This function ...
        :return:
        """

        return np.any(self.negatives.data)

    # -----------------------------------------------------------------

    @property
    def all_negatives(self):

        """
        This function ...
        """

        return np.all(self.negatives.data)

    # -----------------------------------------------------------------

    @property
    def positives(self):

        """
        This function ...
        :return:
        """

        return self.where_greater_than(zero_value)

    # -----------------------------------------------------------------

    @property
    def positives_pixels(self):

        """
        This function ...
        :return:
        """

        return [Pixel(x, y) for y, x in np.transpose(np.where(self.positives))]

    # -----------------------------------------------------------------

    @property
    def npositives(self):

        """
        This function ...
        :return:
        """

        return np.sum(self.positives.data)

    # -----------------------------------------------------------------

    @property
    def has_positives(self):

        """
        This function ...
        :return:
        """

        return np.any(self.positives.data)

    # -----------------------------------------------------------------

    @property
    def all_positives(self):

        """
        This function ...
        :return:
        """

        return np.all(self.positives.data)

    # -----------------------------------------------------------------

    def nnans_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of nan pixels
        #return np.sum(np.equal(self.data[mask], nan_value))

        # 2nd attempt
        #array = self.data[mask]
        #from .mask import union
        #return np.sum(union(*[np.equal(array, value) for value in nan_values]))

        return np.sum(np.isnan(self.data[mask]))

    # -----------------------------------------------------------------

    def ninfs_in(self, region_or_mask):

        """
        Thisn function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of nan pixels
        #return np.sum(np.equal(self.data[mask], inf_values[0]) + np.equal(self.data[mask], inf_values[1]))

        # 2nd attempt
        #array = self.data[mask]
        #from .mask import union
        #return np.sum(union(*[np.equal(array, value) for value in inf_values]))

        return np.sum(np.isinf(self.data[mask]))

    # -----------------------------------------------------------------

    def nzeroes_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of zero pixels
        return np.sum(np.equal(self.data[mask], zero_value))

    # -----------------------------------------------------------------

    def nnegatives_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of negative pixels
        return np.sum(np.less(self.data[mask], zero_value))

    # -----------------------------------------------------------------

    def npositives_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of positive pixels
        return np.sum(np.greater(self.data[mask], zero_value))

    # -----------------------------------------------------------------

    @property
    def npixels(self):

        """
        This function ...
        :return:
        """

        return self.xsize * self.ysize

    # -----------------------------------------------------------------

    def npixels_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return the number of pixels
        return np.sum(mask)

    # -----------------------------------------------------------------

    @property
    def unique_values(self):

        """
        This function ...
        :return:
        """

        # Loop over the unique values in the gridded data
        values = np.unique(self._data)
        return list(values)

    # -----------------------------------------------------------------

    @property
    def unique_value_masks(self):

        """
        This function ...
        :return:
        """

        masks = []

        for value in self.unique_values:
            where = self.where(value)
            masks.append(where)

        return masks

    # -----------------------------------------------------------------

    @property
    def unique_values_and_masks(self):

        """
        This function ...
        :return:
        """

        returns = []
        for value in self.unique_values:
            where = self.where(value)
            returns.append((value, where))

        return returns

    # -----------------------------------------------------------------

    @property
    def pixelscale(self):

        """
        This function ...
        :return:
        """

        # Return the pixelscale of the WCS is WCS is defined
        if self.wcs is not None: return self.wcs.pixelscale
        else: return self._pixelscale  # return the pixelscale

    # -----------------------------------------------------------------

    @pixelscale.setter
    def pixelscale(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        if not isinstance(value, Pixelscale): value = Pixelscale(value)
        self._pixelscale = value

    # -----------------------------------------------------------------

    @property
    def average_pixelscale(self):

        """
        This function ...
        :return:
        """

        if self.wcs is not None: return self.wcs.average_pixelscale
        else: return self._pixelscale.average if self._pixelscale is not None else None

    # -----------------------------------------------------------------

    @property
    def pixelarea(self):

        """
        This function ...
        :return:
        """

        try:
            solid = (self.pixelscale.x * self.pixelscale.y).to("sr")
            return solid
        except UnitConversionError:
            log.warning("UNIT CONVERSION ERROR: " + str(self.pixelscale.x) + ", " + str(self.pixelscale.y))
            deg = (self.pixelscale.x * self.pixelscale.y).value
            return (deg * u("deg")).to("sr")

        #return (self.pixelscale.x * self.pixelscale.y).to("sr")

    # -----------------------------------------------------------------

    @classmethod
    def random(cls, shape, wcs=None, filter=None):

        """
        This function ...
        :param shape: 
        :param wcs: 
        :param filter:
        :return: 
        """

        # Create a new frame
        new = cls(np.random.random(shape), wcs=wcs, filter=filter)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def ones(cls, shape, wcs=None, filter=None, unit=None):

        """
        This function ...
        :param shape: 
        :param wcs: 
        :param filter: 
        :return: 
        """

        # Create a new frame
        new = cls(np.ones(shape), wcs=wcs, filter=filter, unit=unit)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def zeros(cls, shape, wcs=None, filter=None, unit=None):

        """
        This function ...
        :param shape:
        :param wcs:
        :param filter:
        :return:
        """

        # Create a new frame
        new = cls(np.zeros(shape), wcs=wcs, filter=filter, unit=unit)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def ones_like(cls, frame):

        """
        This function ...
        :param frame: 
        :return: 
        """

        if hasattr(frame, "wcs"): wcs = frame.wcs
        else: wcs = None

        # Create a new frame
        if hasattr(frame, "_data"): new = cls(np.ones_like(frame._data), wcs=wcs)
        else: new = cls(np.zeros_like(frame), wcs=wcs)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def zeros_like(cls, frame):

        """
        This function ...
        :param frame:
        :return:
        """

        if hasattr(frame, "wcs"): wcs = frame.wcs
        else: wcs = None

        # Create a new frame
        if hasattr(frame, "_data"): new = cls(np.zeros_like(frame._data), wcs=wcs)
        else: new = cls(np.zeros_like(frame), wcs=wcs)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def nans_like(cls, frame):

        """
        This function ...
        :param frame:
        :return:
        """

        # Return a NaN-filled copy of the frame
        nans = cls.zeros_like(frame)
        nans.fill(np.nan)
        return nans

    # -----------------------------------------------------------------

    @classmethod
    def filled_like(cls, frame, value):

        """
        This function ...
        :param frame:
        :param value:
        :return:
        """

        frame = cls.zeros_like(frame)
        frame.fill(value)
        return frame

    # -----------------------------------------------------------------

    @property
    def is_constant(self):

        """
        This function ...
        :return:
        """

        return np.nanmax(self._data) == np.nanmin(self._data)

    # -----------------------------------------------------------------

    def is_constant_in(self, region_or_mask):

        """
        This function ...
        :param region_or_mask:
        :return:
        """

        # Get mask
        if isinstance(region_or_mask, PixelRegion): mask = region_or_mask.to_mask(self.xsize, self.ysize)
        elif isinstance(region_or_mask, Mask): mask = region_or_mask
        else: raise ValueError("Argument must be pixel region or mask")

        # Return whether constant
        return np.nanmax(self.data[mask]) == np.nanmin(self.data[mask])

    # -----------------------------------------------------------------

    @property
    def xsize(self): return self.shape.x

    # -----------------------------------------------------------------

    @property
    def ysize(self): return self.shape.y

    # -----------------------------------------------------------------

    @property
    def fwhm_pix(self):

        """
        This function ...
        :return:
        """

        return (self.fwhm / self.average_pixelscale).to("").value if self.fwhm is not None else None

    # -----------------------------------------------------------------

    @property
    def header(self):

        """
        This function ...
        """

        # If the WCS for this frame is defined, use it to create a header
        if self.wcs is not None: header = self.wcs.to_header()

        # Else, create a new empty header
        else: header = fits.Header()

        # Add properties to the header
        header['NAXIS'] = 2
        header['NAXIS1'] = self.xsize
        header['NAXIS2'] = self.ysize

        # ISSUE: see bug #4592 on Astropy GitHub (WCS.to_header issue)
        # temporary fix !!
        # I don't know whether this is a good fix.. but it seems to fix it for a particular situation
        #if "PC1_1" in header:

            #if "NAXIS1" in header: header.remove("NAXIS1")
            #if "NAXIS2" in header: header.remove("NAXIS2")
            #if "CDELT1" in header: header.remove("CDELT1")
            #if "CDELT2" in header: header.remove("CDELT2")
            #header.rename_keyword("PC1_1", "CD1_1")
            #header.rename_keyword("PC2_2", "CD2_2")

        # Return the header
        return header

    # -----------------------------------------------------------------

    @property
    def wavelength(self):

        """
        This function ...
        :return:
        """

        # Return the wavelength of the frame's filter, if defined
        if self.filter is not None: return self.filter.wavelength
        else: return self._wavelength # return the wavelength (if defined, is None otherwise)

    # -----------------------------------------------------------------

    @wavelength.setter
    def wavelength(self, value):

        """
        This function ...
        :return:
        """

        self._wavelength = value

    # -----------------------------------------------------------------

    @property
    def pivot_wavelength_or_wavelength(self):

        """
        This fucntion ...
        :return: 
        """

        if self.filter is not None: return self.filter.pivot
        else: return self.wavelength
        
    # -----------------------------------------------------------------

    def cutout_around(self, position, radius):

        """
        This function ...
        :param position:
        :param radius:
        :return:
        """

        return Cutout.cutout(self, position, radius)

    # -----------------------------------------------------------------

    def convert_to(self, to_unit, distance=None, density=False, brightness=False, density_strict=False, brightness_strict=False):

        """
        This function ...
        :param to_unit:
        :param distance:
        :param density:
        :param brightness:
        :param density_strict:
        :param brightness_strict:
        :return:
        """

        # Parse "to unit": VERY IMPORTANT, BECAUSE DOING SELF.UNIT = TO_UNIT WILL OTHERWISE REPARSE AND WILL BE OFTEN INCORRECT!! (NO DENSITY OR BRIGHTNESS INFO)
        to_unit = PhotometricUnit(to_unit, density=density, brightness=brightness, brightness_strict=brightness_strict, density_strict=density_strict)

        # Debugging
        log.debug("Converting the frame from unit " + tostr(self.unit, add_physical_type=True) + " to unit " + tostr(to_unit, add_physical_type=True) + " ...")

        # Set the distance
        if distance is None: distance = self.distance

        # Calculate the conversion factor
        factor = self.unit.conversion_factor(to_unit, wavelength=self.pivot_wavelength_or_wavelength, distance=distance,
                                             pixelscale=self.pixelscale, density=density, brightness=brightness,
                                             density_strict=density_strict, brightness_strict=brightness_strict)

        # Debugging
        log.debug("Conversion factor: " + str(factor))

        # Multiply the frame with the conversion factor
        self.__imul__(factor)

        # Set the new unit
        self.unit = to_unit

        # Return the conversion factor
        return factor

    # -----------------------------------------------------------------

    def converted_to(self, to_unit, distance=None, density=False, brightness=False, density_strict=False, brightness_strict=False):

        """
        This function ...
        :param to_unit: 
        :param distance:  
        :param density:
        :param brightness:
        :param density_strict:
        :param brightness_strict:
        :return: 
        """

        new = self.copy()
        new.convert_to(to_unit, distance=distance, density=density, brightness=brightness, density_strict=density_strict, brightness_strict=brightness_strict)
        return new

    # -----------------------------------------------------------------

    @property
    def corresponding_angular_area_unit(self):

        """
        This function ...
        :return: 
        """

        return self.unit.corresponding_angular_area_unit

    # -----------------------------------------------------------------

    def convert_to_corresponding_angular_area_unit(self, distance=None):

        """
        This function ...
        :param distance: 
        :return: 
        """

        self.convert_to(self.corresponding_angular_area_unit, distance=distance)

    # -----------------------------------------------------------------

    def converted_to_corresponding_angular_area_unit(self, distance=None):

        """
        This function ...
        :param distance:  
        :return: 
        """

        #print(self.corresponding_angular_area_unit)
        return self.converted_to(self.corresponding_angular_area_unit, distance=distance)

    # -----------------------------------------------------------------

    def sum(self):

        """
        This function ...
        :return:
        """

        return np.nansum(self._data)

    # -----------------------------------------------------------------

    def quadratic_sum(self):

        """
        This function ...
        :return:
        """

        return np.sqrt(np.sum(self._data[self.nans.inverse()]**2))

    # -----------------------------------------------------------------

    def normalize(self, to=1.0):

        """
        This function ...
        :param to:
        :return:
        """

        # Calculate the sum of all the pixels
        sum = np.nansum(self)

        # Check whether the sum is nonnegative
        if sum < 0: raise RuntimeError("The sum of the frame is negative")

        # Calculate the conversion factor
        if hasattr(to, "unit"): # quantity
            factor = to.value / sum
            unit = to.unit
        else:
            factor = to / sum
            unit = None

        # Debugging
        log.debug("Multiplying the frame with a factor of " + tostr(factor) + " to normalize ...")

        # Multiply the frame with the conversion factor
        try: self.__imul__(factor)
        except TypeError:
            print(np.nanmax(self.data))
            from ..tools import plotting
            plotting.plot_box(self)
            exit()

        # Set the unit to None
        self.unit = unit

    # -----------------------------------------------------------------

    def normalized(self, to=1.):
        
        """
        This function ...
        :param to: 
        :return: 
        """

        new = self.copy()
        new.normalize(to=to)
        return new

    # -----------------------------------------------------------------

    def is_normalized(self, to=1., rtol=1.e-5, atol=1.e-8):

        """
        This function ...
        :param to:
        :param rtol
        :parma atol:
        :return:
        """

        # In some unit
        if hasattr(to, "unit"): # quantity

            total = self.sum() * self.unit
            return np.isclose(total.to(to.unit).value, to.value, atol=atol, rtol=rtol)

        # Numerically
        else: return np.isclose(self.sum(), to, atol=atol, rtol=rtol)

    # -----------------------------------------------------------------

    def convolved(self, *args, **kwargs):

        """
        This function ...
        :return:
        """

        new = self.copy()
        new.convolve(*args, **kwargs)
        return new

    # -----------------------------------------------------------------

    def convolve(self, kernel, allow_huge=True, fft=True):

        """
        This function ...
        :param kernel:
        :param allow_huge:
        :param fft:
        :return:
        """

        # Get the kernel FWHM and PSF filter
        kernel_fwhm = kernel.fwhm
        kernel_psf_filter = kernel.psf_filter

        # Skip the calculation for a constant frame
        if self.is_constant:
            self._fwhm = kernel_fwhm
            self._psf_filter = kernel_psf_filter
            return

        # Check whether the kernel is prepared
        if not kernel.prepared:
            log.warning("The convolution kernel is not prepared, creating a prepared copy ...")
            kernel = kernel.copy()
            kernel.prepare(self.pixelscale)

        # Check where the NaNs are at
        nans_mask = np.isnan(self._data)

        # Assert that the kernel is normalized
        if not kernel.normalized: raise RuntimeError("The kernel is not properly normalized: sum is " + repr(kernel.sum()) + " , difference from unity is " + repr(kernel.sum() - 1.0))

        # Do the convolution on this frame
        if fft: new_data = convolve_fft(self._data, kernel.data, normalize_kernel=False, interpolate_nan=True, allow_huge=allow_huge)
        else: new_data = convolve(self._data, kernel.data, normalize_kernel=False)

        # Put back NaNs
        new_data[nans_mask] = nan_value

        # Replace the data and FWHM
        self._data = new_data
        self._fwhm = kernel_fwhm
        self._psf_filter = kernel_psf_filter

    # -----------------------------------------------------------------

    def rebinned(self, reference_wcs, exact=False, parallel=True):

        """
        This function ...
        :param reference_wcs:
        :param exact:
        :param parallel:
        :return:
        """

        new = self.copy()
        new.rebin(reference_wcs, exact=exact, parallel=parallel)
        return new

    # -----------------------------------------------------------------

    def rebin(self, reference_wcs, exact=False, parallel=True):

        """
        This function ...
        :param reference_wcs:
        :param exact:
        :param parallel:
        :return:
        """

        # Check whether the frame has a WCS
        if not self.has_wcs: raise RuntimeError("Cannot rebin a frame without coordinate system")

        # Check the unit
        #if self.unit is not None and not self.unit.is_per_pixelsize: raise ValueError("Cannot rebin a frame that is expressed per angular area. First convert the units.")

        # Calculate rebinned data and footprint of the original image
        if exact: new_data, footprint = reproject_exact((self._data, self.wcs), reference_wcs, shape_out=reference_wcs.shape, parallel=parallel)
        else: new_data, footprint = reproject_interp((self._data, self.wcs), reference_wcs, shape_out=reference_wcs.shape)

        # Replace the data and WCS
        self._data = new_data
        self._wcs = reference_wcs.copy()

        # Return the footprint
        return Frame(footprint, wcs=reference_wcs.copy())

    # -----------------------------------------------------------------

    def cropped(self, x_min, x_max, y_min, y_max):

        """
        This function ...
        :param x_min:
        :param x_max:
        :param y_min:
        :param y_max:
        :return:
        """

        new = self.copy()
        new.crop(x_min, x_max, y_min, y_max)
        return new

    # -----------------------------------------------------------------

    def crop(self, x_min, x_max, y_min, y_max):

        """
        This function ...
        :param x_min:
        :param x_max:
        :param y_min:
        :param y_max:
        :return:
        """

        # Crop the frame
        new_data = cropping.crop_check(self._data, x_min, x_max, y_min, y_max)

        # Adapt the WCS
        if self.wcs is not None:

            # Copy the current WCS
            new_wcs = self.wcs.copy()

            # Change the center pixel position
            new_wcs.wcs.crpix[0] -= x_min
            new_wcs.wcs.crpix[1] -= y_min

            # Change the number of pixels
            new_wcs.naxis1 = x_max - x_min
            new_wcs.naxis2 = y_max - y_min

            new_wcs._naxis1 = new_wcs.naxis1
            new_wcs._naxis2 = new_wcs.naxis2

        else: new_wcs = None

        # Check shape of data
        assert new_data.shape[1] == (x_max - x_min) and new_data.shape[0] == (y_max - y_min)

        # Replace the data and WCS
        self._data = new_data
        self._wcs = new_wcs

    # -----------------------------------------------------------------

    def cropped_to(self, region, factor=1):

        """
        Ths function ...
        :param region:
        :param factor:
        :return:
        """

        new = self.copy()
        new.crop_to(region, factor=factor)
        return new

    # -----------------------------------------------------------------

    def crop_to(self, region, factor=1.):

        """
        This function ...
        :param region:
        :param factor:
        :return:
        """

        # Pixel rectangle
        if isinstance(region, PixelRectangleRegion):
            if factor != 1: region = region * factor
            self.crop(region.x_min_pixel, region.x_max_pixel, region.y_min_pixel, region.y_max_pixel)

        # Sky rectangle: to pixel rectangle
        elif isinstance(region, SkyRectangleRegion): self.crop_to(region.to_pixel(self.wcs), factor=factor)

        # Other kind of shape
        else: self.crop_to(region.bounding_box, factor=factor)

    # -----------------------------------------------------------------

    def soften_edges(self, region, factor_range):

        """
        This function ...
        :param region:
        :param factor_range:
        :return:
        """

        # Create alpha mask
        alpha = AlphaMask.from_ellipse(region, self.shape, factor_range, wcs=self.wcs)

        # Apply alpha
        self._data *= alpha.as_real()

        # Return the alpha mask
        return alpha

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return Position(self.wcs.wcs.crpix[0], self.wcs.wcs.crpix[1])

    # -----------------------------------------------------------------

    @property
    def pixel_center(self):

        """
        This function ...
        :return:
        """

        return Pixel.for_coordinate(self.center)

    # -----------------------------------------------------------------

    @property
    def center_value(self):

        """
        This function ...
        :return:
        """

        return self.data[self.pixel_center.y, self.pixel_center.x]

    # -----------------------------------------------------------------

    def padded(self, nx=0, ny=0):

        """
        This function ...
        :param nx:
        :param ny:
        :return:
        """

        new = self.copy()
        new.pad(nx, ny)
        return new

    # -----------------------------------------------------------------

    def pad(self, nx=0, ny=0):

        """
        This function ...
        :param nx:
        :param ny:
        :return:
        """

        if nx == 0 and ny == 0: return

        new_data = np.pad(self._data, ((ny,0), (nx,0)), 'constant')

        if self.wcs is not None:

            new_wcs = copy.deepcopy(self.wcs)

            new_wcs.wcs.crpix[0] += nx
            new_wcs.wcs.crpix[1] += ny

            # Change the number of pixels
            new_wcs.naxis1 = new_data.shape[1]
            new_wcs.naxis2 = new_data.shape[0]
            new_wcs._naxis1 = new_wcs.naxis1
            new_wcs._naxis2 = new_wcs.naxis2

        else: new_wcs = None

        # Set the new data and the new WCS
        self._data = new_data
        self._wcs = new_wcs

    # -----------------------------------------------------------------

    def unpad(self, nx=0, ny=0):

        """
        This function ...
        :param nx:
        :param ny:
        :return:
        """

        if nx == 0 and ny == 0: return

        # Slice
        new_data = self._data[ny:, nx:]

        if self.wcs is not None:

            new_wcs = self.wcs.copy()

            new_wcs.wcs.crpix[0] -= nx
            new_wcs.wcs.crpix[1] -= ny

            # Change the number of pixels
            new_wcs.naxis1 = new_data.shape[1]
            new_wcs.naxis2 = new_data.shape[0]
            new_wcs._naxis1 = new_wcs.naxis1
            new_wcs._naxis2 = new_wcs.naxis2

        else: new_wcs = None

        # Set the new data and the new WCS
        self._data = new_data
        self._wcs = new_wcs

    # -----------------------------------------------------------------

    def downsampled(self, factor, order=3):

        """
        This function ...
        :return:
        """

        new = self.copy()
        new.downsample(factor, order)
        return new

    # -----------------------------------------------------------------

    def downsample(self, factor, order=3):

        """
        This function ...
        :param factor:
        :param order:
        :return:
        """

        # Check if factor is 1.
        if factor == 1: return

        #print(self.nans.data)
        #print(self.data[0,0], type(self.data[0,0]), self.data[0,0] is nan_value)

        # Get mask of nans and infs
        if self.has_nans: nans = self.nans
        else: nans = None
        if self.has_infs: infs = self.infs
        else: infs = None

        # REMOVE NANS?
        #self.replace_nans(zero_value)
        #self.replace_infs(zero_value)
        if nans is not None: self.apply_mask(nans)
        if infs is not None: self.apply_mask(infs)

        #print(factor)
        #print(self._data)
        #print(self.nnans, self.ninfs)

        # Calculate the downsampled array
        new_data = ndimage.interpolation.zoom(self._data, zoom=1.0/factor, order=order)
        #print(new_data)

        new_xsize = new_data.shape[1]
        new_ysize = new_data.shape[0]

        relative_center = Position(self.center.x / self.xsize, self.center.y / self.ysize)

        new_center = Position(relative_center.x * new_xsize, relative_center.y * new_ysize)

        if self.wcs is not None:

            # Make a copy of the current WCS
            new_wcs = self.wcs.copy()

            # Change the center pixel position
            new_wcs.wcs.crpix[0] = new_center.x
            new_wcs.wcs.crpix[1] = new_center.y

            # Change the number of pixels
            new_wcs.naxis1 = new_xsize
            new_wcs.naxis2 = new_ysize

            new_wcs._naxis1 = new_wcs.naxis1
            new_wcs._naxis2 = new_wcs.naxis2

            # Change the pixel scale
            new_wcs.wcs.cdelt[0] *= float(self.xsize) / float(new_xsize)
            new_wcs.wcs.cdelt[1] *= float(self.ysize) / float(new_ysize)

            # Rebin the masks
            if nans is not None:

                nans.rebin(new_wcs)
                nans.dilate_rc(2, connectivity=1, iterations=2) # 1 also worked in test
                #print("NANS", nans.data)
                new_data[nans.data] = nan_value

            if infs is not None:

                infs.rebin(new_wcs)
                infs.dilate_rc(2, connectivity=1, iterations=2)  # 1 also worked in test
                #print("INFS", infs.data)
                new_data[infs.data] = inf_value

        else:

            new_wcs = None

            # Zoom the masks
            if nans is not None:

                new_nans_data = ndimage.interpolation.zoom(nans.data.astype(int), zoom=1.0/factor, order=0)

                # Check the shapes
                if new_nans_data.shape[1] != new_data.shape[1]:
                    log.warning("Could not downsample the mask of NaN values: all NaNs have been replaced by zero")
                elif new_nans_data.shape[0] != new_data.shape[0]:
                    log.warning("Could not downsample the mask of NaN values: all NaNs have been replaced by zero")

                # Apply the masks
                else:

                    new_nans = newMask.above(new_nans_data, 0.5)
                    #new_nans = new_nans_data > 0.5
                    new_nans.dilate_rc(2, connectivity=1, iterations=2)
                    new_data[new_nans] = nan_value

            if infs is not None:

                new_infs_data = ndimage.interpolation.zoom(infs.data.astype(int), zoom=1.0 / factor, order=0)

                if new_infs_data.shape[1] != new_data.shape[1]:
                    log.warning("Could not downsample the mask of infinite values: all infinities have been replaced by zero")
                elif new_infs_data.shape[0] != new_data.shape[0]:
                    log.warning("Could not downsample the mask of infinite values: all infinities have been replaced by zero")

                # Apply the masks
                else:

                    new_infs = newMask.above(new_infs_data, 0.5)
                    #new_infs = new_infs_data > 0.5
                    new_infs.dilate_rc(2, connectivity=1, iterations=2)
                    new_data[new_infs] = inf_value

        # Set the new data and wcs
        self._data = new_data
        self._wcs = new_wcs

    # -----------------------------------------------------------------

    def upsampled(self, factor, integers=False):

        """
        This function ...
        :param factor:
        :param integers:
        :return:
        """

        new = self.copy()
        new.upsample(factor, integers)
        return new

    # -----------------------------------------------------------------

    def upsample_integers(self, factor): # For segmentation map class??

        """
        This function ...
        :param factor:
        :return:
        """

        # Check whether the upsampling factor is an integer or not
        if int(factor) == factor:

            new_data = ndimage.zoom(self._data, factor, order=0)

            new_xsize = new_data.shape[1]
            new_ysize = new_data.shape[0]

            relative_center = Position(self.center.x / self.xsize, self.center.y / self.ysize)

            new_center = Position(relative_center.x * new_xsize, relative_center.y * new_ysize)

            new_wcs = copy.deepcopy(self.wcs)
            # Change the center pixel position
            new_wcs.wcs.crpix[0] = new_center.x
            new_wcs.wcs.crpix[1] = new_center.y

            # Change the number of pixels
            new_wcs.naxis1 = new_xsize
            new_wcs.naxis2 = new_ysize
            new_wcs._naxis1 = new_wcs.naxis1
            new_wcs._naxis2 = new_wcs.naxis2

            # Change the pixel scale
            new_wcs.wcs.cdelt[0] *= float(self.xsize) / float(new_xsize)
            new_wcs.wcs.cdelt[1] *= float(self.ysize) / float(new_ysize)

            # return Frame(data, wcs=new_wcs, name=self.name, description=self.description, unit=self.unit, zero_point=self.zero_point, filter=self.filter, sky_subtracted=self.sky_subtracted, fwhm=self.fwhm)

            # Set the new data and wcs
            self._data = new_data
            self._wcs = new_wcs

        # Upsampling factor is not an integer
        else:

            old = self.copy()

            self.downsample(1. / factor)

            # print("Checking indices ...")
            indices = np.unique(old._data)

            # print("indices:", indices)

            # Loop over the indices
            for index in list(indices):
                # print(index)

                index = int(index)

                where = Mask(old._data == index)

                # Calculate the downsampled array
                data = ndimage.interpolation.zoom(where.astype(float), zoom=factor)
                upsampled_where = data > 0.5

                self[upsampled_where] = index

    # -----------------------------------------------------------------

    def upsample(self, factor, integers=False):

        """
        This function ...
        :param factor:
        :param integers:
        :return:
        """

        # Check if factor is 1.
        if factor == 1: return

        # Just do inverse of downsample
        else: self.downsample(factor)

    # -----------------------------------------------------------------

    def fill(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data.fill(value)

    # -----------------------------------------------------------------

    def rotate(self, angle):

        """
        This function ...
        :param angle:
        :return:
        """

        data = ndimage.interpolation.rotate(self.data, angle.to("deg").value, reshape=False, order=1, mode='constant', cval=float('nan'))

        # Replace data
        self._data = data

        # Rotate wcs
        if self.wcs is not None:

            rotated_wcs = self.wcs.deepcopy()
            rotated_wcs.rotateCD(angle)  # STILL UNTESTED

            # Replace wcs
            self.wcs = rotated_wcs

        # Return mask of padded pixels
        return self.nans()

    # -----------------------------------------------------------------

    def rotation_mask(self, angle):

        """
        This function ...
        :param angle:
        :return:
        """

        data = ndimage.interpolation.rotate(self.data, angle.to("deg").value, reshape=False, order=1, mode='constant', cval=float('nan'))
        return newMask(np.isnan(data))

    # -----------------------------------------------------------------

    def rotated(self, angle):

        """
        This function ...
        :param angle:
        :return:
        """

        # Calculate the rotated array
        #frame[np.isnan(frame)] = 0.0
        data = ndimage.interpolation.rotate(self.data, angle.to("deg").value, reshape=False, order=1, mode='constant', cval=float('nan'))
        #new_frame = misc.imrotate(frame, angle, interp="bilinear")

        # Convert the wcs to header
        #header = self.wcs.to_header()

        # Rotate the header (Sebastien's script)
        #from ..tools import rotation
        #rotated_header = rotation.rotate_header(header, angle)

        # Create the new WCS
        #rotated_wcs = CoordinateSystem(rotated_header)

        rotated_wcs = self.wcs.deepcopy()
        rotated_wcs.rotateCD(angle) # STILL UNTESTED

        # Return the rotated frame
        # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
        return Frame(data,
                     wcs=rotated_wcs,
                     name=self.name,
                     description=self.description,
                     unit=self.unit,
                     zero_point=self.zero_point,
                     filter=self.filter,
                     sky_subtracted=self.sky_subtracted,
                     fwhm=self.fwhm)

    # -----------------------------------------------------------------

    def shifted(self, extent):

        """
        This function ...
        :param extent:
        :return:
        """

        # TODO: change the WCS !!!

        # Transform the data
        data = ndimage.interpolation.shift(self.data, (extent.y, extent.x))

        # Return the shifted frame
        # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
        return Frame(data,
                     wcs=None,
                     name=self.name,
                     description=self.description,
                     unit=self.unit,
                     zero_point=self.zero_point,
                     filter=self.filter,
                     sky_subtracted=self.sky_subtracted,
                     fwhm=self.fwhm)

    # -----------------------------------------------------------------

    def centered_around(self, position):

        """
        This function ...
        :param position:
        :return:
        """

        center = Position(x=0.5*self.xsize, y=0.5*self.ysize)
        shift = position - center

        # Return the shifted frame
        return self.shifted(shift)

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        return self.wcs.bounding_box

    # -----------------------------------------------------------------

    @property
    def corners(self):

        """
        This function ...
        :return:
        """

        # Get coordinate values
        coordinate_values = self.wcs.calc_footprint(undistort=True)

        # Initialize a list to contain the coordinates of the corners
        corners = []

        for ra_deg, dec_deg in coordinate_values:

            # Create sky coordinate
            coordinate = SkyCoordinate(ra=ra_deg, dec=dec_deg, unit="deg", frame="fk5")

            # Add the coordinate of this corner to the list
            corners.append(coordinate)

        # Return the list of coordinates
        return corners

    # -----------------------------------------------------------------

    @property
    def coordinate_range(self):

        """
        This property ...
        :return:
        """

        return self.wcs.coordinate_range

    # -----------------------------------------------------------------

    @property
    def coordinate_box(self):

        """
        This function ...
        :return:
        """

        # Get coordinate range
        center, ra_span, dec_span = self.coordinate_range

        #ra = center.ra.to(unit).value
        #dec = center.dec.to(unit).value

        #ra_span = ra_span.to(unit).value
        #dec_span = dec_span.to(unit).value

        # Create rectangle
        center = SkyCoordinate(center.ra, center.dec)
        radius = SkyStretch(0.5 * ra_span, 0.5 * dec_span)
        box = SkyRectangleRegion(center, radius)

        # Return the box
        return box

    # -----------------------------------------------------------------

    def contains(self, coordinate):

        """
        This function ...
        :param coordinate:
        :return:
        """

        pixel = coordinate.to_pixel(self.wcs)
        return 0.0 <= pixel.x < self.xsize and 0.0 <= pixel.y < self.ysize

    # -----------------------------------------------------------------

    def replace_nans(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        # Set all NaN pixels to the specified value
        self._data[self.nans] = value

    # -----------------------------------------------------------------

    def replace_infs(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        # Set all inf pixels to the specified value
        self._data[self.infs] = value

    # -----------------------------------------------------------------

    def replace_zeroes(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data[self.zeroes] = value

    #

    def replace_negatives(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        self._data[self._data < 0] = value

    # -----------------------------------------------------------------

    def box_like(self, box):

        """
        This function ...
        :param box:
        :return:
        """

        data = self._data[box.y_min:box.y_max, box.x_min:box.x_max]

        # Create the new box and return it
        return Cutout(data, box.x_min, box.x_max, box.y_min, box.y_max)

    # -----------------------------------------------------------------

    def to_rgba(self, interval="pts", scale="log", alpha="absolute", peak_alpha=1., colours="red", normalize_in=None):

        """
        This function ...
        :param interval:
        :param scale:
        :param alpha:
        :param peak_alpha:
        :param colours:
        :param normalize_in:
        :return:
        """

        from .rgba import RGBAImage
        return RGBAImage.from_frame(self, interval=interval, scale=scale, alpha=alpha, peak_alpha=peak_alpha,
                                    colours=colours, normalize_in=normalize_in)

    # -----------------------------------------------------------------

    @property
    def file_size(self):

        """
        This function ...
        :return:
        """

        # Give warning message
        log.warning("The size of the frame in itself is perhaps not accurately represented by the size of the file it originates from, because it possibly contains muliple frames")

        # Check if path is defined
        if self.path is None: raise ValueError("Path is not defined")

        # Return the file size, if the frame has a path
        return fs.file_size(self.path)

    # -----------------------------------------------------------------

    @property
    def data_size(self):

        """
        This function ...
        :return:
        """

        return (self._data.nbytes * u("byte")).to("GB")

    # -----------------------------------------------------------------

    def save(self, header=None, origin=None, extra_header_info=None, add_meta=True):

        """
        This function ...
        :param header:
        :param origin:
        :param extra_header_info:
        :param add_meta:
        :return:
        """

        # Inform the user
        log.info("Saving the frame ...")

        # Check if path is defined
        if self.path is None: raise RuntimeError("Path for the frame is not defined")

        # Check if original file was not multiplane
        if self._from_multiplane: raise RuntimeError("Cannot save frame into a multiplane image")

        # Save
        self.saveto(self.path, header=header, origin=origin, extra_header_info=extra_header_info, add_meta=add_meta)

    # -----------------------------------------------------------------

    def saveto(self, path, **kwargs):

        """
        This function ...
        :param path:
        :param kwargs:
        """

        if path.endswith("fits"): self.saveto_fits(path, **kwargs)
        elif path.endswith("asdf"): self.saveto_asdf(path, **kwargs)
        elif path.endswith("png"): self.saveto_png(path, **kwargs)
        else: raise ValueError("Unknown file format: " + fs.get_extension(path))

    # -----------------------------------------------------------------

    def saveto_fits(self, path, header=None, origin=None, extra_header_info=None, add_meta=True, update_path=True):

        """
        This function ...
        :param path:
        :param header:
        :param origin:
        :param extra_header_info:
        :param add_meta:
        :param update_path:
        :return:
        """

        if header is None: header = self.header

        # Set unit, FWHM and filter description
        if self.unit is not None:
            header.set("SIGUNIT", represent_unit(self.unit), "Unit of the map")
            header.set("PHYSTYPE", self.unit.physical_type, "Physical type of the unit")
        if self.fwhm is not None: header.set("FWHM", self.fwhm.to("arcsec").value, "[arcsec] FWHM of the PSF")

        # Set filter
        if self.filter is not None: header.set("FILTER", str(self.filter), "Filter used for this observation")
        else: header.set("FILTER", "n/a", "This image does not correspond to a certain observational filter")

        # Set pixelscale
        if self.wcs is None and self.pixelscale is not None:
            header.set("XPIXSIZE", repr(self.pixelscale.x.to("arcsec").value), "[arcsec] Pixelscale for x axis")
            header.set("YPIXSIZE", repr(self.pixelscale.y.to("arcsec").value), "[arcsec] Pixelscale for y axis")

        # Set distance
        if self.distance is not None: header.set("DISTANCE", repr(self.distance.to("Mpc").value), "[Mpc] Distance to the object")

        # Set PSF FILTER
        if self.psf_filter is not None: header.set("PSFFLTR", str(self.psf_filter), "Filter to which the PSF of the frame corresponds")

        # Add origin description
        if origin is not None: header["ORIGIN"] = origin
        else: header["ORIGIN"] = "Frame class of PTS package"

        # Add meta information
        if add_meta:
            for key in self.metadata:
                #print(key, self.metadata[key])
                header[key] = self.metadata[key]

        # Add extra info
        if extra_header_info is not None:
            for key in extra_header_info: header[key] = extra_header_info[key]

        # Write
        from .fits import write_frame

        #try:
        write_frame(self._data, header, path)
        #except IOError("Something went wrong during write")

        # Replace the path
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

        if header is None: header = self.header

        # Import
        from asdf import AsdfFile

        # Create the tree
        tree = dict()

        # Add data and header
        tree["data"] = self._data
        tree["header"] = header

        # Create the asdf file
        ff = AsdfFile(tree)

        # Write
        ff.write_to(path)

        # Update the path
        if update_path: self.path = path

    # -----------------------------------------------------------------

    def saveto_png(self, path, interval="pts", scale="log", alpha="absolute", peak_alpha=1., colours="red", normalize_in=None):

        """
        This function ...
        :param path:
        :param interval:
        :param scale:
        :param alpha:
        :param peak_alpha:
        :param colours:
        :param normalize_in:
        :return:
        """

        # Get image values
        image = self.to_rgba(interval=interval, scale=scale, alpha=alpha, peak_alpha=peak_alpha, colours=colours, normalize_in=normalize_in)

        # Save
        image.saveto(path)

# -----------------------------------------------------------------

def sum_frames(*args, **kwargs):

    """
    This function ...
    :param args:
    :return:
    """

    #arrays = [np.array(arg) for arg in args] # how it used to be
    arrays = [arg.data for arg in args]
    return Frame(np.sum(arrays, axis=0), **kwargs)

# -----------------------------------------------------------------

def sum_frames_quadratically(*args):

    """
    This function ...
    :param args:
    :return:
    """

    #arrays = [np.array(arg)**2 for arg in args]
    arrays = [arg.data**2 for arg in args]
    return Frame(np.sqrt(np.sum(arrays, axis=0)))

# -----------------------------------------------------------------

def linear_combination(frames, coefficients, checks=True):

    """
    This function ...
    :param frames:
    :param coefficients:
    :param checks:
    :return:
    """

    if checks:
        from .list import check_uniformity
        unit, wcs, pixelscale, psf_filter, fwhm, distance = check_uniformity(*frames)
    else: unit = wcs = pixelscale = psf_filter = fwhm = distance = None

    #print("unit", unit)
    #print("wcs", wcs)
    #print("pixelscale", pixelscale)
    #print("psf_filter", psf_filter)
    #print("fwhm", fwhm)
    #print("distance", distance)

    #print(coefficients)
    return sum_frames(*[frame*coefficient for coefficient, frame in zip(coefficients, frames)], unit=unit, wcs=wcs, pixelscale=pixelscale, psf_filter=psf_filter, fwhm=fwhm, distance=distance)

# -----------------------------------------------------------------

def log10(frame):

    """
    This function ...
    :param frame:
    :return:
    """

    return frame.get_log10()

# -----------------------------------------------------------------
