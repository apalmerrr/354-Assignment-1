import math
import os
import sys

from lark import Lark, Transformer

# Load grammar.lark from the same folder as this file, so the program works
# no matter which directory it is run from. The LALR parser refuses any grammar
# with conflicts, which also confirms that the grammar is unambiguous.
GRAMMAR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grammar.lark")
with open(GRAMMAR_PATH) as f:
    parser = Lark(f.read(), start="start", parser="lalr")


class CalcTransformer(Transformer):
    """Turns Lark's parse tree into an AST made of nested tuples.

    Each method is named after a label in grammar.lark (the name after "->")
    and receives the already transformed children of that node.
    """

    def num(self, args):
        text = str(args[0])
        try:
            return ("num", int(text))
        except ValueError:
            return ("num", float(text))

    def plus(self, args):
        return ("plus", args[0], args[1])

    def minus(self, args):
        return ("minus", args[0], args[1])

    def times(self, args):
        return ("times", args[0], args[1])

    def power(self, args):
        return ("power", args[0], args[1])

    def neg(self, args):
        return ("neg", args[0])

    def log(self, args):
        return ("log", args[0], args[1])


def evaluate(ast):
    """Recursively computes the value of an AST produced by CalcTransformer."""
    op = ast[0]
    if op == "num":
        return ast[1]
    if op == "plus":
        return evaluate(ast[1]) + evaluate(ast[2])
    if op == "minus":
        return evaluate(ast[1]) - evaluate(ast[2])
    if op == "times":
        return evaluate(ast[1]) * evaluate(ast[2])
    if op == "power":
        return evaluate(ast[1]) ** evaluate(ast[2])
    if op == "neg":
        return -evaluate(ast[1])
    if op == "log":
        return math.log(evaluate(ast[1]), evaluate(ast[2]))
    raise ValueError(f"Unknown operation: {op}")


def format_result(value):
    """Prints whole numbers without a decimal point, so log 8 base 2 shows 3 and not 3.0.

    Values within a tiny distance of a whole number are rounded, which hides
    floating point noise such as math.log(1000, 10) = 2.9999999999999996.
    """
    if isinstance(value, float) and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return str(value)


def main():
    if len(sys.argv) < 2:
        print('Usage: python calculator_cfg.py "expression"')
        sys.exit(1)
    tree = parser.parse(sys.argv[1])
    ast = CalcTransformer().transform(tree)
    print(format_result(evaluate(ast)))


if __name__ == "__main__":
    main()
