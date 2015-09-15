"""
This module handles accessing, storing, and managing the graph reference.

"""
from __future__ import absolute_import

import json
import re
import requests

from plotly import exceptions, files, utils

GRAPH_REFERENCE_PATH = '/plot-schema.json'

# for backwards compat, we need to add a few class names
_BACKWARDS_COMPAT_CLASS_NAME_TO_OBJECT_NAME = {
    'AngularAxis': 'angularaxis',
    'ColorBar': 'colorbar',
    'Area': 'scatter',
    'Font': 'textfont',
    'Histogram2dContour': 'histogram2dcontour',
    'RadialAxis': 'radialaxis',
    'XAxis': 'xaxis',
    'XBins': 'xbins',
    'YAxis': 'yaxis',
    'YBins': 'ybins',
    'ZAxis': 'zaxis'
}


def get_graph_reference():
    """
    Attempts to load local copy of graph reference or makes GET request if DNE.

    :return: (dict) The graph reference.
    :raises: (PlotlyError) When graph reference DNE and GET request fails.

    """
    if files.check_file_permissions():
        graph_reference = utils.load_json_dict(files.GRAPH_REFERENCE_FILE)
        config = utils.load_json_dict(files.CONFIG_FILE)
        plotly_domain = config['plotly_domain']
    else:
        graph_reference = {}
        plotly_domain = files.FILE_CONTENT[files.CONFIG_FILE]['plotly_domain']

    if not graph_reference:

        graph_reference_url = plotly_domain + GRAPH_REFERENCE_PATH

        try:
            response = requests.get(graph_reference_url)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            raise exceptions.PlotlyError(
                "The schema used to validate Plotly figures has never been "
                "downloaded to your computer. You'll need to connect to a "
                "Plotly server at least once to do this.\n"
                "You're seeing this error because the attempt to download "
                "the schema from '{}' failed.".format(graph_reference_url)
            )

        # TODO: Hash this so we don't have to load it every time. The server
        #       will need to accept a hash query param as well.
        graph_reference = json.loads(response.content)

    return utils.decode_unicode(graph_reference)


def string_to_class_name(string):
    """
    Single function to handle turning object names into class names.

    GRAPH_REFERENCE has names like `error_y`, which we'll turn into `ErrorY`.

    :param (str) string: Presumably an object_name from GRAPH_REFERENCE.
    :return: (str)

    """

    # capitalize first letter
    string = re.sub(r'[A-Za-z]', lambda m: m.group().title(), string, count=1)

    # replace `*_<c>` with `*<C>` E.g., `Error_x` --> `ErrorX`
    string = re.sub(r'_[A-Za-z]+', lambda m: m.group()[1:].title(), string)

    return string



def _get_objects():
    """
    Return the main dict that we'll work with for graph objects.

    This maps object names to paths inside GRAPH_REFERENCE. If the object
    doesn't have a path, no path is associated and methods are provided to look
    the object up *by name*.

    :return: (dict)

    """
    objects = {}
    for object_path in OBJECT_PATHS:

        name = object_path[-1]
        value = utils.get_by_path(GRAPH_REFERENCE, object_path)

        if value.get('_isLinkedToArray', False):
            item_name = name[:-1]
            if item_name not in objects:
                objects[item_name] = []
            objects[item_name].append(object_path)

        if name not in objects:
            objects[name] = []
        objects[name].append(object_path)

    objects.update({trace_name: [] for trace_name in TRACE_NAMES})
    objects.update(figure=[], data=[], layout=[])

    return objects


def _get_class_names_to_object_names():
    """
    We eventually make classes out of the objects in GRAPH_REFERENCE.

    :return: (dict) A mapping of class names to object names.

    """
    class_names_to_object_names = {}
    for object_name in OBJECTS:
        class_name = string_to_class_name(object_name)
        class_names_to_object_names[class_name] = object_name

    for class_name in _BACKWARDS_COMPAT_CLASS_NAME_TO_OBJECT_NAME:
        object_name = _BACKWARDS_COMPAT_CLASS_NAME_TO_OBJECT_NAME[class_name]
        class_names_to_object_names[class_name] = object_name

    return class_names_to_object_names


# The ordering here is important.
GRAPH_REFERENCE = get_graph_reference()
TRACE_NAMES = GRAPH_REFERENCE['traces'].keys()
OBJECT_PATHS = [path for node, path in utils.node_generator(GRAPH_REFERENCE)
                if node.get('role') == 'object']
OBJECTS = _get_objects()
CLASS_NAMES_TO_OBJECT_NAMES = _get_class_names_to_object_names()
