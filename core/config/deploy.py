#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.remote.host import find_host_ids
from pts.core.basics.configuration import ConfigurationDefinition

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# Add optional
definition.add_optional("host_ids", "string_list", "remote host ids", choices=find_host_ids(), default=find_host_ids())

# Add flags
definition.add_flag("local", "also deploy locally", True)
definition.add_flag("skirt", "deploy SKIRT", True)
definition.add_flag("pts", "deploy PTS", True)
definition.add_flag("check", "check versions after deployment", True)

# Add optional
definition.add_optional("pts_on", "string_list", "hosts on which PTS should be installed (None means all)", choices=find_host_ids())

# -----------------------------------------------------------------