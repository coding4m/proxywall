from jinja2 import Template


def render(source, context):
    """
    
    :param source:
    :param context:
    :return:
    """
    return Template(source).render(context)
