import sys
import ast
from .clike import CLikeTranspiler
from .scope import add_scope_context
from .context import add_variable_context, add_list_calls
from .analysis import add_imports, is_void_function, get_id
from .tracer import decltype, is_list, defined_before


def transpile(source:str)->str:
    """
    Transpile a single python translation unit (a python script) into
    C code.
    """
    tree = ast.parse(source)
    add_variable_context(tree)
    add_scope_context(tree)
    add_list_calls(tree)
    add_imports(tree)

    transpiler = CppTranspiler()

    buf = []

    cpp = transpiler.visit(tree)
    if transpiler.headers:
        buf += transpiler.headers

    if transpiler.headers:
        buf.append('')  # Force empty line
    return "\n".join(buf) + cpp


def generate_catch_test_case(node, body):
    funcdef = 'TEST_CASE("{0}")'.format(node.name)
    return funcdef + " {\n" + body + "\n}"


def generate_template_fun(node, body):
    params = []
    for idx, arg in enumerate(node.args.args):
        params.append(("int", get_id(arg)))
    typenames = []

    template = ""
    if len(typenames) > 0:
        template = "template <{0}>\n".format(", ".join(typenames))
    params = ["{0} {1}".format(arg[0], arg[1]) for arg in params]

    return_type = "int"

    funcdef = "{0}{1} {2}({3})".format(template, return_type, node.name,
                                          ", ".join(params))
    return funcdef + " {\n" + body + "\n}"


# def generate_lambda_fun(node, body):# this actually doesn't work
#     params = ["auto {0}".format(param.id) for param in node.args.args]
#     funcdef = "auto {0} = []({1})".format(node.name, ", ".join(params))
#     return funcdef + " {\n" + body + "\n};"


