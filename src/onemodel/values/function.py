from onemodel.values.value import Value
from onemodel.values.number import Number
from onemodel.values.string import String
from onemodel.values.list import List
from onemodel.errors import *
from onemodel.runTimeResult import RunTimeResult
from onemodel import interpreter
import os

class BaseFunction(Value):
    def __init__(self, name):
        super().__init__()
        self.name = name or "<anonymous>"

    def generate_new_context(self):
        new_context = interpreter.Context(self.name, self.context, self.pos_start)
        new_context.symbol_table = interpreter.SymbolTable(new_context.parent.symbol_table)
        return new_context

    def check_args(self, arg_names, args):
        res = RunTimeResult()

        if len(args) > len(arg_names):
            return res.failure(RunTimeError(
                self.pos_start, self.pos_end,
                f"{len(args) - len(arg_names)} too many args passed into {self}",
                self.contex
                ))

        if len(args) < len(arg_names):
            return res.failure(RunTimeError(
                self.pos_start, self.pos_end,
                f"{len(arg_names) - len(args)} too few args passed into {self}",
                self.context
                ))

        return res.success(None)

    def populate_args(self, arg_names, args, exec_ctx):
        for i in range(len(args)):
            arg_name = arg_names[i]
            arg_value = args[i]
            arg_value.set_context(exec_ctx)
            exec_ctx.symbol_table.set(arg_name, arg_value)

    def check_and_populate_args(self, arg_names, args, exec_ctx):
        res = RunTimeResult()
        res.register(self.check_args(arg_names, args))
        if res.should_return(): return res
        self.populate_args(arg_names, args, exec_ctx)
        return res.success(None)

class Function(BaseFunction):
    def __init__(self, name, body_node, arg_names, should_auto_return):
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.should_auto_return = should_auto_return

    def execute(self, args):
        res = RunTimeResult()
        my_interpreter = interpreter.Interpreter()
        exec_ctx = self.generate_new_context()

        res.register(self.check_and_populate_args(self.arg_names, args, exec_ctx))
        if res.should_return(): return res

        value = res.register(my_interpreter.visit(self.body_node, exec_ctx))
        if res.should_return() and res.func_return_value == None: return res

        return_value = (value if self.should_auto_return else None) or res.func_return_value or Number.null

        return res.success(return_value)

    def copy(self):
        copy = Function(self.name, self.body_node, self.arg_names, self.should_auto_return)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<function {self.name}>"

class BuiltInFunction(BaseFunction):
    def __init__(self, name):
        super().__init__(name)

    def execute(self, args):
        res = RunTimeResult()
        exec_ctx = self.generate_new_context()

        method_name = f'execute_{self.name}'
        method = getattr(self, method_name, self.no_visit_method)

        res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
        if res.should_return(): return res

        return_value = res.register(method(exec_ctx))
        if res.should_return(): return res
        return res.success(return_value)
  
    def no_visit_method(self, node, context):
        raise Exception(f'No execute_{self.name} method defined')

    def copy(self):
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function {self.name}>"


    def execute_print(self, exec_ctx):
        print(str(exec_ctx.symbol_table.get('value')))
        return RunTimeResult().success(Number.null)
    execute_print.arg_names = ['value']

    def execute_print_ret(self, exec_ctx):
        return RunTimeResult().success(String(str(exec_ctx.symbol_table.get('value'))))
    execute_print_ret.arg_names = ['value']

    def execute_input(self, exec_ctx):
        text = input()
        return RunTimeResult().success(String(text))
    execute_input.arg_names = []

    def execute_input_int(self, exec_ctx):
        while True:
            text = input()
            try:
                number = int(text)
                break
            except ValueError:
                print(f"'{text}' must be an integer. Try again!")
        return RunTimeResult().success(Number(number))
    execute_input_int.arg_names = []

    def execute_clear(self, exec_ctx):
        os.system('cls' if os.name == 'nt' else 'cls')
        return RunTimeResult().success(Number.null)
    execute_clear.arg_names = []

    def execute_is_number(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RunTimeResult().success(Number.true if is_number else Number.false)
    execute_is_number.arg_names = ["value"]

    def execute_is_string(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RunTimeResult().success(Number.true if is_number else Number.false)
    execute_is_string.arg_names = ["value"]

    def execute_is_list(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
        return RunTimeResult().success(Number.true if is_number else Number.false)
    execute_is_list.arg_names = ["value"]

    def execute_is_function(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)
        return RunTimeResult().success(Number.true if is_number else Number.false)
    execute_is_function.arg_names = ["value"]

    def execute_append(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(list_, List):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
                ))

        list_.elements.append(value)
        return RunTimeResult().success(Number.null)
    execute_append.arg_names = ["list", "value"]

    def execute_pop(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        index = exec_ctx.symbol_table.get("index")

        if not isinstance(list_, List):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
                ))

        if not isinstance(index, Number):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "Second argument must be number",
                exec_ctx
                ))

        try:
            element = list_.elements.pop(int(index.value))
        except:
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                'Element at this index could not be removed from list because index is out of bounds',
                exec_ctx
            ))
        return RunTimeResult().success(element)
    execute_pop.arg_names = ["list", "index"]

    def execute_extend(self, exec_ctx):
        listA = exec_ctx.symbol_table.get("listA")
        listB = exec_ctx.symbol_table.get("listB")

        if not isinstance(listA, List):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
                ))

        if not isinstance(listB, List):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "Second argument must be list",
                exec_ctx
                ))

        listA.elements.extend(listB.elements)
        return RunTimeResult().success(Number.null)
    execute_extend.arg_names = ["listA", "listB"]

    def execute_len(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")

        if not isinstance(list_, List) and not isinstance(list_, String):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "Argument must be list or string",
                exec_ctx
                ))

        if isinstance(list_, List):
            return RunTimeResult().success(Number(len(list_.elements)))

        return RTResult().success(Number(len(list_.value)))
    execute_len.arg_names = ["list"]

    def execute_run(self, exec_ctx):
        fn = exec_ctx.symbol_table.get("fn")

        if not isinstance(fn, String):
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                "Argument must be string",
                exec_ctx
                ))

        fn = fn.value

        try:
            with open(fn, "r") as f:
                script = f.read()
        except Exception as e:
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                f"Failed to load script \"{fn}\"\n" + str(e),
                exec_ctx
                ))

        _, error = interpreter.run(fn, script)

        if error:
            return RunTimeResult().failure(RunTimeError(
                self.pos_start, self.pos_end,
                f"Failed to finish executing script \"{fn}\"\n" +
                error.as_string(),
                exec_ctx
                ))

        return RunTimeResult().success(Number.null)
    execute_run.arg_names = ["fn"]

BuiltInFunction.print       = BuiltInFunction("print")
BuiltInFunction.print_ret   = BuiltInFunction("print_ret")
BuiltInFunction.input       = BuiltInFunction("input")
BuiltInFunction.input_int   = BuiltInFunction("input_int")
BuiltInFunction.clear       = BuiltInFunction("clear")
BuiltInFunction.is_number   = BuiltInFunction("is_number")
BuiltInFunction.is_string   = BuiltInFunction("is_string")
BuiltInFunction.is_list     = BuiltInFunction("is_list")
BuiltInFunction.is_function = BuiltInFunction("is_function")
BuiltInFunction.append      = BuiltInFunction("append")
BuiltInFunction.pop         = BuiltInFunction("pop")
BuiltInFunction.extend      = BuiltInFunction("extend")
BuiltInFunction.len         = BuiltInFunction("len")
BuiltInFunction.run         = BuiltInFunction("run")
