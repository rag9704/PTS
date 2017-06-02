#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.core.list Contains the CoordinateSystemList, FrameList, and ImageList classes.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ...core.filter.filter import parse_filter
from ..region.list import SkyRegionList
from ...core.units.parsing import parse_unit as u
from .frame import Frame
from .image import Image
from ..basics.coordinatesystem import CoordinateSystem
from ..tools import coordinates
from ..basics.coordinate import SkyCoordinate
from ..basics.stretch import SkyStretch
from ..region.rectangle import SkyRectangleRegion
from ...core.basics.containers import NamedList, FilterBasedList
from ...core.tools import filesystem as fs
from ..convolution.aniano import AnianoKernels
from ..convolution.matching import MatchingKernels
from ..convolution.kernels import get_fwhm
from ...core.tools import types

# -----------------------------------------------------------------

class CoordinateSystemList(FilterBasedList):

    """
    This class ...
    """

    def __init__(self):

        """
        THe constructor ...
        """

        # Call the constructor of the base class
        super(CoordinateSystemList, self).__init__()

    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path):

        """
        This function ...
        :param path: 
        :return: 
        """

        new = cls()
        for path in fs.files_in_path(path): new.append(Frame.from_file(path))
        return new

    # -----------------------------------------------------------------

    @property
    def systems(self): # an alias for the contents for this subclass

        """
        This function ...
        :return: 
        """

        return self.contents

    # -----------------------------------------------------------------

    def append(self, frame_or_wcs, fltr=None):

        """
        This function ...
        :param frame_or_wcs: 
        :param fltr: 
        :return: 
        """

        # Get WCS and filter
        if isinstance(frame_or_wcs, Frame):
            wcs = frame_or_wcs.wcs
            fltr = frame_or_wcs.filter
        elif isinstance(frame_or_wcs, CoordinateSystem):
            wcs = frame_or_wcs
            if fltr is None: raise ValueError("Filter must be specified")
        else: raise ValueError("Invalid input")

        # Check the key
        if fltr in self.filters: raise ValueError("Already a coordinate system for the '" + str(fltr) + "' filter")

        # Call the append function of the base class
        super(CoordinateSystemList, self).append(fltr, wcs)

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def min_ra(self):

        """
        This function ...
        :return:
        """

        min_ra = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            wcs_min_ra = wcs.min_ra

            if min_ra is None or min_ra > wcs_min_ra: min_ra = wcs_min_ra

        return min_ra

    # -----------------------------------------------------------------

    @property
    def min_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_ra.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def max_ra(self):

        """
        This function ...
        :return:
        """

        max_ra = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            wcs_max_ra = wcs.max_ra

            if max_ra is None or max_ra < wcs_max_ra: max_ra = wcs_max_ra

        return max_ra

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def max_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_ra.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def ra_center(self):

        """
        This function ...
        :return:
        """

        return 0.5 * (self.min_ra + self.max_ra)

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def ra_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.ra_center.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def ra_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]

            if the_range is None: the_range = wcs.ra_range
            else: the_range.adjust(wcs.ra_range)

        # Return the range
        return the_range

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def min_dec(self):

        """
        This function ...
        :return:
        """

        min_dec = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            wcs_min_dec = wcs.min_dec

            if min_dec is None or min_dec > wcs_min_dec: min_dec = wcs_min_dec

        # Return
        return min_dec

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def min_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_dec.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def max_dec(self):

        """
        This function ...
        :return:
        """

        max_dec = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            wcs_max_dec = wcs.max_dec

            if max_dec is None or max_dec < wcs_max_dec: max_dec = wcs_max_dec

        # Return
        return max_dec

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def dec_center(self):

        """
        This function ...
        :return:
        """

        dec_center = 0.5 * (self.min_dec + self.max_dec)
        return dec_center

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def dec_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.dec_center.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def max_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_dec.to("deg").value

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def dec_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]

            if the_range is None: the_range = wcs.dec_range
            else: the_range.adjust(wcs.dec_range)

        # Return the dec range
        return the_range

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return SkyCoordinate(self.ra_center_deg, self.dec_center_deg, unit="deg")

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def coordinate_range(self):

        """
        This function ...
        :return:
        """

        # Calculate the actual RA and DEC distance in degrees
        ra_distance = abs(coordinates.ra_distance(self.dec_center_deg, self.min_ra_deg, self.max_ra_deg))
        dec_distance = abs(self.max_dec_deg - self.min_dec_deg)

        # Create RA and DEC span as quantities
        ra_span = ra_distance * u("deg")
        dec_span = dec_distance * u("deg")

        # Return the center coordinate and the RA and DEC span
        return self.center, ra_span, dec_span

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Get coordinate range
        center, ra_span, dec_span = self.coordinate_range

        # Create box
        radius = SkyStretch(0.5 * ra_span, 0.5 * dec_span)
        box = SkyRectangleRegion(center, radius)

        # Return the box
        return box

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def min_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            if pixelscale is None or wcs.average_pixelscale < pixelscale: pixelscale = wcs.average_pixelscale

        # Return the minimum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    #@lazyproperty
    @property
    def max_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the coordinate systems
        for fltr in self.filters:

            wcs = self[fltr]
            if pixelscale is None or wcs.average_pixelscale > pixelscale: pixelscale = wcs.average_pixelscale

        # Return the maximum pixelscale
        return pixelscale

