#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       Astromagic -- the image editor for Astronomers        **
# *****************************************************************

# Import Python 3 functionality
from __future__ import (absolute_import, division, print_function)

# Import standard modules
import numpy as np

# Import astronomical modules
from astropy import units as u
from photutils import segment_properties, properties_table
from photutils import EllipticalAperture

# Import Astromagic modules
from ..tools import analysis
from .vector import Position, Extent
from ..tools import interpolation
from astropy.coordinates import Angle

# *****************************************************************

class Galaxy(object):

    """
    This class ...
    """

    def __init__(self, pgc_id=None, name=None, type=type, redshift=None, center=None, names=None, major=None, minor=None, pa=None, satellite=False):

        """
        The constructor ...
        :param ra:
        :param dec:
        :param name:
        :return:
        """

        # Set the attributes
        self.pgc_id = pgc_id
        self.name = name
        self.type = type
        self.redshift = redshift
        self.center = center
        self.names = names
        self.major = major
        self.minor = minor
        self.pa = pa
        self.satellite = satellite
        self.principal = False

        # Set the source attribute to None initially
        self.source = None

        # Set the aperture attribute to None initially
        self.aperture = None

    # *****************************************************************

    @property
    def has_source(self):

        """
        This function ...
        :return:
        """

        return self.source is not None

    # *****************************************************************

    @property
    def has_aperture(self):

        """
        This function ...
        :return:
        """

        return self.aperture is not None

    # *****************************************************************

    def ellipse_parameters(self, wcs, pixelscale, default_radius):

        """
        This function ...
        :param default_radius:
        :return:
        """

        # Get the center of the galaxy in pixel coordinates
        x_center, y_center = self.center.to_pixel(wcs, origin=0)

        if self.pa is None: angle = Angle(0.0, u.deg)
        else: angle = self.pa

        if self.major is None:

            x_radius = default_radius
            y_radius = default_radius

        elif self.minor is None or angle == 0.0:

            x_radius = self.major.to("arcsec") / pixelscale
            y_radius = x_radius

        else:

            x_radius = self.major.to("arcsec") / pixelscale
            y_radius = self.minor.to("arcsec") / pixelscale

        # Return the parameters
        return Position(x=x_center, y=y_center), Extent(x=x_radius, y=y_radius), angle

    # *****************************************************************

    def find_source(self, frame, config):

        """
        This function ...
        :return:
        """

        # Get the parameters of the ellipse
        center, radius, angle = self.ellipse_parameters(frame.wcs, frame.pixelscale, config.initial_radius)

        # Find a source
        self.source = analysis.find_source(frame, center, radius, angle, config)

    # *****************************************************************

    def fit_model(self, config):

        """
        This function ...
        :param frame:
        :param config:
        :return:
        """

        pass

    # *****************************************************************

    def remove(self, frame, config):

        """
        This function ...
        :param frame:
        :param config:
        :return:
        """

        # If a segment was found that can be identified with a source
        if self.has_source:

            # Estimate the background
            self.source.estimate_background(config.remove_method, config.sigma_clip)

            #from ..tools import plotting
            #plotting.plot_box(np.ma.masked_array(self.source.background, mask=self.source.mask))

            # Replace the frame with the estimated background
            self.source.background.replace(frame, where=self.source.mask)

    # *****************************************************************

    def find_aperture(self, sigma_level=3.0):

        """
        This function ...
        :return:
        """

        props = segment_properties(self.source.cutout, self.source.mask)
        #tbl = properties_table(props)

        x_shift = self.source.cutout.x_min
        y_shift = self.source.cutout.y_min

        # Since there is only one segment in the self.source.mask (the center segment), the props
        # list contains only one entry (one galaxy)
        properties = props[0]

        # Obtain the position, orientation and extent
        position = (properties.xcentroid.value + x_shift, properties.ycentroid.value + y_shift)
        a = properties.semimajor_axis_sigma.value * sigma_level
        b = properties.semiminor_axis_sigma.value * sigma_level
        theta = properties.orientation.value

        # Create the aperture
        self.aperture = EllipticalAperture(position, a, b, theta=theta)

    # *****************************************************************

    def plot(self, frame):

        """
        This function ...
        :return:
        """

        if self.has_source:

            pass

        else:

            from astropy.visualization import SqrtStretch, LogStretch
            from astropy.visualization.mpl_normalize import ImageNormalize

            x_centers = []
            y_centers = []
            apertures = []

            # Loop over all galaxies
            for galaxy in self.galaxies:

                x_center, y_center = galaxy.center.to_pixel(frame.wcs)
                x_centers.append(x_center)
                y_centers.append(y_center)

                # If the galaxy does not have a source, continue
                if galaxy.has_aperture: apertures.append(galaxy.aperture)

            # Initialize the plot
            #norm = ImageNormalize(stretch=SqrtStretch())
            norm = ImageNormalize(stretch=LogStretch())
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Determine the maximum value in the box and the mimimum value for plotting
        vmax = np.max(frame)
        vmin = np.min(frame) if vmax <= 0 else 0.0

        # Plot the frame and the segments mask
        ax1.imshow(frame, origin='lower', interpolation='nearest', norm=norm, vmin=vmin, vmax=vmax)
        ax2.imshow(self.create_mask(frame), origin='lower', cmap='jet')

        # Set axes limits
        plt.xlim(0, frame.xsize-1)
        plt.ylim(0, frame.ysize-1)

        # Plot the apertures
        for aperture in apertures:

            aperture.plot(color='white', lw=1.5, alpha=0.5, ax=ax1)
            aperture.plot(color='white', lw=1.5, alpha=1.0, ax=ax2)

        # Plot centers of the galaxies
        plt.plot(x_centers, y_centers, ls='none', color='white', marker='+', ms=40, lw=10, mew=4)

        # Show the plot
        plt.show()
        
# *****************************************************************