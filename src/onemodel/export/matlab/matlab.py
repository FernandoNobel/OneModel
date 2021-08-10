import os
import sympy as sym

from onemodel.equation import EquationType
from onemodel.math_expr import MathLexer, MathTokenType

class Matlab:
    """ This class exports a onemodel model into Matlab syntax.

    This class auto-generates Matlab code that implements the information in
    a onemodel model.

    Attributes:
        onemodel: OneModel
    """

    def __init__(self, onemodel):
        """ Inits Matlab.
        
        Args:
            onemodel: OneModel
                OneModel object to export into Matlab syntax.
        """
        self.onemodel = onemodel
        self.onemodel.check()

    def math2matlab(self, expr):
        """ Convert a mathematical expresion into a matlab expression.
        
        Args:
            expr: sympy or str
                
        Returns:
            A string with translated into matlab expression.
        """
        # 'k1/k2'
        tokens = MathLexer(str(expr)).generate_tokens()
        matlab_expr = ''

        i = 0
        while i < len(tokens):
            if tokens[i].type == MathTokenType.IDENTIFIER:
                if tokens[i].value in self.onemodel.parameters_name:
                    matlab_expr += 'p.' + tokens[i].value

                if tokens[i].value in self.onemodel.variables_name:
                    matlab_expr += tokens[i].value

            elif tokens[i].type == MathTokenType.OPERATOR and tokens[i].value in '*/^':
                matlab_expr += '.' + tokens[i].value

            else:
                matlab_expr += tokens[i].value

            i += 1
        
        return matlab_expr

    def states(self):
        """ Return a multi-line str with the matlab expresssion of the states.
        
        This function returns a multi-line string with the matlab expressions
        which will calculate all states variables (ODE, substitution and
        algebraic) and will load the values into the workspace of matlab.

        Returns:
            A str with the matlab expressions.
        """
        exprs = ''

        # Keep track of which values are defined in Matlab's workspace.
        # All the parameters are known by default.
        known_vars = self.onemodel.parameters_name

        # Define ODE and algebraic variables in the workspace.
        exprs += f'\n% States:\n'
        vars_ = self.onemodel.variables

        i = 1
        for var in vars_:

            if var.equation.equation_type == EquationType.ODE:
                exprs += f'{var.name} = x({i},:);\t % {var.comment}\n'
                # Add this var to known variables.
                known_vars.append(var.name)
                i += 1

            if var.equation.equation_type == EquationType.ALGEBRAIC:
                exprs += f'{var.name} = x({i},:);\t % (algebraic) {var.comment}\n'
                # Add this var to known variables.
                known_vars.append(var.name)
                i += 1


        # Calculate substitution variables.
        exprs += f'\n% Calculate substitution variables.\n'

        known_vars_max = len(self.onemodel.parameters) + len(self.onemodel.variables)

        advance = 1

        while len(known_vars) < known_vars_max:
            advance = 0

            for var in vars_:
                if var.name in known_vars:
                    continue

                if var.equation.equation_type == EquationType.SUBSTITUTION:
                    # Get the variables dependency.
                    dependencies = MathLexer(var.equation.value).identifier_names()

                    # Check that all dependencies are satisfied.
                    if all(elem in known_vars for elem in dependencies):
                        # If so, add it.
                        known_vars.append(var.name)
                        exprs += f'{var.name} = {self.math2matlab(var.equation.value)}; % {var.comment}\n'
                        advance = 1

                if advance == 0:
                    # TODO: improve this error message.
                    raise ValueError('dependencies of substitution varibles cannot be satisfied.')

        return exprs
        
    def generate_param(self):
        """ Generate Matlab function which returns the default parameters.
        """

        # Check if build folder exists
        dirName = './build/'
        if not os.path.exists(dirName):
            # Create it.
            os.mkdir(dirName)

        # Create and open the file to export.
        f = open(dirName + self.onemodel.name + '_param.m', "w")

        # Function header.
        f.write(f'function [p,x0,M] = {self.onemodel.name}_param()\n')
        f.write(f'% This script was autogenerated with onemodel.\n\n')

        # Default parameters.
        f.write(f'% Default parameters value.\n')
        for par in self.onemodel.parameters:
            f.write(f'p.{par.name} = {par.value};\n')

        # Default initial conditions.
        f.write(f'\n% Default initial conditions.\n')
        f.write(f'x0 = [\n')
        for var in self.onemodel.variables:
            if var.equation.equation_type == EquationType.ODE:
                f.write(f'\t{var.value} % {var.name}\n')
            if var.equation.equation_type == EquationType.ALGEBRAIC:
                f.write(f'\t{var.value} % {var.name} (Algebraic)\n')
        f.write(f'];\n')

        # Mass matrix.
        f.write(f'\n% Mass matrix for algebraic simulations.\n')
        f.write(f'M = [\n')
        vars_ = self.onemodel.variables
        M = []
        for var in vars_:
            if var.equation.equation_type == EquationType.ODE:
                M.append(1)
            if var.equation.equation_type == EquationType.ALGEBRAIC:
                M.append(0)

        i = 0
        i_max = len(M)
        while i < i_max:
            f.write('\t')
            f.write('0 '*i)
            # TODO: Write if the variable is algebraic o not.
            f.write(f'{M[i]} ')
            f.write('0 '*(i_max-i-1))
            f.write('\n')
            i += 1

        f.write(f'];\n')

        f.write(f'\nend\n')

        f.close()

    def generate_ode(self):
        """ Generate a Matlab function which evaluates the ODE.

        """
        # Check if build folder exists
        dirName = './build/'
        if not os.path.exists(dirName):
            # Create it.
            os.mkdir(dirName)

        # Create and open the file to export.
        f = open(dirName + self.onemodel.name + '_ode.m', "w")

        # Function header.
        f.write(f'function [dx] = {self.onemodel.name}_ode(t,x,p)\n')
        f.write(f'% This function was autogenerated with onemodel.\n')

        # Comment arguments.
        f.write(f'\n% Args:\n')
        f.write(f'%\t t Current time in the simulation.\n')
        f.write(f'%\t x Array with the state value.\n')
        f.write(f'%\t p Struct with the parameters.\n')

        # Comment return.
        f.write(f'\n% Return:\n')
        f.write(f'%\t dx Array with the ODE.\n')

        f.write(self.states())

        # Generate ODE equations.
        vars_ = self.onemodel.variables
        f.write(f'\n')
        i = 1
        for var in vars_:
            if var.equation.equation_type == EquationType.ODE:
                f.write(f'% der({var.name}) "{var.equation.comment}"\n')
                f.write(f'dx({i},1) = {self.math2matlab(var.equation.value)};\n\n')
                i += 1

            if var.equation.equation_type == EquationType.ALGEBRAIC:
                f.write(f'% der({var.name}) (algebraic) "{var.equation.comment}"\n')
                f.write(f'dx({i},1) = -{var.name} + {self.math2matlab(var.equation.value)};\n\n')
                i += 1

        f.write(f'end\n')
        f.close()

    def generate_states(self):
        """ Generate a function which calculates all the states of the model.
        
        Generate a function which calculates all the states of the model from
        the simulation result. When simulating not all states are simulated, it
        is just simulated the reduced model. Then after the simulation we have
        to recalculate the rest of the states.
        """
         # Check if build folder exists
        dirName = './build/'
        if not os.path.exists(dirName):
            # Create it.
            os.mkdir(dirName)

        # Create and open the file to export.
        f = open(dirName + self.onemodel.name + '_states.m', "w")

        # Function header.
        f.write(f'function [out] = {self.onemodel.name}_states(t,x,p)\n')
        f.write(f'% This function was autogenerated with onemodel.\n')

        # Comment states.
        f.write(self.states())

        # Save the time.
        f.write(f'\n% Save simulation time.\n')
        f.write(f'out.t = t;\n')

        # Save ODE and ALGEBRAIC variables.
        f.write(f'\n% Save ODE variables.\n')
        vars_ = self.onemodel.variables
        for var in vars_:
            if var.equation.equation_type == EquationType.ODE:
                f.write(f'out.{var.name} = {var.name}; % {var.comment}\n')

            if var.equation.equation_type == EquationType.ALGEBRAIC:
                f.write(f'out.{var.name} = {var.name}; % {var.comment} (Algebraic)\n')

        # Save parameters.
        f.write(f'\n% Save parameters.\n')
        for param in self.onemodel.parameters:
            f.write(f'out.{param.name} = p.{param.name}*ones(size(t)); % {param.comment}\n')

        # Save extra states.
        f.write(f'\n% Calculate and save extended states.\n')
        for var in self.onemodel.variables:
            if var.equation.equation_type == EquationType.SUBSTITUTION:
                f.write(f'out.{var.name} = {var.name}.*ones(size(t)); % {var.comment}\n')

        f.write(f'\nend\n')
        f.close()

    def generate_driver(self):
        """ Generate an example driver script.
        
        Generate an example driver script taht will call all the generated
        functions and will perform a basic simulation of the model and plot the
        result.
        """
        # Check if build folder exists
        dirName = './build/'
        if not os.path.exists(dirName):
            # Create it.
            os.mkdir(dirName)

        # Create and open the file to export.
        f = open(dirName + self.onemodel.name + '_driver.m', "w")

        # Function header.
        f.write(f'%% Example driver script for simulating "{self.onemodel.name}" model.\n')
        f.write(f'% This sript was autogenerated with onemodel.\n')

        # Clear and close all.
        f.write(f'\nclear all;\n')
        f.write(f'close all;\n')

        # Default parameters.
        f.write(f'\n% Default parameters.\n')
        f.write(f'[p,x0,M] = {self.onemodel.name}_param();\n')

        # Solver options.
        f.write(f'\n% Solver options.\n')
        f.write(f"opt = odeset('AbsTol',1e-8,'RelTol',1e-8);\n")
        f.write(f"opt = odeset(opt,'Mass',M);\n")

        # Simulation time span.
        f.write(f'\n% Simulation time span.\n')
        f.write(f'tspan = [0 10];\n')

        # Simulate.
        f.write(f'\n[t,x] = ode15s(@(t,x) {self.onemodel.name}_ode(t,x,p),tspan,x0,opt);\n')
        f.write(f'out = {self.onemodel.name}_states(t,x,p);\n')
        
        # Plot.
        f.write(f'\n% Plot result.\n')
        f.write(f'plot(t,x);\n')
        f.write(f'grid on;\n')
        # TODO: Add a legend.
