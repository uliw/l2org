- [l2org a LaTeX to emacs org mode converter](#orgd45dd37)


<a id="orgd45dd37"></a>

# l2org a LaTeX to emacs org mode converter

Purpose: Enable full roundtrip latex to org-mode to latex conversion, e.g., when collaborating with someone who works with latex.

Limitations: Many latex features have no corresponding org-representation, and more often than not it is better to keep the original latex. E.g., there is almost no benefit to converting figures and tables to org-syntax. As such, this converter will simply wrap all special environments in latex-export blocks.

Features: l2h does a reasonable job of converting text and citations into org-mode. Note that this version will convert to org-ref v3 citation syntax (<https://github.com/jkitchin/org-ref>).

Acknowledgments: This code is loosely based on <https://github.com/MarcvdSluys/Orgmode-convert>