#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.extinction Get the galactic extinction for a certain galaxy.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, parse_arguments
from pts.magic.services.extinction import GalacticExtinction
from pts.core.basics.plot import Plot
from pts.core.filter.broad import categorize_filters, categorized_filters_sorted_labels, get_filters_for_regimes

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()
definition.add_required("galaxy_name", "string", "galaxy name")

# Get the configuration
config = parse_arguments("extinction", definition)

# -----------------------------------------------------------------

# Create extinction object
extinction = GalacticExtinction(config.galaxy_name)

# -----------------------------------------------------------------

#specs = categorize_filters()
#for label in categorized_filters_sorted_labels(specs):
#    filter_names = specs[label]
#    curve = extinction.extinction_curve(filter_names)
#    plot = Plot()
#    plot.add_curve(curve, "hello")
#    plot.finish()

# -----------------------------------------------------------------

filters = get_filters_for_regimes("UV-NIR")

# -----------------------------------------------------------------

curve = extinction.extinction_curve(filters, ignore_errors=True)
print(curve)
plot = Plot()
plot.set_x_log_scale()
plot.set_y_log_scale()
plot.add_curve(curve, "extinction")
plot.finish()

# -----------------------------------------------------------------