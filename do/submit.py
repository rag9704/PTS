#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package do.submit Submit a job for running a ski file to the HPC infrastructure
#

# -----------------------------------------------------------------

# Import standard modules
import os
import os.path
import argparse
import subprocess

# Import the relevant PTS class
from pts.jobscript import JobScript

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument('skifile', type=str, help='the name of the ski file')
parser.add_argument('inpath', type=str, help='the simulation input path')
parser.add_argument('outpath', type=str, help='the simulation output path')
parser.add_argument('nodes', type=int, help='the number of nodes to use for the simulation')
parser.add_argument('threadspp', type=int, help='the number of parallel threads per process')
parser.add_argument('walltime', type=int, help='the expected walltime for this simulation in hh:mm:ss format')
parser.add_argument('cluster', nargs='?', type=str, help='the cluster to which the job should be submitted', default="delcatty")

# Parse the command line arguments
args = parser.parse_args()
skifile = args.skifile
inpath = args.inpath
outpath = args.outpath
nodes = args.nodes
threadspp = args.threadspp
walltime = args.walltime
cluster = args.cluster

# -----------------------------------------------------------------

cores = {'delcatty': 16, 'gulpin': 32}

# -----------------------------------------------------------------

# Calculate the walltime in seconds
hours, minutes, seconds = walltime.split(':')
time = int(hours)*3600 + int(minutes)*60 + int(seconds)

# Determine the full path to the ski file
skifilepath = os.path.abspath(skifile)

# Determine the full path to the input and output directories
inputpath = os.path.abspath(inpath)
outputpath = os.path.abspath(outpath)

# Set the environment for submitting to the specified cluster
clusterstring = "cluster/" + cluster
subprocess.call(["module", "swap", clusterstring])

# Get the number of processors per node on the specified cluster
ppn = cores[cluster]

# Create a job script for this simulation
jobscript = JobScript("job.sh", skifilepath, nodes, ppn, threadspp, outputpath, time, mail=True)

# Submit the job script to the cluster
jobscript.submit()

# Remove the job script
jobscript.remove()

# -----------------------------------------------------------------
