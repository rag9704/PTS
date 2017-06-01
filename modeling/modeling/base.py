#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.modeling.base Contains the ModelerBase class, which is the base class for the specific modelers
#  such as the GalaxyModeler, SEDModeler and ImagesModeler.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from abc import ABCMeta, abstractmethod

# Import astronomical modules
from astropy.utils import lazyproperty

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ...core.tools.logging import log, set_log_file, unset_log_file
from ...core.tools import filesystem as fs
from ..fitting.explorer import ParameterExplorer
from ..fitting.sedfitting import SEDFitter
from ..component.component import load_modeling_history, get_config_file_path, load_modeling_configuration
from ...core.launch.synchronizer import RemoteSynchronizer
from ...core.prep.deploy import Deployer
from ..fitting.run import get_generations_table, has_unevaluated_generations, get_unevaluated_generations
from ...core.remote.moderator import PlatformModerator
from ...core.tools import stringify
from ...core.tools.loops import repeat_check
from ...core.remote.remote import Remote
from ..fitting.finisher import ExplorationFinisher
from ...core.tools import time
from ..core.history import commands_after_and_including

# -----------------------------------------------------------------

fitting_methods = ["genetic", "grid"]
default_fitting_method = "genetic"

# -----------------------------------------------------------------

class ModelerBase(Configurable):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        """

        # Call the constructor of the base class
        super(ModelerBase, self).__init__(*args, **kwargs)

        # A timestamp
        self.timestamp = None

        # The path to the modeling directory
        self.modeling_path = None

        # The modeling environment
        self.environment = None

        # The modeling configuration
        self.modeling_config = None

        # Platform moderator
        self.moderator = None

        # The modeling history
        self.history = None

        # Fixed names for the fitting run and the model
        self.fitting_run_name = "run_1"
        self.model_name = "model_a"
        self.representation_name = "highres"

        # Parameter ranges
        self.parameter_ranges = None

        # The parameter explorer instance
        self.explorer = None

        # The SED fitter instance
        self.fitter = None

        # The exploration finisher
        self.finisher = None

        # egege
        self.fixed_initial_parameters = None

        # The fitting method (grid, genetic)
        self.fitting_method = None

    # -----------------------------------------------------------------

    def log_path_for_component(self, cls_or_instance):

        """
        This function ...
        :param cls_or_instance:
        :return:
        """

        command_name = cls_or_instance.command_name()
        log_path = fs.join(self.environment.log_path, command_name + "_" + self.timestamp + ".txt")
        return log_path

    # -----------------------------------------------------------------

    def set_log_path_for_component(self, cls_or_instance):

        """
        This function ...
        :param cls_or_instance:
        :return:
        """

        set_log_file(self.log_path_for_component(cls_or_instance))

    # -----------------------------------------------------------------

    @property
    def grid_fitting(self):

        """
        This function ...
        :return: 
        """

        return self.fitting_method == "grid"

    # -----------------------------------------------------------------

    @property
    def genetic_fitting(self):

        """
        This function ...
        :return: 
        """

        return self.fitting_method == "genetic"

    # -----------------------------------------------------------------

    @property
    def configured_fitting_host_ids(self):

        """
        This function ...
        :return:
        """

        if self.modeling_config.fitting_host_ids is None: return []
        else: return self.modeling_config.fitting_host_ids

    # -----------------------------------------------------------------

    @property
    def has_configured_fitting_host_ids(self):

        """
        This function ...
        :return:
        """

        return len(self.configured_fitting_host_ids) > 0

    # -----------------------------------------------------------------

    @property
    def multiple_generations(self):

        """
        This function ...
        :return:
        """

        return self.config.ngenerations > 1

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(ModelerBase, self).setup(**kwargs)

        # Create timestamp
        self.timestamp = time.filename_timestamp()

        # Set the path to the modeling directory
        self.modeling_path = self.config.path

        # Check for the presence of the configuration file
        if not fs.is_file(get_config_file_path(self.modeling_path)): raise ValueError("The current working directory (" + self.config.path + ") is not a radiative transfer modeling directory (the configuration file is missing)")
        else: self.modeling_config = load_modeling_configuration(self.modeling_path)

        # Set execution platforms
        self.set_platforms()

        # Check the number of generations
        if self.config.ngenerations > 1 and self.moderator.any_remote: raise ValueError("When remote execution is enabled, the number of generations per run can only be one")

        # Load the modeling history
        self.history = load_modeling_history(self.modeling_path)

        # Clear remotes
        if self.config.clear_remotes:
            for host_id in self.moderator.all_host_ids:

                # Inform the user
                log.info("Clearing remote '" + host_id + "' ...")

                # Setup the remote
                remote = Remote()
                if not remote.setup(host_id): log.warning("Could not connect to remote host '" + host_id + "'")

                # Clear temporary data and close sessions
                remote.clear_temp_and_sessions()

        # Deploy SKIRT and PTS
        if self.config.deploy: self.deploy()

        # Set the fitting method
        if "fitting_method" in kwargs: self.fitting_method = kwargs.pop("fitting_method")
        else: self.fitting_method = self.config.fitting_method #self.fitting_method = prompt_string("fitting_method", "fitting method", choices=fitting_methods)

    # -----------------------------------------------------------------

    @property
    def fitting_local(self):

        """
        This function ...
        :return: 
        """

        # If local flag is set
        if self.config.fitting_local: return True

        # Fitting remotes have been set
        elif self.config.fitting_remotes is not None: return True

        # If no host ids have been set
        else: return self.modeling_config.fitting_host_ids is None or self.modeling_config.fitting_host_ids == []

    # -----------------------------------------------------------------

    @property
    def other_local(self):

        """
        This function ...
        :return: 
        """

        # If local flag is set
        if self.config.local: return True

        # Remotes have been set
        elif self.config.remotes is not None: return True

        # If no host ids have been set
        else: return self.modeling_config.host_ids is None or self.modeling_config.host_ids == []

    # -----------------------------------------------------------------

    @property
    def fitting_host_ids(self):

        """
        This function ...
        :return: 
        """

        if self.fitting_local: return None
        elif self.config.fitting_remotes is not None: return self.config.fitting_remotes
        elif self.modeling_config.fitting_host_ids is None: return None
        else: return self.modeling_config.fitting_host_ids

    # -----------------------------------------------------------------

    @property
    def other_host_ids(self):

        """
        This function ...
        :return: 
        """

        if self.config.local: return None
        elif self.config.remotes is not None: return self.config.remotes
        elif self.modeling_config.host_ids is None: return None
        else: return self.modeling_config.host_ids

    # -----------------------------------------------------------------

    def set_platforms(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Determining execution platforms ...")

        # Setup the platform moderator
        self.moderator = PlatformModerator()

        # Set platform(s) for fitting (simulations)
        if self.fitting_local: self.moderator.add_local("fitting")
        else: self.moderator.add_ensemble("fitting", self.fitting_host_ids)

        # Other computations
        if self.other_local: self.moderator.add_local("other")
        else: self.moderator.add_single("other", self.other_host_ids)

        # Run the moderator
        self.moderator.run()

    # -----------------------------------------------------------------

    def deploy(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Deploying SKIRT and PTS ...")

        # Create the deployer
        deployer = Deployer()

        # Set the host ids
        deployer.config.host_ids = self.moderator.all_host_ids

        # Set the host id on which PTS should be installed (on the host for extra computations and the fitting hosts
        # that have a scheduling system to launch the pts run_queue command)
        deployer.config.pts_on = self.moderator.all_host_ids

        # Set
        deployer.config.check = self.config.check_versions

        # Set
        deployer.config.update_dependencies = self.config.update_dependencies

        # Run the deployer
        deployer.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def rerun_commands(self):

        """
        This function ...
        :return:
        """

        if self.config.rerun is None: return []
        else: return commands_after_and_including(self.config.rerun)

    # -----------------------------------------------------------------

    def fit(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Inform the user
        log.info("Fitting radiative transfer models ...")

        # Configure the fitting
        if not self.history.has_configured_fit: self.configure_fit()

        # Initialize the fitting
        if not self.history.has_initialized_fit: self.initialize_fit()

        # If we do multiple generations at once
        if self.multiple_generations: self.fit_multiple(**kwargs)

        # We just do one generation now, or finish
        else: self.fit_single(**kwargs)

    # -----------------------------------------------------------------

    def fit_multiple(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return: 
        """

        # Inform the user
        log.info("Fitting multiple generations at once ...")

        # Start: launch the initial generation
        self.start(**kwargs)

        # Advance: launch generations 0 -> (n-1)
        repeat_check(self.advance, self.config.ngenerations, **kwargs)

        # Finish
        self.finish(**kwargs)

    # -----------------------------------------------------------------

    def fit_single(self, **kwargs):

        """
        This function ...
        :param kwargs: 
        :return: 
        """

        # Inform the user
        log.info("Fitting a single generation ...")

        # Load the generations table
        generations = get_generations_table(self.modeling_path, self.fitting_run_name)

        # If finishing the generation is requested
        if self.config.finish: self.finish(**kwargs)

        # If this is the initial generation
        elif generations.last_generation_name is None: self.start(**kwargs)

        # Advance the fitting with a new generation
        else: self.advance(**kwargs)

    # -----------------------------------------------------------------

    @abstractmethod
    def configure_fit(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def initialize_fit(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def start(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Inform the user
        log.info("Starting with the initial generation ...")

        # Explore
        self.explore(**kwargs)

    # -----------------------------------------------------------------

    def advance(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Inform the user
        log.info("Advancing the fitting with a new generation ...")

        # Load the generations table
        generations = get_generations_table(self.modeling_path, self.fitting_run_name)

        # Check whether there is a generation preceeding this one
        if generations.last_generation_name is None: raise RuntimeError("Preceeding generation cannot be found")

        # Debugging
        log.debug("Previous generation: " + generations.last_generation_name)

        # If some generations have not finished, check the status of and retrieve simulations
        if generations.has_unfinished and self.has_configured_fitting_host_ids: self.synchronize()

        # Debugging
        if generations.has_finished: log.debug("There are finished generations: " + stringify.stringify(generations.finished_generations)[1])
        if has_unevaluated_generations(self.modeling_path, self.fitting_run_name): log.debug("There are unevaluated generations: " + stringify.stringify(get_unevaluated_generations(self.modeling_path, self.fitting_run_name))[1])

        # If some generations have finished, fit the SED
        if generations.has_finished and has_unevaluated_generations(self.modeling_path, self.fitting_run_name): self.fit_sed()

        # If all generations have finished, explore new generation of models
        if generations.all_finished:

            # Explore a new generation
            self.explore(**kwargs)
            return True

        # Return False if exploration could not be performed (not all generations had finished)
        else: return False

    # -----------------------------------------------------------------

    def synchronize(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Synchronizing with the remotes (retrieving and analysing finished models) ...")

        # Create the remote synchronizer
        synchronizer = RemoteSynchronizer()

        # Set the host IDs
        synchronizer.config.host_ids = self.modeling_config.fitting_host_ids

        # Run the remote synchronizer
        synchronizer.run()

    # -----------------------------------------------------------------

    def fit_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fitting the SED to the finished generations ...")

        # Configuration settings
        config = dict()
        config["name"] = self.fitting_run_name

        # Create the SED fitter
        self.fitter = SEDFitter(config)

        # Set log path
        self.set_log_path_for_component(self.fitter)

        # Run the fitter
        with self.history.register(self.fitter): self.fitter.run()

        # Unset log path
        unset_log_file()

    # -----------------------------------------------------------------

    def explore(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Exploring the parameter space ...")

        # Configuration settings
        config = dict()
        config["name"] = self.fitting_run_name

        # Set flags
        if self.moderator.ensemble_is_local("fitting"):
            config["record_timing"] = False
            config["record_memory"] = False
        else:
            config["record_timing"] = True
            config["record_memory"] = True

        # Create the parameter explorer
        self.explorer = ParameterExplorer(config, cwd=self.modeling_path)

        # Set the working directory
        self.explorer.config.path = self.modeling_path

        # Set the remote host IDs
        self.explorer.config.remotes = self.moderator.host_ids_for_ensemble("fitting")
        self.explorer.config.attached = self.config.fitting_attached

        # Set the number of generations
        #if self.config.ngenerations is not None: explorer.config.ngenerations = self.config.ngenerations
        # NO: THIS ALWAYS HAVE TO BE ONE: BECAUSE HERE IN THIS CLASS WE ALREADY USE REPEAT(SELF.ADVANCE)
        # IF NGENERATIONS > 1, THE CONTINUOUSOPTIMIZER IS USED INSTEAD OF THE STEPWISEOPTIMIZER
        self.explorer.config.ngenerations = 1

        # Set the number of simulations per generation
        if self.config.nsimulations is not None: self.explorer.config.nsimulations = self.config.nsimulations

        # Set other settings
        self.explorer.config.npackages_factor = self.config.npackages_factor
        self.explorer.config.increase_npackages = self.config.increase_npackages
        #explorer.config.refine_wavelengths = self.config.refine_wavelengths
        self.explorer.config.refine_spectral = self.config.refine_spectral
        #explorer.config.refine_dust = self.config.refine_dust
        self.explorer.config.refine_spatial = self.config.refine_spatial
        self.explorer.config.selfabsorption = self.config.selfabsorption
        self.explorer.config.transient_heating = self.config.transient_heating

        # Set the input
        input_dict = dict()
        if self.parameter_ranges is not None: input_dict["ranges"] = self.parameter_ranges

        # Add the fixed parameter values
        if self.fixed_initial_parameters is not None: input_dict["fixed_initial_parameters"] = self.fixed_initial_parameters

        # NEW: Add additional input (such as parameter grid scales)
        input_dict.update(kwargs)

        # Set log path
        self.set_log_path_for_component(self.explorer)

        # Run the parameter explorer
        with self.history.register(self.explorer): self.explorer.run(**input_dict)

        # Unset log path
        unset_log_file()

    # -----------------------------------------------------------------

    def finish(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Inform the user
        log.info("Finishing the parameter exploration ...")

        # Configuration settings
        settings = dict()
        settings["name"] = self.fitting_run_name

        # Set the input
        input_dict = dict()

        # Create the exploration finisher
        self.finisher = ExplorationFinisher(settings)

        # NEW: Add additional input (such as parameter grid scales)
        input_dict.update(kwargs)

        # Set log path
        self.set_log_path_for_component(self.finisher)

        # Run the finisher
        with self.history.register(self.finisher): self.finisher.run(**input_dict)

        # Unset log path
        unset_log_file()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

# -----------------------------------------------------------------