class CppTranspiler(CLikeTranspiler):
    def __init__(self):
        self.headers = set()
        self.usings = set()
        self.use_catch_test_cases = False

    def visit_FunctionDef(self, node):
        body = "\n".join([self.visit(n) for n in node.body])

        if (self.use_catch_test_cases and
            is_void_function(node) and
            node.name.startswith("test")):
            return generate_catch_test_case(node, body)
        # is_void_function(node) or is_recursive(node):
        return generate_template_fun(node, body)
        # else:
        #    return generate_lambda_fun(node, body)

    def visit_Attribute(self, node):
        attr = node.attr
        value_id = get_id(node.value)
        if value_id == "math":
            if node.attr == "asin":
                return "asin"
            elif node.attr == "atan":
                return "atan"
            elif node.attr == "acos":
                return "acos"

        if is_list(node.value):
            if node.attr == "append":
                attr = "push_back"
        return value_id + "." + attr

    def visit_Call(self, node):
        fname = self.visit(node.func)
        if node.args:
            args = [self.visit(a) for a in node.args]
            args = ", ".join(args)
        else:
            args = ''

        if fname == "range":
            if sys.version_info[0] >= 3:
                return args

        return '{0}({1})'.format(fname, args)

    def visit_For(self, node):
        target = self.visit(node.target)
        it = self.visit(node.iter)
        buf = []
        buf.append('for(int {0}=0;{0}<{1};{0}++) {{'.format(target, it))
        buf.extend([self.visit(c) for c in node.body])
        buf.append("}")
        return "\n".join(buf)

    def visit_Expr(self, node):
        s = self.visit(node.value)
        if s.strip() and not s.endswith(';'):
            s += ';'
        if s == ';':
            return ''
        else:
            return s

    def visit_Str(self, node):
        """Use a C++ 14 string literal instead of raw string"""
        return ("string {" +
                super(CppTranspiler, self).visit_Str(node) + "}")

    def visit_Name(self, node):
        if node.id == 'None':
            return 'nullptr'
        else:
            return super(CppTranspiler, self).visit_Name(node)

    def visit_NameConstant(self, node):
        if node.value is True:
            return "true"
        elif node.value is False:
            return "false"
        else:
            return super(CppTranspiler, self).visit_NameConstant(node)

    def visit_If(self, node):
        body_vars = set([get_id(v) for v in node.scopes[-1].body_vars])
        orelse_vars = set([get_id(v) for v in node.scopes[-1].orelse_vars])
        node.common_vars = body_vars.intersection(orelse_vars)

        var_definitions = []
        for cv in node.common_vars:
            definition = node.scopes.find(cv)
            var_type = decltype(definition)
            var_definitions.append("{0} {1};\n".format(var_type, cv))

        if self.visit(node.test) == '__name__ == string {"__main__"}':
            buf = ["int main(int argc, char ** argv) {",
                   "py14::sys::argv = "
                   "vector<string>(argv, argv + argc);"]
            buf.extend([self.visit(child) for child in node.body])
            buf.append("}")
            return "\n".join(buf)
        else:
            return ("".join(var_definitions) +
                    super(CppTranspiler, self).visit_If(node))

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.USub):
            if isinstance(node.operand, (ast.Call, ast.Num)):
                # Shortcut if parenthesis are not needed
                return "-{0}".format(self.visit(node.operand))
            else:
                return "-({0})".format(self.visit(node.operand))
        else:
            return super(CppTranspiler, self).visit_UnaryOp(node)

    def visit_BinOp(self, node):
        if (isinstance(node.left, ast.List)
                and isinstance(node.op, ast.Mult)
                and isinstance(node.right, ast.Num)):
            return "vector ({0},{1})".format(self.visit(node.right),
                                                  self.visit(node.left.elts[0]))
        else:
            return super(CppTranspiler, self).visit_BinOp(node)

    def visit_Module(self, node):
        buf = [self.visit(b) for b in node.body]
        return "\n".join(buf)

    def visit_alias(self, node):
        return '#include "{0}.h"'.format(node.name)

    def visit_Import(self, node):
        imports = [self.visit(n) for n in node.names]
        return "\n".join(i for i in imports if i)

    def visit_List(self, node):
        if len(node.elts) > 0:
            elements = [self.visit(e) for e in node.elts]
            value_type = decltype(node.elts[0])
            return "vector<{0}>{{{1}}}".format(value_type,
                                                    ", ".join(elements))

        else:
            raise ValueError("Cannot create vector without elements")

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Ellipsis):
            raise NotImplementedError('Ellipsis not supported')

        if not isinstance(node.slice, ast.Index):
            raise NotImplementedError("Advanced Slicing not supported")

        value = self.visit(node.value)
        return "{0}[{1}]".format(value, self.visit(node.slice.value))

    def visit_Tuple(self, node):
        elts = [self.visit(e) for e in node.elts]
        return "make_tuple({0})".format(", ".join(elts))

    def visit_Assert(self, node):
        return "REQUIRE({0});".format(self.visit(node.test))

    def visit_Assign(self, node):
        target = node.targets[0]

        if isinstance(target, ast.Tuple):
            elts = [self.visit(e) for e in target.elts]
            value = self.visit(node.value)
            return "tie({0}) = {1};".format(", ".join(elts), value)

        if isinstance(node.scopes[-1], ast.If):
            outer_if = node.scopes[-1]
            if target.id in outer_if.common_vars:
                value = self.visit(node.value)
                return "{0} = {1};".format(target.id, value)

        if isinstance(target, ast.Subscript):
            target = self.visit(target)
            value = self.visit(node.value)
            return "{0} = {1};".format(target, value)

        definition = node.scopes.find(target.id)
        if (isinstance(target, ast.Name) and
              defined_before(definition, node)):
            target = self.visit(target)
            value = self.visit(node.value)
            return "{0} = {1};".format(target, value)
        elif isinstance(node.value, ast.List):
            elements = [self.visit(e) for e in node.value.elts]
            return "{0} {1} {{{2}}};".format(decltype(node),
                                             self.visit(target),
                                             ", ".join(elements))
        else:
            target = self.visit(target)
            value = self.visit(node.value)
            return "int {0} = {1};".format(target, value)
