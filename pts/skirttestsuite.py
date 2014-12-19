#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.skirttestsuite Performing a suite of SKIRT test cases
#
# An instance of the SkirtTestSuite class in this module represents a suite of SKIRT test cases, stored as
# a nested structure of files and directories according to a specific layout, and provides facilities to
# perform the tests, verify the results, and prepare a summary test report.

# -----------------------------------------------------------------

import datetime
import filecmp
import os
import os.path
import re
import time

from pts.skirtsimulation import SkirtSimulation
from pts.skirtexec import SkirtExec
from pts.log import Log
import subprocess

# -----------------------------------------------------------------
#  SkirtTestSuite class
# -----------------------------------------------------------------

## An instance of the SkirtTestSuite class represents a suite of SKIRT test cases, stored as
# a nested structure of files and directories according to a specific layout, and provides facilities to
# perform the tests, verify the results, and prepare a summary test report.
#
# A test suite consists of a set of independent test cases (i.e. test cases can be executed in arbitrary order)
#
# Each test case in a test suite is defined by a collection of files and directories as follows:
#  - a directory with arbitrary name containing all test case files and directories, called the "case directory"
#  - immediately inside the case directory there is:
#    - exactly one ski file with an arbitrary name (with the \c .ski filename extension) specifying the simulation
#      to be performed for the test case
#    - a directory named \c in containing the input files for the simulation, if any
#    - a directory named \c ref containing the reference files for the test, i.e. a copy of the output files
#      generated by a correct simulation run
#    - a directory named \c out to receive the actual output files when the test is performed; this directory
#      and its contents are automatically removed and created when running the test case
#    - everything else is ignored, as long as there are no additional files with a \c .ski filename extension
#
# A test suite is defined by a collection of files and directories as follows:
#  - a directory directly or indirectly containing all test cases, called the "suite directory";
#    a test suite is named after this directory
#  - each ski file directly or indirectly contained in the suite directory defines a test case that
#    must adhere to the description above (no other ski files in the same directory, special directories
#    next to the ski file, etc.)
#
# For example, a test suite may be structured with nested sub-suites as follows (where each \c CaseN directory
# contains a ski file plus \c ref, \c in, and \c out directories):
# \verbatim
# SKIRT Tests
#   SPH simulations
#       Case1
#       Case2
#   Geometries
#     Radial
#         Case1
#         Case2
#     Cilindrical
#         Case1
#         Case2
#         Case3
#     Full 3D
#         Case1
#         Case2
#   Instruments
# \endverbatim
#
# It is also allowed to nest test cases inside another test case, but this is not recommended.
#
class SkirtTestSuite:

    ## The constructor accepts a single argument specifying the path of the suite directory containing the test suite,
    #  including the directory name. The path may be absolute, relative to a user's home folder, or relative to the
    #  current working directory.
    #
    def __init__(self, suitedirpath):
        self._suitedirpath = os.path.realpath(os.path.expanduser(suitedirpath))
        self._suitename = os.path.basename(self._suitedirpath)
        self._doMPI = True

    ## This function performs all tests in the test suite, verifies the results, and prepares a summary test report.
    # It accepts the following arguments:
    # - reportpath: the path where the test report should be placed, \em not including the filename;
    #   if empty or missing the current working directory is used.
    # - skirtpath: the path to the SKIRT executable to be used; this is simply passed to the SkirtExec constructor.
    # - sleepsecs: the time in seconds to sleep before checking for simulation completion again; the default
    #   value is 60 seconds.
    #
    # The paths may be absolute, relative to a user's home folder, or relative to the current working directory.
    #
    def performtests(self, reportpath="", skirtpath="", sleepsecs="60"):
        
        # create skirt execution context
        skirt = SkirtExec()

        # create the logging mechanism
        self._log = Log(reportpath)
        
        # show the path of the test suite and the SKIRT version number
        self._log.info("Starting report for test suite " + self._suitedirpath)
        self._log.info("Using " + skirt.version())
        
        # make an object that keeps track of the number of failed and succeeded simulations
        self._statistics = dict()

        # cleanup the contents of all "out" directories that reside next to a ski file
        for dirpath, dirs, files in os.walk(self._suitedirpath):
            if dirpath.endswith("/out"):
                for skifile in filter(lambda fn: fn.endswith(".ski"), os.listdir(dirpath[:-4])):
                    prefix = skifile[:-4] + "_"
                    for name in filter(lambda fn: fn.startswith(prefix), files):
                        os.remove(os.path.join(dirpath, name))

        # start performing the simulations
        skipattern = os.path.join(self._suitedirpath, "*.ski")
        simulations = skirt.execute(skipattern, recursive=True, inpath="in", outpath="out", skirel=True, \
                                    threads=1, simulations=4, wait=False)

        try:
            devnull = open(os.devnull)
            subprocess.Popen("mpirun", stdout=devnull, stderr=devnull).communicate()
        except:
            self._log.warning("No mpirun executable: skipping MPI test cases!")
            self._doMPI = False
        
        if self._doMPI:
            mpiskirt = SkirtExec()
            MPIpattern = os.path.join(self._suitedirpath, "*_MPI")
            simulations = simulations + mpiskirt.execute(MPIpattern, recursive=True, inpath="in", outpath="out", skirel=True, \
                                        threads=1, simulations=1, wait=False, processes=4)
        
        numsimulations = len(simulations)
        self._log.info("Number of test cases: " + str(numsimulations))

        # verify the results of each simulation, once it finishes (processed items are removed from the list)
        while True:
            for simulation in simulations[:]:
                if simulation.status().endswith("shed"): # "Finished" or "Crashed"
                    self._reportsimulation(simulation)
                    simulations.remove(simulation)
            if len(simulations) == 0 or not skirt.isrunning(): break
            time.sleep(sleepsecs)
        for simulation in simulations:
            self._reportsimulation(simulation)
        skirt.wait()

        # write statistics and close the report file
        self._log.info("Summary for total of: "+ str(numsimulations))
        for key,value in self._statistics.iteritems():
            self._log.info("  " + key + ": " + str(value))
        self._log.info("Finished report for test suite " + self._suitedirpath)

    ## This function verifies and reports on the test result of the given simulation.
    # It writes a line to the console and it updates the statistics.
    def _reportsimulation(self, simulation):
        casedirpath = os.path.dirname(simulation.outpath())
        casename = casedirpath[len(self._suitedirpath)+1:]
        status = simulation.status()
        message = ""
        if status == "Finished":
            message = self._finddifference(casedirpath)
            if message == "":
                status = "Succeeded"
                self._log.success("Test case " + casename + ": succeeded!")
            else:
                status = "Failed"
                self._log.error("Test case " + casename + ": failed - " + message)
        self._statistics[status] = self._statistics.get(status,0) + 1

    ## This function looks for relevant differences between the contents of the output and reference directories
    # of a test case. The test case is specified as an absolute case directory path.
    # The function returns a brief message describing the first relevant difference found, or the empty string
    # if there are no relevant differences.
    def _finddifference(self, casedirpath):
        outpath = os.path.join(casedirpath, "out")
        refpath = os.path.join(casedirpath, "ref")
        if not os.path.isdir(refpath):
            return "Test case has no reference directory"

        # verify list of filenames
        if len(filter(lambda fn: os.path.isdir(fn), os.listdir(outpath))) > 0:
            return "Output contains a directory"
        dircomp = filecmp.dircmp(outpath, refpath, ignore=['.DS_Store'])
        if (len(dircomp.left_only) > 0):
            return "Output contains " + str(len(dircomp.left_only)) + " extra file(s)"
        if (len(dircomp.right_only) > 0):
            return "Output misses " + str(len(dircomp.right_only)) + " file(s)"

        # compare files, focusing on those that aren't trivially equal
        matches, mismatches, errors = filecmp.cmpfiles(outpath, refpath, dircomp.common, shallow=False)
        for filename in mismatches + errors:
            if not equalfiles(os.path.join(outpath, filename), os.path.join(refpath, filename)):
                return "Output file differs: " + filename

        # no relevant differences found
        return ""

