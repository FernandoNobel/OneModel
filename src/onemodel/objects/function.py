from onemodel.objects.base_function import BaseFunction

class Function (BaseFunction):
    """ Functions that are implemented with OneModel code.

    Parameters
    ----------
    argument_names : :obj:`list` of :obj:`str`
        Names of the arguments.
    body : :obj:`function`
        The OneModel code.
    """

    def execute(self, scope):
        """ Run the builtin function given the scope. """
        # result = self["body"](scope)
        # return result
