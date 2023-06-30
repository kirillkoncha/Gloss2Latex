import argparse
import sys
from pathlib import Path
import subprocess


def pdf2image(pdf_filename, png_dir="./png", args=None):
    _args = ["-dBATCH", "-dNOPAUSE"]
    if args:
        _args.extend(args)

    _args.extend(["-sDEVICE=pngalpha"])

    png_dir = Path(png_dir)
    if not png_dir.exists():
        png_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = Path(pdf_filename)
    new_path = png_dir.joinpath(pdf_path.with_suffix('.png').name)
    _args.append(f"-sOutputFile={new_path}")

    _args.append("-r144")
    _args.append(pdf_filename)

    final_args = ["gs", *_args]
    print(final_args)
    return subprocess.run(final_args)


def pdfdir2image(dir, png_dir=None):
    dir = Path(dir)
    print(dir.resolve())
    for pdf in dir.glob("*.pdf"):
        print(pdf)
        if png_dir:
            res = pdf2image(pdf, png_dir=png_dir)
        else:
            res = pdf2image(pdf)
        print(res.returncode)


if __name__ == "__main__":
    dir = sys.argv[1]
    if len(sys.argv) > 2:
        png_dir = sys.argv[2]
        pdfdir2image(dir, png_dir)
    else:
        pdfdir2image(dir)


