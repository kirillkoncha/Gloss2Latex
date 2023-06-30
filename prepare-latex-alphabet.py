import json
import re

import pandas as pd


TOKENIZE_PATTERN = re.compile(
    "(\\\\[a-zA-Z]+)|"+                     # \[command name]
    "((\\\\)*[$-/:-?{-~!\"^_`\[\]])|"+      # math symbols
    "(\w)|"+                                # single letters or other chars
    "(\\\\)"                                # \ characters
)


def tokenize_formula(formula):
    """Returns list of tokens in given formula.
    formula - string containing the LaTeX formula to be tokenized
    Note: Somewhat work-in-progress"""
    # Tokenize
    tokens = re.finditer(TOKENIZE_PATTERN, formula)
    # To list
    tokens = list(map(lambda x: x.group(0), tokens))
    # Clean up
    tokens = [x for x in tokens if x is not None and x != ""]
    return tokens


s = set()


def merge(x):
    global s
    s |= set(tokenize_formula(x))


df = pd.read_csv('im2expex.csv')
print(df.shape)
df.formula.map(merge)

with open('latex_tokens.json', 'w', encoding="utf-8") as f:
    json.dump(['<p>', '<s>', '<e>'] + list(s), f)

