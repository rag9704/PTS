#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.core.plot.scaling import scaling_properties, simulation_phases, communication_phases

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# Flags
definition.add_flag("recursive", "look for simulation in directories recursively", True)

# Add optional
definition.add_positional_optional("properties", "string_list", "plot the scaling of these properties", choices=scaling_properties, default=scaling_properties)
definition.add_positional_optional("phases", "string_list", "simulation phases for which to do the plotting", choices=simulation_phases, default=["total"])

definition.add_flag("hybridisation", "plot as a function of number of processes for constant number of cores")

# Output
definition.add_optional("output", "directory_path", "output directory", letter="o")
definition.add_optional("figsize", "integer_tuple", "figure size", default=(12,8))

definition.add_flag("xlog", "log scale for x axis", True)
definition.add_flag("ylog", "log scale for y axis", True)

# Sigma level for plotting error bars
definition.add_optional("sigma_level", "real", "sigma level for plotting error bars", 1.0)

# Make fit and plot fit
definition.add_flag("fit", "fit theoretical curves to timing and memory data", True)
definition.add_flag("plot_fit", "plot the fitted relations", True)

# Normalize runtimes and memory usages
definition.add_flag("normalize_runtimes", "normalize runtimes for plotting")
definition.add_flag("normalize_memory", "normalize memory usage for plotting")

# Split communication into subphases
definition.add_flag("split_communication", "split the different communication steps")
definition.add_optional("communication_subphases", "string_list", "communication subphases to plot", communication_phases)

# Enable all properties and phases
definition.add_flag("all", "plot everything (enable all properties and phases)")
definition.add_flag("all_timing", "plot everything related to timing")
definition.add_flag("all_memory", "plot everything related to memory usage")

# Enable all phases
definition.add_flag("all_phases", "enable all phases")

# Timelines
definition.add_section("timelines", "options for plotting timelines")
definition.sections["timelines"].add_flag("add_serial", "add CPU times of serial run for comparison")
definition.sections["timelines"].add_flag("percentages", "add percentages for the different phases compared to the total simulation", True)

# FROM HERE: ADVANCED STUFF: USE WITH CARE
definition.add_flag("hetero", "not necessarily a single ski")

# EXTRAPOLATION
definition.add_section("extrapolation", "extrapolate ...")

# TIMING
definition.sections["extrapolation"].add_section("timing", "extrapolation of timing data")
definition.sections["extrapolation"].sections["timing"].add_flag("ncores", "extrapolate the data to a number of cores of one to get a serial timing")
definition.sections["extrapolation"].sections["timing"].add_flag("npackages", "extrapolate the number of photon packages of a serial run to obtain a serial run for a series of simulations with a higher number of packages (requires 'hetero' to be enabled)")
definition.sections["extrapolation"].sections["timing"].add_flag("nwavelengths", "extrapolate the number of wavelengths of a serial run to obtain a serial run for a series of simulations with a higher number of wavelengths (requires 'hetero' to be enabled) [THIS OPTION IS VERY TRICKY: LOAD BALANCING CAN VARY!]")
definition.sections["extrapolation"].sections["timing"].add_flag("in_times", "not only extrapolate for normalizing, but also plot the serial time as if it were a genuine data point")

# MEMORY
definition.sections["extrapolation"].add_section("memory", "extrapolation of memory data")
definition.sections["extrapolation"].sections["memory"].add_flag("nprocesses", "extrapolate the data to a number of processes of one to get serial memory data points")
definition.sections["extrapolation"].sections["memory"].add_flag("nwavelengths", "extrapolate the number of wavelengths of a serial run to obtain a serial run for a series of simulations with a higher number of wavelengths (required 'hetero' to be enabled)")
definition.sections["extrapolation"].sections["memory"].add_flag("extrapolate_ncells", "extrapolate the number of dust cells")
definition.sections["extrapolation"].sections["memory"].add_flag("in_memory", "not only extrapolate for normalizing, but also plot the serial time as if it were a genuine data point")

# -----------------------------------------------------------------
