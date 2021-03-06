#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.tools import filesystem as fs
from pts.modeling.maps.collection import MapsCollection
from pts.core.remote.host import find_host_ids
from pts.modeling.config.maps import definition
from pts.modeling.maps.components import steps
from pts.magic.core.cutout import interpolation_methods
from pts.modeling.config.build_stars import degeyter_ratio, scalelength_scaleheight_ratios

# -----------------------------------------------------------------

default_sigma_level = 3.0

# -----------------------------------------------------------------

# Set the modeling path
modeling_path = fs.cwd()

# Create the maps collection
collection = MapsCollection.from_modeling_path(modeling_path)

# -----------------------------------------------------------------

# Get maps
old_map_paths = collection.get_old_stellar_disk_map_paths()
young_map_paths = collection.get_young_map_paths(flatten=True)
ionizing_map_paths = collection.get_ionizing_map_paths(flatten=True)
dust_map_paths = collection.get_not_hot_dust_map_paths(flatten=True)

# Get map names
old_map_names = old_map_paths.keys()
young_map_names = young_map_paths.keys()
ionizing_map_names = ionizing_map_paths.keys()
dust_map_names = dust_map_paths.keys()

# Get number of maps
nold_maps = len(old_map_names)
nyoung_maps = len(young_map_names)
nionizing_maps = len(ionizing_map_names)
ndust_maps = len(dust_map_names)

# -----------------------------------------------------------------

# Steps
definition.add_flag("steps", "save the results of intermediate steps", True)

# Remote
definition.add_optional("remote", "string", "remote host to use for creating the clip masks", choices=find_host_ids(schedulers=False))

# CONVOLUTION
definition.add_flag("convolve", "perform convolution during the creation of the clip masks", True)

# REBINNING
definition.add_optional("rebin_remote_threshold", "data_quantity", "data size threshold for remote rebinning", "0.5 GB", convert_default=True)

# Selections
definition.add_optional("old", "string_list", "selected old stellar maps", choices=old_map_names)
definition.add_optional("young", "string_list", "selected young stellar maps", choices=young_map_names)
definition.add_optional("ionizing", "string_list", "selected ionizing stellar maps", choices=ionizing_map_names)
definition.add_optional("dust", "string_list", "selected dust maps", choices=dust_map_names)

# Selections with indices
definition.add_optional("old_indices", "integer_list", "selected old stellar maps", choices=range(nold_maps))
definition.add_optional("young_indices", "integer_list", "selected young stellar maps", choices=range(nyoung_maps))
definition.add_optional("ionizing_indices", "integer_list", "selected ionizing stellar maps", choices=range(nionizing_maps))
definition.add_optional("dust_indices", "integer_list", "selected dust maps", choices=range(ndust_maps))

# Anti-selections
definition.add_optional("not_old", "string_list", "ignore old stellar maps", choices=old_map_names)
definition.add_optional("not_young", "string_list", "ignore young stellar maps", choices=young_map_names)
definition.add_optional("not_ionizing", "string_list", "ignore ionizing stellar maps", choices=ionizing_map_names)
definition.add_optional("not_dust", "string_list", "ignore dust maps", choices=dust_map_names)

# Anti-selections with indices
definition.add_optional("not_old_indices", "integer_list", "ignore old stellar maps", choices=range(nold_maps))
definition.add_optional("not_young_indices", "integer_list", "ignore young stellar maps", choices=range(nyoung_maps))
definition.add_optional("not_ionizing_indices", "integer_list", "ignore ionizing stellar maps", choices=range(nionizing_maps))
definition.add_optional("not_dust_indices", "integer_list", "ignore dust maps", choices=range(ndust_maps))

# Random selections
definition.add_optional("random_old", "positive_integer", "select x random old stellar maps")
definition.add_optional("random_young", "positive_integer", "select x random young stellar maps")
definition.add_optional("random_ionizing", "positive_integer", "select x random ionizing stellar maps")
definition.add_optional("random_dust", "positive_integer", "select x random dust maps")
definition.add_optional("random", "positive_integer", "select x maps for old stars, young stars, ionizing stars and dust")

# Flags
definition.add_flag("all_old", "select all old stellar maps")
definition.add_flag("all_young", "select all young stellar maps")
definition.add_flag("all_ionizing", "select all ionizing stellar maps")
definition.add_flag("all_dust", "select all dust maps")
definition.add_flag("all", "select all maps")

# Levels
definition.add_optional("levels", "filter_real_dictionary", "significance levels for the different images")
definition.add_optional("default_level", "real", "default significance level", default_sigma_level)
definition.add_flag("all_levels", "use the default sigma level for all maps")

# CROPPING
definition.add_optional("cropping_factor", "positive_real", "multiply the cropping box with this factor", 1.3)

# Image edge softening
definition.add_optional("softening_start", "real", "relative radius for softening to start (relative to truncation ellipse)", 0.75)

# ADVANCED
definition.add_optional("nopen_files", "positive_integer", "number of open files necessary to make the script work", 1024)

# Scale heights
definition.add_optional("scalelength_to_scaleheight", "real", "ratio of scalelength to scaleheight", default=degeyter_ratio, suggestions=scalelength_scaleheight_ratios)
definition.add_optional("young_scaleheight_ratio", "real", "ratio of the young stellar scaleheight to the old stellar scaleheight", 0.5)
definition.add_optional("ionizing_scaleheight_ratio", "real", "ratio of the ionizing scaleheight to the old stellar scaleheight", 0.25)
definition.add_optional("dust_scaleheight_ratio", "real", "ratio of the dust scaleheight to the old stellar scaleheight", 0.5)

# -----------------------------------------------------------------

