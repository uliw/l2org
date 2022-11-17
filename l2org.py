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

debug = True


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
        sys.stderr.write("Input and output file have the same name: " + outfile + "\n")

    print("Input file:  " + args.infile)

    print("Output file: " + outfile)

    return args.infile, outfile


def read_header(nl, lines, ofl) -> bool:
    """header lines are all lines between \documentclass and \begin{document}
    precede all read lines with #+latexheader:

    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    return values:
    header: True of header data was written
    """

    # nl: str = next(lines)
    header: bool = False
    s: str = ""

    if "documentclass" in nl:
        header = True
        while "begin{document}" not in nl:
            if nl.strip() != "":
                if "\\author" in nl:
                    s = re.search(r"\\author{.*\}", nl).group()[8:-1]
                    nl = f"#+author: {s}\n"
                elif "\\date" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    nl = f"#+date: {s}\n"
                elif "\\title" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    nl = f"#+title: {s}\n"
                elif "\\email" in nl:
                    s = re.search(r"\{.*\}", nl).group()[1:-1]
                    nl = f"#+email: {s}\n"
                else:
                    nl = f"#+latex_header: {nl}"

                ofl.write(f"{nl}")
            nl: str = next(lines)

    return header


def get_string_between_brackets(brackets: str, string: str) -> tuple[str, int, int]:
    """return the strinf delimited by two brackets
    Arguments:
     brackets = "{}"
     string = "{Hello"}. Must start with first bracket!
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


def citations(nl, lines, ofl) -> str:
    """Convert to Org type citations
    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    Return true if citation was found
    """

    i1 = i1 = j1 = j2 = 0  # counter
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
    if not "\cite" in nl:
        return False

    while nl.count("{") != nl.count("}"):
        nl = f"{nl} {next(lines)}"
        nl = nl.replace("\n", " ")
        i = i + 1
        if debug:
            print(f"i = {i}")
        if i > 10:
            raise ValueError(f"Unable to find end of citation in {nl}")

    # what kind of cite are we dealing with
    # find the first cite expression
    temp = re.search(r"\\cite.*?\{", nl).group()
    if debug:
        print(f"temp = {temp}")

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
        if debug:
            print(f"temp = {temp}")
            print(f"ct = {ct}")
            print(f"ss = {ss}")
            print(f"cs = {cs}")
            print(f"cl = {cl}")
            print()
    else:  # citation with optional arguments
        # get first citation
        temp = re.search(r"\\cit[a-z]+\[", nl).group()
        ct = temp[1:-1]  # citation type
        if debug:
            print(f"ct = {ct}")
        # get entire string starting with citation
        temp = nl[nl.index(temp) :]
        print(f"temp = {temp}")
        # get text between first brackets
        b1, j1, i1 = get_string_between_brackets("[]", temp)
        if b1:
            cs = ct + "[" + b1 + "]"  # build citation string
        else:
            cs = ct + "[]"

        if debug:
            print(f"b1 cs = {cs}")

        # test if second pair of brackets
        if temp[i1 + 1] == "[":
            b2, j2, i2 = get_string_between_brackets("[]", temp[i1 + 1 :])
            i1 = i1 + i2
            if b2:
                cs = cs + "[" + b2 + "]"
            else:
                cs = cs + "[]"
        # get citations list
        if debug:
            print(f"b2 cs = {cs}")
        cl = re.search(r"\{.*?\}", temp[i1 + 1 :]).group()[1:-1]
        if debug:
            print(f"cl = {cl}")

    # create complete cite expression
    ce = "\\" + cs + "{" + cl + "}"
    print(f"ce for split = {ce}")
    # split string into before and after center
    pre_text, post_text = nl.split(ce)
    if debug:
        print(f"pre_text = {pre_text}\n")
        print(f"post_text = {post_text}\n")

    # build org mode syntax
    cl_list = cl.split(",")
    cl = ""
    for e in cl_list:  # org mode citation list
        cl = cl + "&" + e.strip() + ";"

    cl = cl[:-1]

    if debug:
        print(f"cl = {cl}")
        print(f"b1 = {b1}")
        print(f"b2= {b2}")
        
    if b1 and not b2:
        cs = f"{ct}:{b1};{cl};"
    elif b1 and b2:
        cs = f"{ct}:{b1};{cl};{b2}"
    elif not b1 and b2:
        cs = f"{ct}:;{cl};{b2}"
    else:  # regular citation
        cs = f"{ct}:{cl}"

    cs = f"[[{cs}]]"
    if debug:
        print(f"cs = {cs}")

    line = line_latex_to_orgmode(f"{pre_text}{cs}")
    ofl.write(line)

    if post_text != "":
        # check for more citations
        if not citations(post_text, lines, ofl):
            ofl.write(post_text)

    return True


def section_commands(nl, lines, ofl) -> bool:
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
    if not ("chapter" in nl or "section" in nl):
        return False

    # test if multiline
    while nl.count("{") != nl.count("}"):
        nl = f"{nl}\n{next(lines)}"
        i = i + 1
        if i > 3:
            raise ValueError(f"Unable to find end of section in {nl}")

    # extract section stype and string
    section_string = re.search(r"^.*?\}", nl).group()
    # test if short format
    if "[" in section_string:
        section_type = re.search(r"^.*?\[", nl).group()[1:-1]
        # ss = r"\\" + section_type + ".*\}"
        # section_string = re.search(ss, nl).group()
        short_title = re.search(r"\[.*?\]", section_string).group()
        short_title = f"PROPERTIES:\n:ALT_TITLE: {short_title}\n:END:\n"
    else:
        section_type = re.search(r"^.*?\{", nl).group()[1:-1]

    section_title = re.search(r"\{.*?\}", section_string).group()[1:-1]

    # test if text after caption
    text_after = nl.split(section_string)[1]

    # get section type
    if section_type in marker_dict:
        marker = marker_dict[section_type]
    else:
        raise ValueError(f"marker = {section_type} is not valid")

    if debug:
        print(f"marker = {marker} {section_title}")
    # build section text
    nl = f"{marker}{section_title}\n"
    if not short_title == "":
        nl = f"{nl}{short_title}"
    if not text_after == "":
        nl = f"{nl}{text_after}"

    ofl.write("%s" % (nl))
    return True


def special_environments(nl, lines, ofl) -> bool:
    """Some environments a better handled by a latex export block
    parameters:
    nl: current line
    lines: io_wrapper
    ofl: iowrapper

    return values: sp: True if environment was written
    """

    is_env = ""
    # list of environments you want to keep in the running text, rather
    # than wrapping in a latex export block
    exclude_env = []  # ["equation", "table"]
    is_env = re.search(r"^\\begin{.*?\}", nl)

    if is_env is not None:
        env = is_env.group()[7:-1]
        if env in exclude_env:
            return False
        if debug:
            print(f"env = {env}")
        ofl.write("\n#+BEGIN_EXPORT latex\n")
        while f"end{{{env}}}" not in nl:
            if nl.strip() != "":
                ofl.write(nl)
                nl: str = next(lines)
        ofl.write(f"\\end{{{env}}}\n")
        ofl.write("#+END_EXPORT\n\n")
    else:
        return False

    return True


def file_latex_to_orgmode(infile, outfile):
    """Covert lines of text from LaTeX format to Orgmode format.

    Parameters:
      infile (str):   Name of the input file.
      outfile (str):  Name of the output file.
    """
    # Open the input and output files:
    # ifl = open(infile, 'r')
    ofl = open(outfile, "w")
    # ofl.write("#+startup: latexpreview")

    iline = 0
    with open(infile, "r") as lines:
        try:
            while True:
                iline += 1

                # Read data line and extract column contents:
                # line = ifl.readline()
                line = next(lines)
                if read_header(line, lines, ofl):
                    pass
                elif section_commands(line, lines, ofl):
                    pass
                elif special_environments(line, lines, ofl):
                    pass
                elif citations(line, lines, ofl):
                    pass
                else:
                    line = line_latex_to_orgmode(line)
                    # line = citations(line, lines, ofl)
                    ofl.write("%s" % (line))
                # if debug: print(iline, line)
        except StopIteration:
            print(str(iline) + " lines processed.")
            exit

    # Close output file
    ofl.close()

    # Reopen output file and remove empty lines:
    # Reopen the output (Org mode) file and read its contents:
    ofl = open(outfile, "r")
    lines = ofl.read()  # Returns lines as a single string, including '\n'
    ofl.close()

    # Remove empty lines:
    for itr in range(10):
        lines = re.sub(r" *\n *\n *\n", r"\n\n", lines)

    # Write the result back to the same file:
    ofl = open(outfile, "w")
    ofl.write(lines)
    ofl.close()
    return


def line_latex_to_orgmode(line):
    """Convert a line of LaTeX code to Orgmode.

    Parameters:
      line (str):  The line containing LaTeX code.

    Returns:
      (str):  A line containing Orgmode code.
    """

    # special escapes
    line = re.sub(r"^%", r"#+latex: %", line)
    line = line.replace("\%", "%")

    # Title, author, etc:
    line = re.sub(r"\\email[* ]*\{([^}]*)\}", r"#+email:  \1", line)
    line = re.sub(r"\\date[* ]*\{([^}]*)\}", r"#+date:   \1", line)

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

    # Spaces:
    line = re.sub(r"\~", r"\\nbsp{}", line)
    line = re.sub(r"\\,", r" ", line)

    # Cetera:
    # line = re.sub(r"^.*\\maketitle.*\n", r"", line)
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
    line = re.sub(r"\\bibliographystyle\{(.*?)\}", r"bibliographystyle:\1", line)
    line = re.sub(r"\\bibliography\{(.*?)\}", r"bibliography:\1", line)
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
    line = re.sub(r"\\item\[([^]]*)\] *", r"+ \1 :: ", line)
    line = re.sub(r"\\item *", r"+ ", line)

    # Verbatim:
    line = re.sub(r"^.*\\begin\{verbatim.*\n", r"#+begin_src text\n", line)
    line = re.sub(r"^.*\\end\{verbatim.*\n", r"#+end_src text\n", line)

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

    # Beamer frames/slides:
    line = re.sub(r"^.*\\frame[\[{].*\n", r"", line)  # Followed by [ or {
    line = re.sub(
        r"^ *\\frametitle[* ]*\{([^}]*)\} *\n", r"\n*** \1", line
    )  # Assume \section and \subsection are converted to * and **
    line = re.sub(
        r" *\\frametitle[* ]*\{([^}]*)\} *", r"\n*** \1", line
    )  # Assume \section and \subsection are converted to * and **

    line = re.sub(
        r"^ *\\begin\{block\}[* ]*\{\} *\n", r"", line
    )  # Block w/o title -> nothing
    line = re.sub(
        r" *\\begin\{block\}[* ]*\{\} *", r"", line
    )  # Block w/o title -> nothing
    line = re.sub(
        r"^ *\\begin\{block\}[* ]*\{([^}]*)\} *\n", r"\n**** \1", line
    )  # Assume \section, \subsection and \frametitle are converted to *, ** and ***
    line = re.sub(
        r" *\\begin\{block\}[* ]*\{([^}]*)\} *", r"\n**** \1", line
    )  # Assume \section, \subsection and \frametitle are converted to *, ** and ***
    line = re.sub(r"^ *\\end\{block\} *\n", r"", line)

    line = re.sub(r"^ *\\begin\{columns\}[* ]* *\n", r"", line)
    line = re.sub(r"^ *\\end\{columns\} *\n", r"", line)
    line = re.sub(r"^ *\\begin\{column\}[* ]*\{.*\} *\n", r"", line)
    line = re.sub(r"^ *\\end\{column\} *\n", r"", line)

    line = re.sub(r"^ *\\uncover<[0-9]*->\{ *\n", r"", line)
    line = re.sub(r"\\uncover<[0-9]*->\{", r"", line)

    # My Beamer macros:
    line = re.sub(r"\{\\bluetext ([^{}]*)\}", r" blue: \1", line)
    line = re.sub(r"\{\\redtext ([^{}]*)\}", r" red: \1", line)
    line = re.sub(r"\{\\purpletext ([^{}]*)\}", r" purple: \1", line)
    line = re.sub(r"\{\\greentext ([^{}]*)\}", r" green: \1", line)
    line = re.sub(r"\{\\yellowtext ([^{}]*)\}", r" yellow: \1", line)
    line = re.sub(r"\\bluetext ", r"blue: ", line)
    line = re.sub(r"\\redtext ", r"red: ", line)
    line = re.sub(r"\\purpletext ", r"purple: ", line)
    line = re.sub(r"\\greentext ", r"green: ", line)
    line = re.sub(r"\\yellowtext ", r"yellow: ", line)
    line = re.sub(r"\\normaltext", r"", line)

    # Labels and references:
    line = re.sub(r"\\label[* ]*\{([^}]*)\}", r"label:\1", line)
    line = re.sub(r"\\ref[* ]*\{([^}]*)\}", r"ref:\1", line)

    # Citations:
    # work just fine using latex syntax and are difficult to parse
    # properly
    # line = re.sub(r"\\cite[pt]*[* ]*\{([^}]*)\}", r"[[cite:&\1]]", line)

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

    # Math text:
    line = re.sub(r"\\mathbf[* ]*\{([^}]*)\}", r"*\1*", line)
    line = re.sub(r"\\mathrm[* ]*\{([^}]*)\}", r"\1", line)
    line = re.sub(r" *\\textgreater\{\} *", r" > ", line)
    line = re.sub(r" *\\textless\{\} *", r" < ", line)
    line = re.sub(r"\\textasciicircum\{\}", r"^", line)
    line = re.sub(r"\\textasciicircum", r"^", line)

    # Spaces in inline equations:
    line = re.sub(r"^([^\$]*\$) ", r"\1", line)  # Remove space after first $ in line
    line = re.sub(r" (\$[^$]*$)", r"\1", line)  # Remove space before last $ in line

    # Inline -> full equations:
    line = re.sub(
        r"^ *\$([^$]*)\$ *$", r"\[ \1 \]\n", line
    )  # Replace whole-line $...$ with \[...\]
    line = re.sub(
        r" +\$ +([^$]+) +\$ +", r"$ \1 $", line
    )  # Replace leftover " $ text $ " text $"

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

    # Fix equations:
    line = re.sub(r"\\int *\\int *\\int", r"\\iiint", line)  # Need amsmath
    line = re.sub(r"\\int *\\int", r"\\iint", line)  # Need amsmath
    line = re.sub(
        r"\|\|([^|]*)\|\|", r"$\\norm{\1}$", line
    )  # Absolute value vector ||v|| -> $||v||$

    # Footnote: ISSUE: may span multiple lines...
    line = re.sub(
        r"\\footnote\{([^}]*)\}", r" [fn:1: \1]", line
    )  # Single-line footnote
    line = re.sub(
        r"\\footnote\{", r" [fn:1: ", line
    )  # Left over: multi-line footnote: DiY

    # Remove spaces:
    line = re.sub(r"^ {1,99}", r"", line)  # Remove leading spaces
    line = re.sub(r" {1,99}$", r"", line)  # Remove trailing spaces

    return line


if __name__ == "__main__":
    main()