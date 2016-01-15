import os

from jinja2 import Template


def render(source, context):
    """
    
    :param source:
    :param context:
    :return:
    """

    temp = Template(source)
    temp.env.filters['exists'] = os.path.exists
    return temp.render(context)
