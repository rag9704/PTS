#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       Astromagic -- the image editor for Astronomers        **
# *****************************************************************

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import os.path
import copy
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

# Import astronomical modules
from astropy import log
from astropy.wcs import WCS
import aplpy
import astropy.io.fits as pyfits
import astropy.units as u
import astropy.coordinates as coord
from astropy.convolution import convolve, convolve_fft, Gaussian2DKernel

# Import Astromagic modules
from ..basics import Position
from ..tools import coordinates, cropping, transformations, interpolation, headers, fitting

# -----------------------------------------------------------------

class Frame(np.ndarray):

    """
    This class ...
    """

    # -----------------------------------------------------------------

    def __new__(cls, data, wcs=None, pixelscale=None, description=None, selected=False, unit=None, name=None, filter=None, sky_subtracted=False):

        """
        This function ...
        :param cls:
        :param input_array:
        :param info:
        :return:
        """

        obj = np.asarray(data).view(cls)
        obj.wcs = wcs
        obj.pixelscale = pixelscale
        obj.description = description
        obj.selected = selected
        obj.unit = unit
        obj.name = name
        obj.filter = filter
        obj.sky_subtracted = sky_subtracted

        return obj

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path, index=0, name=None, description=None, plane=None):

        """
        This function ...
        :param path:
        :return:
        """

        # Show which image we are importing
        log.info("Reading in file: " + path)

        # Open the HDU list for the FITS file
        hdulist = pyfits.open(path)

        # Get the primary HDU
        hdu = hdulist[0]

        # Get the image header
        header = hdu.header

        # Check whether multiple planes are present in the FITS image
        nframes = headers.get_number_of_frames(header)

        # Remove references to a potential third axis
        flat_header = copy.deepcopy(header)
        flat_header["NAXIS"] = 2
        if "NAXIS3" in flat_header: del flat_header["NAXIS3"]
        for key in flat_header:
            if "PLANE" in key: del flat_header[key]

        # Obtain the world coordinate system from the 'flattened' header
        wcs = WCS(flat_header)

        # Load the frames
        pixelscale = headers.get_pixelscale(header)

        # Obtain the filter for this image
        filter = headers.get_filter(os.path.basename(path[:-5]), header)

        # Obtain the units of this image
        unit = headers.get_unit(header)

        # Check whether the image is sky-subtracted
        sky_subtracted = headers.is_sky_subtracted(header)

        if nframes > 1:

            # Get the description of this frame index
            description = headers.get_frame_description(header, index)

            if plane is not None:

                description = plane
                index = headers.get_frame_index(header, plane)

            # Get the name from the file path
            if name is None: name = os.path.basename(path[:-5])

            # Return the frame
            return cls(hdu.data[index], wcs, pixelscale, description, False, unit, name, filter, sky_subtracted)

        else:

            # Sometimes, the 2D frame is embedded in a 3D array with shape (1, xsize, ysize)
            if len(hdu.data.shape) == 3: hdu.data = hdu.data[0]

            # Get the name from the file path
            if name is None: name = os.path.basename(path[:-5])

            # Return the frame
            return cls(hdu.data, wcs, pixelscale, description, False, unit, name, filter, sky_subtracted)

    # -----------------------------------------------------------------

    @classmethod
    def zeros_like(cls, frame):

        """
        This function ...
        :param frame:
        :return:
        """

        # Return a zero-filled copy of the frame
        return np.zeros_like(frame)

    # -----------------------------------------------------------------

    def __array_finalize__(self, obj):

        """
        This function ...
        :param obj:
        :return:
        """

        if obj is None: return
        self.wcs = getattr(obj, 'wcs', None)
        self.pixelscale = getattr(obj, 'wcs', None)
        self.description = getattr(obj, 'description', None)
        self.selected = getattr(obj, 'selected', False)
        self.unit = getattr(obj, 'unit', None)
        self.name = getattr(obj, 'name', None)
        self.filter = getattr(obj, 'filter', None)
        self.sky_subtracted = getattr(obj, 'sky_subtracted', False)

    # -----------------------------------------------------------------

    def select(self):

        """
        This function ...
        :return:
        """

        self.selected = True

    # -----------------------------------------------------------------

    def deselect(self):

        """
        This function ...
        :return:
        """

        self.selected = False

    # -----------------------------------------------------------------

    @property
    def xsize(self): return self.shape[1]

    # -----------------------------------------------------------------

    @property
    def ysize(self): return self.shape[0]

    # -----------------------------------------------------------------

    @property
    def header(self):

        """
        This function ...
        """

        # If the WCS for this frame is defined, use it to create a header
        if self.wcs is not None: header = self.wcs.to_header()

        # Else, create a new empty header
        else: header = pyfits.Header()

        # Add properties to the header
        header['NAXIS'] = 2
        header['NAXIS1'] = self.xsize
        header['NAXIS2'] = self.ysize

        # Return the header
        return header

    # -----------------------------------------------------------------

    @property
    def wavelength(self):

        """
        This function ...
        :return:
        """

        # Return the pivot wavelength of the frame's filter, if defined
        if self.filter is None: return None
        else: return self.filter.pivotwavelength() * u.Unit("micron")

    # -----------------------------------------------------------------

    def set_unit(self, unit):

        """
        This function ...
        :param unit:
        :return:
        """

        self.unit = unit

    # -----------------------------------------------------------------

    def set_fwhm(self, fwhm):

        """
        This function ...
        :param fwhm:
        :return:
        """

        self.fwhm = fwhm

    # -----------------------------------------------------------------

    def convert_to(self, unit):

        """
        This function ...
        :param unit:
        :return:
        """

        # Convert the data
        conversion_factor = self.unit / unit
        frame = self * conversion_factor

        # Set the new unit
        frame.unit = unit

        # Return the converted frame
        return frame

    # -----------------------------------------------------------------

    def to_magnitude(self, m_0):

        """
        This function ...
        :return:
        """

        # TODO: adapt the unit

        # Do the conversion
        return m_0 - 2.5 * np.log10(self)

    # -----------------------------------------------------------------

    def to_flux(self, f_0):

        """
        This function ...
        :return:
        """

        # TODO: adapt the unit

        # Do the conversion
        return f_0 * np.power(10.0, - self / 2.5)

     # -----------------------------------------------------------------

    def convolve(self, kernel):

        """
        This function ...
        :param frame:
        :return:
        """

        # Calculate the zooming factor
        factor = (self.pixelscale / kernel.pixelscale).value

        # Rebin the kernel to the same grid of the image
        kernel = ndimage.interpolation.zoom(kernel, zoom=1.0/factor)

        # Do the convolution on this frame
        data = convolve_fft(self, kernel, normalize_kernel=True)

        # Return the convolved frame
        return Frame(data, self.wcs, self.pixelscale, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

    # -----------------------------------------------------------------

    def rebin(self, ref_frame):

        """
        This function ...
        :param ref_frame:
        :return:
        """

        # Do the rebinning
        data = transformations.align_and_rebin(self, self.header, ref_frame.header)

        # Return the rebinned frame
        return Frame(data, ref_frame.wcs, ref_frame.pixelscale, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

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

        # TODO: change the WCS

        # Crop the frame
        data = cropping.crop_check(self, x_min, x_max, y_min, y_max)

        # Return the cropped frame
        return Frame(data, None, self.pixelscale, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

    # -----------------------------------------------------------------

    def downsample(self, factor):

        """
        This function ...
        :return:
        """

        # TODO: change the WCS

        # Calculate the downsampled array
        data = ndimage.interpolation.zoom(self, zoom=1.0/factor)

        # Return the downsampled frame
        return Frame(data, None, self.pixelscale*factor, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

    # -----------------------------------------------------------------

    def rotate(self, angle):

        """
        This function ...
        :param angle:
        :return:
        """

        # TODO: change the WCS

        # Calculate the rotated array
        data = ndimage.interpolation.rotate(self, angle)

        # Return the rotated frame
        return Frame(data, None, self.pixelscale, self.description, self.selected, self.unit)

    # -----------------------------------------------------------------

    def shift(self, extent):

        """
        This function ...
        :return:
        """

        # TODO: change the WCS

        # Transform the data
        data = ndimage.interpolation.shift(self, (extent.y, extent.x))

        # Return the shifted frame
        return Frame(data, None, self.pixelscale, self.description, self.selected, self.unit)

    # -----------------------------------------------------------------

    def center_around(self, position):

        """
        This function ...
        :param position:
        :return:
        """

        center = Position(x=0.5*self.xsize, y=0.5*self.ysize)
        shift = position - center

        # Return the shifted frame
        return self.shift(shift)

    # -----------------------------------------------------------------

    def coordinate_range(self):

        """
        This function ...
        :return:
        """

        # Some pixel coordinates of interest.
        pixels = np.array([[0,0],[self.xsize-1, self.ysize-1]], dtype=float)

        world = self.wcs.all_pix2world(pixels, 0)  # Convert pixel coordinates to world coordinates (RA and DEC in degrees)

        #print(world)

        coordinate1 = world[0]
        coordinate2 = world[1]
        ra_range = [coordinate2[0], coordinate1[0]]
        dec_range = [coordinate1[1], coordinate2[1]]

        # Determine the center in RA and DEC (in degrees)
        ra_center = 0.5*(ra_range[0] + ra_range[1])
        dec_center = 0.5*(dec_range[0] + dec_range[1])

        # Determine the width in RA and DEC (both in degrees)
        dec_width = dec_range[1] - dec_range[0]
        ra_width = ra_range[1] - ra_range[0]   # WRONG!

        # Calculate the start and end RA coordinates (in degrees)
        ra_begin = ra_center - 0.5*ra_width
        ra_end = ra_center + 0.5*ra_width

        # Calculate the start and end DEC coordinates (in degrees)
        dec_begin = dec_center - 0.5*dec_width
        dec_end = dec_center + 0.5*dec_width

        # Calculate the
        ra_distance = coordinates.ra_distance(dec_center, ra_begin, ra_end)
        dec_distance = dec_end - dec_begin

        # Calculate the pixel scale of this image in degrees
        pixelscale = self.pixelscale
        pixelscale_deg = pixelscale.to("deg").value

        # Get the center pixel
        ref_pix = self.wcs.wcs.crpix
        ref_world = self.wcs.wcs.crval

        # Get the number of pixels
        size_dec_deg = self.ysize * pixelscale_deg
        size_ra_deg = self.xsize * pixelscale_deg

        # Check whether the two different ways of calculating the RA width result in approximately the same value
        assert np.isclose(ra_distance, size_ra_deg, rtol=0.02), "The coordinate system and pixel scale do not match"
        assert np.isclose(dec_distance, size_dec_deg, rtol=0.02), "The coordinate system and pixel scale do not match"

        center = coord.SkyCoord(ra=ra_center, dec=dec_center, unit=(u.deg, u.deg), frame='fk5')
        ra_span = size_ra_deg * u.deg
        dec_span = size_dec_deg * u.deg

        # Return the center coordinate and the RA and DEC span
        return center, ra_span, dec_span

    # -----------------------------------------------------------------

    def contains(self, coordinate):

        """
        This function ...
        :param coordinate:
        :return:
        """

        pixel_coordinate = self.wcs.all_world2pix([[coordinate.ra.value, coordinate.dec.value]], 0)

        x = pixel_coordinate[0][0]
        y = pixel_coordinate[0][1]

        return 0.0 <= x < self.xsize and 0.0 <= y < self.ysize

    # -----------------------------------------------------------------

    def replace_nans(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        # Set all NaN pixels to the specified value
        self[np.isnan(self)] = value

    # -----------------------------------------------------------------

    def fit_polynomial(self, order, mask=None):

        """
        This function ...
        :return:
        """

        # Do the fitting
        polynomial = fitting.fit_polynomial(self, order, mask=mask)

        # Evaluate the polynomial
        data = fitting.evaluate_model(polynomial, 0, self.xsize, 0, self.ysize)

        # Return a new Frame
        return Frame(data, self.wcs, self.pixelscale, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

    # -----------------------------------------------------------------

    def interpolated(self, mask, method):

        """
        This function ...
        :param mask:
        :return:
        """

        # Fit a polynomial to the data
        if method == "polynomial":
            try:
                return self.fit_polynomial(3, mask=mask)
            except TypeError:
                mask = mask.eroded(2, 1)
                return self.fit_polynomial(3, mask=mask)

        # Interpolate using the local mean method
        elif method == "local_mean":

            # Calculate the interpolated data
            data = interpolation.in_paint(self, mask)

            # Return a new Frame
            return Frame(data, self.wcs, self.pixelscale, self.description, self.selected, self.unit, self.name, self.filter, self.sky_subtracted)

        # Calculate the mean value of the data
        elif method == "mean":

            mean = np.ma.mean(np.ma.masked_array(self, mask=mask))
            return self.full(mean)

        # Calculate the median value of the data
        elif method == "median":

            median = np.ma.median(np.ma.masked_array(self, mask=mask))
            return self.full(median)

        # Invalid option
        else: raise ValueError("Unknown interpolation method")

    # -----------------------------------------------------------------

    def save(self, path):

        """
        This function ...
        """

        # Create the HDU
        hdu = pyfits.PrimaryHDU(self, self.header)

        # Write the HDU to a FITS file
        hdu.writeto(path, clobber=True)

    # -----------------------------------------------------------------

    def plot(self, mask=None, color=True, nan_color='black', grid=False):

        """
        This function ...
        :param mask:
        :return:
        """

        # Mask the frame with nans
        maskedimage = np.ma.array(self, mask=mask)
        frame_with_nans = maskedimage.filled(np.NaN)

        # Create a HDU from this frame with the image header
        hdu = pyfits.PrimaryHDU(frame_with_nans, self.wcs.to_header())

        # Create a figure canvas
        figure = plt.figure(figsize=(12, 12))

        # Create a figure from this frame
        plot = aplpy.FITSFigure(hdu, figure=figure)

        # Set color scale
        if color: plot.show_colorscale()
        else: plot.show_grayscale()

        # Add a color bar
        plot.add_colorbar()

        # Set color for NaN values
        plot.set_nan_color(nan_color)

        # Set grid
        if grid: plot.add_grid()

        # Show the plot on screen
        plt.show()

# -----------------------------------------------------------------