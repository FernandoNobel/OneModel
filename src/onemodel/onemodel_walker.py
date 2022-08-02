from importlib_resources import files
import tatsu
from tatsu.walkers import NodeWalker
from onemodel.onemodel import OneModel
from onemodel.objects.parameter import Parameter
from onemodel.objects.species import Species
from onemodel.objects.reaction import Reaction

class OneModelWalker(NodeWalker):

    numberOfUnnamedReactions = 0
    numberOfUnnamedRules = 0
    
    def __init__(self):
        self.onemodel = OneModel()

        grammar = files("onemodel").joinpath("onemodel.ebnf").read_text()
        self.parser = tatsu.compile(grammar, asmodel=True)

    def run(self, onemodel_code):

        ast = self.parser.parse(onemodel_code)
        result = self.walk(ast)

        return result, ast

    def walk_Parameter(self, node):
        namespace, name = self.walk(node.name)
        value = self.walk(node.value)
        documentation = self.walk(node.documentation)

        namespace[name] = Parameter()

        if value:
            namespace[name]["value"] = value

        if documentation:
            namespace[name]["__doc__"] = documentation

    def walk_Species(self, node):
        namespace, name = self.walk(node.name)
        value = self.walk(node.value)
        documentation = self.walk(node.documentation)

        namespace[name] = Species()

        if value:
            namespace[name]["value"] = value

        if documentation:
            namespace[name]["__doc__"] = documentation

    def walk_Reaction(self, node):
        namespace, name = self.walk(node.name)

        namespace[name] = Reaction()

    def walk_AssignName(self, node):
        namespace, name = self.walk(node.name)
        value = self.walk(node.value)

        namespace[name] = value

    def walk_AccessName(self, node):
        namespace, name = self.walk(node.name)

        return namespace[name]

    def walk_DottedName(self, node):
        qualifiers = node.qualifiers
        namespace = self.onemodel

        for qualifier in qualifiers:
            namespace = namespace[qualifier]

        return namespace, node.name

    def walk_Float(self, node):
        return float(node.value)

    def walk_Integer(self, node):
        return int(node.value)

    def walk_Docstring(self, node):
        text = str(node.value)
        lines = text.split("\n")
        result = "\n".join(line.strip() for line in lines)  
        return result
    
    def walk_String(self, node):
        return str(node.value)

    def walk_list(self, nodes):
        """Walk every object in a list. 
        
        Notes
        -----
        If we don't implement this method, the walker will not
        evaluate list nodes.
        """
        results = []

        for node in nodes:
            results.append(self.walk(node))

        return results

    def walk_tuple(self, nodes):
        return self.walk_list(nodes)