# -----------------------------------------------------------------

class NamedCoordinateSystemList(NamedList):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        The constructor ...
        :param kwargs: 
        """

        # Call the constructor of the base class
        super(NamedCoordinateSystemList, self).__init__()

        # Add coordinate systems
        for name in kwargs: self.append(name, kwargs[name])

    # -----------------------------------------------------------------

    def append(self, frame_or_wcs, name=None):

        """
        This function ...
        :param frame_or_wcs:
        :param name: 
        :return: 
        """

        # Get WCS and name
        if isinstance(frame_or_wcs, Frame):
            wcs = frame_or_wcs.wcs
            if name is None: name = frame_or_wcs.name
        elif isinstance(frame_or_wcs, CoordinateSystem): wcs = frame_or_wcs
        else: raise ValueError("Invalid input")

        # Check whether name is defined
        if name is None: raise ValueError("Name not specified")

        # Call the append function of the base class
        super(NamedCoordinateSystemList, self).append(name, wcs)

    # -----------------------------------------------------------------

    @property
    def min_ra(self):

        """
        This function ...
        :return:
        """

        min_ra = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            wcs_min_ra = wcs.min_ra

            if min_ra is None or min_ra > wcs_min_ra: min_ra = wcs_min_ra

        # Return
        return min_ra

    # -----------------------------------------------------------------

    @property
    def min_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_ra.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_ra(self):

        """
        This function ...
        :return:
        """

        max_ra = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            wcs_max_ra = wcs.max_ra

            if max_ra is None or max_ra < wcs_max_ra: max_ra = wcs_max_ra

        return max_ra

    # -----------------------------------------------------------------

    @property
    def max_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_ra.to("deg").value

    # -----------------------------------------------------------------

    @property
    def ra_center(self):

        """
        This function ...
        :return:
        """

        return 0.5 * (self.min_ra + self.max_ra)

    # -----------------------------------------------------------------

    @property
    def ra_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.ra_center.to("deg").value

    # -----------------------------------------------------------------

    @property
    def ra_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]

            if the_range is None: the_range = wcs.ra_range
            else: the_range.adjust(wcs.ra_range)

        # Return the range
        return the_range

    # -----------------------------------------------------------------

    @property
    def min_dec(self):

        """
        This function ...
        :return:
        """

        min_dec = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            wcs_min_dec = wcs.min_dec

            if min_dec is None or min_dec > wcs_min_dec: min_dec = wcs_min_dec

        # Return
        return min_dec

    # -----------------------------------------------------------------

    @property
    def min_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_dec.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_dec(self):

        """
        This function ...
        :return:
        """

        max_dec = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            wcs_max_dec = wcs.max_dec

            if max_dec is None or max_dec < wcs_max_dec: max_dec = wcs_max_dec

        # Return
        return max_dec

    # -----------------------------------------------------------------

    @property
    def dec_center(self):

        """
        This function ...
        :return:
        """

        dec_center = 0.5 * (self.min_dec + self.max_dec)
        return dec_center

    # -----------------------------------------------------------------

    @property
    def dec_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.dec_center.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_dec.to("deg").value

    # -----------------------------------------------------------------

    @property
    def dec_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]

            if the_range is None: the_range = wcs.dec_range
            else: the_range.adjust(wcs.dec_range)

        # Return the dec range
        return the_range

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return SkyCoordinate(self.ra_center_deg, self.dec_center_deg, unit="deg")

    # -----------------------------------------------------------------

    @property
    def coordinate_range(self):

        """
        This function ...
        :return:
        """

        # Calculate the actual RA and DEC distance in degrees
        ra_distance = abs(coordinates.ra_distance(self.dec_center_deg, self.min_ra_deg, self.max_ra_deg))
        dec_distance = abs(self.max_dec_deg - self.min_dec_deg)

        # Create RA and DEC span as quantities
        ra_span = ra_distance * u("deg")
        dec_span = dec_distance * u("deg")

        # Return the center coordinate and the RA and DEC span
        return self.center, ra_span, dec_span

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Get coordinate range
        center, ra_span, dec_span = self.coordinate_range

        # Create box
        radius = SkyStretch(0.5 * ra_span, 0.5 * dec_span)
        box = SkyRectangleRegion(center, radius)

        # Return the box
        return box

    # -----------------------------------------------------------------

    @property
    def min_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            if pixelscale is None or wcs.average_pixelscale < pixelscale: pixelscale = wcs.average_pixelscale

        # Return the minimum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def max_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the coordinate systems
        for name in self.names:

            wcs = self[name]
            if pixelscale is None or wcs.average_pixelscale > pixelscale: pixelscale = wcs.average_pixelscale

        # Return the maximum pixelscale
        return pixelscale

# -----------------------------------------------------------------

class FrameList(FilterBasedList):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        THe constructor ...
        :param args:
        :param kwargs:
        """

        # Call the constructor of the base class
        super(FrameList, self).__init__()

        # Add frames
        for frame in args: self.append(frame)
        for filter_name in kwargs: self.append(kwargs[filter_name], fltr=parse_filter(filter_name))

    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path):

        """
        This function ...
        :param path: 
        :return: 
        """

        new = cls()
        for path in fs.files_in_path(path, extension="fits"): new.append(Frame.from_file(path))
        return new

    # -----------------------------------------------------------------

    @property
    def frames(self): # an alias for the contents for this subclass

        """
        This function ...
        :return: 
        """

        return self.contents

    # -----------------------------------------------------------------

    def append(self, frame, fltr=None):

        """
        This function ...
        :param frame: 
        :param fltr:
        :return: 
        """

        if fltr is None: fltr = frame.filter

        # Check keys
        if fltr in self.frames: raise ValueError("Already a frame for the '" + str(fltr) + "' filter")

        # Call the function of the base class
        super(FrameList, self).append(fltr, frame)

    # -----------------------------------------------------------------

    @property
    def min_fwhm(self):

        """
        This function ...
        :return:
        """

        fwhm = None

        # Loop over the frames
        for fltr in self.frames:
            if fwhm is None or self.frames[fltr].fwhm < fwhm: fwhm = self.frames[fltr].fwhm

        # Return the minimum FWHM
        return fwhm

    # -----------------------------------------------------------------

    @property
    def max_fwhm(self):

        """
        This function ...
        :return:
        """

        fwhm = None

        # Loop over the frames
        for fltr in self.frames:
            if fwhm is None or self.frames[fltr].fwhm > fwhm: fwhm = self.frames[fltr].fwhm

        # Return the maximum FWHM
        return fwhm

    # -----------------------------------------------------------------

    @property
    def max_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the frames
        for fltr in self.frames:

            wcs = self.frames[fltr].wcs
            if pixelscale is None or wcs.average_pixelscale > pixelscale: pixelscale = wcs.average_pixelscale

        # Return the maximum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def min_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the frames
        for fltr in self.frames:

            wcs = self.frames[fltr].wcs
            if pixelscale is None or wcs.average_pixelscale < pixelscale: pixelscale = wcs.average_pixelscale

        # Return the minimum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Region of all the bounding boxes
        boxes_region = SkyRegionList()

        # Add the bounding boxes as sky rectangles
        for name in self.frames: boxes_region.append(self.frames[name].wcs.bounding_box)

        # Return the bounding box of the region of rectangles
        return boxes_region.bounding_box

    # -----------------------------------------------------------------

    @property
    def center_coordinate(self):

        """
        This function ...
        :return:
        """

        return self.bounding_box.center

    # -----------------------------------------------------------------

    @property
    def coordinate_systems(self):

        """
        THis function ...
        :return: 
        """

        for fltr in self.frames: yield self.frames[fltr].wcs

    # -----------------------------------------------------------------

    @property
    def min_ra(self):

        """
        This function ...
        :return:
        """

        min_ra = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]
            wcs_min_ra = wcs.min_ra

            if min_ra is None or min_ra > wcs_min_ra: min_ra = wcs_min_ra

        return min_ra

    # -----------------------------------------------------------------

    @property
    def min_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_ra.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_ra(self):

        """
        This function ...
        :return:
        """

        max_ra = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]
            wcs_max_ra = wcs.max_ra

            if max_ra is None or max_ra < wcs_max_ra: max_ra = wcs_max_ra

        return max_ra

    # -----------------------------------------------------------------

    @property
    def max_ra_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_ra.to("deg").value

    # -----------------------------------------------------------------

    @property
    def ra_center(self):

        """
        This function ...
        :return:
        """

        return 0.5 * (self.min_ra + self.max_ra)

    # -----------------------------------------------------------------

    @property
    def ra_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.ra_center.to("deg").value

    # -----------------------------------------------------------------

    @property
    def ra_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]

            if the_range is None: the_range = wcs.ra_range
            else: the_range.adjust(wcs.ra_range)

        # Return the range
        return the_range

    # -----------------------------------------------------------------

    @property
    def min_dec(self):

        """
        This function ...
        :return:
        """

        min_dec = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]
            wcs_min_dec = wcs.min_dec

            if min_dec is None or min_dec > wcs_min_dec: min_dec = wcs_min_dec

        # Return
        return min_dec

    # -----------------------------------------------------------------

    @property
    def min_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.min_dec.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_dec(self):

        """
        This function ...
        :return:
        """

        max_dec = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]
            wcs_max_dec = wcs.max_dec

            if max_dec is None or max_dec < wcs_max_dec: max_dec = wcs_max_dec

        # Return
        return max_dec

    # -----------------------------------------------------------------

    @property
    def dec_center(self):

        """
        This function ...
        :return:
        """

        dec_center = 0.5 * (self.min_dec + self.max_dec)
        return dec_center

    # -----------------------------------------------------------------

    @property
    def dec_center_deg(self):

        """
        This function ...
        :return:
        """

        return self.dec_center.to("deg").value

    # -----------------------------------------------------------------

    @property
    def max_dec_deg(self):

        """
        This function ...
        :return:
        """

        return self.max_dec.to("deg").value

    # -----------------------------------------------------------------

    @property
    def dec_range(self):

        """
        This function ...
        :return:
        """

        the_range = None

        # Loop over the coordinate systems
        #for fltr in self.coordinate_systems:
        for wcs in self.coordinate_systems:

            #wcs = self.coordinate_systems[fltr]

            if the_range is None: the_range = wcs.dec_range
            else: the_range.adjust(wcs.dec_range)

        # Return the dec range
        return the_range

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return SkyCoordinate(self.ra_center_deg, self.dec_center_deg, unit="deg")

    # -----------------------------------------------------------------

    @property
    def coordinate_range(self):

        """
        This function ...
        :return:
        """

        # Calculate the actual RA and DEC distance in degrees
        ra_distance = abs(coordinates.ra_distance(self.dec_center_deg, self.min_ra_deg, self.max_ra_deg))
        dec_distance = abs(self.max_dec_deg - self.min_dec_deg)

        # Create RA and DEC span as quantities
        ra_span = ra_distance * u("deg")
        dec_span = dec_distance * u("deg")

        # Return the center coordinate and the RA and DEC span
        return self.center, ra_span, dec_span

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Get coordinate range
        center, ra_span, dec_span = self.coordinate_range

        # Create box
        radius = SkyStretch(0.5 * ra_span, 0.5 * dec_span)
        box = SkyRectangleRegion(center, radius)

        # Return the box
        return box

    # -----------------------------------------------------------------

    def converted_to_same_unit(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return: 
        """

        # Inform the user
        log.info("Converting frames to the same unit ...")

        # Check if the unit is defined
        if "unit" in kwargs: unit = kwargs.pop("unit")
        else: unit = self[0].unit

        # Debugging
        log.debug("Converting to unit '" + str(unit) + "' ...")

        # Initialize list for converted frames
        new_frames = FrameList()

        # Convert all
        for fltr in self.frames:
            frame = self.frames[fltr]
            new_frames.append(frame.converted_to(unit, **kwargs))

        # Return the new set of frames
        return new_frames

    # -----------------------------------------------------------------

    def convolve_to_highest_fwhm(self):

        """
        This function ...
        :return: 
        """

        new_frames = convolve_to_highest_fwhm(*self.values, names=self.filter_names)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def rebin_to_highest_pixelscale(self):

        """
        This function ...
        :return: 
        """

        new_frames = rebin_to_highest_pixelscale(*self.values, names=self.filter_names)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def convert_to_same_unit(self, unit=None, **kwargs):

        """
        This function ...
        :param unit:
        :param kwargs:
        :return: 
        """
        
        new_frames = convert_to_same_unit(*self.values, unit=unit, names=self.filter_names, **kwargs)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def convolve_rebin_and_convert(self, unit=None, **kwargs):

        """
        This function ...
        :param unit: 
        :param kwargs: 
        :return: 
        """

        new_frames = convolve_rebin_and_convert(*self.values, unit=unit, names=self.filter_names, **kwargs)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def uniformize(self, unit=None, **kwargs):

        """
        This function is an alias for convolve_rebin_and_convert
        :param unit:
        :param kwargs:
        :return: 
        """

        return self.convolve_rebin_and_convert(unit=unit, **kwargs)

# -----------------------------------------------------------------

class NamedFrameList(NamedList):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        This function ...
        :param kwargs:
        """

        # Call the constructor of the base class
        super(NamedFrameList, self).__init__()

        # Add
        for name in kwargs: self.append(kwargs[name], name)

    # -----------------------------------------------------------------

    @property
    def frames(self): # an alias for the contents for this subclass

        """
        This function ...
        :return: 
        """

        return self.contents

    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path, contains=None):

        """
        This function ...
        :param path: 
        :param contains:
        :return: 
        """

        new = cls()
        for path, name in fs.files_in_path(path, returns=["path", "name"], extension="fits", contains=contains): new.append(name, Frame.from_file(path))
        return new

    # -----------------------------------------------------------------

    @classmethod
    def from_paths(cls, **paths):

        """
        This function ...
        :param paths: 
        :return: 
        """

        new = cls()
        for name in paths: new.append(Frame.from_file(paths[name]), name)
        return new

    # -----------------------------------------------------------------

    @classmethod
    def from_dictionary(cls, dictionary):

        """
        This function ...
        :param dictionary: 
        :return: 
        """

        new = cls()
        for name in dictionary: new.append(dictionary[name], name=name)
        return new

    # -----------------------------------------------------------------

    def append(self, frame, name=None):

        """
        This function ...
        :param frame: 
        :param name: 
        :return: 
        """

        if name is None: name = frame.name
        if name is None: raise ValueError("Frame does not have a name")

        # Call the append function of the base class
        super(NamedFrameList, self).append(name, frame)

    # -----------------------------------------------------------------

    def convolve_to_name(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Get FWHM and PSF filter
        fwhm = self[name].fwhm
        psf_filter = self[name].psf_filter

        # Convolve and replace
        new_frames = convolve_to_fwhm(*self.values, names=self.names, fwhm=fwhm, filter=psf_filter)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def rebin_to_name(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Get pixelscale and wcs
        pixelscale = self[name].average_pixelscale
        wcs = self[name].wcs

        # Rebin and replace
        new_frames = rebin_to_pixelscale(*self.values, names=self.names, pixelscale=pixelscale, wcs=wcs)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    @property
    def highest_fwhm_name(self):

        """
        This function ...
        :return:
        """

        return get_highest_fwhm_name(*self.values, names=self.names)

    # -----------------------------------------------------------------

    @property
    def highest_pixelscale_name(self):

        """
        This function ...
        :return:
        """

        return get_highest_pixelscale_name(*self.values, names=self.names)

    # -----------------------------------------------------------------

    def convolve_to_highest_fwhm(self):

        """
        This function ...
        :return:
        """

        new_frames = convolve_to_highest_fwhm(*self.values, names=self.names)
        self.remove_all()
        for frame in new_frames: self.append(frame)

    # -----------------------------------------------------------------

    def rebin_to_highest_pixelscale(self):

        """
        This function ...
        :return:
        """

        new_frames = rebin_to_highest_pixelscale(*self.values, names=self.names)
        self.remove_all()
        for frame in new_frames: self.append(frame)

# -----------------------------------------------------------------

class ImageList(FilterBasedList):
        
    """
    This class ...
    """

    def __init__(self):

        """
        THe constructor ...
        """

        # Call the constructor of the base class
        super(ImageList, self).__init__()

    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path):

        """
        This function ...
        :param path: 
        :return: 
        """

        new = cls()
        for path in fs.files_in_path(path): new.append(Image.from_file(path))
        return new

    # -----------------------------------------------------------------

    def append(self, image):

        """
        This function ...
        :param image: 
        :return: 
        """

        # Check keys
        if image.fltr in self.images: raise ValueError("Already an image for the '" + str(image.filter) + "' filter")

        # Call the function of the base class
        super(ImageList, self).append(image.filter, image)

    # -----------------------------------------------------------------

    @property
    def images(self): # an alias for the contents for this subclass

        """
        This function ...
        :return: 
        """

        return self.contents

# -----------------------------------------------------------------

class NamedImageList(NamedList):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        The constructor ...
        :param kwargs:
        """

        # Call the constructor of the base class
        super(NamedImageList, self).__init__()

        # Add
        for name in kwargs: self.append(kwargs[name], name)

    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path):

        """
        This function ...
        :param path: 
        :return: 
        """

        new = cls()
        for path, name in fs.files_in_path(path, returns=["path", "name"], extension="fits"): new.append(Image.from_file(path), name)
        return new

    # -----------------------------------------------------------------

    @property
    def images(self): # an alias for the contents for this subclass

        """
        This function ...
        :return: 
        """

        return self.contents

    # -----------------------------------------------------------------

    @classmethod
    def from_dictionary(cls, dictionary):

        """
        This function ...
        :param dictionary: 
        :return: 
        """

        new = cls()
        for name in dictionary: new.append(dictionary[name], name=name)
        return new

    # -----------------------------------------------------------------

    @property
    def names(self):

        """
        THis function ...
        :return: 
        """

        return self.keys

    # -----------------------------------------------------------------

    def append(self, image, name=None):

        """
        This function ...
        :param image: 
        :param name: 
        :return: 
        """

        if name is None: name = image.name
        if name is None: raise ValueError("Image does not have a name")

        # Check
        if name in self.images: raise ValueError("Already an image with the name '" + name + "'")

        # Call the append function of the base class
        super(NamedImageList, self).append(name, image)

    # -----------------------------------------------------------------

    @property
    def min_fwhm(self):

        """
        This function ...
        :return:
        """

        fwhm = None

        # Loop over the images
        for name in self.names:
            if fwhm is None or self.images[name].fwhm < fwhm: fwhm = self.images[name].fwhm

        # Return the minimum FWHM
        return fwhm

    # -----------------------------------------------------------------

    @property
    def max_fwhm(self):

        """
        This function ...
        :return:
        """

        fwhm = None

        # Loop over the images
        for name in self.names:
            if fwhm is None or self.images[name].fwhm > fwhm: fwhm = self.images[name].fwhm

        # Return the maximum FWHM
        return fwhm

    # -----------------------------------------------------------------

    @property
    def max_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the images
        for name in self.names:

            wcs = self.images[name].wcs
            if pixelscale is None or wcs.average_pixelscale > pixelscale: pixelscale = wcs.average_pixelscale

        # Return the maximum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def min_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the images
        for name in self.names:

            wcs = self.images[name].wcs
            if pixelscale is None or wcs.average_pixelscale < pixelscale: pixelscale = wcs.average_pixelscale

        # Return the minimum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Region of all the bounding boxes
        boxes_region = SkyRegionList()

        # Add the bounding boxes as sky rectangles
        for name in self.names: boxes_region.append(self.images[name].wcs.bounding_box)

        # Return the bounding box of the region of rectangles
        return boxes_region.bounding_box

    # -----------------------------------------------------------------

    @property
    def center_coordinate(self):

        """
        This function ...
        :return:
        """

        return self.bounding_box.center

# -----------------------------------------------------------------

def convolve_rebin_and_convert(*frames, **kwargs):

    """
    This function ...
    :param frames: 
    :param kwargs: 
    :return: 
    """

    # First rebin
    frames = rebin_to_highest_pixelscale(*frames, **kwargs)

    # Then convolve
    frames = convolve_to_highest_fwhm(*frames, **kwargs)

    # Then convert
    frames = convert_to_same_unit(*frames, **kwargs)

    # Return the frames
    return frames

# -----------------------------------------------------------------

def convert_to_same_unit(*frames, **kwargs):

    """
    This function ...
    :param frames:
    :param kwargs:
    :return: 
    """

    # Get frame names
    names = kwargs.pop("names", None)

    # Inform the user
    log.info("Converting frames to the same unit ...")

    # Check if the unit is defined
    if "unit" in kwargs:
        unit = kwargs.pop("unit")
        #if types.is_string_type(unit): unit = u(unit, **kwargs) # not necessary: converted_to() of frame takes **kwargs
    else: unit = frames[0].unit

    # Debugging
    log.debug("Converting frames to unit '" + str(unit) + "' ...")

    # Initialize list for converted frames
    new_frames = []

    # Convert all
    index = 0
    for frame in frames:

        # Get frame name
        name = "'" + names[index] + "' " if names is not None else ""

        # Debugging
        log.debug("Converting frame " + name + "with unit '" + str(frame.unit) + "' to '" + str(unit) + "' ...")
        converted = frame.converted_to(unit, **kwargs)
        new_frames.append(converted)

        # Increment index
        index += 1

    # Return the new set of frames
    return new_frames

# -----------------------------------------------------------------

def get_highest_pixelscale_name(*frames, **kwargs):

    """
    This function ...
    :param frames:
    :param kwargs:
    :return:
    """

    # Get frame names
    names = kwargs.pop("names")

    highest_pixelscale = None
    highest_pixelscale_wcs = None
    highest_pixelscale_name = None

    # Loop over the frames
    for frame, name in zip(frames, names):

        wcs = frame.wcs
        if highest_pixelscale is None or wcs.average_pixelscale > highest_pixelscale:

            highest_pixelscale = wcs.average_pixelscale
            highest_pixelscale_wcs = wcs
            highest_pixelscale_name = name

    # Return the name
    return highest_pixelscale_name

# -----------------------------------------------------------------

def rebin_to_highest_pixelscale(*frames, **kwargs):

    """
    This function ...
    :param frames: 
    :param kwargs:
    :return: 
    """

    # Get frame names
    names = kwargs.pop("names", None)

    # Inform the user
    log.info("Rebinning frames to the coordinate system with the highest pixelscale ...")

    highest_pixelscale = None
    highest_pixelscale_wcs = None

    # Loop over the frames
    for frame in frames:

        wcs = frame.wcs
        if highest_pixelscale is None or wcs.average_pixelscale > highest_pixelscale:

            highest_pixelscale = wcs.average_pixelscale
            highest_pixelscale_wcs = wcs

    # Rebin
    return rebin_to_pixelscale(*frames, names=names, pixelscale=highest_pixelscale, wcs=highest_pixelscale_wcs)

# -----------------------------------------------------------------

def rebin_to_pixelscale(*frames, **kwargs):

    """
    THis function ...
    :param frames:
    :param kwargs:
    :return:
    """

    # Get input
    names = kwargs.pop("names")
    highest_pixelscale = kwargs.pop("pixelscale")
    highest_pixelscale_wcs = kwargs.pop("wcs")

    # Initialize list for rebinned frames
    new_frames = []

    # Rebin
    index = 0
    for frame in frames:

        # Determine frame name
        name = "'" + names[index] + "' " if names is not None else ""

        # If the current frame is the frame with the highest pixelscale
        if frame.wcs == highest_pixelscale_wcs:

            if names is not None: log.debug("Frame " + name + "has highest pixelscale of '" + str(highest_pixelscale) + "' and is not rebinned")
            new_frames.append(frame.copy())

        # The frame has a lower pixelscale, has to be rebinned
        else:

            # Is per pixelsize
            if frame.unit.is_per_pixelsize:

                # Debugging
                log.debug("Frame " + name + "is expressed in units per angular or intrinsic area (pixelsize squared)")

                # Debugging
                log.debug("Rebinning frame " + name + "with unit '" + str(frame.unit) + "' ...")
                rebinned = frame.rebinned(highest_pixelscale_wcs)

            # Not per pixelsize
            else:

                # Debugging
                log.debug("Frame " + name + "is not expressed in units per angular or intrinsic area (pixelsize squared)")

                # Debugging
                #log.debug("Converting frame " + name + "with unit '" + str(frame.unit) + "' to '" + str(frame.corresponding_angular_area_unit) + "' prior to rebinning ...")
                #old_unit = frame.unit
                #rebinned = frame.converted_to_corresponding_angular_area_unit(**kwargs)
                #rebinned.rebin(highest_pixelscale_wcs)
                # Convert back to old unit
                #rebinned.convert_to(old_unit)

                #print(rebinned)

                # NEW WAY:

                # Converting unit is not necessary if we calculate the ratio of both pixel areas
                ratio = highest_pixelscale_wcs.pixelarea / frame.wcs.pixelarea

                # Debugging
                log.debug("Rebinning frame " + name + " and multiplying with a factor of " + str(ratio) + " to correct for the changing pixelscale ...")

                # Rebin and multiply
                rebinned = frame.rebinned(highest_pixelscale_wcs)
                rebinned *= ratio

                #print(rebinned)

            # Add the rebinned frame
            new_frames.append(rebinned)

        index += 1

    # Return the rebinned frames
    return new_frames

# -----------------------------------------------------------------

def get_highest_fwhm_name(*frames, **kwargs):

    """
    THis function ...
    :param frames:
    :param kwargs:
    :return:
    """

    # Get frame names
    names = kwargs.pop("names")

    highest_fwhm = None
    highest_fwhm_filter = None
    highest_fwhm_name = None

    # Loop over the frames
    for frame, name in zip(frames, names):

        # Search and set frame FWHM
        frame_fwhm = frame.fwhm
        if frame_fwhm is None: frame_fwhm = get_fwhm(frame.filter)
        frame.fwhm = frame_fwhm

        if highest_fwhm is None or frame.fwhm > highest_fwhm:

            highest_fwhm = frame.fwhm
            highest_fwhm_filter = frame.psf_filter
            highest_fwhm_name = name

    # Return the name
    return highest_fwhm_name

# -----------------------------------------------------------------

def convolve_to_highest_fwhm(*frames, **kwargs):

    """
    This function ...
    :param frames: 
    :return: 
    """

    # Get frame names
    names = kwargs.pop("names", None)

    # Inform the user
    log.info("Convolving frames to the resolution of the frame with the highest FWHM ...")

    highest_fwhm = None
    highest_fwhm_filter = None

    # Loop over the frames
    for frame in frames:

        # Search and set frame FWHM
        frame_fwhm = frame.fwhm
        if frame_fwhm is None: frame_fwhm = get_fwhm(frame.filter)
        frame.fwhm = frame_fwhm

        if highest_fwhm is None or frame.fwhm > highest_fwhm:

            highest_fwhm = frame.fwhm
            highest_fwhm_filter = frame.psf_filter

    # Convolve
    return convolve_to_fwhm(*frames, names=names, fwhm=highest_fwhm, filter=highest_fwhm_filter)

# -----------------------------------------------------------------

def convolve_to_fwhm(*frames, **kwargs):

    """
    This function ...
    :param frames:
    :param kwargs:
    :return:
    """

    # Get input
    names = kwargs.pop("names")
    highest_fwhm = kwargs.pop("fwhm")
    highest_fwhm_filter = kwargs.pop("filters")

    # Get kernel services
    aniano = AnianoKernels()
    matching = MatchingKernels()

    # Initialize list for convolved frames
    new_frames = []

    # Convolve
    index = 0
    for frame in frames:

        # Get frame name
        name = "'" + names[index] + "' " if names is not None else ""

        if frame.psf_filter == highest_fwhm_filter:

            # Debugging
            log.debug("Frame '" + names[index] + "' has highest FWHM of " + str(highest_fwhm) + " and is not convolved")

            # Add a copy of the frame
            new_frames.append(frame.copy())

        # Convolve
        else:

            # Debugging
            log.debug("Frame " + name + " is convolved to a PSF with FWHM = " + str(highest_fwhm) + " ...")

            # Get the kernel, either from aniano or from matching kernels
            if aniano.has_kernel_for_filters(frame.psf_filter, highest_fwhm_filter): kernel = aniano.get_kernel(frame.psf_filter, highest_fwhm_filter)
            else:

                # Get from and to filter
                from_filter = frame.psf_filter
                to_filter = highest_fwhm_filter

                # Get from and to FWHM
                if frame.fwhm is not None: from_fwhm = frame.fwhm
                else: from_fwhm = get_fwhm(from_filter)
                to_fwhm = highest_fwhm

                # Generate the kernel
                kernel = matching.get_kernel(from_filter, to_filter, frame.pixelscale, from_fwhm=from_fwhm, to_fwhm=to_fwhm)

            # Convolve with the kernel
            convolved = frame.convolved(kernel)
            new_frames.append(convolved)

        # Increment the index
        index += 1

    # Return the convolved frames
    return new_frames

# -----------------------------------------------------------------
