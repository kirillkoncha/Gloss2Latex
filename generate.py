import typing as T
import csv
import json
from pathlib import Path
import random
import subprocess

from pdfdir2image import (
    pdf2image,
    pdfdir2image,
)


IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


OptionsType = T.Dict[str, T.Optional[str]]


class LatexSourceBase:
    def __str__(self): ...


def linearise_options(options: OptionsType, sep=",") -> str:
    str_options = []
    for key, val in options.items():
        if val is not None:
            str_options.append(f"{key}={val}")
        else:
            str_options.append(f"{key}")
    return sep.join(str_options)



class LatexItemUsed(LatexSourceBase):
    __kind__: str = None

    def __init__(self, name: str, options: T.Dict[str, T.Optional[str]] = None):
        self.name = name
        self.options = options

    def __str__(self):
        options = self.options
        options_str = None
        if options:
            options_str = linearise_options(options)

        return (
            fr"\{self.__kind__}"
            f"{f'[{options_str}]' if options_str is not None else ''}"
            "{" + self.name + "}"
        )


class LatexPackageUsed(LatexItemUsed):
    __kind__ = "usepackage"


class LatexDocClassUsed(LatexItemUsed):
    __kind__ = "documentclass"


class LatexDoc(LatexSourceBase):
    preamble: T.List[LatexSourceBase] = None
    content: T.List[LatexSourceBase] = None

    def __init__(self, preamble, content, documentclass="standalone"):
        if not isinstance(preamble[0], LatexDocClassUsed):
            doc_class = LatexDocClassUsed(documentclass)
            preamble.insert(0, doc_class)

        self.preamble = preamble
        self.content = content

    def __str__(self):
        return "\n".join(
            [str(item) for item in self.preamble]
            + ["", r"\begin{document}"]
            + [""]
            + [str(item) for item in self.content]
            + ["", r"\end{document}"]
        )


class ExpexGlossedExample(LatexSourceBase):
    def __init__(
        self, words: T.List[str], glosses: T.List[str],
        translation: str
    ):
        self.words = words
        self.glosses = glosses
        self.translation = translation

    @staticmethod
    def make_gloss_line(items):
        return ' '.join(items)

    def __str__(self):
        content_strs = []
        if self.words:
            content_strs.append(
                fr"\gla {self.make_gloss_line(self.words)} //"
            )
        if self.glosses:
            content_strs.append(
                fr"\glb {self.make_gloss_line(self.glosses)} //"
            )
        if self.translation:
            content_strs.append(fr"\glft {self.translation} //")

        return "\n".join(
            [r"\begingl"]
            + content_strs
            + [r"\endgl"]
        )


class ExamplePart(LatexSourceBase):
    def __init__(self, content):
        self.content = content

    def __str__(self):
        return "\n".join(
            [r"\a",
             str(self.content)
            ]
        )


class ExpexExample(LatexSourceBase):
    def __init__(self, parts):
        self.parts = parts

    def __str__(self):
        content = []
        parts = self.parts
        if len(parts) > 1:
            content.append(r"\pex")
            for part in parts:
                content.append(r"\a")
                content.append(str(part))
        else:
            content.append(r"\ex")
            content.append(str(parts[0]))

        content.append(r"\xe")

        return "\n".join(content)


class LatexEnv(LatexSourceBase):
    def __init__(
        self, name: str, args: T.List[str] = None,
        contents: T.List[LatexSourceBase] = None,
        parent: 'LatexEnv' = None
    ):
        self.name = name
        self.args = args

        if contents is None:
            contents = []
        self.contents = contents

        self.parent = parent

    def __str__(self):
        # contents_str = "\n".join(self.contents)

        begin_items = [fr"\begin{{{self.name}}}"]
        if self.args:
            begin_items.extend(f"{{{arg}}}" for arg in self.args)

        return "\n".join(
            ["".join(begin_items)]
            + [str(content) for content in self.contents]
            + [rf"\end{{{self.name}}}"]
        )

    def add_content(self, content: LatexSourceBase):
        if isinstance(content, LatexEnv):
            content.parent = self

        self.contents.append(content)

    def get_top_env(self):
        if self.parent is None:
            return self
        return self.parent.get_top_env()


class LatexCommand(LatexSourceBase):
    def __init__(
        self, name: str, args: T.List[str] = None,
    ):
        self.name = name
        self.args = args

    def __str__(self):
        command = [fr"\{self.name}"]
        if self.args:
            command.extend(f"{{{arg}}}" for arg in self.args)

        return "".join(command)


def get_env_for_example():
    minipage_env = LatexEnv("minipage", args=[r".9\textwidth"])
    center_env = LatexEnv("center")
    minipage_env.add_content(center_env)
    return center_env


def generate_pdf(source_filename: str, aux_dir="./pdf", quiet=False):
    source = Path(source_filename)
    assert source.exists()

    args = [*("-output-directory", aux_dir), "-interaction=batchmode"]
    if quiet:
        args.append("-quiet")

    args.append(source_filename)

    subprocess.run(
        ["xelatex", *args]
    )


def test_LatexEnv():
    ...


