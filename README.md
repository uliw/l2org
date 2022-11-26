- [l2org a LaTeX to emacs org mode converter](#org3a68e76)


<a id="org3a68e76"></a>

# l2org a LaTeX to emacs org mode converter

****Purpose:**** Enable full roundtrip latex to org-mode to latex conversion, e.g., when collaborating with someone who works with latex.

****Limitations:**** Many latex features have no corresponding org-representation, and more often than not it is better to keep the original latex. E.g., there is almost no benefit to converting tables to org-syntax. As such, this converter will simply wrap all special environments in latex-export blocks. See the `exclude_env` variable to specify a list of environments that should not be wrapped.

****Features:**** l2h does a reasonable job of converting text and citations into org-mode. Note that this version will convert to org-ref v3 citation syntax (<https://github.com/jkitchin/org-ref>).

****Requirements:**** python >= 3.9 and pathlib

****Acknowledgments:**** This code is loosely based on <https://github.com/MarcvdSluys/Orgmode-convert>

****License:**** GPL v3