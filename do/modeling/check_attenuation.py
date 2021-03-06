#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.check_attenuation Check the attenuation correction of the prepared images.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, parse_arguments
from pts.modeling.core.environment import GalaxyModelingEnvironment
from pts.modeling.preparation.preparer import load_statistics
from pts.core.filter.filter import parse_filter
from pts.magic.services.attenuation import GalacticAttenuation
from pts.core.basics.log import log
from pts.modeling.component.galaxy import get_galaxy_properties
from pts.modeling.core.environment import verify_modeling_cwd

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# Create the configuration
config = parse_arguments("check_attenuation", definition)

# -----------------------------------------------------------------

# Modeling path
modeling_path = verify_modeling_cwd()

# Load the modeling environment
environment = GalaxyModelingEnvironment(modeling_path)

# -----------------------------------------------------------------

properties = get_galaxy_properties(modeling_path)

# -----------------------------------------------------------------

attenuation = GalacticAttenuation(properties.center)

# -----------------------------------------------------------------

print("")

# Loop over the names
for prep_name in environment.preparation_names:

    # Load the statistics
    statistics = load_statistics(modeling_path, prep_name)

    # Determine filter
    fltr = parse_filter(prep_name)

    # Get the extinction
    att = attenuation.extinction_for_filter(fltr)

    if att == 0.0:
        if statistics.attenuation != 0.0: log.warning(prep_name + ": attenuation is zero but preparation attenuation value was " + str(statistics.attenuation))
        continue

    # Ratio
    ratio = statistics.attenuation / att
    rel = abs((statistics.attenuation - att)/att)

    #print(prep_name, statistics.attenuation, ext, ratio, rel * 100)

    print(prep_name)
    print("")
    print(" - preparation: " + str(statistics.attenuation))
    print(" - real: " + str(ext))
    print(" - ratio: " + str(ratio))
    print(" - rel difference: " + str(rel * 100) + "%")
    print("")

# -----------------------------------------------------------------
