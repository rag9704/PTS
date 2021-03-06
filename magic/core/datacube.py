#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.datacube Contains the DataCube class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
from multiprocessing import Pool, Process, Manager
import numpy as np

# Import the relevant PTS classes and modules
from .image import Image
from .frame import Frame
from ...core.data.sed import SED, ObservedSED
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ...core.basics.log import log
from ..basics.mask import Mask, MaskBase
from ...core.basics.errorbar import ErrorBar
from ...core.tools import introspection
from ...core.tools import filesystem as fs
from ...core.tools import time
from ...core.filter.broad import BroadBandFilter
from ..basics.vector import Pixel

# -----------------------------------------------------------------

class DataCube(Image):

    """
    This class...
    """

    # Set the default extension
    default_extension = "fits"

    # -----------------------------------------------------------------

    def __init__(self, name="untitled"):

        """
        The constructor ...
        """

        # Call the constructor of the base class
        super(DataCube, self).__init__(name)

        # The wavelength grid
        self.wavelength_grid = None

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, image_path, wavelength_grid):

        """
        This function ...
        :param image_path:
        :param wavelength_grid:
        :return:
        """

        # Call the corresponding base class function
        datacube = super(DataCube, cls).from_file(image_path, always_call_first_primary=False, no_filter=True)

        # Check wavelength grid size
        assert len(wavelength_grid) == datacube.nframes

        # Set the wavelength grid
        datacube.wavelength_grid = wavelength_grid

        # Loop over the frames
        for i in range(datacube.nframes):

            # Frame name
            frame_name = "frame" + str(i)

            # Set the wavelength of the frame
            datacube.frames[frame_name].wavelength = datacube.wavelength_grid[i]

        # Return the datacube instance
        return datacube

    # -----------------------------------------------------------------

    @classmethod
    def from_files(cls, paths):

        """
        This function ...
        :param paths: paths of frames
        :return:
        """

        frames = [Frame.from_file(path) for path in paths]
        return cls.from_frames(frames)

    # -----------------------------------------------------------------

    @classmethod
    def from_frames(cls, frames):

        """
        This function ...
        :param frames:
        :return:
        """

        # Create a datacube instance
        datacube = cls()

        # The indices of the frames, sorted on wavelength
        sorted_indices = sorted(range(len(frames)), key=lambda i: frames[i].filter.pivotwavelength())

        # The list of wavelengths
        wavelengths = []

        # Add the frames
        nframes = 0
        for index in sorted_indices:

            # Add the frame
            frame_name = "frame" + str(nframes)
            datacube.add_frame(frames[index], frame_name)

            # Add the wavelength
            wavelengths.append(frames[index].filter.pivotwavelength())

            # Increment the number of frames
            nframes += 1

        # Create the wavelength grid
        datacube.wavelength_grid = WavelengthGrid.from_wavelengths(wavelengths, unit="micron")

        # Return the datacube
        return datacube

    # -----------------------------------------------------------------

    def wavelengths(self, unit=None, asarray=False, add_unit=True):

        """
        This function ...
        :return:
        """

        return self.wavelength_grid.wavelengths(unit, asarray, add_unit)

    # -----------------------------------------------------------------

    def wavelength_indices(self, min_wavelength=None, max_wavelength=None):

        """
        This function ...
        :param min_wavelength:
        :param max_wavelength:
        :return:
        """

        return self.wavelength_grid.wavelength_indices(min_wavelength, max_wavelength)

    # -----------------------------------------------------------------

    def asarray(self, axis=3):

        """
        This function ...
        :return:
        """

        # Get a list that contains the frames
        frame_list = self.frames.as_list()

        # Stack the frames into a 3D numpy array
        if axis == 3: return np.dstack(frame_list)
        elif axis == 2: return np.hstack(frame_list)
        elif axis == 1: return np.vstack(frame_list)
        elif axis == 0: return np.stack(frame_list)
        else: raise ValueError("'axis' parameter should be integer 0-3")

    # -----------------------------------------------------------------

    def get_frame_index_for_wavelength(self, wavelength):

        """
        This function ...
        :return:
        """

        return self.wavelength_grid.closest_wavelength_index(wavelength)

    # -----------------------------------------------------------------

    def get_frame_name_for_wavelength(self, wavelength):

        """
        This function ...
        :param wavelength:
        :return:
        """

        index = self.get_frame_index_for_wavelength(wavelength)
        return self.frames.keys()[index]

    # -----------------------------------------------------------------

    def get_frame_for_wavelength(self, wavelength):

        """
        This function ...
        :param wavelength:
        :return:
        """

        index = self.get_frame_index_for_wavelength(wavelength)
        return self.frames[index]

    # -----------------------------------------------------------------

    def __getitem__(self, item):

        """
        This function ...
        :param item:
        :return:
        """

        # If the slicing item is a mask
        if isinstance(item, MaskBase) or isinstance(item, Mask):

            # Create a 3D Numpy array containing
            stack = []
            for frame_name in self.frames:
                stack.append(self.frames[frame_name][item])
            #return np.array(stack)
            return stack # return the list of frame slices

        # If the slicing item is a pixel (x,y)
        if isinstance(item, Pixel):

            # Create a 1D Numpy array
            stack = np.zeros(self.nframes)

            # Set the values
            for index, frame_name in enumerate(self.frames.keys()):
                stack[index] = self.frames[item]

            # Return the numpy array
            return stack

        # Not implemented
        elif isinstance(item, slice): raise NotImplementedError("Not implemented yet")

    # -----------------------------------------------------------------

    def local_sed(self, region, min_wavelength=None, max_wavelength=None, errorcube=None):

        """
        This function ...
        :param region:
        :param min_wavelength:
        :param max_wavelength:
        :param errorcube:
        :return:
        """

        # Initialize the SED
        sed = ObservedSED(photometry_unit=self.unit)

        # Create a mask from the region (or shape)
        mask = region.to_mask(self.xsize, self.ysize)

        # Loop over the wavelengths
        for index in self.wavelength_indices(min_wavelength, max_wavelength):

            # Determine the name of the frame in the datacube
            frame_name = "frame" + str(index)

            # Get the flux in the pixels that belong to the region
            flux = np.sum(self.frames[frame_name][mask]) * self.unit

            # Get error
            if errorcube is not None:

                # Get the error in the pixel
                error = errorcube.frames[frame_name][mask] * self.unit
                errorbar = ErrorBar(error)

                # Add an entry to the SED
                sed.add_point(self.frames[frame_name].filter, flux, errorbar)

            # Add an entry to the SED
            else: sed.add_point(self.frames[frame_name].filter, flux)

            # Increment the index
            index += 1

        # Return the SED
        return sed

    # -----------------------------------------------------------------

    def pixel_sed(self, x, y, min_wavelength=None, max_wavelength=None, errorcube=None):

        """
        This function ...
        :param x:
        :param y:
        :param min_wavelength:
        :param max_wavelength:
        :param errorcube:
        :return:
        """

        # Initialize the SED
        sed = ObservedSED(photometry_unit=self.unit)

        # Loop over the wavelengths
        for index in self.wavelength_indices(min_wavelength, max_wavelength):

            # Determine the name of the frame in the datacube
            frame_name = "frame" + str(index)

            # Get the flux in the pixel
            flux = self.frames[frame_name][y, x] * self.unit

            # Get error
            if errorcube is not None:

                # Get the error in the pixel
                error = errorcube.frames[frame_name][y, x] * self.unit
                errorbar = ErrorBar(error)

                # Add an entry to the SED
                sed.add_point(self.frames[frame_name].filter, flux, errorbar)

            # Add an entry to the SED
            else: sed.add_point(self.frames[frame_name].filter, flux)

            # Increment the index
            index += 1

        # Return the SED
        return sed

    # -----------------------------------------------------------------

    def global_sed(self, mask=None, min_wavelength=None, max_wavelength=None):

        """
        This function ...
        :param mask:
        :param min_wavelength:
        :param max_wavelength:
        :return:
        """

        # Determine the mask
        if isinstance(mask, basestring): inverse_mask = self.masks[mask].inverse()
        elif isinstance(mask, Mask): inverse_mask = mask.inverse()
        elif mask is None: inverse_mask = None
        else: raise ValueError("Mask must be string or Mask (or None) instead of " + str(type(mask)))

        # Initialize the SED
        sed = SED(photometry_unit=self.unit)

        # Loop over the wavelengths
        for index in self.wavelength_indices(min_wavelength, max_wavelength):

            # Get the wavelength
            wavelength = self.wavelength_grid[index]

            # Determine the name of the frame in the datacube
            frame_name = "frame" + str(index)

            # Calculate the total flux
            if mask is not None: total_flux = self.frames[frame_name].sum() * self.unit
            else: total_flux = np.sum(self.frames[frame_name][inverse_mask]) * self.unit

            # Add an entry to the SED
            sed.add_point(wavelength, total_flux)

            # Increment the index
            index += 1

        # Return the SED
        return sed

    # -----------------------------------------------------------------

    def convolve_with_filter(self, fltr):

        """
        This function ...
        :param fltr:
        :return:
        """

        # Inform the user
        log.info("Convolving the datacube with the " + str(fltr) + " filter ...")

        # Convert the datacube to a numpy array where wavelength is the third dimension
        array = self.asarray()

        # Calculate the observed image frame
        data = fltr.convolve(self.wavelengths(asarray=True), array)
        frame = Frame(data)

        # Set the unit of the frame
        frame.unit = self.unit

        # Set the wcs of the frame
        frame.wcs = self.wcs

        # Return the resulting frame
        return frame

    # -----------------------------------------------------------------

    def frames_for_filters(self, filters, convolve=False, nprocesses=8):

        """
        This function ...
        :param filters:
        :param convolve:
        :param nprocesses:
        :return:
        """

        # Inform the user
        log.info("Getting frames for " + str(len(filters)) + " different filters ...")

        frames = []
        for_convolution = []

        # Loop over the filters
        for fltr in filters:

            # Broad band filter, with spectral convolution
            if isinstance(fltr, BroadBandFilter) and convolve:

                # Debugging
                log.debug("The frame for the " + str(fltr) + " filter will be calculated by convolving spectrally")

                # Add to list
                for_convolution.append(fltr)

                # Add placeholder
                frames.append(None)

            # Broad band filter without spectral convolution or narrow band filter
            else:

                # Debugging
                log.debug("Getting the frame for the " + str(fltr) + " filter ...")

                # Get the index of the wavelength closest to that of the filter
                index = self.get_frame_index_for_wavelength(fltr.pivot)

                # Get the frame
                frames.append(self.frames[index])

        # Calculate convolved frames
        if len(for_convolution) > 0: convolved_frames = self.convolve_with_filters(for_convolution, nprocesses=nprocesses)
        else: convolved_frames = []

        # Add the convolved frames
        for fltr, frame in zip(for_convolution, convolved_frames):

            # Set the frame
            index = filters.index(fltr)
            frames[index] = frame

        # Return the list of frames
        return frames

    # -----------------------------------------------------------------

    def convolve_with_filters(self, filters, nprocesses=8):

        """
        This function ...
        :param filters:
        :param nprocesses:
        :return:
        """

        # Inform the user
        parallel_info = " in parallel with " + str(nprocesses) + " processes" if nprocesses > 1 else ""
        log.info("Convolving the datacube with " + str(len(filters)) + " different filters" + parallel_info + " ...")

        # Initialize list to contain the output frames per filter
        nfilters = len(filters)
        frames = [None] * nfilters

        # PARALLEL EXECUTION
        if nprocesses > 1:

            # Save the datacube to a temporary directory
            temp_dir_path = introspection.create_temp_dir(time.unique_name("datacube-parallel-filter-convolution"))

            # Save the datacube
            temp_datacube_path = fs.join(temp_dir_path, "datacube.fits")
            self.saveto(temp_datacube_path)

            # Save the wavelength grid
            temp_wavelengthgrid_path = fs.join(temp_dir_path, "wavelengthgrid.dat")
            self.wavelength_grid.saveto(temp_wavelengthgrid_path)

            # Create process pool
            pool = Pool(processes=nprocesses)

            # Get string for the unit of the datacube
            unitstring = str(self.unit)

            # EXECUTE THE LOOP IN PARALLEL
            for index in range(nfilters):

                # Get filtername
                fltrname = str(filters[index])

                # Determine path for resulting frame
                result_path = fs.join(temp_dir_path, str(index) + ".fits")

                # Get the current filter
                pool.apply_async(_do_one_filter_convolution_from_file, args=(temp_datacube_path, temp_wavelengthgrid_path, result_path, unitstring, fltrname,)) # All simple types (strings)

            # CLOSE AND JOIN THE PROCESS POOL
            pool.close()
            pool.join()

            # Load the resulting frames
            for index in range(nfilters):

                # Determine path of resulting frame
                result_path = fs.join(temp_dir_path, str(index) + ".fits")

                # Inform the user
                log.debug("Loading the frame for filter " + str(filters[index]) + " from '" + result_path + "' ...")

                # Load the frame and set it in the list
                frames[index] = Frame.from_file(result_path)

        # SERIAL EXECUTION
        else:

            # Debugging
            log.debug("Converting the datacube into a single 3D array ...")

            # Convert the datacube to a numpy array where wavelength is the third dimension
            array = self.asarray()

            # Get the array of wavelengths
            wavelengths = self.wavelengths(asarray=True, unit="micron")

            # Loop over the filters
            for index in range(nfilters):

                # Get the current filter
                fltr = filters[index]

                # Do the filter convolution, put frame in the frames list
                _do_one_filter_convolution(fltr, wavelengths, array, frames, index, self.unit, self.wcs)

        # Return the list of resulting frames
        return frames

    # -----------------------------------------------------------------

    def to_wavelength_density(self, new_unit, wavelength_unit):

        """
        This function ...
        :param new_unit:
        :param wavelength_unit:
        :return:
        """

        # Inform the user
        log.info("Converting the datacube from neutral flux density to flux density per unit of wavelength (in " + wavelength_unit + ")")

        # Get list of wavelengths in desired unit
        wavelengths = self.wavelength_grid.wavelengths(unit=wavelength_unit, add_unit=False)

        # Convert the frames from neutral surface brightness to wavelength surface brightness
        for l in range(self.nframes):

            # Get the wavelength
            wavelength = wavelengths[l]

            # Determine the name of the frame in the datacube
            frame_name = "frame" + str(l)

            # Divide this frame by the wavelength in micron
            self.frames[frame_name] /= wavelength

        # Set the new unit of the datacube
        self.unit = new_unit

