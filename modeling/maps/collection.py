#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.maps.collection Contains the MapsCollection class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ...core.tools import filesystem as fs
from ...core.tools.serialization import load_dict
from ..core.environment import GalaxyModelingEnvironment
from ..core.history import ModelingHistory
from ...core.tools import sequences
from ...magic.core.list import NamedFrameList
from ...magic.core.frame import Frame
from ...core.filter.filter import parse_filter
from ...core.tools.stringify import tostr
from ...core.tools import types
from ..core.environment import colours_name, ssfr_name, tir_name, attenuation_name, old_name, young_name, ionizing_name, dust_name

# -----------------------------------------------------------------

origins_filename = "origins.txt"

# -----------------------------------------------------------------

maps_commands = ["make_colours_maps", "make_ssfr_maps", "make_tir_maps", "make_attenuation_maps", "make_old_stellar_maps", "make_dust_map", "make_young_stellar_maps", "make_ionizing_stellar_maps"]

# -----------------------------------------------------------------

def sub_name_for_command(command):

    """
    This function ...
    :param command:
    :return:
    """

    if command == "make_colours_maps": return colours_name
    elif command == "make_ssfr_maps": return ssfr_name
    elif command == "make_tir_maps": return tir_name
    elif command == "make_attenuation_maps": return attenuation_name
    elif command == "make_old_stellar_maps": return old_name
    elif command == "make_young_stellar_maps": return young_name
    elif command == "make_ionizing_stellar_maps": return ionizing_name
    elif command == "make_dust_map": return dust_name
    else: raise ValueError("Invalid commands: " + command)

# -----------------------------------------------------------------

def command_for_sub_name(name):

    """
    This function ...
    :param name:
    :return:
    """

    if name == colours_name: return "make_colours_maps"
    elif name == ssfr_name: return "make_ssfr_maps"
    elif name == tir_name: return "make_tir_maps"
    elif name == attenuation_name: return "make_attenuation_maps"
    elif name == old_name: return "make_old_stellar_maps"
    elif name == young_name: return "make_young_stellar_maps"
    elif name == ionizing_name: return "make_ionizing_stellar_maps"
    elif name == dust_name: return "make_dust_map"
    else: raise ValueError("Invalid sub name: " + name)

# -----------------------------------------------------------------

