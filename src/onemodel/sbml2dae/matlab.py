from tokenize import tokenize, NAME, OP, ENCODING
from io import BytesIO

from onemodel.sbml2dae.dae_model import DaeModel, StateType

class Matlab:
    """ Takes a DAE model as input and exports a matlab implementation.
    """
    def __init__(self, dae, output_path):
        """ Inits Matlab.
        """
        self.dae = dae
        self.output_path = output_path

    def exportExample(self):
        """ Generate an example driver script.
        """
        filepath = self.output_path
        filepath += '/'
        filepath += self.dae.getModelName()
        filepath += '_example.m'

        # Create and open the file to export.
        f = open(filepath, "w")

        # Function header.
        name = self.dae.getModelName() 
        f.write(f'%% Example driver script for simulating "{name}" model.\n')
        self.writeWarning(f)

        # Clear and close all.
        f.write(f'clear all;\n')
        f.write(f'close all;\n')

        f.write(f'\n% Init model.\n')
        f.write(f'm = {name}();\n')

        # Solver options.
        f.write(f'\n% Solver options.\n')
        f.write(f"opt = odeset('AbsTol',1e-8,'RelTol',1e-8);\n")
        f.write(f"opt = odeset(opt,'Mass',m.M);\n")

        # Simulation time span.
        f.write(f'\n% Simulation time span.\n')
        f.write(f'tspan = [m.opts.t_init m.opts.t_end];\n')

        # Simulate.
        f.write(f'\n[t,x] = ode15s(@(t,x) m.ode(t,x,m.p),tspan,m.x0,opt);\n')
        f.write(f'out = m.simout2struct(t,x,m.p);\n')
        
        # Plot.
        f.write(f'\n% Plot result.\n')
        f.write(f'plot(t,x);\n')
        f.write(f'grid on;\n')
        # TODO: Add a legend.


        f.close()

        return filepath

    def exportClass(self):
        """ Export daeModel into a Matlab class.
        """
        filepath = self.output_path
        filepath += '/'
        filepath += self.dae.getModelName()
        filepath += '.m'

        # Create and open the file to export.
        f = open(filepath, "w")

        self.writeClassHeader(f)
        self.writeConstructor(f)
        self.writeDefaultParameters(f)
        self.writeInitialConditions(f)
        self.writeMassMatrix(f)
        self.writeSimulationOptions(f)
        self.writeOde(f)
        self.writeSimout2Struct(f)

        f.write(f'\tend\n')
        f.write(f'end\n')

        return filepath

    def writeClassHeader(self, f):
        """ Write into file the header of the class file.
        """
        # Function header.
        f.write(f'classdef {self.dae.getModelName()}\n')
        self.writeWarning(f, 1)

        # Write the properties.
        f.write(f'\tproperties\n')
        f.write(f'\t\tp      % Default model parameters.\n')
        f.write(f'\t\tx0     % Default initial conditions.\n')
        f.write(f'\t\tM      % Mass matrix for DAE systems.\n')
        f.write(f'\t\topts   % Simulation options.\n')
        f.write(f'\tend\n')
        f.write(f'\n')

        # Write the methods.
        f.write(f'\tmethods\n')

    def writeWarning(self, f, tab=0):
        """ Write warning comment into f.
        """
        tab = '\t'*tab

        f.write(f'{tab}% This file was automatically generated by OneModel.\n')
        f.write(
            f'{tab}% Any changes you make to it will be overwritten the next time\n'
        )
        f.write(f'{tab}% the file is generated.\n\n')

    def writeConstructor(self, f):
        """ Write class constructor into f.
        """
        f.write(f'\t\tfunction obj = {self.dae.getModelName()}()\n')
        f.write(f'\t\t\t%% Constructor of {self.dae.getModelName()}.\n')
        f.write(f'\t\t\tobj.p    = obj.default_parameters();\n')
        f.write(f'\t\t\tobj.x0   = obj.initial_conditions();\n')
        f.write(f'\t\t\tobj.M    = obj.mass_matrix();\n')
        f.write(f'\t\t\tobj.opts = obj.simulation_options();\n')
        f.write(f'\t\tend\n')
        f.write(f'\n')

    def writeDefaultParameters(self, f):
        """ Write method which returns default parameters.
        """
        f.write(f'\t\tfunction p = default_parameters(~)\n')
        f.write(f'\t\t\t%% Default parameters value.\n')
        f.write(f'\t\t\tp = [];\n')
        for item in self.dae.getParameters():
            f.write(f'\t\t\tp.{item["id"]} = {item["value"]};\n')
        f.write(f'\t\tend\n')
        f.write(f'\n')

    def writeInitialConditions(self, f):
        """ Write method which returns default initial conditions.
        """
        f.write(f'\t\tfunction x0 = initial_conditions(~)\n')
        f.write(f'\t\t\t%% Default initial conditions.\n')

        f.write(f'\t\t\tx0 = [\n')
        for item in self.dae.getStates():
            if item['type'] == StateType.ODE:
                f.write(
                    f'\t\t\t\t{item["initialCondition"]} % {item["id"]}\n'
                )
            elif item['type'] == StateType.ALGEBRAIC:
                f.write(
                    f'\t\t\t\t{item["initialCondition"]} % {item["id"]} (algebraic)\n'
                )
        f.write(f'\t\t\t];\n')

        f.write(f'\t\tend\n')
        f.write(f'\n')

    def writeMassMatrix(self,f):
        """ Write method which returns the mass matrix.
        """
        f.write(f'\t\tfunction M = mass_matrix(~)\n')
        f.write(f'\t\t\t%% Mass matrix for DAE systems.\n')

        f.write(f'\t\t\tM = [\n')
        M = []
        for item in self.dae.getStates():
            if item['type'] == StateType.ODE:
                M.append(1)
            elif item['type'] == StateType.ALGEBRAIC:
                M.append(0)

        i = 0
        i_max = len(M)
        while i < i_max:
            f.write('\t\t\t\t')
            f.write('0 '*i)
            f.write(f'{M[i]} ')
            f.write('0 '*(i_max-i-1))
            f.write('\n')
            i += 1

        f.write(f'\t\t\t];\n')

        f.write(f'\t\tend\n')
        f.write(f'\n')

    def writeSimulationOptions(self, f):
        """ Write method which returns the mass matrix.
        """
        f.write(f'\t\tfunction opts = simulation_options(~)\n')
        f.write(f'\t\t\t%% Default simulation options.\n')

        options = self.dae.getOptions()
        for item in options:
            value = options.get(item, None)
            f.write(f'\t\t\topts.{item} = {value};\n')

        f.write(f'\t\tend\n')
        f.write(f'\n')

    def writeLocalStates(self, f):
        """ Write all the states as local variables in the method.
        """
        # List of states that are already defined in the file.
        known_states = []
        states_num = len(self.dae.getStates())

        # Write ODE and ALGEBRAIC states.
        f.write(f'\t\t\t% ODE and algebraic states:\n')
        i = 1
        for state in self.dae.getStates():
            # Skip not ODE or ALGEBRAIC states.
            if not state['type'] in (StateType.ODE, StateType.ALGEBRAIC):
                continue

            f.write(f'\t\t\t{state["id"]} = x({i},:);\n')
            known_states.append(state['id'])
            i += 1
        f.write(f'\n')

        f.write(f'\t\t\t% Assigment states:\n')

        while len(known_states) != states_num:
            for state in self.dae.getStates():
                # Skip not ASSIGMENT states.
                if not state['type'] == StateType.ASSIGMENT:
                    continue

                # Skipe states that are already defined.
                if state in known_states:
                    continue

                dependencies = self.getStates(state['equation'])

                if all(elem in known_states for elem in dependencies):
                    equation = self.string2matlab(state['equation'])
                    f.write(f'\t\t\t{state["id"]} = {equation};\n')
                    known_states.append(state['id'])

        f.write(f'\n')

    def writeOde(self, f):
        """ Write method which evaluates the ODE.
        """
        f.write(f'\t\tfunction dx = ode(~,t,x,p)\n')
        f.write(f'\t\t\t%% Evaluate the ODE.\n')
        f.write(f'\t\t\t%\n')

        # Comment arguments.
        f.write(f'\t\t\t% Args:\n')
        f.write(f'\t\t\t%\t t Current time in the simulation.\n')
        f.write(f'\t\t\t%\t x Array with the state value.\n')
        f.write(f'\t\t\t%\t p Struct with the parameters.\n')
        f.write(f'\t\t\t%\n')

        # Comment return.
        f.write(f'\t\t\t% Return:\n')
        f.write(f'\t\t\t%\t dx Array with the ODE.\n')
        f.write(f'\n')

        self.writeLocalStates(f)
       
        # Generate ODE equations.
        i = 1
        for item in self.dae.getStates():
            string = f'\t\t\t% der({item["id"]})\n'

            if item['type'] == StateType.ODE:
                equation = self.string2matlab(item['equation'])
                string += f'\t\t\tdx({i},1) = {equation};\n\n'
                f.write(string)
                i += 1

            elif item['type'] == StateType.ALGEBRAIC:
                equation = self.string2matlab(item['equation'])
                string += f'\t\t\tdx({i},1) = {equation};\n\n'
                f.write(string)
                i += 1

        f.write(f'\t\tend\n')

    def writeSimout2Struct(self, f):
        """ Write method which calculate all the states of a simulation.
        """
        f.write(f'\t\tfunction out = simout2struct(~,t,x,p)\n')
        f.write(f'\t\t\t%% Convert the simulation output into an easy-to-use struct.\n')
        f.write(f'\n')

        self.writeLocalStates(f)

        # Save the time.
        f.write(f'\t\t\t% Save simulation time.\n')
        f.write(f'\t\t\tout.t = t;')
        f.write(f'\n')

        # Crate ones vector.
        f.write(f'\n')
        f.write('\t\t\t% Vector for extending single-value states and parameters.\n')
        f.write('\t\t\tones_t = ones(size(t));\n')
        f.write(f'\n')

        # Save states.
        f.write(f'\n\t\t\t% Save states.\n')
        for item in self.dae.getStates():
                f.write(f'\t\t\tout.{item["id"]} = {item["id"]}.*ones_t;\n')
        f.write(f'\n')

        # Save parameters.
        f.write(f'\t\t\t% Save parameters.\n')
        for item in self.dae.getParameters():
            f.write(f'\t\t\tout.{item["id"]} = p.{item["id"]}.*ones_t;\n')
        f.write(f'\n')

        f.write(f'\t\tend\n')

    def string2matlab(self, math_expr):
        """ Parses a libSBML math string formula into a matlab expression.

        Arguments:
            math_expr: str
                Math formula obtained with libSBML.formulaToL3String()
        """
        result = ''

        parameters = []
        for item in self.dae.getParameters():
            parameters.append(item['id'])

        g = tokenize(BytesIO(math_expr.encode('utf-8')).readline)

        for toknum, tokval, _, _, _ in g:
            if toknum == ENCODING:
                continue

            elif toknum == NAME and tokval in parameters:
                result += 'p.' + str(tokval)

            elif toknum == OP and tokval in ('*','/','^'):
                result += '.' + str(tokval)

            elif toknum == OP and tokval in ('+','-'):
                result += ' ' + str(tokval) + ' '

            else:
                result += str(tokval)

        return result

    def getStates(self, math_expr):
        """ Return a list with the states present in the string.
        """
        result = []

        states = []
        for state in self.dae.getStates():
            states.append(state['id'])

        g = tokenize(BytesIO(math_expr.encode('utf-8')).readline)

        for toknum, tokval, _, _, _ in g:
            if toknum == NAME and tokval in states:
                result.append(tokval)

        return result
