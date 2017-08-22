#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.component.galaxy Contains the GalaxyModelingComponent class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import gc
from abc import ABCMeta

# Import the relevant PTS classes and modules
from ...core.tools import filesystem as fs
from ...core.data.sed import ObservedSED
from ...magic.core.dataset import DataSet
from ...magic.core.frame import Frame
from ...magic.region.list import SkyRegionList
from ..basics.models import load_3d_model, load_2d_model
from ..basics.properties import GalaxyProperties
from ...core.basics.log import log
from ...magic.prepare.statistics import PreparationStatistics
from .component import ModelingComponent
from ...core.tools import types
from ...core.filter.filter import parse_filter
from ...core.remote.remote import Remote
from ..core.steps import cached_directory_path_for_single_command
from ..core.environment import GalaxyModelingEnvironment
from ...magic.core.remote import get_filter_name
from ...magic.tools import headers
from pts.core.tools.utils import lazyproperty

# -----------------------------------------------------------------

def needs_poisson_errors(fltr):

    """
    This function ...
    :param fltr:
    :return:
    """

    if types.is_string_type(fltr): fltr = parse_filter(fltr)
    filter_string = str(fltr)
    return "GALEX" in filter_string or "SDSS" in filter_string

# -----------------------------------------------------------------

class GalaxyModelingComponent(ModelingComponent):
    
    """
    This class...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(GalaxyModelingComponent, self).__init__(*args, **kwargs)

        # The path to the components/models directory
        self.components_models_path = None

        # The path to the components/projections directory
        self.components_projections_path = None

        # The paths to the bulge and disk models
        self.bulge_model_path = None
        self.disk_model_path = None

        # The path to the components/images directory
        self.components_images_path = None

        # The paths to the final bulge, disk and model images
        self.bulge2d_image_path = None
        self.bulge_image_path = None
        self.disk_image_path = None
        self.model_image_path = None

        # The path to the DustPedia observed SED for the galaxy
        self.dustpedia_sed_path = None

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(GalaxyModelingComponent, self).setup(**kwargs)

        # -- Attributes --

        # Set the path to the components/models directory
        self.components_models_path = fs.create_directory_in(self.components_path, "models")

        # Set the path to the components/projections directory
        self.components_projections_path = fs.create_directory_in(self.components_path, "projections")

        # Set the paths to the bulge and disk models
        self.bulge_model_path = fs.join(self.components_models_path, "bulge.mod")
        self.disk_model_path = fs.join(self.components_models_path, "disk.mod")

        # Set the path to the components/images directory
        self.components_images_path = fs.create_directory_in(self.components_path, "images")

        # Set the path to the final bulge, disk and model images
        self.bulge2d_image_path = fs.join(self.components_images_path, "bulge2d.fits")
        self.bulge_image_path = fs.join(self.components_images_path, "bulge.fits")
        self.disk_image_path = fs.join(self.components_images_path, "disk.fits")
        self.model_image_path = fs.join(self.components_images_path, "model.fits")

        # The DustPedia SED path
        self.dustpedia_sed_path = fs.join(self.data_seds_path, "DustPedia.dat")

    # -----------------------------------------------------------------

    @property
    def galaxy_name(self):

        """
        THis function ...
        :return:
        """

        return self.environment.galaxy_name

    # -----------------------------------------------------------------

    @property
    def data_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.data_path

    # -----------------------------------------------------------------

    @property
    def observed_sed_dustpedia_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.observed_sed_dustpedia_path

    # -----------------------------------------------------------------

    @property
    def galaxy_properties_path(self):

        """
        THis function ...
        :return:
        """

        return self.environment.galaxy_properties_path

    # -----------------------------------------------------------------

    @property
    def galaxy_info_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_info_path

    # -----------------------------------------------------------------

    @property
    def data_seds_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.data_seds_path

    # -----------------------------------------------------------------

    @property
    def data_images_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.data_images_path

    # -----------------------------------------------------------------

    @property
    def prep_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.prep_path

    # -----------------------------------------------------------------

    @property
    def inspect_path(self):

        """
        This function ...
        :return: 
        """

        return self.environment.inspect_path

    # -----------------------------------------------------------------

    @property
    def truncation_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.truncation_path

    # -----------------------------------------------------------------

    @property
    def phot_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.phot_path

    # -----------------------------------------------------------------

    @property
    def maps_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_path

    # -----------------------------------------------------------------

    @property
    def maps_raw_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_raw_path

    # -----------------------------------------------------------------

    @property
    def maps_components_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_components_path

    # -----------------------------------------------------------------

    @property
    def components_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.components_path

    # -----------------------------------------------------------------

    # @property
    # def deprojection_path(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     return self.environment.deprojection_path

    # -----------------------------------------------------------------

    @property
    def playground_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.playground_path

    # -----------------------------------------------------------------

    @lazyproperty
    def ngc_name(self):

        """
        This function ...
        :return:
        """

        # Get the NGC name from the configuration
        return self.modeling_configuration.ngc_name

    # -----------------------------------------------------------------

    @lazyproperty
    def ngc_name_nospaces(self):

        """
        This function ...
        :return:
        """

        return self.ngc_name.replace(" ", "")

    # -----------------------------------------------------------------

    @lazyproperty
    def hyperleda_name(self):

        """
        This function ...
        :return:
        """

        # Get the HYPERLEDA name from the configuration
        return self.modeling_configuration.hyperleda_name

    # -----------------------------------------------------------------

    @property
    def initial_dataset(self):

        """
        This function ...
        :return:
        """

        return self.environment.initial_dataset

    # -----------------------------------------------------------------

    @property
    def preparation_names(self):

        """
        This function ...
        :return:
        """

        return self.environment.preparation_names

    # -----------------------------------------------------------------

    @property
    def prep_names(self):

        """
        This function ...
        :return:
        """

        return self.preparation_names

    # -----------------------------------------------------------------

    @property
    def preparation_paths(self):

        """
        This function ...
        :return:
        """

        return self.environment.preparation_paths

    # -----------------------------------------------------------------

    @property
    def dataset(self):

        """
        This function ...
        :return:
        """

        return self.environment.dataset

    # -----------------------------------------------------------------

    @property
    def frame_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.frame_list

    # -----------------------------------------------------------------

    @property
    def named_frame_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.named_frame_list

    # -----------------------------------------------------------------

    @property
    def errormap_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.errormap_list

    # -----------------------------------------------------------------

    @property
    def named_errormap_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.named_errormap_list

    # -----------------------------------------------------------------

    @property
    def frame_path_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.frame_path_list

    # -----------------------------------------------------------------

    @property
    def named_frame_path_list(self):

        """
        This function ...
        :return:
        """

        return self.environment.named_frame_path_list

    # -----------------------------------------------------------------

    @lazyproperty
    def disk_frame(self):

        """
        This function ...
        :return:
        """

        # Check whether the file is present
        if not fs.is_file(self.disk_image_path): raise IOError("The disk image is not present. Run the 'decompose' step to create it")

        # Load the frame
        frame = Frame.from_file(self.disk_image_path)

        # Return the frame
        return frame

    # -----------------------------------------------------------------

    @lazyproperty
    def bulge_frame(self):

        """
        This function ...
        :return:
        """

        # Check whether the file is present
        if not fs.is_file(self.bulge_image_path): raise IOError("The bulge image is not present. Run the 'decompose' step to create it")

        # Load the frame
        frame = Frame.from_file(self.bulge_image_path)

        # Return the frame
        return frame

    # -----------------------------------------------------------------

    @property
    def disk_region_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.disk_region_path

    # -----------------------------------------------------------------

    @property
    def disk_ellipse(self):

        """
        This function ...
        :return:
        """

        return self.environment.disk_ellipse

    # -----------------------------------------------------------------

    @property
    def disk_position_angle(self):

        """
        This function ...
        :return:
        """

        return self.environment.disk_position_angle

    # -----------------------------------------------------------------

    @property
    def significance_levels_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.significance_levels_path

    # -----------------------------------------------------------------

    @property
    def truncation_ellipse_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.truncation_ellipse_path

    # -----------------------------------------------------------------

    @property
    def truncation_ellipse(self):

        """
        This function ...
        :return:
        """

        return self.environment.truncation_ellipse

    # -----------------------------------------------------------------

    @property
    def physical_truncation_ellipse(self):

        """
        This fucntion ...
        :return: 
        """

        return self.environment.physical_truncation_ellipse

    # -----------------------------------------------------------------

    @property
    def truncation_area(self):

        """
        This function ...
        :return:
        """

        return self.environment.truncation_area

    # -----------------------------------------------------------------

    @property
    def truncation_box(self):

        """
        This function ...
        :return:
        """

        return self.environment.truncation_box

    # -----------------------------------------------------------------

    def highest_resolution_wcs(self):

        """
        This function ...
        :return:
        """

        return self.dataset.min_pixelscale_wcs

    # -----------------------------------------------------------------

    def lowest_resolution_wcs(self):

        """
        This function ...
        :return:
        """

        return self.dataset.max_pixelscale_wcs

    # -----------------------------------------------------------------

    def wcs_for_filter(self, fltr):

        """
        This function ...
        :param fltr:
        :return:
        """

        return self.dataset.get_wcs_for_filter(fltr)

    # -----------------------------------------------------------------

    def sky_annulus_region(self, image_name):

        """
        This function ...
        :param image_name:
        :return:
        """

        path = fs.join(self.prep_path, image_name, "sky", "annulus.reg")
        return SkyRegionList.from_file(path)

    # -----------------------------------------------------------------

    def sky_annulus_outer(self, image_name):

        """
        This function ...
        :return:
        """

        # Get the sky annulus region for this image
        region = self.sky_annulus_region(image_name)

        # Return the ellipse with the largest radius
        #return max(region, key=lambda ellipse: ellipse.radius)

        return region[0].base

    # -----------------------------------------------------------------

    def sky_annulus_inner(self, image_name):

        """
        This function ...
        :return:
        """

        # Get the sky annulus region for this image
        region = self.sky_annulus_region(image_name)

        # Return the ellipse with the smallest radius
        #return min(region, key=lambda ellipse: ellipse.radius)

        return region[0].exclude

    # -----------------------------------------------------------------

    #def truncation_mask_path(self, image_name):

        #"""
        #This function ...
        #:param image_name:
        #:return:
        #"""

        # Check whether mask is present with image name, or else use the reference mask file
        #path = fs.join(self.truncation_masks_path, image_name + ".fits")
        #if not fs.is_file(path): path = self.reference_mask_path

        # Return None if truncation has not been performed yet
        #if not fs.is_file(path): return None
        #else: return path

    # -----------------------------------------------------------------

    #def truncation_mask(self, image_name):

        #"""
        #This function ...
        #:param image_name:
        #:return:
        #"""

        # Get the path to the truncation mask
        #path = self.truncation_mask_path(image_name)

        # Return None if no mask is present
        #if path is None: return None

        # Else, return the mask
        #return Mask.from_file(path)

    # -----------------------------------------------------------------

    @property
    def galaxy_properties(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_properties

    # -----------------------------------------------------------------

    @property
    def galaxy_info(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_info

    # -----------------------------------------------------------------

    @property
    def galaxy_ellipse(self): # from properties

        """
        This function ...
        :return: 
        """

        return self.environment.galaxy_ellipse

    # -----------------------------------------------------------------

    @property
    def galaxy_distance(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_distance

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_center(self):

        """
        This function ...
        :return: 
        """

        return self.environment.galaxy_center

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_inclination(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_inclination

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_position_angle(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_position_angle

    # -----------------------------------------------------------------

    @lazyproperty
    def galaxy_redshift(self):

        """
        This function ...
        :return:
        """

        return self.environment.galaxy_redshift

    # -----------------------------------------------------------------

    @lazyproperty
    def bulge_model(self):

        """
        This function returns the bulge model
        :return:
        """

        # Check whether the file is present
        if not fs.is_file(self.bulge_model_path): raise IOError("The bulge model file is not present. Run the 'decompose' step to create it")

        # Load the model
        return load_3d_model(self.bulge_model_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def disk_model(self):

        """
        This function returns the disk model
        :return:
        """

        # Check whether the file is present
        if not fs.is_file(self.disk_model_path): raise IOError("The disk model file is not present. Run the 'decompose' step to create it")

        # Load the model
        return load_3d_model(self.disk_model_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def bulge2d_model(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.components_path, "2D", "S4G", "bulge.mod")
        return load_2d_model(path)

    # -----------------------------------------------------------------

    @lazyproperty
    def disk2d_model(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.components_path, "2D", "S4G", "disk.mod")
        return load_2d_model(path)

    # -----------------------------------------------------------------

    #@property
    #def input_map_paths(self):

        #"""
        #This function returns the paths to the input maps of stellar and dust distribution
        #:return:
        #"""

        # Check whether the FITS files exist
        #if not fs.is_file(self.old_stellar_map_path): raise RuntimeError("The map of old stars is not present. Run make_old_map first.")
        #if not fs.is_file(self.young_stellar_map_path): raise RuntimeError("The map of young stars is not present. Run make_young_map first.")
        #if not fs.is_file(self.ionizing_stellar_map_path): raise RuntimeError("The map of ionizing stars is not present. Run make_ionizing_map first.")
        #if not fs.is_file(self.dust_map_path): raise RuntimeError("The dust map is not present. Run make_dust_map first.")

        # Return the paths to the maps of stars and dust
        #return [self.old_stellar_map_path, self.young_stellar_map_path, self.ionizing_stellar_map_path, self.dust_map_path]

    # -----------------------------------------------------------------

    #@property
    #def old_stellar_map_filename(self):

        #"""
        #This function ...
        #:return:
        #"""

        #return fs.name(self.old_stellar_map_path)

    # -----------------------------------------------------------------

    #@property
    #def young_stellar_map_filename(self):

        #"""
        #This function ...
        #:return:
        #"""

        #return fs.name(self.young_stellar_map_path)

    # -----------------------------------------------------------------

    #@property
    #def ionizing_stellar_map_filename(self):

        #"""
        #This function ...
        #:return:
        #"""

        #return fs.name(self.ionizing_stellar_map_path)

    # -----------------------------------------------------------------

    #@property
    #def dust_map_filename(self):

        #"""
        #This function ...
        #:return:
        #"""

        #return fs.name(self.dust_map_path)

    # -----------------------------------------------------------------

    #@lazyproperty
    #def old_stars_map(self):

        #"""
        #This function ...
        #:return:
        #"""

        # Check whether the file is present
        #if not fs.is_file(self.old_stellar_map_path): raise IOError("The map of old stars is not present. Run 'make_old_map' to create it")

        # Open and return the frame of the old stellar distribution
        #return Frame.from_file(self.old_stellar_map_path)

    # -----------------------------------------------------------------

    #@lazyproperty
    #def young_stars_map(self):

        #""""
        #This function ...
        #:return:
        #"""

        # Check whether the file is present
        #if not fs.is_file(self.young_stellar_map_path): raise IOError("The map of young stars is not present. Run 'make_young_map' to create it")

        # Open and return the frame of the young stellar distribution
        #return Frame.from_file(self.young_stellar_map_path)

    # -----------------------------------------------------------------

    #@lazyproperty
    #def ionizing_stars_map(self):

        #"""
        #This function ...
        #:return:
        #"""

        # Check whether the file is present
        #if not fs.is_file(self.ionizing_stellar_map_path): raise IOError("The map of ionizing stars is not present. Run 'make_ionizing_map' to create it")

        # Open and return the frame of the ionizing stellar distribution
        #return Frame.from_file(self.ionizing_stellar_map_path)

    # -----------------------------------------------------------------

    #@lazyproperty
    #def dust_map(self):

        #"""
        #This function ...
        #:return:
        #"""

        # Check whether the file is present
        #if not fs.is_file(self.dust_map_path): raise IOError("The dust map is not present. Run 'make_dust_map' to create it")

        # Open and return the frame of the dust distribution
        #return Frame.from_file(self.dust_map_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_seds(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the reference SEDs ...")

        # Loop over the SEDs in the data/SEDs directory
        for path, name in fs.files_in_path(self.data_seds_path, extension="dat", returns=["path", "name"], not_contains="Lines"):

            # Open the observed SED
            sed = ObservedSED.from_file(path)

            # Add the SED to the dictionary
            self.reference_seds[name] = sed

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_sed_labels(self):

        """
        This function ...
        :return:
        """

        return self.reference_seds.keys()

    # -----------------------------------------------------------------

    @lazyproperty
    def dustpedia_sed(self):

        """
        This function ...
        :return:
        """

        # Open the SED
        sed = ObservedSED.from_file(self.dustpedia_sed_path)

        # Return the SED
        return sed

    # -----------------------------------------------------------------

    @property
    def has_cache_host(self):

        """
        This function ...
        :return:
        """

        return self.cache_host_id is not None

    # -----------------------------------------------------------------

    @property
    def cache_host_id(self):

        """
        This function ...
        :return:
        """

        return self.environment.cache_host_id

    # -----------------------------------------------------------------

    @property
    def cache_host(self):

        """
        This function ...
        :return:
        """

        return self.environment.cache_host

    # -----------------------------------------------------------------

    @property
    def cache_remote(self):

        """
        This function ...
        :return:
        """

        return self.environment.cache_remote

    # -----------------------------------------------------------------

    def get_data_image_paths(self):

        """
        This function ...
        :return:
        """

        return get_data_image_paths(self.config.path)

    # -----------------------------------------------------------------

    def get_data_image_paths_with_cached(self, lazy=False):

        """
        This function ...
        :param lazy:
        :return:
        """

        return get_data_image_paths_with_cached(self.config.path, self.cache_host_id, lazy=lazy)

    # -----------------------------------------------------------------

    def get_data_image_and_error_paths(self):

        """
        This function ...
        :return: 
        """

        return get_data_image_and_error_paths(self.config.path)

    # -----------------------------------------------------------------

    def get_data_image_and_error_paths_with_cached(self, lazy=False):

        """
        This function ...
        :param lazy:
        :return:
        """

        return get_data_image_and_error_paths_with_cached(self.config.path, self.cache_host_id, lazy=lazy)

    # -----------------------------------------------------------------

    @property
    def analysis_context(self):

        """
        This function ...
        :return:
        """

        return self.environment.analysis_context

    # -----------------------------------------------------------------

    @property
    def analysis_runs(self):

        """
        This function ...
        :return:
        """

        return self.environment.analysis_runs

# -----------------------------------------------------------------

def load_preparation_statistics(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    # Determine path
    prep_path = fs.join(modeling_path, "prep")
    path = fs.join(prep_path, "statistics.dat")

    # Load and return the statistics
    if fs.is_file(path): return PreparationStatistics.from_file(path)
    else: return None

# -----------------------------------------------------------------

def get_observed_sed_file_path(modeling_path):

    """
    This function ...
    :return:
    """

    return fs.join(modeling_path, "phot", "fluxes.dat")

# -----------------------------------------------------------------

def get_observed_sed(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return ObservedSED.from_file(get_observed_sed_file_path(modeling_path))

# -----------------------------------------------------------------

def get_galaxy_properties_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    data_path = fs.join(modeling_path, "data")
    return fs.join(data_path, "properties.dat")

# -----------------------------------------------------------------

def get_galaxy_properties(modeling_path):

    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    # get path
    path = get_galaxy_properties_path(modeling_path)

    # Check whether the file is present
    if not fs.is_file(path): raise IOError("The galaxy properties file is not present. Perform 'fetch_properties' to create this file'")

    # Load the properties
    properties = GalaxyProperties.from_file(path)

    # Return the property map
    return properties

# -----------------------------------------------------------------

def get_data_seds_path(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    data_path = fs.join(modeling_path, "data")
    return fs.join(data_path, "SEDs")

# -----------------------------------------------------------------

def get_data_images_path(modeling_path):

    """
    This function ....
    :param modeling_path:
    :return:
    """

    data_path = fs.join(modeling_path, "data")
    return fs.join(data_path, "images")

# -----------------------------------------------------------------

def get_reference_seds(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    seds = dict()

    # Loop over the SEDs in the data/SEDs directory
    for path, name in fs.files_in_path(get_data_seds_path(modeling_path), extension="dat", returns=["path", "name"], not_contains="Lines"):

        # Open the observed SED
        sed = ObservedSED.from_file(path)

        # Add the SED to the dictionary
        seds[name] = sed

    # Return the SEDs
    return seds

# -----------------------------------------------------------------

def get_dustpedia_sed_path(modeling_path):

    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    return fs.join(get_data_seds_path(modeling_path), "DustPedia.dat")

# -----------------------------------------------------------------

def get_dustpedia_sed(modeling_path):

    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    # Open the SED and return it
    return ObservedSED.from_file(get_dustpedia_sed_path(modeling_path))

# -----------------------------------------------------------------

def load_image_frame(path):

    """
    This function ...
    :param path: 
    :return: 
    """

    name = fs.strip_extension(fs.name(path))

    frame = None
    # Try opening
    try:
        # Open the image frame
        frame = Frame.from_file(path)
    except IOError:
        log.warning("The file '" + path + "' is probably damaged. Removing the file and exitting. Run the command again.")
        fs.remove_file(path)
        exit()

    # Determine the preparation name
    #if frame.filter is not None: prep_name = str(frame.filter)
    #else: prep_name = image_name
    if frame.filter is None:

        #log.warning("Did not recognize the filter of the '" + image_name + "' image: skipping")
        #continue
        raise RuntimeError("Did not recognize the filter for the '" + name + "' image")

    # Return the frame
    return frame

# -----------------------------------------------------------------

def get_disk_position_angle(modeling_path):

    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    # Determine the path to the regions file
    components_path = fs.join(modeling_path, "components")
    disk_region_path = fs.join(components_path, "disk.reg")

    # Open the region
    region = SkyRegionList.from_file(disk_region_path)

    # Return the first and only shape
    disk_ellipse = region[0]

    # Return the orientation angle
    return disk_ellipse.angle

# -----------------------------------------------------------------

def get_initial_dataset_path(modeling_path):
    
    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    return fs.join(modeling_path, "prep", "initial_dataset.dat")

# -----------------------------------------------------------------

def get_initial_dataset(modeling_path, check=True):

    """
    This function ...
    :param modeling_path:
    :param check:
    :return:
    """

    return DataSet.from_file(get_initial_dataset_path(modeling_path), check=check)

# -----------------------------------------------------------------

def get_prepared_dataset_path(modeling_path):
    
    """
    This function ...
    :param modeling_path: 
    :return: 
    """

    return fs.join(modeling_path, "prep", "dataset.dat")

# -----------------------------------------------------------------

def get_prepared_dataset(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    return DataSet.from_file(get_prepared_dataset_path(modeling_path))

# -----------------------------------------------------------------

def get_data_image_paths(modeling_path):

    """
    This function ...
    :param modeling_path:
    :return:
    """

    data_images_path = get_data_images_path(modeling_path)

    paths = dict()

    # Loop over the images
    for image_path, image_name in fs.files_in_path(data_images_path, extension="fits", not_contains="poisson",
                                                   returns=["path", "name"], recursive=True, recursion_level=1):

        # Load the primary image frame
        frame = load_image_frame(image_path)

        # Determine name
        name = frame.filter_name

        # Add the image path
        paths[name] = image_path

        # Free memory
        gc.collect()

    # Return the paths
    return paths

# -----------------------------------------------------------------

def get_data_image_paths_with_cached(modeling_path, host_id, lazy=False):

    """
    This function ...
    :param modeling_path:
    :param host_id:
    :param lazy:
    :return:
    """

    paths = get_data_image_paths(modeling_path)
    paths.update(**get_cached_data_image_paths(modeling_path, host_id, lazy=lazy))
    return paths

# -----------------------------------------------------------------

def get_cached_data_image_paths(modeling_path, host_id, lazy=False):

    """
    This function ...
    :param modeling_path:
    :param host_id:
    :param lazy:
    :return:
    """

    # Create the remote and start (detached) python session
    remote = Remote(host_id=host_id)
    if not lazy: session = remote.start_python_session(output_path=remote.pts_temp_path)
    else: session = None

    # Load the environment
    environment = GalaxyModelingEnvironment(modeling_path)

    paths = dict()

    command_name = "initialize_preparation"

    # Get the remote path
    remote_data_path = cached_directory_path_for_single_command(environment, command_name, remote)

    # Loop over the images
    for image_path, image_name in remote.files_in_path(remote_data_path, extension="fits", not_contains="poisson",
                                                   returns=["path", "name"], recursive=True): #, recursion_level=1):

        # Get filter name
        if lazy:
            #name = str(parse_filter(image_name))
            fltr = headers.get_filter(image_name)
            if fltr is None:
                #raise RuntimeError("Could not determine the filter for the '" + image_name + "' image")
                log.warning("Could not determine the filter for the '" + image_name + "' image: skipping ...")
                continue
            name = str(fltr)
        else: name = get_filter_name(image_path, session)

        if name is None: raise RuntimeError("Could not determine the filter name for the '" + image_name + "' image")

        # Add the image path
        paths[name] = image_path

    # Return the paths
    return paths

# -----------------------------------------------------------------

def get_data_image_and_error_paths(modeling_path):

    """
    This function ...
    :return: 
    """

    data_images_path = get_data_images_path(modeling_path)

    paths = dict()
    error_paths = dict()

    # Loop over the images
    for image_path, image_name in fs.files_in_path(data_images_path, extension="fits", not_contains="poisson",
                                                   returns=["path", "name"], recursive=True, recursion_level=1):

        # Determine directory path
        path = fs.directory_of(image_path)

        # Load the primary image frame
        frame = load_image_frame(image_path)

        # Determine name
        name = frame.filter_name

        # Add the image path
        paths[name] = image_path

        # Determine path to poisson error map
        poisson_path = fs.join(path, image_name + "_poisson.fits")

        # Set the path to the poisson error map
        if fs.is_file(poisson_path):

            # Debugging
            log.debug("Poisson error frame found for '" + name + "' image ...")
            error_paths[name] = poisson_path

        # Poisson frame not present
        elif needs_poisson_errors(frame.filter): raise RuntimeError("Poisson error frame not found for the " + name + " image. Run the appropriate command to create the mosaics and poisson frames.")

        # Free memory
        gc.collect()

    # Return the paths and error paths
    return paths, error_paths

# -----------------------------------------------------------------

def get_data_image_and_error_paths_with_cached(modeling_path, host_id, lazy=False):

    """
    This function ...
    :param modeling_path:
    :param host_id:
    :param lazy:
    :return:
    """

    paths, error_paths = get_data_image_and_error_paths(modeling_path)
    cached_paths, cached_error_paths = get_cached_data_image_and_error_paths(modeling_path, host_id, lazy=lazy)
    paths.update(**cached_paths)
    error_paths.update(**cached_error_paths)
    return paths, error_paths

# -----------------------------------------------------------------

def get_cached_data_image_and_error_paths(modeling_path, host_id, lazy=False):

    """
    This function ...
    :param modeling_path:
    :param host_id:
    :param lazy:
    :return:
    """

    # Create the remote and start (detached) python session
    if isinstance(host_id, Remote): remote = host_id
    else: remote = Remote(host_id=host_id)
    if not lazy: session = remote.start_python_session(output_path=remote.pts_temp_path)
    else: session = None

    # Load the environment
    environment = GalaxyModelingEnvironment(modeling_path)

    paths = dict()
    error_paths = dict()

    command_name = "initialize_preparation"

    # Get the remote path
    remote_data_path = cached_directory_path_for_single_command(environment, command_name, remote)

    # Loop over the images
    for image_path, image_name in remote.files_in_path(remote_data_path, extension="fits", not_contains="poisson",
                                                   returns=["path", "name"], recursive=True): #, recursion_level=1):

        # Determine directory path
        path = fs.directory_of(image_path)

        # Get filter name
        if lazy:
            #name = str(parse_filter(image_name))
            #name = str(headers.get_filter(image_name))
            fltr = headers.get_filter(image_name)
            if fltr is None:
                log.warning("Could not determine the filter of the '" + image_name + "' image: skipping ...")
                continue
            else: name = str(fltr)
        else: name = get_filter_name(image_path, session)

        if name is None: raise RuntimeError("Could not determine the filter name for the '" + image_name + "' image")

        # Add the image path
        paths[name] = image_path

        # Determine path to poisson error map
        poisson_path = fs.join(path, image_name + "_poisson.fits")

        # Set the path to the poisson error map
        if remote.is_file(poisson_path):

            # Debugging
            log.debug("Poisson error frame found for '" + name + "' image ...")
            error_paths[name] = poisson_path

        # Poisson frame not present
        elif needs_poisson_errors(name): raise RuntimeError("Poisson error frame not found for the " + name + " image. Run the appropriate command to create the mosaics and poisson frames.")

    # Return the paths
    return paths, error_paths

# -----------------------------------------------------------------
