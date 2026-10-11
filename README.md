# Programming Assignment 1

A command line calculator built in Python with a parser. It supports `+`, `-`, `*`, `^`, unary minus, `log ... base ...` and parentheses, following the usual order of operations.

**Team:** Alex Palmer

## Files

```
Assignment1/
    calculator_cfg.py   parses, builds the AST and evaluates it
    grammar.lark        unambiguous grammar used to generate the parser
```

## Setup

Requires Python 3 and Lark:

```
pip install lark
```

## Usage

Run from the repo folder and pass the expression in quotes:

```
python Assignment1/calculator_cfg.py "1+2*3"
7
```