class MapsCollection(object):

    """
    This class...
    """

    def __init__(self, maps_path):

        """
        The constructor ...
        :param maps_path:
        :return:
        """

        # Set the maps path
        self.maps_path = maps_path

    # -----------------------------------------------------------------

    @property
    def modeling_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.maps_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def environment(self):

        """
        This function ...
        :return:
        """

        return GalaxyModelingEnvironment(self.modeling_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def history(self):

        """
        This fucntion ...
        :return:
        """

        return ModelingHistory.from_file(self.environment.history_file_path)

    # -----------------------------------------------------------------

    @property
    def maps_colours_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_colours_path

    # -----------------------------------------------------------------

    @property
    def maps_colours_name(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_colours_name

    # -----------------------------------------------------------------

    @property
    def maps_ssfr_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_ssfr_path

    # -----------------------------------------------------------------

    @property
    def maps_ssfr_name(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_ssfr_name

    # -----------------------------------------------------------------

    @property
    def maps_tir_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_tir_path

    # -----------------------------------------------------------------

    @property
    def maps_tir_name(self):

        """
        THis function ...
        :return:
        """

        return self.environment.maps_tir_name

    # -----------------------------------------------------------------

    @property
    def maps_attenuation_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_attenuation_path

    # -----------------------------------------------------------------

    @property
    def maps_attenuation_name(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_attenuation_name

    # -----------------------------------------------------------------

    @property
    def maps_old_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_old_path

    # -----------------------------------------------------------------

    @property
    def maps_old_name(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_old_name

    # -----------------------------------------------------------------

    @property
    def maps_young_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_young_path

    # -----------------------------------------------------------------

    @property
    def maps_young_name(self):

        """
        This function ...
        :return:
        """

        return self.environment.maps_young_name

    # -----------------------------------------------------------------

    @property
    def maps_ionizing_path(self):

        """
        This fucntion ...
        :return:
        """

        return self.environment.map_ionizing_path

    # -----------------------------------------------------------------

    @property
    def maps_ionizing_name(self):

        """
        THis function ...
        :return:
        """

        return self.environment.maps_ionizing_name

    # -----------------------------------------------------------------

    @property
    def maps_dust_path(self):

        """
        This fucntion ...
        :return:
        """

        return self.environment.maps_dust_path

    # -----------------------------------------------------------------

    @property
    def maps_dust_name(self):

        """
        THis function ...
        :return:
        """

        return self.environment.maps_dust_name

    # -----------------------------------------------------------------

    @property
    def maps_sub_paths(self):

        """
        This function ...
        :return:
        """

        return [self.maps_colours_path, self.maps_ssfr_path, self.maps_tir_path, self.maps_attenuation_path,
                self.maps_old_path, self.maps_young_path, self.maps_ionizing_path, self.maps_dust_path]

    # -----------------------------------------------------------------

    @property
    def maps_sub_names(self):

        """
        This function ...
        :return:
        """

        return [fs.name(path) for path in self.maps_sub_paths]

    # -----------------------------------------------------------------

    def get_origins_sub_name(self, name, flatten=False, method=None):

        """
        This function ...
        :param name:
        :param flatten:
        :param method:
        :return: 
        """

        # Determine path
        sub_path = fs.join(self.maps_path, name)
        if not fs.is_directory(sub_path): raise ValueError("Invalid name '" + name + "'")
        direct_origins_path = fs.join(sub_path, origins_filename)

        # No subdirectories
        if fs.is_file(direct_origins_path): origins = load_dict(direct_origins_path)

        # Subdirectories
        else:

            if method is not None:

                # Check whether valid method
                method_path = fs.join(sub_path, method)
                if not fs.is_directory(method_path): raise ValueError("Could not find a directory for the '" + method + "' method")
                origins_path = fs.join(method_path, origins_filename)
                if not fs.is_file(origins_path): raise ValueError("File '" + origins_path + "' is missing")

                # Load the origins
                origins = load_dict(origins_path)

            else:

                # Initialize
                origins = dict()

                # Loop over subdirectories
                for method_path in fs.directories_in_path(sub_path):

                    origins_path = fs.join(method_path, origins_filename)
                    if not fs.is_file(origins_path): raise ValueError("File '" + origins_path + "' is missing")

                    #print(origins_path)

                    # Determine method
                    method_name = fs.name(method_path)

                    # Load the origins for this method
                    origins_method = load_dict(origins_path)

                    # Flatten into a one-level dict
                    if flatten:
                        for map_name in origins_method: origins[method_name + "_" + map_name] = origins_method[map_name]

                    # Don't flatten: get nested dict
                    else: origins[method_name] = origins_method

        # Return the origins
        return origins

    # -----------------------------------------------------------------

    def get_origins_sub_names(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        origins = dict()
        for name in self.maps_sub_names: origins[name] = self.get_origins_sub_name(name, flatten=flatten)
        return origins

    # -----------------------------------------------------------------

    def get_maps_sub_names(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        maps = dict()
        for name in self.maps_sub_names: maps[name] = self.get_maps_sub_name(name, flatten=flatten)
        return maps

    # ORIGINS

    def get_colours_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return: 
        """

        return self.get_origins_sub_name(self.maps_colours_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_ssfr_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_ssfr_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_tir_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_tir_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_attenuation_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_attenuation_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_old_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_old_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_young_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_young_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_ionizing_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_ionizing_name, flatten=flatten)

    # -----------------------------------------------------------------

    def get_dust_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        return self.get_origins_sub_name(self.maps_dust_name, flatten=flatten)

    def get_colour_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_colours_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_ssfr_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_ssfr_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_tir_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_tir_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_attenuation_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist::
        :return:
        """

        return self.get_maps_sub_name(self.maps_attenuation_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_old_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_old_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_young_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_young_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_ionizing_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_ionizing_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_dust_maps(self, flatten=False, framelist=False):

        """
        This function ...
        :param flatten:
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_dust_name, flatten=flatten, framelist=framelist)

    # -----------------------------------------------------------------

    def get_tir_single_maps(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.maps_tir_path, "single")
        return NamedFrameList.from_directory(path).to_dictionary()

    # -----------------------------------------------------------------

    def get_tir_multi_maps(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.maps_tir_path, "multi")
        return NamedFrameList.from_directory(path).to_dictionary()

    # -----------------------------------------------------------------

    def get_tir_single_origins(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.maps_tir_path, "single", origins_filename)
        return load_dict(path)

    # -----------------------------------------------------------------

    def get_tir_multi_origins(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.maps_tir_path, "multi", origins_filename)
        return load_dict(path)

    # -----------------------------------------------------------------

    def get_fuv_attenuation_maps(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        cortese = self.get_cortese_fuv_attenuation_maps()
        buat = self.get_buat_fuv_attenuation_maps()

        if flatten:

            maps = dict()
            for name in cortese: maps["cortese__" + name] = cortese[name]
            for name in buat: maps["buat__" + name] = buat[name]
            return maps

        else:

            maps = dict()
            maps["cortese"] = cortese
            maps["buat"] = buat
            return maps

    # -----------------------------------------------------------------

    def get_fuv_attenuation_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        cortese = self.get_cortese_fuv_attenuation_origins()
        buat = self.get_buat_fuv_attenuation_origins()

        if flatten:

            origins = dict()
            for name in cortese: origins["cortese__" + name] = cortese[name]
            for name in buat: origins["buat__" + name] = buat[name]
            return origins

        else:

            origins = dict()
            origins["cortese"] = cortese
            origins["buat"] = buat
            return origins

    # -----------------------------------------------------------------

    def get_fuv_attenuation_maps_and_origins(self, flatten=False):

        """
        This function ...
        :param flatten:
        :return:
        """

        maps = self.get_fuv_attenuation_maps(flatten=flatten)
        origins = self.get_fuv_attenuation_origins(flatten=flatten)

        # Check
        if not sequences.same_contents(maps.keys(), origins.keys()):

            log.error("Mismatch between FUV attenuation maps and their origins:")
            #raise ValueError("Mismatch between FUV attenuation maps names and their origins")

            sorted_keys_maps = sorted(maps.keys())
            sorted_keys_origins = sorted(origins.keys())

            if len(sorted_keys_maps) != len(sorted_keys_origins): log.error("Number of maps: " + str(len(sorted_keys_maps)) + " vs Number of origins: " + str(len(sorted_keys_origins)))

            indices = sequences.find_differences(sorted_keys_maps, sorted_keys_origins)

            log.error("Number of mismatches: " + str(len(indices)))

            #for index in indices: log.error(" - " + sorted_keys_maps[index] + " vs " + sorted_keys_origins[index])

            for index in range(min(len(sorted_keys_maps), len(sorted_keys_origins))):

                if sorted_keys_maps[index] == sorted_keys_origins[index]: log.success(" - " + sorted_keys_maps[index] + " = " + sorted_keys_origins[index])
                else: log.error(" - " + sorted_keys_maps[index] + " != " + sorted_keys_origins[index])

        #exit()

        # Return
        return maps, origins

    # -----------------------------------------------------------------

    def get_buat_fuv_attenuation_maps(self):

        """
        This function ...
        :return:
        """

        buat_path = fs.join(self.maps_attenuation_path, "buat")
        return NamedFrameList.from_directory(buat_path, contains="FUV").to_dictionary()

    # -----------------------------------------------------------------

    def get_cortese_fuv_attenuation_maps(self):

        """
        This function ...
        :return:
        """

        cortese_path = fs.join(self.maps_attenuation_path, "cortese")
        return NamedFrameList.from_directory(cortese_path).to_dictionary()

    # -----------------------------------------------------------------

    def get_buat_fuv_attenuation_origins(self):

        """
        This function ...
        :return:
        """

        buat_path = fs.join(self.maps_attenuation_path, "buat")
        table_path = fs.join(buat_path, origins_filename)
        origins = load_dict(table_path)

        # ONLY KEEP FUV
        for name in list(origins.keys()):
            if not name.startswith("FUV"): del origins[name]

        # Return
        return origins

    # -----------------------------------------------------------------

    def get_buat_nuv_attenuation_origins(self):

        """
        This function ...
        :return:
        """

        buat_path = fs.join(self.maps_attenuation_path, "buat")
        table_path = fs.join(buat_path, origins_filename)
        origins = load_dict(table_path)

        # ONLY KEEP NUV
        for name in list(origins.keys()):
            if not name.startswith("NUV"): del origins[name]

        # Return
        return origins

    # -----------------------------------------------------------------

    def get_cortese_fuv_attenuation_origins(self):

        """
        This function ...
        :return:
        """

        cortese_path = fs.join(self.maps_attenuation_path, "cortese")
        table_path = fs.join(cortese_path, origins_filename)
        return load_dict(table_path)

    # -----------------------------------------------------------------

    def get_old_stellar_bulge_map(self, fltr):

        """
        This function ...
        :param fltr:
        :return:
        """

        if types.is_string_type(fltr): fltr = parse_filter(fltr)

        path = fs.join(self.maps_old_path, "bulge", tostr(fltr, delimiter="_") + ".fits")
        return Frame.from_file(path)

    # -----------------------------------------------------------------

    def get_old_stellar_bulge_maps(self, framelist=False):

        """
        This function ...
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_old_name, )

    # -----------------------------------------------------------------

    def get_old_stellar_disk_map(self, fltr):

        """
        This fucntion ...
        :param fltr:
        :return:
        """

        if types.is_string_type(fltr): fltr = parse_filter(fltr)

        path = fs.join(self.maps_old_path, "disk", tostr(fltr, delimiter="_") + ".fits")
        return Frame.from_file(path)

    # -----------------------------------------------------------------

    def get_old_stellar_disk_maps(self, framelist=False):

        """
        This function ...
        :param framelist:
        :return:
        """

        return self.get_maps_sub_name(self.maps_old_name, framelist=framelist, method="disk")

    # -----------------------------------------------------------------

    def get_old_stellar_disk_origins(self):

        """
        This function ...
        :return:
        """

        return self.get_origins_sub_name(self.maps_old_name, method="disk")

    # -----------------------------------------------------------------

    def get_hot_dust_maps(self):

        """
        This function ...
        :return:
        """

        hot_dust_path = fs.join(self.maps_dust_path, "hot")
        return NamedFrameList.from_directory(hot_dust_path).to_dictionary()

    # -----------------------------------------------------------------

    def get_hot_dust_origins(self):

        """
        This function ...
        :return:
        """

        hot_dust_path = fs.join(self.maps_dust_path, "hot")
        origins_path = fs.join(hot_dust_path, origins_filename)
        return load_dict(origins_path)

    # -----------------------------------------------------------------

    def get_map_paths_sub_name(self, name, flatten=False, method=None):

        """
        This function ...
        :param name:
        :param flatten:
        :param method:
        :return:
        """

        return get_map_paths_sub_name(self.environment, name, flatten=flatten, method=method)

    # -----------------------------------------------------------------

    def get_maps_sub_name(self, name, flatten=False, framelist=False, method=None):

        """
        This function ...
        :param name:
        :param flatten:
        :param framelist:
        :param method:
        :return:
        """

        return get_maps_sub_name(self.environment, self.history, name, flatten=flatten, framelist=framelist, method=method)

# -----------------------------------------------------------------

def get_map_paths_sub_name(environment, name, flatten=False, method=None):

    """
    This function ...
    :param environment:
    :param name:
    :param flatten:
    :param method:
    :return:
    """

    # Determine path
    sub_path = fs.join(environment.maps_path, name)
    if not fs.is_directory(sub_path): raise ValueError("Invalid name '" + name + "'")
    # direct_origins_path = fs.join(sub_path, origins_filename)
    # No subdirectories
    # if fs.is_file(direct_origins_path): origins = load_dict(direct_origins_path)

    # Subdirectories
    if fs.contains_directories(sub_path):

        # One method is specified
        if method is not None:

            # Check whether valid method
            method_path = fs.join(sub_path, method)
            if not fs.is_directory(method_path): raise ValueError("Directory not found for method '" + method + "'")

            # Return the file paths
            return fs.files_in_path(method_path, returns="dict", extension="fits")

        # Method not specified
        else:

            paths = dict()

            # Loop over the subdirectories
            for method_path, method_name in fs.directories_in_path(sub_path, returns=["path", "name"]):

                # Skip other method if method is defined
                if method is not None and method_name != method: continue

                # Get dictionary of file paths, but only FITS files
                files = fs.files_in_path(method_path, returns="dict", extension="fits")

                # Flatten into a one-level dict
                if flatten:
                    for map_name in files: paths[method_name + "_" + map_name] = files[map_name]

                # Don't flatten
                else: paths[method_name] = files

            # Return the paths
            return paths

    # Files present
    elif fs.contains_files(sub_path):

        # Method cannot be defined
        if method is not None: raise ValueError("Specified method '" + method + "', but all maps are in one directory")

        # Return the file paths
        return fs.files_in_path(sub_path, returns="dict", extension="fits")

    # Nothing present
    else: return dict()

# -----------------------------------------------------------------

def get_maps_sub_name(environment, history, name, flatten=False, framelist=False, method=None):

    """
    This function ...
    :param environment:
    :param history:
    :param name:
    :param flatten:
    :param framelist:
    :param method:
    :return:
    """

    # Initialize the maps dictionary
    maps = dict()

    # Get map paths
    paths = get_map_paths_sub_name(environment, name, flatten=flatten, method=method)

    # Loop over the entries
    for method_or_name in paths:

        # Methods
        if types.is_dictionary(paths[method_or_name]):

            method_name = method_or_name
            maps[method_name] = dict()

            # Loop over the paths, load the maps and add to dictionary
            for name in paths[method_or_name]:

                map_path = paths[method_or_name][name]
                try: maps[method_name][name] = Frame.from_file(map_path)
                except IOError:
                    command = command_for_sub_name(name)
                    log.warning("The " + method_name + "/" + name + " map is probably damaged. Run the '" + command + "' command again.")
                    log.warning("Removing the " + map_path + " map ...")
                    fs.remove_file(map_path)
                    history.remove_entries_and_save(command)

        # Just maps
        elif types.is_string_type(paths[method_or_name]):

            name = method_or_name
            map_path = paths[method_or_name]
            try:
                maps[name] = Frame.from_file(map_path)
            except IOError:
                command = command_for_sub_name(name)
                log.warning("The " + name + " map is probably damaged. Run the '" + command + "' command again.")
                log.warning("Removing the " + map_path + " map ...")
                fs.remove_file(map_path)
                history.remove_entries_and_save(command)

        # Something wrong
        else: raise RuntimeError("Something went wrong")

    # Return the maps
    if framelist: return NamedFrameList(**maps)
    else: return maps

# -----------------------------------------------------------------