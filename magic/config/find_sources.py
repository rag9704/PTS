#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from .find_stars import definition as stars_definition
from .find_galaxies import definition as galaxies_definition
from .find_other import definition as other_definition

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# The dataset or image
definition.add_required("dataset", "file_path", "name of the dataset file or image file")

# Flags
definition.add_flag("find_stars", "find stars in the images", True)

# Flags
definition.add_flag("find_other_sources", "find other contaminating sources", True)

# Optional settings
definition.add_optional("galactic_catalog_file", "file_path", "galactic catalog file")
definition.add_optional("stellar_catalog_file", "file_path", "stellar catalog file")

# Regions
definition.add_optional("special_region", "file_path", "region indicating areas that require special attention")
definition.add_optional("ignore_region", "file_path", "region indicating areas that should be ignored")

# Output
definition.add_optional("output", "directory_path", "output directory", letter="o")
definition.add_optional("input", "directory_path", "input directory", letter="i")

# Sections
definition.import_section("galaxies", "options for galaxy finder", galaxies_definition)
definition.import_section("stars", "options for star finder", stars_definition)
definition.import_section("other_sources", "options for finding other contaminating sources", other_definition)

# -----------------------------------------------------------------