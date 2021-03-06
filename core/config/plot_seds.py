#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.core.config.plot import definition as plot_definition
from pts.core.basics.plot import plotting_libraries, mpl

# -----------------------------------------------------------------

default_residual_reference = "models"
residual_references = ["models", "observations"]

# -----------------------------------------------------------------

# Create configuration definition
definition = ConfigurationDefinition()

# Add required
definition.add_positional_optional("seds", "filepath_list", "SED files to be plotted")

# Add plotting options
definition.import_section("plot", "plotting options", plot_definition)

# The unit in which to plot
definition.add_optional("wavelength_unit", "length_unit", "unit of wavelength", "micron", convert_default=True)
definition.add_optional("unit", "photometric_unit", "photometric unit", "Jy", convert_default=True)

# Residual reference
definition.add_optional("residual_reference", "string", "reference for the residuals", default_residual_reference, choices=residual_references)

# The plotting library to use
definition.add_optional("library", "string", "plotting library", mpl, plotting_libraries)

# -----------------------------------------------------------------

definition.add_flag("show", "show the plot (default is automatic)", None)

# -----------------------------------------------------------------