# For clip mask
definition.add_optional("min_npixels", "positive_integer", "minimum number of pixels", 1)
definition.add_optional("connectivity", "positive_integer", "connectiviy", 4)

# For plotting mask
#definition.add_flag("mask_alpha", "use alpha for the mask", True) -> No: we write masks as FITS files, not as PNG plots

# For masking
definition.add_flag("fuzzy_mask", "use fuzzy masks", True)
definition.add_optional("fuzziness", "percentage", "relative fuzziness edge width", "50", convert_default=True)
definition.add_optional("fuzzy_min_significance_offset", "positive_real", "minimum significance offset from start of fuzzy edge to maximum (peak) significance (in sigma levels)", 1.)

# -----------------------------------------------------------------

# ADVANCED
definition.add_optional("rerun", "string", "rerun the map processing (for all maps) from this step", choices=steps)
definition.add_optional("rerun_old", "string", "rerun the map processing (for all old stellar maps) from this step", choices=steps)
definition.add_optional("rerun_young", "string", "rerun the map processing (for all young stellar maps) from this step", choices=steps)
definition.add_optional("rerun_ionizing", "string", "rerun the map processing (for all ionizing stellar maps) from this step", choices=steps)
definition.add_optional("rerun_dust", "string", "rerun the map processing (for all dust maps) from this step", choices=steps)

# ADVANCED
# to save space
definition.add_flag("remove_other", "remove maps, masks and intermediate results for maps other than those that are selected", False)
definition.add_flag("remove_other_old", "remove other old stellar maps", False)
definition.add_flag("remove_other_young", "remove other young stellar maps", False)
definition.add_flag("remove_other_ionizing", "remove other ionizing stellar maps", False)
definition.add_flag("remove_other_dust", "remove other dust maps", False)

# -----------------------------------------------------------------

# REDEPROJECT

definition.add_flag("redeproject", "redeproject all maps")
definition.add_flag("redeproject_old", "redeproject the old stellar maps")
definition.add_flag("redeproject_young", "redeproject the young stellar maps")
definition.add_flag("redeproject_ionizing", "redeproject the ionizing stellar maps")
definition.add_flag("redeproject_dust", "redeproject the dust maps")

# REDEPROJECT WITH SKIRT

definition.add_flag("redeproject_skirt", "redeproject all maps with SKIRT")
definition.add_flag("redeproject_skirt_old", "redeproject the old stellar maps with SKIRT")
definition.add_flag("redeproject_skirt_young", "redeproject the young stellar maps with SKIRT")
definition.add_flag("redeproject_skirt_ionizing", "redeproject the ionizing stellar maps with SKIRT")
definition.add_flag("redeproject_skirt_dust", "redeproject the dust maps with SKIRT")

# REPROJECT

definition.add_flag("reproject", "reproject all maps")
definition.add_flag("reproject_old", "reproject the old stellar maps")
definition.add_flag("reproject_young", "reproject the young stellar maps")
definition.add_flag("reproject_ionizing", "reproject the ionizing stellar maps")
definition.add_flag("reproject_dust", "reproject the dust maps")

# -----------------------------------------------------------------

default_interpolation_method = "pts"

# -----------------------------------------------------------------

# INTERPOLATION OF CORE OF THE MAPS
definition.add_optional("interpolate_old", "real", "interpolation core boundary for the old stellar maps, relative to the truncation ellipse", suggestions=[0.06]) # suggestion is for M81
definition.add_optional("interpolate_young", "real", "interpolation core boundary for the young stellar maps, relative to the truncation ellipse")
definition.add_optional("interpolate_ionizing", "real", "interpolation core boundary for the ionizing stellar maps, relative to the truncation ellipse")
definition.add_optional("interpolate_dust", "real", "interpolation core boundary for the dust maps, relative to the truncation ellipse")
definition.add_optional("source_outer_factor", "real", "outer factor", 1.4)
definition.add_optional("interpolation_method", "string", "interpolation method", default_interpolation_method, choices=interpolation_methods)
definition.add_flag("sigma_clip", "apply sigma clipping before interpolation", True)

# ALSO FOR INTERPOLATION
definition.add_optional("interpolation_angle_offset_old", "angle", "offset of angle of ellipse for interpolation w.r.t. angle of truncation ellipse", "0 deg", convert_default=True, suggestions=["-18 deg"], convert_suggestions=True) # suggestion is for M81
definition.add_optional("interpolation_angle_offset_young", "angle", "offset of angle of ellipse for interpolation w.r.t. angle of truncation ellipse", "0 deg", convert_default=True)
definition.add_optional("interpolation_angle_offset_ionizing", "angle", "offset of angle of ellipse for interpolation w.r.t. angle of truncation ellipse", "0 deg", convert_default=True)
definition.add_optional("interpolation_angle_offset_dust", "angle", "offset of angle of ellipse for interpolation w.r.t. angle of truncation ellipse", "0 deg", convert_default=True)

# MORE FOR INTERPOLATION
definition.add_optional("interpolation_softening_start", "real", "relative radius for softening to start (relative to interpolation ellipse)", 0.65)
definition.add_optional("interpolation_softening_end", "real", "relative radius for softening to end (relative to interpolation ellipse", 1.2)

# -----------------------------------------------------------------

# CLEAR ALL
definition.add_flag("clear_all", "clear all previous results")

# -----------------------------------------------------------------

# FOR DEPROJECTION
definition.add_optional("downsample_factor", "positive_real", "downsample factor for rendering the deprojected maps", 2.)

# FOR PROJECTION
definition.add_optional("scale_heights", "positive_real", "scale heights", 10.)

# -----------------------------------------------------------------