# -----------------------------------------------------------------

def _do_one_filter_convolution_from_file(datacube_path, wavelengthgrid_path, result_path, unit, fltrname):

    """
    This function ...
    :param datacube_path:
    :param wavelengthgrid_path:
    :param result_path:
    :param unit:
    :param fltrname:
    :return:
    """

    log.info("[convolution with " + fltrname + " filter] Loading filter ...")

    # Resurrect the filter
    fltr = BroadBandFilter(fltrname)

    log.info("[convolution with " + fltrname + " filter] Loading wavelength grid ...")

    # Resurrect the wavelength grid
    wavelength_grid = WavelengthGrid.from_file(wavelengthgrid_path)

    log.info("[convolution with " + fltrname + " filter] Loading datacube ...")

    # Resurrect the datacube
    datacube = DataCube.from_file(datacube_path, wavelength_grid)

    log.info("[convolution with " + fltrname + " filter] Getting wavelength array ...")

    # Get the array of wavelengths
    wavelengths = datacube.wavelengths(asarray=True, unit="micron")

    log.info("[convolution with " + fltrname + " filter] Converting datacube to 3D array ...")

    # Convert the datacube to a numpy array where wavelength is the third dimension
    array = datacube.asarray()

    log.info("[convolution with " + fltrname + " filter] Starting convolution ...")

    # Do the convolution
    data = fltr.convolve(wavelengths, array)

    log.info("[convolution with " + fltrname + " filter] Convolution completed")

    # Create frame
    frame = Frame(data)
    frame.unit = unit
    frame.filter = fltr
    frame.wcs = datacube.wcs

    log.info("[convolution with " + fltrname + " filter] Saving result to " + result_path + " ...")

    # Save the frame with the index as name
    frame.saveto(result_path)

# -----------------------------------------------------------------

def _do_one_filter_convolution(fltr, wavelengths, array, frames, index, unit, wcs):

    """
    This function ...
    :param fltr:
    :param wavelengths:
    :param array:
    :param frames:
    :param index:
    :return:
    """

    # Debugging
    log.debug("Convolving the datacube with the " + str(fltr) + " filter ...")

    # Calculate the observed image frame
    data = fltr.convolve(wavelengths, array)
    frame = Frame(data)

    # Debugging
    log.success("Convolved the datacube with the " + str(fltr) + " filter ...")

    # Set the unit of the frame
    frame.unit = unit

    # Set the filter
    frame.filter = fltr

    # Set the wcs
    frame.wcs = wcs

    # Add the frame to the list
    frames[index] = frame

# -----------------------------------------------------------------
