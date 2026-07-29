arXiv submission package -- "When Consensus Lies: Fake Redundancy in Multi-Model AI Systems"
De-anonymized preprint built from paper/tex (single author: Shenning Zhang, Chang'an University).

HOW TO SUBMIT
1. arXiv does NOT run BibTeX. The pre-built consensus-lies.bbl is included and MUST be uploaded.
2. Upload these files (a .zip of this folder minus the excluded items below is fine):
     consensus-lies.tex
     consensus-lies.bbl
     references.bib            (optional; not used by arXiv, kept for reference)
     acmart.cls
     ACM-Reference-Format.bst  (optional with .bbl present; harmless)
     acm-jdslogo.png
     figures/*.pdf             (all 7 referenced figures; paths are relative via \graphicspath{{figures/}})
3. Do NOT upload: consensus-lies.pdf (arXiv recompiles), and any .aux/.log/.out/.blg intermediates.
4. Primary class: cs.HC (Human-Computer Interaction). Suggested cross-list: cs.AI, cs.CL, cs.MA.
5. License: choose in the arXiv UI (CC BY 4.0 recommended). No license file is needed in the package.

BUILD (verified locally, self-contained -- class/bst/bib all live in this folder):
   pdflatex consensus-lies
   bibtex   consensus-lies
   pdflatex consensus-lies
   pdflatex consensus-lies
   => 28 pages, 0 undefined references.

DIFFERENCES FROM paper/tex (de-anonymization only; no numbers/claims changed):
 - documentclass: removed "review,anonymous"; added "nonacm" (preprint: no ACM journal footer, DOI, or copyright block; a neutral "Author's Contact Information" line is shown instead).
 - author: Anonymous -> Shenning Zhang <203900907@chd.edu.cn>, Chang'an University, Xi'an, China.
 - removed the placeholder \acmDOI{XXXXXXX.XXXXXXX} and the \acmJournal/\acmVolume/\acmNumber/\acmArticle/\acmMonth metadata; \setcopyright{rightsretained}.
 - restored the real benchmark constructor slug: Microsoft mai-code-1-flash (was "fourth vendor / slug in camera-ready").
 - reworded "for anonymous review" / "anonymous artifact" and removed the anonymous-review acks note.
 - \graphicspath flattened to {figures/} and the 7 referenced figures copied into figures/.
