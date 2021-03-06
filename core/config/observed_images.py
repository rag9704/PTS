#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# Add optional
definition.add_optional("output", "string", "output directory")

# Add flags
definition.add_flag("spectral_convolution", "convolve over the wavelengths to get the most accurate images", True)
definition.add_flag("group", "group the images per instrument", False)

# Number of parallel processes to use to create the images
definition.add_optional("nprocesses_local", "positive_integer", "number of parallel processes to use for local calculation", 2)
definition.add_optional("nprocesses_remote", "positive_integer", "number of parallel processes to use for remote calculation", 8)

# -----------------------------------------------------------------
