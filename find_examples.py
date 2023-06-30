import typing as T
import json
from pathlib import Path
import re


EXPEX_EXAMPLE = r"""
    \\(?P<start>p?ex)   # ex beginning
    (?:.(?!\\xe))+      # content of example
    .\\xe               # ex end
"""
expex_example = re.compile(EXPEX_EXAMPLE, flags=re.DOTALL | re.VERBOSE)
print(expex_example.pattern)

MULTIPART_EX_NAME = "pex"

EXPEX_EXAMPLE_PART = r"""
    \\a                 # part begins
    (?:.(?!\\xe|\\a))+   # content of the part
"""
expex_example_part = re.compile(EXPEX_EXAMPLE_PART, re.DOTALL | re.VERBOSE)

_EXPEX_LEVEL = r"^ *\\{gloss_level}( .+)//$"
EXPEX_ORIG_WORDS = _EXPEX_LEVEL.format(gloss_level="gla")
EXPEX_GLOSSES = _EXPEX_LEVEL.format(gloss_level="glb")
EXPEX_TRANSLATION = _EXPEX_LEVEL.format(gloss_level="glft")

print(EXPEX_ORIG_WORDS, EXPEX_GLOSSES, EXPEX_TRANSLATION, sep="\n")

expex_orig_words = re.compile(EXPEX_ORIG_WORDS, re.M)
expex_glosses = re.compile(EXPEX_GLOSSES, re.M)
expex_translation = re.compile(EXPEX_TRANSLATION, re.M)


TOKEN = r"\s+([^\s]+)"
token = re.compile(TOKEN)

word_re = re.compile(r"\w")
EXCLUDE = set("[](){}/|")


def remove_extras(s: str):
    # replace glosses
    s = re.sub(r"\\(\w+){}", r"\1", s)

    for i in range(3):
        s = re.sub(r"\\(\w+\b(?:[^{]|$))", r"\1", s)

    return s


def find_examples(text: str, demand_char_like_words=True) -> T.List[T.Dict[str, str]]:
    examples = []

    for ex_match in expex_example.finditer(text):
        ex = ex_match.group(0)

        to_parse = []
        if ex_match.group("start") == MULTIPART_EX_NAME:
            # print("trying multipart")
            to_parse.extend(expex_example_part.findall(ex))
        else:
            to_parse.append(ex)

        for item in to_parse:
            print(item)

            words_m = expex_orig_words.search(item)
            glosses_m = expex_glosses.search(item)
            translation_str = expex_translation.search(item)

            if not (words_m and glosses_m):
                continue

            example = {}

            words_str = remove_extras(words_m.group(1))
            glosses_str = remove_extras(glosses_m.group(1))

            words = token.findall(words_str)
            glosses = token.findall(glosses_str)
            if demand_char_like_words:
                words = [word for word in words if word not in EXCLUDE]
                glosses = [gloss for gloss in glosses if gloss not in EXCLUDE]

            is_len_eq = len(words) == len(glosses)
            if not is_len_eq:
                continue

            print(words, glosses, sep="\n")

            example["items"] = [{"word": word, "gloss": gloss}
                                for word, gloss in zip(words, glosses)]
            if translation_str:
                example["translation"] = translation_str.group(1)
            examples.append(example)

    return examples


def find_tex_files(dir: str):
    return Path(dir).glob("**/*.tex")


def parse_dir(dir: str):
    res = []

    for file in find_tex_files(dir):
        print(file)
        with open(file, "r", encoding="utf-8") as f:
            _res = find_examples(f.read())
            if _res:
                for item in _res:
                    item["source"] = str(file.parent).replace(" ", "_")
                    res.append(item)

    return res


if __name__ == "__main__":
    res = parse_dir("data-students")
    with open("students-examples.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
