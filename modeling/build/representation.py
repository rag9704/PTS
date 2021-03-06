#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.build.representation Contains the RepresentationBuilder class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math

# Import the relevant PTS classes and modules
from ...core.tools import filesystem as fs
from ..basics.instruments import SEDInstrument, FrameInstrument, SimpleInstrument
from ..basics.projection import EdgeOnProjection, FaceOnProjection, GalaxyProjection
from ...core.simulation.grids import load_grid
from ...core.simulation.grids import FileTreeDustGrid
from ...core.simulation.tree import DustGridTree
from pts.core.tools.utils import lazyproperty

# -----------------------------------------------------------------

class Representation(object):

    """
    This class ...
    """

    def __init__(self, name, model_name, path):

        """
        This function ...
        :param name:
        :param model_name:
        :param path:
        """

        # General properties
        self.name = name
        self.model_name = model_name
        self.path = path

        # Directories of the representation
        self.projections_path = fs.create_directory_in(self.path, "projections")
        self.instruments_path = fs.create_directory_in(self.path, "instruments")
        self.grid_path = fs.create_directory_in(self.path, "grid")

        # Individual projection paths
        self.earth_projection_path = fs.join(self.projections_path, "earth.proj")
        self.edgeon_projection_path = fs.join(self.projections_path, "edgeon.proj")
        self.faceon_projection_path = fs.join(self.projections_path, "faceon.proj")

        # Individual instrument paths
        self.sed_instrument_path = fs.join(self.instruments_path, "sed.instr")
        self.frame_instrument_path = fs.join(self.instruments_path, "frame.instr")
        self.simple_instrument_path = fs.join(self.instruments_path, "simple.instr")

        # Dust grid file path
        self.dust_grid_path = fs.join(self.grid_path, "dust_grid.dg")

        # Dust grid SKIRT output path
        self.grid_out_path = fs.create_directory_in(self.grid_path, "out")

        # Dust grid tree path
        self.dust_grid_tree_path = fs.join(self.grid_path, "tree.dat")

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid_tree(self):

        """
        This function ...
        :return: 
        """

        return DustGridTree.from_file(self.dust_grid_tree_path)

    # -----------------------------------------------------------------

    def create_file_tree_dust_grid(self, search_method="Neighbor", write=False):

        """
        This function ...
        :param search_method:
        :param write:
        :return: 
        """

        grid = FileTreeDustGrid(filename=self.dust_grid_tree_path, search_method=search_method, write=write)
        return grid

    # -----------------------------------------------------------------

    @lazyproperty
    def has_dust_grid_tree(self):

        """
        This function ...
        :return: 
        """

        return fs.is_file(self.dust_grid_tree_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def pixelscale(self):

        """
        This function ...
        :return:
        """

        return self.earth_projection.pixelscale

    # -----------------------------------------------------------------

    @lazyproperty
    def earth_projection(self):

        """
        This function ...
        :return:
        """

        return GalaxyProjection.from_file(self.earth_projection_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def edgeon_projection(self):

        """
        This function ...
        :return:
        """

        return EdgeOnProjection.from_file(self.edgeon_projection_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def faceon_projection(self):

        """
        This function ...
        :return:
        """

        return FaceOnProjection.from_file(self.faceon_projection_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def sed_instrument(self):

        """
        This function ...
        :return:
        """

        return SEDInstrument.from_file(self.sed_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def frame_instrument(self):

        """
        This function ...
        :return:
        """

        return FrameInstrument.from_file(self.frame_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simple_instrument(self):

        """
        This function ...
        :return:
        """

        return SimpleInstrument.from_file(self.simple_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid(self):

        """
        This function ...
        :return:
        """

        return load_grid(self.dust_grid_path)

# -----------------------------------------------------------------
