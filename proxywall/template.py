from jinja2 import Template


def render(source, context):
    """
    
    :param source:
    :param context:
    :return:
    """
    _template = Template(source)
    return _template.render(context)
