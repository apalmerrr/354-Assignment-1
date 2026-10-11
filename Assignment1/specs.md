# Calculator Specification

## Overview

`calculator_cfg.py` evaluates arithmetic expressions given on the command line, for example:

```
python calculator_cfg.py "1+2*3"
7
```

The program runs in three stages:

1. **Parse.** Lark reads `grammar.lark` and builds an LALR parser. The parser turns the input string into a parse tree.
2. **Transform.** `CalcTransformer` walks the parse tree bottom up and turns it into an abstract syntax tree, or AST, made of nested Python tuples.
3. **Evaluate.** `evaluate` walks the AST recursively and computes a number, which `format_result` turns into the printed output.

## The Grammar

### Starting point

The assignment gives this ambiguous grammar:

```
exp -> exp '+' exp
exp -> exp '*' exp
exp -> exp '^' exp
exp -> exp '-' exp
exp -> '-' exp
exp -> 'log' exp 'base' exp
exp -> '(' exp ')'
exp -> number
```

It is ambiguous because a string such as `1+2*3` has two parse trees, one meaning `(1+2)*3` and one meaning `1+(2*3)`. The grammar says nothing about which operator binds tighter or which way repeated operators group.

### Modified grammar

To remove the ambiguity, the single nonterminal `exp` is split into five levels. Each level handles one group of operators, and a level can only refer to itself and to the level directly below it, except inside parentheses or inside the first argument of `log`, where a full `exp` is allowed again.

```
exp  -> exp '+' exp1  |  exp '-' exp1  |  exp1
exp1 -> exp1 '*' exp2 |  exp2
exp2 -> '-' exp2      |  'log' exp 'base' exp2  |  exp3
exp3 -> exp4 '^' exp2 |  exp4
exp4 -> number        |  '(' exp ')'
```

| Level | Operators | Associativity |
|---|---|---|
| `exp`  | binary `+`, `-` | left |
| `exp1` | `*` | left |
| `exp2` | unary `-`, `log ... base ...` | prefix, nests to the right |
| `exp3` | `^` | right |
| `exp4` | numbers, parentheses | none |

In `grammar.lark` each alternative is given a label with `->`, such as `-> plus` or `-> power`. These labels become the node names in the parse tree and match the method names in `CalcTransformer`. Rules are written with a leading `?` so that Lark inlines a rule when it has only one child. This means `exp1 -> exp2` does not create an extra node, and the tree only contains labelled operations. Whitespace is ignored with `%ignore WS_INLINE`, and `NUMBER` is Lark's predefined number token, which accepts integers and decimals.

### Why the grammar is unambiguous

The parser is built with `parser="lalr"`. Lark refuses to build an LALR parser if the grammar has shift/reduce or reduce/reduce conflicts, and every LALR(1) grammar is unambiguous. The fact that the program starts at all is therefore a check that each input has exactly one parse tree.

### Why it accepts the same language

Every operand position in the original grammar can hold any expression. In the new grammar, any expression can still appear in any operand position because a lower level can always reach a higher one through parentheses, and the prefix operators accept `exp2`, which covers numbers, powers, negations and logs. Inputs such as `2^-1`, `2*-3`, `2--3` and `log 8 base -2` all parse. The new grammar only fixes how a string is grouped. It does not reject strings that the original accepted.

## Order of Operations

### Precedence

From tightest to loosest binding:

1. Parentheses
2. `^`
3. Unary `-` and `log ... base ...`
4. `*`
5. Binary `+` and `-`

Examples from the tests:

* `1+2*3` is `1+(2*3) = 7`, because `*` sits at a lower level than `+`.
* `2^3+1` is `(2^3)+1 = 9` and `2^3*2` is `(2^3)*2 = 16`, because `^` binds tighter than both.
* `-3^2` is `-(3^2) = -9`. Unary minus sits above `^` in the hierarchy, so its operand is the whole power. This matches the usual mathematical convention.

### Associativity

* `+`, `-` and `*` are left associative. The rule `exp -> exp '-' exp1` is left recursive, so `1-2-3` groups as `(1-2)-3 = -4`.
* `^` is right associative. The rule `exp3 -> exp4 '^' exp2` puts the recursion on the right, so `2^3^2` groups as `2^(3^2) = 2^9 = 512`. The left operand of `^` is an `exp4`, meaning a number or a parenthesized expression, so `(2^3)^2` must be written with parentheses.
* Unary minus can be repeated because `exp2 -> '-' exp2` refers to itself, so `--1` is `-(-1) = 1`.