# -----------------------------------------------------------------

## This function returns True if the specified files are equal except for irrelevant differences (such as
# time stamps in a file header or prolog), and False otherwise. Since the structure of the allowed differences
# varies with the type of file, this function dispatches the comparison to various other functions depending on
# the last portion of the first filename (i.e a generalized filename extension).
def equalfiles(filepath1, filepath2):
    # don't compare log files because it is too complicated (time & duration differences, changes to messages, ...)
    if filepath1.endswith("_log.txt"): return True

    #  supported file types
    if filepath1.endswith(".fits"): return equalfitsfiles(filepath1, filepath2)
    if filepath1.endswith("_parameters.xml"): return equaltextfiles(filepath1, filepath2, 1)
    if filepath1.endswith("_parameters.tex"): return equaltextfiles(filepath1, filepath2, 2)

    # unsupported file type
    return False

## This function returns True if the specified text files are equal except for time stamp information in
#  a number of lines not larger than \em allowedDiffs, and False otherwise.
def equaltextfiles(filepath1, filepath2, allowedDiffs):
    return equallists(readlines(filepath1), readlines(filepath2), allowedDiffs)

## This function returns True if the specified fits files are equal except for time stamp information in a single
#  header record, and False otherwise.
def equalfitsfiles(filepath1, filepath2):
    return equallists(readblocks(filepath1), readblocks(filepath2), 1)

## This function returns True if the specified lists are equal except for possible time information in
#  a number of items not larger than \em allowedDiffs, and False otherwise.
def equallists(list1, list2, allowedDiffs):
    # the lists must have the same length, which must be at least 2 (to avoid everything being read into 1 line)
    length = len(list1)
    if length < 2 or length != len(list2): return False

    # compare the lists item by item
    diffs = 0
    for index in range(length):
        if list1[index] != list2[index]:
            # verify against allowed number of differences
            diffs += 1
            if diffs > allowedDiffs: return False
            # verify that the differing items are identical up to numerics and months
            pattern = re.compile(r"(\d{1,4}-[0-9a-f]{7,7}(-dirty){0,1})|\d{1,4}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec")
            item1 = re.sub(pattern, "*", list1[index])
            item2 = re.sub(pattern, "*", list2[index])
            if item1 != item2: return False

    # no relevant differences
    return True

# -----------------------------------------------------------------

## This function reads the lines of the specified text file into a list of strings, and returns the list.
def readlines(filepath):
    with open(filepath) as f: result = f.readlines()
    return result

## This function reads blocks of 80 bytes from the specified binary file into a list of strings, and returns the list.
def readblocks(filepath):
    result = []
    with open(filepath) as f:
        while (True):
            block = f.read(80)
            if len(block) == 0: break
            result.append(block)
    return result

# -----------------------------------------------------------------