def generate_ex(
    words, glosses, translation, filename,
    generate_pdf_kwargs={},
):
    """Generate example with document model"""
    gl = ExpexGlossedExample(words, glosses, translation)
    ex = ExpexExample([gl])

    ex_env = get_env_for_example()
    ex_env.add_content(ex)

    content = [ex_env.get_top_env()]

    doc = LatexDoc(default_preamble, content)

    path = Path(filename)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(doc))

    generate_pdf(filename, **generate_pdf_kwargs)

    return doc, ex


def load_examples(filename: str) -> T.List[T.Dict[str, T.Union[T.Dict[str, str], str]]]:
    """Load .json of examples (words-glosses-translation)"""
    with open(filename, "r", encoding="utf-8") as f:
        examples = json.load(f)

    words = {}
    for example in examples:
        items = example["items"]
        for item in items:
            word = item["word"]
            gloss = item["gloss"]

            if word in words:
                existing_value = words[word]
                if gloss != existing_value:
                    print(f"[WARNING] {word} already in word with different value "
                          f"{existing_value} (cur is {gloss})")

            words[word] = gloss

    return examples, {"words": words}


def sample_sentence_paired(word_gloss_pairs: T.Dict[str, str], words: T.List[str],
                           length=4):
    _words = random.sample(words, length)
    _glosses = [word_gloss_pairs[word] for word in _words]
    return _words, _glosses


def sample_sentences_paired(
    word_gloss_pairs: T.Dict[str, str], k=300, length=(4, 9),
):
    """Sample sentences accounting for which word has which gloss"""
    sentences = []

    length_range = range(*length)
    all_words = sorted(word_gloss_pairs)
    for i in range(k):
        l = random.choice(length_range)
        words, glosses = sample_sentence_paired(word_gloss_pairs, all_words, l)
        sentences.append((words, glosses))

    return sentences


def sample_sentence_various(
    all_words: T.List[str], all_glosses: T.List[str], length=4
):
    """Sample single sentence regardless of..."""
    words = random.sample(all_words, length)
    glosses = random.sample(all_glosses, length)
    return words, glosses


def sample_sentences_various(
    word_gloss_pairs: T.Dict[str, str], k=300, length=(4, 9),
):
    """Sample sentences regardless of which word has which gloss"""

    sentences = []
    all_words = sorted(word_gloss_pairs)
    all_glosses = sorted(word_gloss_pairs.values())

    length_range = range(*length)
    for i in range(k):
        l = random.choice(length_range)
        words, glosses = sample_sentence_various(all_words, all_glosses, l)
        sentences.append((words, glosses))

    return sentences



default_preamble = [
    LatexDocClassUsed("standalone", options={"preview": None}),
    LatexPackageUsed("babel", options={"english": None, "russian": None}),
    LatexPackageUsed("fontspec"),
    LatexPackageUsed("noto"),
    LatexPackageUsed("color"),
    LatexCommand("pagecolor", ["white"]),
    LatexPackageUsed("expex")
]


def generate_orig(examples, vocab, START_I=0, filename_template = "./tex/orig-{i}.tex"):
    """Generate source and pdf of original examples from data (but now standalone example only)"""
    data = []

    for i, example in enumerate(examples):
        if i < START_I:
            continue

        words = [item["word"] for item in example["items"]]
        glosses = [item["gloss"] for item in example["items"]]
        translation = example.get("translation", "")

        tex_filename = filename_template.format(i=i)
        document_tex, example_tex = generate_ex(
            words, glosses, translation, tex_filename,
            generate_pdf_kwargs={"aux_dir": "./pdf"},
        )

        png_filename = tex_filename[:-3] + "png"
        data.append({"formula": str(example_tex), "image": png_filename})

    ROWS.extend(data)
    # with open("im2expex.csv", "w", encoding="utf-8") as f:
    #     dw = csv.DictWriter(f, ["formula", "image"])
    #     dw.writeheader()
    #     for row in data:
    #         dw.writerow(row)


ROWS = []


if __name__ == "__main__":
    N_OTHERS = 100

    tex_dir = Path("tex-2")
    examples, vocab = load_examples("students-examples.json")

    pair_sents = sample_sentences_paired(vocab["words"], k=N_OTHERS)
    for i, sent in enumerate(pair_sents):
        words, glosses = sent

        tex_filename = str(tex_dir / Path(f"paired-{i}.tex"))
        print(tex_filename)
        document_tex, example_tex = generate_ex(words, glosses, "",
                                                tex_filename)
        png_filename = tex_filename[:-3] + "png"
        ROWS.append({"formula": str(example_tex), "image": png_filename})

    var_sents = sample_sentences_various(vocab["words"], k=N_OTHERS)
    for i, sent in enumerate(var_sents):
        words, glosses = sent

        tex_filename = str(tex_dir / Path (f"var-{i}.tex"))
        document_tex, example_tex = generate_ex(words, glosses, "",
                                                tex_filename)
        png_filename = tex_filename[:-3] + "png"
        ROWS.append({"formula": str(example_tex), "image": png_filename})

    # generate_orig(examples, vocab)

    with open("im2expex.csv", "w", encoding="utf-8", newline='') as f:
        dw = csv.DictWriter(f, ["formula", "image"])
        dw.writeheader()
        for row in ROWS:
            dw.writerow(row)
