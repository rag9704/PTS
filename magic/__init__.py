#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       Astromagic -- the image editor for Astronomers        **
# *****************************************************************

# Import Python 3 functionality
from __future__ import (absolute_import, division, print_function)

# Import standard modules
import os
import os.path
import math
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
import copy

# Import astronomical modules
import aplpy
import pyregion
import astropy.io.fits as pyfits
from astropy import wcs
import astropy.units as u
from astropy import log

# Import Astromagic modules
from .tools import headers
from .tools import interpolation
from .tools import fitting
from .tools import plotting
from .tools import analysis
from .core import regions
from .tools import statistics
from .tools import catalogs
from .core.layers import Layers
from .core.frames import Frame
from .core.masks import Mask
from .core.regions import Region

# *****************************************************************

# Do not show warnings, to block Canopy's UserWarnings from spoiling the console log
import warnings
warnings.filterwarnings("ignore")

# *****************************************************************

class Image(object):

    """
    This class ...
    """

    def __init__(self, filename=None):

        """
        The constructor ...
        :param filename:
        :return:
        """

        if filename is None:
            
            # Initialize a set of layers to represent image frames, masks and regions
            self.frames = Layers()
            self.masks = Layers()
            self.regions = Layers()

            # Set default values for other attributes
            self.unit = None
            self.fwhm = None
            self.header = None
            
            return

        # Check if the specified file exists, otherwise exit with an error
        if not os.path.isfile(filename): raise IOError("No such file: " + filename)

        # Set the name of the image
        self.name = os.path.splitext(os.path.basename(filename))[0]

        # Initialize a set of layers to represent image frames, masks and regions
        self.frames = Layers()
        self.masks = Layers()
        self.regions = Layers()
        
        # Read in the image
        self._load_image(filename)

        # Set default values for other attributes
        self.unit = None
        self.fwhm = None

    # *****************************************************************

    def deselect_all(self):

        """
        This function ...
        :return:
        """

        self.frames.deselect_all()
        self.regions.deselect_all()
        self.masks.deselect_all()

    # *****************************************************************

    def import_datacube(self, path, name):

        """
        This function imports the datacube of a FITS file into this image
        :param path:
        :param name:
        :return:
        """

        # TODO: add coordinates !

        # Open the HDU list for the FITS file
        hdulist = pyfits.open(path)

        # Get the primary data
        hdu = hdulist[0]
        
        header = hdu.header

        # Check whether multiple planes are present in the FITS image
        nframes = headers.get_number_of_frames(header)
        if nframes > 1:

            # For each frame
            for i in range(nframes):

                # Get the name of this frame, but the first frame always gets the name 'primary'
                description = headers.get_frame_description(header, i)
                frame_name = name + "_" + headers.get_frame_name(description) if i else name

                # Add this frame to the frames dictionary
                #self.add_frame(hdu.data[i], coordinates, frame_name, description)
                self.add_frame(Frame(hdu.data[i], None, None, description), frame_name)

        else:

            # Sometimes, the 2D frame is embedded in a 3D array with shape (1, xsize, ysize)
            if len(hdu.data.shape) == 3: hdu.data = hdu.data[0]

            # Add the primary image frame
            self.add_frame(Frame(hdu.data, None, None, None), name)

        # Close the fits file
        hdulist.close()

    # *****************************************************************

    def export_datacube(self, filepath):

        """
        This function exports the currently selected frame(s) as a datacube into FITS file
        :param filepath:
        :return:
        """

        # Create an array to contain the data cube
        datacube = []

        # Get the coordinates of the primary frame
        coordinates = self.frames["primary"].wcs
        
        # Construct a header for the image based on the coordinates of the primary frame
        header = coordinates.to_header() if coordinates is not None else None
        
        if header is None and self.header: header = self.header
        if header is None: header = pyfits.Header()

        plane_index = 0

        # Export all active frames to the specified file
        for frame_name in self.frames.get_selected():

            # Inform the user that this frame is being rebinned
            log.info("Exporting the " + frame_name + " frame to " + filepath)

            # Add this frame to the data cube, if its coordinates match those of the primary frame
            if coordinates == self.frames[frame_name].wcs: datacube.append(self.frames[frame_name])
            
            # Add the name of the frame to the header
            header["PLANE"+str(plane_index)] = frame_name
            
            plane_index += 1

        # Create the HDU from the data array and the header
        hdu = pyfits.PrimaryHDU(np.array(datacube), header)

        # Write the HDU to a FITS file
        hdu.writeto(filepath, clobber=True)

        # Inform the user that the file has been created
        log.info("File " + filepath + " created")

    # *****************************************************************

    def import_region(self, path, name):

        """
        This function imports a new region from a DS9 region file
        :param path:
        :param name:
        :return:
        """

        # Create an pyregion object from the regions file
        region = pyregion.open(path)

        # Add the region to the set of regions
        self._add_region(region, name)

    # *****************************************************************

    def export_region(self, path):

        """
        This function exports the currently selected region(s) to a DS9 region file
        :param path:
        :return:
        """

        # Find the active region
        region = self.regions.get_selected(require_single=True)

        # Inform the user
        log.info("Creating " + path + " from the " + region + " region")

        # Write the region file
        self.regions[region].region.write(path)

    # *****************************************************************

    def get_state(self):

        """
        This function ...
        :return:
        """

        # Create an empty dictionary to contain the state of the current image
        state = dict()

        # Loop over all frames, regions and masks and record whether they are selected
        for frame_name in self.frames: state["frames/"+frame_name] = self.frames[frame_name].selected
        for region_name in self.regions: state["regions/"+region_name] = self.regions[region_name].selected
        for mask_name in self.masks: state["masks/"+mask_name] = self.masks[mask_name].selected

        # Return the state dictionary
        return state

    # *****************************************************************

    def set_state(self, state):

        """
        This function ...
        :param state:
        :return:
        """

        # Deselect all frames, regions and masks of this image
        self.deselect_all()

        # Loop over the entries in the state dictionary
        for identifier, selected in state.items():

            # Split the layer identifier into the layer type and the actual name of that layer
            layer_type, name = identifier.split("/")

            # Set the appropriate flag
            if layer_type == "frames": self.frames[name].selected = selected
            elif layer_type == "regions": self.regions[name].selected = selected
            elif layer_type == "masks": self.masks[name].selected = selected
            else: raise ValueError("Invalid state dictionary")

    # *****************************************************************

    def plot(self, path=None, color=True, grid=False, blacknan=False, publication=False):

        """
        This function shows a plot of the currently selected frame, combined with the active regions and masks
        :param path:
        :param color:
        :param grid:
        :param blacknan:
        :param publication:
        :return:
        """

        # Get the currently active frame
        frame = self.frames.get_selected()[0]

        # Create a total mask of the currently active masks
        total_mask = self.combine_masks(return_mask=True)

        # Mask the frame with nans
        maskedimage = np.ma.array(self.frames[frame], mask = total_mask)
        image_with_nans =  maskedimage.filled(np.NaN)

        # Create a HDU from this frame with the image header
        hdu = pyfits.PrimaryHDU(image_with_nans, self.header)

        if path is None:

            # Create a figure canvas
            figure = plt.figure(figsize=(12, 12))

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu, figure=figure)

        else:

            # Create a figure from this frame
            plot = aplpy.FITSFigure(hdu)

        if color:

            # Plot in color scale
            plot.show_colorscale()

        else:

            # Plot in gray scale
            plot.show_grayscale()

        # Add a color bar
        plot.add_colorbar()

        if blacknan:

            # Set the nan color to black
            plot.set_nan_color('black')

        if grid:

            # Add a grid
            plot.add_grid()

        # If requested, use the 'publication' theme
        if publication: plot.set_theme('publication')

        # Add the regions
        for region in self.regions.get_selected():

            # Get the shape list
            shapes = self.regions[region].region.as_imagecoord(self.header)

            # Add these shapes to the plot
            plot.show_regions(shapes)

        if path is None:

            #plt.draw()
            #plt.close('all') # redundant
            #plt.show(block=False)
            plt.show()

        else: plot.save(path)

    # *****************************************************************

    def delete_frames(self):

        """
        This function removes the currently selected frame(s)
        :return:
        """

        # For each active frame
        for frame_name in self.frames.get_selected(allow_none=False):

            # Inform the user
            log.info("Deleting the " + frame_name + " frame")

            # Remove this frame from the frames dictionary
            del self.frames[frame_name]

    # *****************************************************************

    def copy_frames(self):

        """
        This function ...
        :return:
        """

        # For each selected frame
        for frame_name in self.frames.get_selected(allow_none=False):

            # Inform the user
            log.info("Copying the " + frame_name + " frame as another frame")

            # Copy the data and add it as a new frame
            data_copy = copy.deepcopy(self.frames[frame_name])
            #coordinates = self.frames[frame_name].coordinates

            data_copy.description = "Copy of the "+frame_name+" frame"

            self.add_frame(data_copy, frame_name+"_copy")

    # *****************************************************************

    def delete_regions(self):

        """
        This function removes the currently selected region(s)
        :return:
        """

        # For each active region
        for region_name in self.regions.get_selected(allow_none=False):

            # Inform the user
            log.info("Deleting the " + region_name + " region")

            # Remove this region from the regions dictionary
            del self.regions[region_name]

    # *****************************************************************

    def delete_masks(self):

        """
        This function removes the currently selected mask(s)
        :return:
        """

        # For each active mask
        for mask_name in self.masks.get_selected(allow_none=False):

            # Inform the user
            log.info("Deleting the " + mask_name + " mask")

            # Remove this mask from the masks dictionary
            del self.masks[mask_name]

    # *****************************************************************

    def apply_masks(self, fill=0.0):

        """
        This function ...
        :param fill:
        :return:
        """

        # Loop over all selected frames
        for frame in self.frames.selected(allow_none=False):

            # Loop over all selected masks
            for mask in self.masks.selected(allow_none=False):

                # Apply the mask
                mask.apply(frame, fill)

    # *****************************************************************

    def combine_regions(self, name=None, allow_none=True):

        """
        This function ...
        :param name:
        :param allow_none:
        :return:
        """

        # Initialize an empty list of shapes
        total_region = pyregion.ShapeList([])

        # TODO: what to do if one region is in image coordinates and other in physical coordinates?
        # Temporary fix: all in image coordinates

        # Loop over all active regions, adding them together
        for region_name in self.regions.get_selected(allow_none=allow_none):

            # Add all the shapes of this region to the combined region
            for shape in self.regions[region_name].region.as_imagecoord(self.header):

                total_region.append(shape)

        # If no name is provided, return the new region
        if name is None: return total_region

        # Else, add the region to the list of regions, with the appropriate name
        else: self._add_region(total_region, name)

    # *****************************************************************

    def combine_masks(self, name=None, allow_none=True, return_mask=False):

        """
        This function ...
        :param name:
        :param allow_none:
        :return:
        """

        # Initialize an boolean array for the total mask
        total_mask = np.zeros_like(self.frames.primary, dtype=bool)

        # For each active mask
        for mask_name in self.masks.get_selected(allow_none=allow_none):

            # Add this mask to the total
            total_mask += self.masks[mask_name].data

        # Set the name of the total mask
        name = name if name is not None else "total"

        # Return the mask or add it to this image
        if return_mask: return total_mask
        else: self._add_mask(total_mask, name)

    # *****************************************************************

    def invert_mask(self, name):

        """
        This function makes a new mask which is the inverse (logical NOT) of the total currently selected mask
        :param name:
        :return:
        """

        # Get the total selected mask
        currentmask = self.combine_masks(return_mask=True)

        # Calculate the inverse of the this total mask
        newmask = np.logical_not(currentmask)

        # Add the new, inverted mask
        self._add_mask(newmask, name)

    # *****************************************************************

    def create_mask(self, return_mask=False):

        """
        This function creates a mask from the currently selected region(s)
        :return:
        """

        # TODO: use combine_regions and regions.create_mask() !!

        # Initialize an boolean array for the total mask
        total_mask = np.zeros_like(self.frames.primary, dtype=bool)

        name = ""

        # For each active region
        for region_name in self.regions.get_selected():

            # Create the mask
            total_mask += regions.create_mask(self.regions[region_name].region, self.header, self.frames.primary.xsize, self.frames.primary.ysize)
            name += region_name + "_"

        # Remove the trailing underscore
        name = name.rstrip("_")

        # Return the mask or add it to this image
        if return_mask: return total_mask
        else: self._add_mask(total_mask, name)

    # *****************************************************************

    def get_galactic_extinction(self, galaxy_name):

        """
        This function ...
        """

        return catalogs.fetch_galactic_extinction(galaxy_name, self.filter)

    # *****************************************************************

    def expand_regions(self, factor, combine=False):

        """
        This function expands the currently selected region(s)
        :param factor:
        :param combine:
        :return:
        """

        if combine:

            # Create a combined region
            region = self.combine_regions(allow_none=False)

            # Expand this region
            expanded_region = regions.expand(region, factor)

            # Add this region to the list of regions
            self._add_region(expanded_region, "expanded")

        else:

            # Loop over all active regions
            for region_name in self.regions.get_selected(allow_none=False):

                # Inform the user
                log.info("Expanding the " + region_name + " region by a factor of " + str(factor))

                # Create expanded region
                expanded_region = regions.expand(self.regions[region_name].region, factor)

                # Add the expanded region to the list of regions
                self._add_region(expanded_region, region_name + "_expanded")

    # *****************************************************************

    def rename_region(self, name):

        """
        This function renames a region
        :param name:
        :return:
        """

        # Get the name of the currently selected region
        region_name = self.regions.get_selected(require_single=True)

        # Remove the region of the dictionary of regions and re-add it under a different key
        self.regions[name] = self.regions.pop(region_name)

    # *****************************************************************

    def rename_frame(self, name):

        """
        This function renames a frame
        :param name:
        :return:
        """

        # Get the name of the currently selected frame
        frame_name = self.frames.get_selected(require_single=True)

        # Remove the frame from the dictionary of frames and re-add it under a different key
        self.frames[name] = self.frames.pop(frame_name)

    # *****************************************************************

    def rename_mask(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Get the name of the currently selected mask
        mask_name = self.masks.get_selected(require_single=True)

        # Remove the mask from the dictionary of masks and re-add it under a different key
        self.masks[name] = self.masks.pop(mask_name)

    # *****************************************************************

    def model_stars(self, model_name='Gaussian', background_inner_sigmas=5.0, background_outer_sigmas=10.0, fit_sigmas=5.0,
                    upsample_factor=1.0, interpolate_background=True, sigma_clip_background=True, plot=False):

        """
        This function ...
        :param model:
        :param plot:
        :param background_inner_sigmas:
        :param background_outer_sigmas:
        :param fit_sigmas:
        :param resample_factor:
        :param interpolate_background:
        :param sigma_clip_background:
        :return:
        """

        # TODO: should not only work with regions that contain nothing but ellipses

        # Create a region for stars that were succesfully modeled and a region for objects that could not be fitted to a star model
        modeled = pyregion.ShapeList([])
        unmodeled = pyregion.ShapeList([])

        # Get the name of the active frame
        frame_name = self.frames.get_selected(require_single=True)

        # Inform the user
        log.info("Modeling stars in the " + frame_name + " frame enclosed by any of the currently selected regions")

        # Create a new frame to contain the modeled stars
        stars_frame = np.zeros_like(self.frames[frame_name])

        # Combine all the active regions
        total_region = self.combine_regions(allow_none=False)

        # Create the background mask
        annuli_mask = masks.annuli_around(total_region, background_inner_sigmas, background_outer_sigmas, self.header, self.xsize, self.ysize)

        # Create a mask that covers pixels too far away from the center of the star (for fitting the model)
        fit_mask = masks.masked_outside(total_region, self.header, self.xsize, self.ysize, expand_factor=fit_sigmas)

        # For each shape (star)
        for shape in total_region:

            # Try to make an analytical model for the star enclosed by this shape
            success, shape, model, extents = analysis.make_star_model(shape, self.frames[frame_name],
                                                                      annuli_mask, fit_mask, background_outer_sigmas,
                                                                      fit_sigmas, model_name,
                                                                      upsample_factor=upsample_factor,
                                                                      interpolate_background=interpolate_background,
                                                                      sigma_clip_background=sigma_clip_background,
                                                                      plot=plot)

            if success:

                # Add the 1-sigma contour of the analytical model to the modeled stars region
                modeled.append(shape)

                # Add the model to the stars frame
                stars_frame[extents[2]:extents[3], extents[0]:extents[1]] += model

            else: unmodeled.append(shape)

        # Add the modelled stars frame to the list of frames
        self.add_frame(stars_frame, "stars")

        # Add the successfully modeled stars and the unmodeled stars to the corresponding regions
        self._add_region(modeled, "modeled_stars")
        self._add_region(unmodeled, "unmodeled_stars")

    # *****************************************************************

    def find_sky(self):

        """
        This function ...
        :return:
        """

        # Get the name of the currently selected frame
        frame_name = self.frames.get_selected(require_single=True)

        # The length of the major axis of the ellipse
        major = 3.0 * self.orientation.majoraxis * 2.5

        # The width and heigth of the ellips
        width = major
        height = major * (1 - self.orientation.eps)

        # Create a string identifying this ellipse
        region_string = "image;ellipse(" + str(self.orientation.ypeak) + "," + str(self.orientation.xpeak) + "," + str(width) + "," + str(height) + "," + str(self.orientation.theta) + ")"

        # Create a region for the outer ellipse of the annulus
        region = pyregion.parse(region_string)

        # Add the annulus region
        self._add_region(region, "annulus")

        # Create the annulus mask
        annulusmask = np.logical_not(self.regions["annulus"].region.get_mask(header=self.header, shape=(self.ysize,self.xsize)))

        # Get a combination of the currently selected masks
        current_mask = self.combine_masks(return_mask=True)

        # Combine the currently selected mask, the galaxy mask and the annulus mask
        sky_mask = (current_mask + self.masks.galaxy.data + annulusmask).astype(bool)

        # Make a mask of > 3 sigma regions
        new_mask = statistics.sigma_clip_mask(self.frames[frame_name], sigma=3.0, mask=sky_mask)

        # Add the mask
        self._add_mask(new_mask, "sky")

        # Make a masked frame, the (sigma-clipped) sky
        skyframe = np.copy(self.frames.primary)

        # Set the sky frame to zero in the pixels masked by the new 'sky' mask
        skyframe[self.masks.sky.data] = 0.0

        # Add this frame to the set of frames
        self.add_frame(skyframe, "sky")

    # *****************************************************************

    def fit_polynomial(self, plot=False, degree=3, sigma_clipping=True):

        """
        This function fits a polynomial function to each of the currently active frames
        :param plot:
        :param upsample_factor:
        :return:
        """

        # Get the currently active mask
        total_mask = self.combine_masks(return_mask=True)

        # For each currently active frame
        for frame_name in self.frames.get_selected(allow_none=False):

            # Inform the user
            log.info("Fitting a polynomial function to the " + frame_name + " frame")

            if sigma_clipping: new_mask = statistics.sigma_clip_mask(self.frames[frame_name], mask=total_mask)
            else: new_mask = total_mask

            # Fit the model
            polynomial = fitting.fit_polynomial(self.frames[frame_name], mask=new_mask, degree=degree)

            # Plot the difference between the data and the model, if requested
            if plot: plotting.plot_difference_model(self.frames[frame_name], polynomial)

            # Evaluate the model
            evaluated = fitting.evaluate_model(polynomial, 0, self.frames[frame_name].xsize, 0, self.frames[frame_name].ysize)

            # Add the evaluated model as a new frame
            description = "A polynomial fit to the " + frame_name + " primary frame"
            self.add_frame(Frame(evaluated, self.frames[frame_name].coordinates, self.pixelscale, description), frame_name+"_polynomial")

    # *****************************************************************

    def subtract(self):

        """
        This function subtracts the currently active frame(s) from the primary image, in the pixels not covered by
        any of the currently active masks (the currently active masks 'protect' the primary image from this subtraction
        :return:
        """

        # Get the currently active mask
        total_mask = self.combine_masks(return_mask=True)

        # Determine the negative of the total mask
        negativetotalmask = np.logical_not(total_mask)

        # For each active frame
        for frame_name in self.frames.get_selected():

            # Inform the user
            log.info("Subtracting " + frame_name + " frame from the primary image frame")

            # Subtract the data in this frame from the primary image, in the pixels that the mask does not cover
            self.frames.primary -= self.frames[frame_name]*negativetotalmask

    # *****************************************************************

    def _load_image(self, filename):

        """
        This function ...
        :param filename:
        :return:
        """

        # Show which image we are importing
        log.info("Reading in file: " + filename)

        # Open the HDU list for the FITS file
        hdulist = pyfits.open(filename)

        # Get the primary HDU
        hdu = hdulist[0]

        # Get the image header
        header = hdu.header

        # Obtain the coordinate system
        coordinates = wcs.WCS(header)

        # Load the frames
        self.pixelscale = headers.get_pixelscale(header)

        # Obtain the filter for this image
        self.filter = headers.get_filter(self.name, header)

        # Obtain the units of this image
        self.unit = headers.get_units(header)

        # Check whether the image is sky-subtracted
        self.sky_subtracted = headers.is_sky_subtracted(header)

        self.wavelength = None
        if self.filter is not None: self.wavelength = self.filter.pivotwavelength() * u.Unit("micron")
        elif "ha" in self.name.lower(): self.wavelength = 0.65628 * u.Unit("micron")
        else: log.warning("Could not determine the wavelength for this image")

        # Check whether multiple planes are present in the FITS image
        nframes = headers.get_number_of_frames(header)
        if nframes > 1:

            # For each frame
            for i in range(nframes):

                # Get the name of this frame, but the first frame always gets the name 'primary'
                description = headers.get_frame_description(header, i) if i else "the primary signal map"    
                name = headers.get_frame_name(description) if i else "primary"

                # Add this frame to the frames dictionary
                self.add_frame(Frame(hdu.data[i], coordinates, self.pixelscale, description), name)

        else:

            # Sometimes, the 2D frame is embedded in a 3D array with shape (1, xsize, ysize)
            if len(hdu.data.shape) == 3: hdu.data = hdu.data[0]

            # Add the primary image frame
            self.add_frame(Frame(hdu.data, coordinates, self.pixelscale, "the primary signal map"), "primary")

        # Set the basic header for this image
        self.header = header.copy(strip=True)
        self.header["NAXIS"] = 2
        self.header["NAXIS1"] = self.frames.primary.xsize
        self.header["NAXIS2"] = self.frames.primary.ysize

        # Select the primary image frame
        self.frames.primary.select()

        # Close the FITS file
        hdulist.close()

    # *****************************************************************

    def add_frame(self, frame, name):

        """
        This function ...
        :param data:
        :param coordinates:
        :param name:
        :param description:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of image frames")

        # Add the layer to the layers dictionary
        self.frames[name] = frame

    # *****************************************************************

    def _add_region(self, region, name):

        """
        This function ...
        :param region:
        :param name:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of regions")

        # Add the region to the regions dictionary
        self.regions[name] = Region(region)

    # *****************************************************************

    def _add_mask(self, data, name):

        """
        This function ...
        :param data:
        :param name:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of masks")

        # Add the mask to the masks dictionary
        self.masks[name] = Mask(data)

    # *****************************************************************

    def add_mask(self, mask, name, overwrite=False):

        """
        This function ...
        :param mask:
        :param name:
        :return:
        """

        # Inform the user
        log.info("Adding '" + name + "' to the set of masks")

        # Check whether a mask with this name already exists
        if name in self.masks and not overwrite: raise RuntimeError("A mask with this name already exists")

        # Add the mask to the set of masks
        self.masks[name] = mask

# *****************************************************************