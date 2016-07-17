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

# Required arguments
definition.add_required("ski_path", "absolute_path", "the name of the ski file to be used for the scaling test")
definition.add_required("remote", str, "the name of the remote host")
definition.add_required("mode", str, "the parallelization mode for the scaling test", choices=["mpi", "hybrid", "threads"])

# Optional arguments
definition.add_positional_optional("maxnodes", float, "the maximum number of nodes", 1)
definition.add_positional_optional("minnodes", float, "the minimum number of nodes. In hybrid mode, this also defines the number of threads per process", 0)
definition.add_optional("cluster", str, "the name of the cluster", None)
definition.add_optional("wavelengths", float, "boost the number of wavelengths by a certain factor", None)
definition.add_optional("packages", float, "boost the number of photon packages by a certain factor", None)

# Flags
definition.add_flag("manual", "launch and inspect job scripts manually")
definition.add_flag("keep", "keep the output generated by the different SKIRT simulations")

# -----------------------------------------------------------------