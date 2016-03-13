#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.interpolate Interpolate an image within regions defined by the user.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant AstroMagic classes and modules
from pts.magic.misc.imageimporter import ImageImporter
from pts.magic.tools import interpolation
from pts.magic.core.frame import Frame
from pts.magic.basics.mask import Mask
from pts.magic.basics.region import Region
from pts.core.tools import logging, time, filesystem

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument("image", type=str, help="the name of the input image")
parser.add_argument("region", type=str, help="the name of the region file over which to interpolate")
parser.add_argument("--mask", action="store_true", help="write out the mask")
parser.add_argument("--color", type=str, help="only interpolate over the shapes with this color")
parser.add_argument("--ignore_color", type=str, help="ignore shapes with this particular color")
parser.add_argument('--report', action='store_true', help='write a report file')
parser.add_argument("-i", "--input", type=str, help="the name of the input directory")
parser.add_argument("-o", "--output", type=str, help="the name of the output directory")
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# If an input directory is given
if arguments.input is not None:

    # Determine the full path to the input directory
    input_path = filesystem.absolute(arguments.input)

    # Give an error if the input directory does not exist
    if not filesystem.is_directory(input_path): raise argparse.ArgumentError(input_path, "The input directory does not exist")

# If no input directory is given, assume the input is placed in the current working directory
else: input_path = filesystem.cwd()

# -----------------------------------------------------------------

# If an output directory is given
if arguments.output is not None:
    
    # Determine the full path to the output directory
    output_path = filesystem.absolute(arguments.output)
    
    # Create the directory if it does not yet exist
    if not filesystem.is_directory(output_path): filesystem.create_directory(output_path)

# If no output directory is given, place the output in the current working directory
else: output_path = filesystem.cwd()

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = filesystem.join(output_path, time.unique_name("log") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.info("Starting interpolate ...")

# -----------------------------------------------------------------

# Inform the user
log.info("Loading the image ...")

# Determine the full path to the image
image_path = filesystem.absolute(arguments.image)

# Import the image
importer = ImageImporter()
importer.run(image_path)

# Get the primary image frame
frame = importer.image.frames.primary

# Get the original header
header = importer.image.original_header

# -----------------------------------------------------------------

# Inform the user
log.info("Loading the region ...")

# Load in the region
region_path = filesystem.join(input_path, arguments.region)
region = Region.from_file(region_path, only=["circle", "ellipse", "polygon"], color=arguments.color, ignore_color=arguments.ignore_color)

# Inform the user
log.info("Creating a mask from the region ...")

# Create a mask from the region
mask = region.to_mask(frame.xsize, frame.ysize)

#plotting.plot_box(mask)

# Inform the user
log.info("Interpolating the frame within the masked pixels ...")

# Create a mask of the pixels that are NaNs
nans = Mask.is_nan(frame)

# Set the NaN pixels to zero in the frame
frame[nans] = 0.0

# Interpolate the frame in the masked pixels
data = interpolation.inpaint_biharmonic(frame, mask)
new_frame = Frame(data)

# Set the original NaN pixels back to NaN
new_frame[nans] = float("nan")

# Inform the user
log.info("Saving the result ...")

# Save the result
path = filesystem.join(output_path, arguments.image)
new_frame.save(path, header=header)

# Write the mask
if arguments.mask:

    path = filesystem.join(output_path, "mask.fits")
    new_frame[mask] = float('nan')
    new_frame.save(path, header=header)

# -----------------------------------------------------------------
