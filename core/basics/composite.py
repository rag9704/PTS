#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.composite Contains the SimplePropertyComposite class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import copy
import warnings
from abc import ABCMeta

# Import the relevant PTS classes and modules
from ..tools import parsing
from ..basics.log import log
from ..tools import formatting as fmt
from ..tools.stringify import stringify, tostr
from .map import Map

# -----------------------------------------------------------------

class SimplePropertyComposite(object):

    """
    This class ...
    @DynamicAttrs
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self):

        """
        This function ...
        """

        # The path
        self._path = None

        # The descriptions
        self._descriptions = dict()

        # The parsing types
        self._ptypes = dict()

        # The choices
        self._choices = dict()

    # -----------------------------------------------------------------

    def add_property(self, name, ptype, description, default_value=None, choices=None):

        """
        This function ...
        :param name:
        :param ptype:
        :param description:
        :param default_value:
        :param choices:
        :return:
        """

        # Check
        if hasattr(self, name): raise ValueError("A property with the name '" + name + "' already exists")

        # Check
        if " " in name: raise ValueError("Name cannot contain spaces")

        # Set the ptype
        self._ptypes[name] = ptype

        # Set the description
        self._descriptions[name] = description

        # Set the choices
        self._choices[name] = choices

        # Set the attribute with the default value
        setattr(self, name, default_value)

    # -----------------------------------------------------------------

    def add_integer_property(self, name, description, default_value=None, choices=None):

        """
        This function ...
        :param name:
        :param description:
        :param default_value:
        :param choices:
        :return:
        """

        self.add_property(name, "integer", description, default_value=default_value, choices=choices)

    # -----------------------------------------------------------------

    def add_real_property(self, name, description, default_value=None, choices=None):

        """
        This function ...
        :param name:
        :param description:
        :param default_value:
        :param choices:
        :return:
        """

        self.add_property(name, "real", description, default_value=default_value, choices=choices)

    # -----------------------------------------------------------------

    def add_string_property(self, name, description, default_value=None, choices=None):

        """
        This function ...
        :param name:
        :param description:
        :param default_value:
        :param choices:
        :return:
        """

        self.add_property(name, "string", description, default_value=default_value, choices=choices)

    # -----------------------------------------------------------------

    def add_boolean_property(self, name, description, default_value=None, choices=None):

        """
        This function ...
        :param name:
        :param description:
        :param default_value:
        :param choices:
        :return:
        """

        self.add_property(name, "boolean", description, default_value=default_value, choices=choices)

    # -----------------------------------------------------------------

    def add_section(self, name, description, dynamic=False):

        """
        This function ...
        :param name:
        :param description:
        :param dynamic:
        :return:
        """

        # Set the description
        self._descriptions[name] = description

        # Set an attribute that is a nested SimplePropertyComposite (or a Map)
        if dynamic: self.__dict__[name] = Map() #setattr(self, name, Map())
        else: self.__dict__[name] = SimplePropertyComposite() #setattr(self, name, SimplePropertyComposite())

    # -----------------------------------------------------------------

    @property
    def sections(self):

        """
        This function ...
        :return:
        """

        sections_dict = dict()
        for name in self.section_names:
            sections_dict[name] = getattr(self, name)
        return sections_dict

    # -----------------------------------------------------------------

    def __setattr__(self, name, value):

        """
        This function ...
        :param name:
        :param value:
        :return:
        """

        # Hidden variable
        if name.startswith("_"):
            self.__dict__[name] = value
            return

        if value is None: pass
        elif isinstance(value, SimplePropertyComposite): assert name in self._descriptions
        elif isinstance(value, Map):
            assert name in self._descriptions
            #print(value)
            #print(getattr(self, name))
            #print(name in self.__dict__)
            for key in value:
                keyvalue = value[key]
                #print(self.__dict__)
                self.__dict__[name].__setattr__(key, keyvalue)
            return
        else:

            # Check the type
            #print(value, type(value), hasattr(value, "__array__"))
            ptype, string = stringify(value)

            # None value
            if string == "None": value = None

            # Actual value
            else:

                # Check
                if name not in self._ptypes: raise AttributeError("A " + self.__class__.__name__ + " object has no attribute '" + name + "'")

                # Try converting the string back to the type it actually needs to be
                the_type = self._ptypes[name]
                parsing_function = getattr(parsing, the_type)
                try: value = parsing_function(string)
                except ValueError: raise ValueError("The value of '" + str(value) + "' for '" + name +  "' given is of the wrong type: '" + ptype + "', must be '" + the_type + "' (value is " + string + ")")

        # Set the attribute
        self.__dict__[name] = value

    # -----------------------------------------------------------------

    def set_properties(self, properties):

        """
        This function ...
        :param properties:
        :return:
        """

        # Loop over all the options defined in the 'options' dictionary
        for name in properties:

            # Check whether an option with this name exists in this class
            if hasattr(self, name):

                # Check if the option is composed of other options (a Map), or if it is just a simple variable
                #if isinstance(getattr(self, name), Map):
                if isinstance(getattr(self, name), SimplePropertyComposite):

                    assert isinstance(properties[name], dict)  # dict, or Map (is derived from dict)
                    getattr(self, name).set_properties(properties[name])

                # If it is a simple variable, just use setattr to set the attribute of this class
                else: setattr(self, name, properties[name])

            # If the option does not exist, ignore it but give a warning
            else: warnings.warn("The property '" + name + "' does not exist")

    # -----------------------------------------------------------------

    @classmethod
    def from_dict(cls, dictionary):

        """
        This function ...
        :param dictionary
        :return:
        """

        # Create a new instance
        composite = cls()

        # Set the properties from the dictionary
        composite.set_properties(dictionary)

        # Return the new property composite
        return composite

    # -----------------------------------------------------------------

    @property
    def all_names(self):

        """
        This function ...
        :return:
        """

        names = []
        for name in vars(self):

            # Skip internal variables
            if name.startswith("_"): continue

            # Add the name
            names.append(name)

        # Return the names
        return names

    # -----------------------------------------------------------------

    @property
    def property_names(self):

        """
        This function ...
        :return:
        """

        names = []
        for name in vars(self):

            # Skip internal variables
            if name.startswith("_"): continue

            if name not in self._ptypes:
                if not (isinstance(getattr(self, name), SimplePropertyComposite) or isinstance(getattr(self, name), Map)): raise Exception("Property '" + name + "' doesn't have its type defined")
                else: continue

            # Add the name
            names.append(name)

        # Return the names
        return names

    # -----------------------------------------------------------------

    @property
    def section_names(self):

        """
        This function ...
        :return:
        """

        names = []
        for name in vars(self):

            # Skip internal
            if name.startswith("_"): continue

            # Skip simple properties
            if name in self._ptypes: continue

            # Should be composite
            if not (isinstance(getattr(self, name), SimplePropertyComposite) or isinstance(getattr(self, name), Map)): raise Exception("Property '" + name + "' doesn't have its type defined")

            # Add the name
            names.append(name)

        # Return the names
        return names

    # -----------------------------------------------------------------

    @property
    def property_types(self):

        """
        This function ...
        :return:
        """

        types = []
        for name in self.property_names:

            # Get the type
            ptype = self._ptypes[name]
            types.append(ptype)

        # Return the types
        return types

    # -----------------------------------------------------------------

    def type_for_property(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return self._ptypes[name]

    # -----------------------------------------------------------------

    @property
    def property_units(self):

        """
        This function ...
        :return:
        """

        units = []
        for name in self.property_names:

            # Get the value
            value = getattr(self, name)

            # Check whether there is a unit
            if hasattr(value, "unit"): unit = value.unit
            else: unit = None

            # Add the unit
            units.append(unit)

        # Return the list of units
        return units

    # -----------------------------------------------------------------

    def unit_for_property(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        # Get the value
        value = getattr(self, name)

        # Check whether there is a unit
        if hasattr(value, "unit"): unit = value.unit
        else: unit = None

        # Return the unit
        return unit

    # -----------------------------------------------------------------

    @property
    def property_descriptions(self):

        """
        This function ...
        :return:
        """

        descriptions = []
        for name in self.property_names:

            # Get the description
            description = self._descriptions[name]
            descriptions.append(description)

        # Return the descriptions
        return descriptions

    # -----------------------------------------------------------------

    def description_for_property(self, name):

        """
        This function ...
        """

        return self._descriptions[name]

    # -----------------------------------------------------------------

    def get_properties(self):

        """
        This function ...
        :return:
        """

        properties = dict()
        for name in vars(self):

            # Skip internal variables
            if name.startswith("_"): continue

            # Set property
            properties[name] = getattr(self, name)

        # Return the properties as a dictionary
        return properties

    # -----------------------------------------------------------------

    def __repr__(self):

        """
        This function ...
        :return:
        """

        lines = []

        # The simple properties
        for name in self.property_names:

            dtype, value = stringify(getattr(self, name))
            line = " - " + fmt.bold + name + fmt.reset + ": " + value
            lines.append(line)

        # Sections
        for name in self.section_names:

            line = " - " + fmt.bold + name + fmt.reset + ":"
            lines.append(line)
            if isinstance(getattr(self, name), SimplePropertyComposite): section_lines = ["    " + line for line in repr(getattr(self, name)).split("\n")]
            elif isinstance(getattr(self, name), Map):
                section_lines = []
                section = getattr(self, name)
                for key in section:
                    line = "    " + " - " + fmt.bold + key + fmt.reset + ": " + tostr(section[key])
                    section_lines.append(line)
            else: raise ValueError("Unknown type for section: " + str(type(getattr(self, name))))
            lines += section_lines

        # Return
        return "\n".join(lines)

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.debug("Loading " + cls.__name__ + " from " + path + " ...")

        properties = dict()

        with open(path, 'r') as f:

            for line in f:

                if "Type:" in line: continue

                line = line[:-1]
                if not line: continue

                name, rest = line.split(": ")
                value, dtype = rest.split(" [")
                dtype = dtype.split("]")[0]

                # Set the property value
                if dtype == "None" or value.strip() == "None": properties[name] = None
                else: properties[name] = getattr(parsing, dtype)(value)

            # TODO: sections!!

        # Create the class instance
        composite = cls(**properties)

        # Set the path
        composite._path = path

        # Return
        return composite

    # -----------------------------------------------------------------

    def save(self):

        """
        This function ...
        :return:
        """

        # Check whether the path is valid
        if self._path is None: raise RuntimeError("The path is not defined")

        # Save
        self.saveto(self._path)

    # -----------------------------------------------------------------

    def saveto(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Inform the user
        log.info("Saving the " + self.__class__.__name__ + " to " + path + " ...")

        # Write the properties
        with open(path, 'w') as fh:

            # Print the type
            print("Type:", self.__class__.__name__, file=fh)

            # Loop over the properties
            for name in self.property_names:

                dtype, value = stringify(getattr(self, name))
                actual_dtype = self._ptypes[name]
                print(name + ":", value + " [" + actual_dtype + "]", file=fh)

            # TODO: sections!!

        # Update the path
        self._path = path

    # -----------------------------------------------------------------

    def as_tuples(self):

        """
        This function ...
        :return:
        """

        tuples = []

        for name in self.property_names:
            value = getattr(self, name)
            tuples.append((name, value))

        for name in self.section_names:
            value = getattr(self, name)
            tuples.append((name, value.as_tuples()))

        # Retunr the tuples
        return tuples

    # -----------------------------------------------------------------

    def copy(self):

        """
        This function ...
        :return:
        """

        return copy.deepcopy(self)

# -----------------------------------------------------------------
