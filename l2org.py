#!/bin/env python3
# -*- coding: utf-8 -*-

""" l2org:  Roundtrip conversion from LaTeX to Orgmode.
    Citations are converted to org-ref format.
    Author: Uli Wortmann

    Copyright (C), 2022 Ulrich G. Wortmann

     This program is free software: you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation, either version 3 of the License, or
     (at your option) any later version.

     This program is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
     GNU General Public License for more details.

     You should have received a copy of the GNU General Public License
     along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# PYTHON_ARGCOMPLETE_OK
import re

debug = False


def main():
    """Main function."""

    infile, outfile = get_arguments()
    file_latex_to_orgmode(infile, outfile)

    exit(0)


def get_arguments():
    """Get CLI arguments.

    Parameters:

    Returns:
      (str):  Input file name.
      (str):  Output file name.
    """

    import argparse
    import argcomplete
    import sys

    # Parse command-line arguments:
    parser = argparse.ArgumentParser(
        description="Try to convert a LaTeX file to Orgmode.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )  # Use capital, period, add default values

    # Required arguments:
    parser.add_argument(
        "infile", type=str, default=None, help="name of the input LaTeX file (file.tex)"
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=str,
        default=None,
        help="name of the output Orgmode file (file.org)",
    )

    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="increase output verbosity"
    )  # Counts number of occurrences

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.outfile is None:
        outfile = re.sub(
            r"\.org\.org", r".org", re.sub(r"\.tex", r".org", str(args.infile)) + ".org"
        )
    else:
        outfile = args.outfile

    if args.infile == outfile:
        sys.stderr.write(f"Input and output file have the same name: {outfile}" + "\n")

    print(f"Input file:  {args.infile}")
    print(f"Output file: {outfile}")

    return args.infile, outfile


def read_header(nl, lines, ofl, outfile) -> bool:
    """header lines are all lines between \documentclass and \begin{document}
    precede all read lines with #+latexheader:

    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    return values:
    header: True of header data was written
    """
    import pathlib as pl

    fn: str = outfile  # file name
    cwd: pl.Path = pl.Path.cwd()  # get the current working directory
    fqfn: pl.Path = pl.Path(f"{cwd}/{fn}")  # fully qualified file name

    header_file = fqfn.stem + "_latex_header.tex"
    s = author = date = title = email = headers = ""

    if "documentclass" in nl:
        while "begin{document}" not in nl:
            if nl.strip() != "":
                if "\\author" in nl:
                    s = re.search(r"\\author{.*\}", nl).group()[8:-1]
                    author = f"#+author: {line_latex_to_orgmode(s)}\n"
                elif "\\date" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    date = f"#+date: {s}\n"
                elif "\\title" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    title = f"#+title: {line_latex_to_orgmode(s)}\n"
                elif "\\email" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    email = f"#+email: {s}\n"
                else:
                    headers = headers + nl
            nl: str = next(lines)
        # write org file header
        ofl.write("#+startup: latexpreview inlineimages\n")
        if title:
            ofl.write(title)
        if author:
            ofl.write(author)
        if email:
            ofl.write(email)
        if date:
            ofl.write(date)
        ofl.write(f"#+latex_header: \\input{{{header_file}}}")
        # write latex headers
        with open(header_file, "w") as hf:
            hf.write(headers)
    else:
        return nl

    return True


def get_string_between_brackets(brackets: str, string: str) -> tuple[str, int, int]:
    """return the string delimited by two brackets
    Arguments:
     brackets = "{}"
     string = "{Hello"}. Must start with first bracket!
    return values:
       string
       start
       stop index
    """
    rs = ""
    start = brackets[0]
    stop = brackets[1]
    s_num = 0
    e_num = 0
    i = 0
    j = 0
    for e in string:
        if e == start:
            s_num = s_num + 1
        elif e == stop:
            e_num = e_num + 1

        if s_num == 0:
            j = j + 1
        if s_num == e_num and s_num > 0:
            rs = string[j + 1 : i]
            break
        i = i + 1
    return rs, j, i


def fix_bibliography(nl, lines, ofl, outfile) -> bool:
    """add the correct file extensions to the bib files"""
    new_list = ""
    if "bibliography{" not in nl:
        return nl
    bibstring = re.search(r"\{.*\}", nl).group()[1:-1]

    biblist = bibstring.split(",")
    for e in biblist:
        new_list = new_list + e + ".bib,"
    new_list = new_list[:-1]
    ofl.write(f"bibliography:{new_list}")

    return True


def citations(nl, lines, ofl, outfile) -> bool:
    """Convert to Org type citations
    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    Return true if citation was found
    """

    i = i1 = i1 = j1 = j2 = 0  # counter
    cs = ""
    cl = ""
    ce = ""
    c_opt = 0
    cl_pre = ""
    cl_post = ""
    post_text = ""
    pre_text = ""
    b1 = ""
    b2 = ""

    # test citation is present
    if "\cite" not in nl:
        return nl

    while nl.count("{") != nl.count("}"):
        nl = f"{nl} {next(lines)}"
        nl = nl.replace("\n", " ")
        i = i + 1

        if i > 10:
            raise ValueError(f"Unable to find end of citation in {nl}")

    # what kind of cite are we dealing with
    # find the first cite expression
    temp = re.search(r"\\cite.*?\{", nl).group()
    ct = re.search(r"\\cit[a-z]+\{", temp)  # test if trivial citation
    if re.search(r"\\cit[a-z]+\{", temp) is not None:
        # trivial citation
        ct = ct.group()[1:-1]  # get citation type
        # get complete citation string
        ss = r"\\" + ct + "\{.*?\}"
        cs = re.search(ss, nl).group()
        # extract citation list
        cl = re.search(r"\{.*?\}", cs).group()[1:-1]
        cs = ct

    else:  # citation with optional arguments
        # get first citation
        temp = re.search(r"\\cit[a-z]+\[", nl).group()
        ct = temp[1:-1]  # citation type

        # get entire string starting with citation
        temp = nl[nl.index(temp) :]

        # get text between first brackets
        b1, j1, i1 = get_string_between_brackets("[]", temp)
        cs = f"{ct}[{b1}]" if b1 else f"{ct}[]"

        # test if second pair of brackets
        if temp[i1 + 1] == "[":
            b2, j2, i2 = get_string_between_brackets("[]", temp[i1 + 1 :])
            i1 = i1 + i2
            cs = f"{cs}[{b2}]" if b2 else f"{cs}[]"
        # get citations list

        cl = re.search(r"\{.*?\}", temp[i1 + 1 :]).group()[1:-1]

    # create complete cite expression
    ce = "\\" + cs + "{" + cl + "}"

    # split string into before and after center
    pre_text, post_text = nl.split(ce, 1)

    # build org mode syntax
    cl_list = cl.split(",")
    cl = ""
    for e in cl_list:  # org mode citation list
        cl = f"{cl}&{e.strip()};"

    cl = cl[:-1]

    if b1 and not b2:
        cs = f"{ct}:{b1}{cl};"
    elif b1:
        cs = f"{ct}:{b1}{cl};{b2}"
    elif b2:
        cs = f"{ct}:{cl};{b2}"
    else:  # regular citation
        cs = f"{ct}:{cl}"

    cs = f"[[{cs}]]"

    line = line_latex_to_orgmode(f"{pre_text}{cs}")
    ofl.write(line)

    if post_text != "":
        scan_text(post_text, lines, ofl, outfile)

    return True


def section_commands(nl, lines, ofl, outfile) -> bool:
    """Convert to Org captions
    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    Return true if section command was found
    """

    i = 0  # counter
    section_string = ""
    section_type = ""
    short_title = ""
    marker_dict = {
        "chapter": "* ",
        "section": "* ",
        "subsection": "** ",
        "abstract": "** ",
        "subsubsection": "*** ",
        "paragraph": "**** ",
        "subparagraph": "***** ",
    }

    # test if chapter or section present
    if "chapter{" in nl or "section{" in nl or "paragraph{" in nl:
        pass
    elif "chapter[" in nl or "section[" in nl or "paragraph[" in nl:
        pass
    else:
        return nl

    # test if multiline
    while nl.count("{") != nl.count("}"):
        nl = f"{nl}\n{next(lines)}"
        i = i + 1
        if i > 3:
            raise ValueError(f"Unable to find end of section in {nl}")

    # extract section stype and string
    # section_string = re.search(r"^.*?\}", nl).group()

    if "[" in nl:
        short_title, j1, i1 = get_string_between_brackets("[]", nl)
        short_title = line_latex_to_orgmode(short_title)
        short_title = f"PROPERTIES:\n:ALT_TITLE: {short_title}\n:END:\n"
        section_type = re.search(r"^.*?\[", nl).group()[1:-1]
    else:
        section_type = re.search(r"^.*?\{", nl).group()[1:-1]

    section_title, j1, i1 = get_string_between_brackets("{}", nl)
    section_title = line_latex_to_orgmode(section_title)

    # test if text after caption
    text_after = nl.split(f"{{{section_title}}}", 1)[1]

    # get section type
    if section_type in marker_dict:
        marker = marker_dict[section_type]
    else:
        raise ValueError(f"marker = {section_type} is not valid")

    # build section text
    nl = f"{marker}{section_title}\n"
    if short_title != "":
        nl = f"{nl}{short_title}"

    ofl.write(f"{nl}")

    if text_after != "":
        scan_text(text_after, lines, ofl, outfile)
    return True


def math_environments(nl, lines, ofl, outfile) -> bool:
    """prevent math environments from being parsed"""
    # list of known evironments
    loke = ["linenomath", "linenomath*", "equation"]

    is_env = ""
    is_env = re.search(r"^\\begin{.*?\}", nl)
    ta: list[str] = []
    if is_env:
        is_env = is_env.group()[7:-1]

    if is_env in loke:
        while f"\\end{{{is_env}}}" not in nl:
            ta.append(nl)
            nl = next(lines)

        ta.append(f"\\end{{{is_env}}}\n")
        # write array
        for e in ta:
            ofl.write(e)
        return True
    else:
        return nl


def special_environments(current_line, lines, ofl, outfile) -> bool:
    """Some environments a better handled by a latex export block
    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    return values: sp: True if environment was written
    """

    is_env = ""
    is_env = re.search(r"^\\begin{.*?\}", current_line)

    if is_env is None:
        return current_line

    env = is_env.group()[7:-1]
    # list of environments you want to keep in the running text, rather
    # than wrapping in a latex export block
    exclude_env = ["itemize", "enumerate"]  #
    if env in exclude_env:
        return current_line

    ofl.write("\n#+BEGIN_EXPORT latex\n")

    while f"end{{{env}}}" not in current_line:
        if current_line.strip() != "":
            ofl.write(current_line)
        current_line = next(lines)
            
    ofl.write(f"\\end{{{env}}}\n")
    ofl.write("#+END_EXPORT\n\n")
    return True


def comments(line, lines, ofl, outfile):
    """Wrap comment lines"""

    chars: int = 0
    num_lines: int = 0
    la: list[str] = []

    if line[0] != "%":
        return line

    while line[0] == "%":
        num_lines = num_lines + 1
        chars = chars + len(line)
        la.append(line)
        line = next(lines)

    if num_lines > 3 or chars > 180:
        ofl.write("\n#+BEGIN_EXPORT latex\n")
        for e in la:
            ofl.write(e)

        ofl.write("#+END_EXPORT\n")
    else:
        for e in la:
            ofl.write(f"#+latex: {e}")

    if line != "":
        scan_text(line, lines, ofl, outfile)

    return True


def scan_text(line, lines, ofl, outfile):
    """Each of these function will write their respective text. If no match
    is found, they will return line for further processing. If a partial match
    is found, the remaining text will be fed to scan_text again,
    until all text is written.

    if all text is written, return to calling code to get the next line. Otherwise
    scan remaining text for matches
    """
    if not isinstance(line := comments(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := section_commands(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := math_environments(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := special_environments(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := citations(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := fix_bibliography(line, lines, ofl, outfile), str):
        return
    elif not isinstance(line := read_header(line, lines, ofl, outfile), str):
        return
    else:  # regular text
        line = line_latex_to_orgmode(line)
        ofl.write(f"{line}")

    return


def file_latex_to_orgmode(infile, outfile):
    """Covert lines of text from LaTeX format to Orgmode format.

    Parameters:
      infile (str):   Name of the input file.
      outfile (str):  Name of the output file.
    """
    # Open the input and output files:
    # ifl = open(infile, 'r')
    # ofl = open(outfile, "w")
    with open(outfile, "w") as ofl:
        # ofl.write("#+startup: latexpreview")
        iline = 0
        with open(infile, "r") as lines:
            try:
                while True:
                    iline += 1
                    line = next(lines)
                    scan_text(line, lines, ofl, outfile)

            except StopIteration:
                print(f"{str(iline)} lines processed.")
                exit()


def line_latex_to_orgmode(line):
    """Convert a line of LaTeX code to Orgmode.

    Parameters:
      line (str):  The line containing LaTeX code.

    Returns:
      (str):  A line containing Orgmode code.
    """
    # special escapes
    # line = re.sub(r"^%", r"#+latex: %", line)
    # line = line.replace("%", "%")

    # References to equations:
    line = re.sub(r"( [Ee]quations*)[~ ]\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Ee]quations*)\\,\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Ee]quations*)[~ ]", r"\1 ", line)
    line = re.sub(r"( [Ee]quations*)\,", r"\1 ", line)

    line = re.sub(r"( [Ee]qs*)\.*[~ ]\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Ee]qs*)\.*\\,\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Ee]qs*)\.*[~ ]", r"\1.", line)
    line = re.sub(r"( [Ee]qs*)\.*\,", r"\1.", line)

    # References to figures:
    line = re.sub(r"( [Ff]igures*)[~ ]\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Ff]igures*)\\,\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Ff]igures*)[~ ]", r"\1 ", line)
    line = re.sub(r"( [Ff]igures*)\,", r"\1 ", line)

    line = re.sub(r"( [Ff]igs*)\.*[~ ]\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Ff]igs*)\.*\\,\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Ff]igs*)\.*[~ ]", r"\1.", line)
    line = re.sub(r"( [Ff]igs*)\.*\,", r"\1.", line)

    # References to tables:
    line = re.sub(r"( [Tt]ables*)[~ ]\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Tt]ables*)\\,\(([^)]*)\)", r"\1 \2", line)
    line = re.sub(r"( [Tt]ables*)[~ ]", r"\1 ", line)
    line = re.sub(r"( [Tt]ables*)\,", r"\1 ", line)

    line = re.sub(r"( [Tt]abs*)\.*[~ ]\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Tt]abs*)\.*\\,\(([^)]*)\)", r"\1.\2", line)
    line = re.sub(r"( [Tt]abs*)\.*[~ ]", r"\1.", line)
    line = re.sub(r"( [Tt]abs*)\.*\,", r"\1.", line)

    # Misc
    # avoid trivial inline math
    line = re.sub(
        r"\$([0-9A-Za-z]+)?([\^|_])({\d+})([0-9A-Za-z])?\$", r"\1\2\3\4", line
    )
    line = re.sub(r"\$(:?[<|>])*(:?[0-9]*)(\^\{[0-9]*\})\$", r"\1\2\3", line)
    line = re.sub(r"\$(:?[<|>])*(:?[0-9]*)(:?\^)*(:?[0-9])*\$", r"\1\2\3\4", line)
    line = re.sub(r"\$([<|>])*\$", r"\1", line)

    line = re.sub(r"~", "\\\space{}", line)
    line = re.sub(r"$~$", "~", line)
    line = re.sub(r"\$\\sim\$", "~", line)
    line = re.sub(r"\\textasciitilde\{\}", r"~", line)
    line = re.sub(r"\\textperthousand\\", r"‰", line)
    line = re.sub(r"\\textperthousand", r"‰", line)
    # line = re.sub(r"\\,", r" ", line)

    # Cetera:
    line = re.sub(r"^.*\\setcounter[\[{].*\n", r"", line)
    line = re.sub(r"^.*\\setlength[\[{].*\n", r"", line)
    line = re.sub(r"^.*\\newlength[\[{].*\n", r"", line)
    line = re.sub(r"^.*\\addtolength[\[{].*\n", r"", line)
    line = re.sub(r"^.*\\raggedleft.*\n", r"", line)
    line = re.sub(r"^.*\\raggedright.*\n", r"", line)
    line = re.sub(r"^ *\\raggedcolumns *\n", r"", line)
    line = re.sub(r"^ *\\vspace\**\{[^}]*\} *\n", r"\n\n", line)
    line = re.sub(r" *\\vspace\**\{[^}]*\} *", r"\n\n", line)
    line = re.sub(r"^ *\\addvspace\**\{[^}]*\} *\n", r"\n\n", line)
    line = re.sub(r" *\\addvspace\**\{[^}]*\} *", r"\n\n", line)
    line = re.sub(r"^ *\\hspace\**\{[^}]*\} *\n", r"", line)
    line = re.sub(r" *\\hspace\**\{[^}]*\} *", r"", line)
    line = re.sub(r"\\vfill", r"", line)
    line = re.sub(r"^ *\\noindent *\n", r"", line)
    line = re.sub(r" *\\noindent *", r"", line)
    line = re.sub(r" *\\parbox\{[^}]*\} *", r"", line)

    line = re.sub(
        r"\} *\\label *\{([^}]*)\}", r"}\n\\label{\1}", line
    )  # Move trailing \label{} to its own line

    # Begin/end stuff:
    line = re.sub(r"^.*\\end{document}.*\n", r"", line)
    line = re.sub(r"^.*\\end{document}", r"", line)
    line = re.sub(r"(^.*\\bibliographystyle{)(.*)\}", r"bibliographystyle:\2", line)
    line = re.sub(r"^.*\\begin\{center\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{center\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{tiny\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{tiny\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{footnotesize\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{footnotesize\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{scriptsize\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{scriptsize\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{normalsize\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{normalsize\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{[Ll]arge\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{[Ll]arge\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{LARGE\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{LARGE\}.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{[Hh]uge\}.*\n", r"", line)
    line = re.sub(r"^.*\\end\{[Hh]uge\}.*\n", r"", line)

    line = re.sub(r"\\centering", r"", line)
    line = re.sub(r"\\caption\{", r"Caption: ", line)

    # Lists:
    line = re.sub(r"^.*\\begin\{itemize.*\n", r"", line)
    line = re.sub(r"^.*\\end\{itemize.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{enumerate.*\n", r"", line)
    line = re.sub(r"^.*\\end\{enumerate.*\n", r"", line)
    line = re.sub(r"^.*\\begin\{description.*\n", r"", line)
    line = re.sub(r"^.*\\end\{description.*\n", r"", line)
    line = re.sub(r"\\item\[([^]]*)\] *", r"  - \1 :: ", line)
    line = re.sub(r"\\item *", r"  - ", line)

    # Appendices:
    line = re.sub(r"^.*\\begin\{appendices.*\n", r"", line)
    line = re.sub(r"^.*\\end\{appendices.*\n", r"", line)
    line = re.sub(r"\\appendix", r"", line)

    # Font size:
    line = re.sub(r"\\tiny", r"", line)
    line = re.sub(r"\\footnotesize", r"", line)
    line = re.sub(r"\\small", r"", line)
    line = re.sub(r"\\normalsize", r"", line)
    line = re.sub(r"\\large", r"", line)
    line = re.sub(r"\\Large", r"", line)
    line = re.sub(r"\\LARGE", r"", line)
    line = re.sub(r"\\huge", r"", line)
    line = re.sub(r"\\Huge", r"", line)

    # line = re.sub(r'\\newline', r'\n', line)  # '\n' will not match $ later
    line = re.sub(r"\\newline", r"", line)
    line = re.sub(r"\\pagebreak", r"", line)
    line = re.sub(r"\\newpage", r"", line)
    line = re.sub(r"^.*\\newtheorem\{.*\n", r"", line)

    line = re.sub(
        r"^ *\\textbf[* ]*\{([^}]*)\} *$", r"\n**** \1", line
    )  # full-line \textbf appears to be used as a paragraph

    # Labels and references:
    line = re.sub(r"\\label[* ]*\{([^}]*)\}", r"label:\1", line)
    line = re.sub(r"\\ref[* ]*\{([^}]*)\}", r"ref:\1", line)

    # URL:
    line = re.sub(r"\\url[* ]*\{([^}]*)\}", r" \1 ", line)
    line = re.sub(r"\\href[* ]*\{([^}]*)\}\{([^}]*)\}", r" \2 (\1) ", line)

    # Bold, italics, etc:
    line = re.sub(r"\\textbf[* ]*\{([^}]*)\}", r"*\1*", line)
    line = re.sub(r"\\textit[* ]*\{([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\\textsc[* ]*\{([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\\emph[* ]*\{([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\\uline[* ]*\{([^}]*)\}", r"_\1_", line)

    line = re.sub(r"\{\\bf *([^}]*)\}", r"*\1*", line)
    line = re.sub(r"\{\\it *([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\{\\em *([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\{\\sc *([^}]*)\}", r"/\1/", line)

    line = re.sub(r"\\bf\{([^}]*)\}", r"*\1*", line)
    line = re.sub(r"\\it\{([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\\em\{([^}]*)\}", r"/\1/", line)
    line = re.sub(r"\\sc\{([^}]*)\}", r"/\1/", line)

    # Text:
    line = re.sub(r"\\textrm[* ]*\{([^}]*)\}", r"\1", line)

    # # convert inline equations
    line = re.sub(r"\$([^$]*)\$", r"\(\1\)", line)

    # Symbols:
    line = re.sub(
        r" & ", r" | ", line
    )  # Tabular - CHECK - does this screw up eqnarrays?
    line = re.sub(r"\\\\", r" ", line)  # Tabular or eqnarray
    line = re.sub(r"\\&", r"&", line)
    line = re.sub(r"\\ldots\\*", r"...", line)
    line = re.sub(r"\\LaTeX\\*", r"LaTeX", line)
    line = re.sub(r"\\BibTeX\\*", r"BibTeX", line)
    line = re.sub(r"\.\\ ", r". ", line)  # Abbreviation

    ##  Remove spaces:
    # line = re.sub(r"^ {1,99}", r"", line)  # Remove leading spaces
    # line = re.sub(r" {1,99}$", r"", line)  # Remove trailing spaces

    return line


if __name__ == "__main__":
    main()
