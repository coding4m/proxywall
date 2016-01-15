import os

from jinja2 import Environment


def render(source, context):
    """
    
    :param source:
    :param context:
    :return:
    """

    env = Environment()
    env.filters['exists'] = os.path.exists
    return env.from_string(source=source).render(context)