### The log operator

`log a base b` is treated as a prefix operator at the same level as unary minus. The first argument sits between the keywords `log` and `base`, so it is clearly delimited and can be any full `exp`. The second argument is an `exp2`, which ends before any `*`, `+` or binary `-`.

* `log 8 base 2 + 1` is `(log 8 base 2) + 1 = 4`.
* `log 8 base 2 * 3` is `(log 8 base 2) * 3 = 9`.
* `log 16 base 2^2` is `log 16 base 4 = 2`, since `^` binds tighter than the prefix operator, in the same way that `-3^2` negates the whole power.

Making the base an `exp2` instead of a plain number keeps inputs like `log 8 base -2` inside the language, as the original grammar allows.

## Methods

### `parser` (module level)

Created once when the program starts. It reads `grammar.lark` from the same folder as `calculator_cfg.py`, so the program works from any working directory, and builds a Lark LALR parser with `start="start"`.

### `CalcTransformer(Transformer)`

A subclass of Lark's `Transformer`. Lark calls the method whose name matches each tree node's label, starting from the leaves, and passes in the node's children after they have already been transformed. Each method returns a tuple whose first element is the operation name.

| Method | Grammar label | Returns |
|---|---|---|
| `num(args)` | `num` | `("num", value)`. The token text is converted with `int`, and with `float` if that fails, so `2.5` is accepted. |
| `plus(args)` | `plus` | `("plus", left, right)` |
| `minus(args)` | `minus` | `("minus", left, right)` |
| `times(args)` | `times` | `("times", left, right)` |
| `power(args)` | `power` | `("power", base, exponent)` |
| `neg(args)` | `neg` | `("neg", operand)` |
| `log(args)` | `log` | `("log", argument, base)` |

For example, `1+2*3` becomes:

```
("plus", ("num", 1), ("times", ("num", 2), ("num", 3)))
```

### `evaluate(ast)`

Looks at the first element of the tuple to decide which operation to perform. For `num` it returns the stored number. For every other operation it first calls `evaluate` on each child, then combines the results:

* `plus`, `minus`, `times` use Python's `+`, `-`, `*`
* `power` uses `**`
* `neg` negates its operand
* `log` uses `math.log(argument, base)`

Recursion ends at `num` nodes, which are the leaves. Because the AST already encodes the order of operations, `evaluate` itself contains no precedence logic. An unknown operation name raises a `ValueError`.

### `format_result(value)`

Turns the computed number into the printed string. If the value is a float that is within `1e-9` of a whole number, it is printed as an integer. This makes `log 8 base 2` print `3` instead of `3.0`, and hides rounding noise such as `math.log(1000, 10)` returning `2.9999999999999996`. Other values are printed with Python's `str`, so `2^-1` prints `0.5`.

### `main()`

Reads the expression from `sys.argv[1]`, printing a usage message and exiting if it is missing. It then runs the three stages in order: `parser.parse`, `CalcTransformer().transform` and `evaluate`, and prints the result of `format_result`.

## Program Flow

```
command line string
      |
      v
parser.parse(...)            -> Lark parse tree, grouping fixed by grammar.lark
      |
      v
CalcTransformer().transform  -> AST of nested tuples
      |
      v
evaluate(ast)                -> number, computed recursively
      |
      v
format_result(...)           -> printed output
```

## Testing

All given tests pass, along with additional cases checking associativity, unary minus inside other operators, decimals and the interaction of `log` with other operators:

| Input | Output |
|---|---|
| `1+2*3` | 7 |
| `2-(4+2)` | -4 |
| `(3+2)*2` | 10 |
| `--1` | 1 |
| `2^3^2` | 512 |
| `2^3+1` | 9 |
| `2^3*2` | 16 |
| `log 8 base 2` | 3 |
| `log 8 base 2 + 1` | 4 |
| `-3^2` | -9 |
| `1-2-3` | -4 |
| `2^-1` | 0.5 |
| `2*-3` | -6 |
| `log 8 base 2 * 3` | 9 |
| `log 16 base 2^2` | 2 |
| `log (2+6) base 2` | 3 |
| `log 1000 base 10` | 3 |
| `2.5*2` | 5 |
