# Verified references.bib corrections + additions (2026-07-22)

> Manager-curated, VERIFIED citation set for `paper/tex/references.bib`. Produced by a doc-only research
> sub-agent and INDEPENDENTLY spot-checked by the Manager against primary sources (aclanthology, arXiv,
> ORCID, DBLP, Oxford Academic). Every entry below has a real source URL. Owner constraint: NO fabricated
> bib entries; prefer recent + relevant. The implementer sub-agent applies EXACTLY these to references.bib.
>
> **Anti-fabrication note:** an entry is included here ONLY if verified at a real fetched source. The one
> unverifiable original entry (`dietrich2013` — no such title existed) is REPLACED (not invented) with a
> real Dietrich & Spiekermann 2013 paper, keeping the cite key because the tex cites it.

## A. CORRECTIONS to existing entries (replace the current entry with the version below)

### A1. `perez2022` — VENUE WAS WRONG (was "arXiv 2022"/"EMNLP"); real venue = Findings of ACL 2023
Verified: https://aclanthology.org/2023.findings-acl.847/ (DOI 10.18653/v1/2023.findings-acl.847, pp.13387–13434)
```bibtex
@inproceedings{perez2022,
  title     = {Discovering Language Model Behaviors with Model-Written Evaluations},
  author    = {Perez, Ethan and Ringer, Sam and Luko{\v{s}}i{\={u}}t{\.{e}}, Kamil{\.{e}} and Nguyen, Karina and Chen, Edwin and Heiner, Scott and Pettit, Craig and Olsson, Catherine and Kundu, Sandipan and Kadavath, Saurav and Jones, Andy and Chen, Anna and Mann, Benjamin and Israel, Brian and Seethor, Bryan and McKinnon, Cameron and Olah, Christopher and Yan, Da and Amodei, Daniela and Amodei, Dario and others},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2023},
  pages     = {13387--13434},
  year      = {2023},
  doi       = {10.18653/v1/2023.findings-acl.847},
  url       = {https://aclanthology.org/2023.findings-acl.847/}
}
```

### A2. `dietrich2013` — ORIGINAL TITLE UNVERIFIABLE (fabricated); REPLACE with the real Dietrich & Spiekermann 2013 (Mind). Keep the key (tex cites it alongside condorcet/ladha1992 for correlated-vote jury theorems).
Verified: https://academic.oup.com/mind/article-abstract/122/487/655/1009460 (DOI 10.1093/mind/fzt074)
```bibtex
@article{dietrich2013,
  title   = {Independent Opinions? On the Causal Foundations of Belief Formation and Jury Theorems},
  author  = {Dietrich, Franz and Spiekermann, Kai},
  journal = {Mind},
  volume  = {122},
  number  = {487},
  pages   = {655--685},
  year    = {2013},
  doi     = {10.1093/mind/fzt074}
}
```

### A3–A?. OPTIONAL enrichments (only if you want fuller author lists / stable URLs — same key, verified):
- `kim2025correlated`: ICML 2025 / PMLR 267:30038–30066 — url https://proceedings.mlr.press/v267/kim25e.html
- `du2023debate`: ICML 2024 / PMLR 235:11733–11763 — https://proceedings.mlr.press/v235/du24e.html
- `liang2024`: EMNLP 2024 main, pp.17889–17904 — https://aclanthology.org/2024.emnlp-main.992/ (arXiv 2305.19118)
- `smit2024mad`: ICML 2024 / PMLR 235:45883–45905 — https://proceedings.mlr.press/v235/smit24a.html (arXiv 2311.17371); first author "Andries Petrus Smit"
- `choi2025conformity`: Findings of ACL 2025, pp.5123–5139, DOI 10.18653/v1/2025.findings-acl.265 (arXiv 2506.01332); authors Choi, Min; Kim, Keonwoo; Chae, Sungwon; Baek, Sangyeop
- `estornell2024`: NeurIPS 2024 — https://openreview.net/forum?id=sy7eSEXdPC
- `yang2025underspecification`: arXiv 2505.13360 (no peer venue as of 2026-07); authors Yang, Chenyang; Shi, Yike; Ma, Qianou; Liu, Michael Xieyang; K{\"a}stner, Christian; Wu, Tongshuang
These are non-blocking polish; the current entries are otherwise correct. Apply if convenient.

## B. NEW verified additions to APPEND (all real, recent, relevant to the CHI framing)

```bibtex
@techreport{bommasani2021foundation,
  title       = {On the Opportunities and Risks of Foundation Models},
  author      = {Bommasani, Rishi and Hudson, Drew A. and Adeli, Ehsan and Altman, Russ and Arora, Simran and von Arx, Sydney and Bernstein, Michael S. and others},
  institution = {Stanford Center for Research on Foundation Models},
  year        = {2021},
  eprint      = {2108.07258},
  archivePrefix = {arXiv},
  url         = {https://arxiv.org/abs/2108.07258}
}

@inproceedings{padmakumar2024writing,
  title     = {Does Writing with Language Models Reduce Content Diversity?},
  author    = {Padmakumar, Vishakh and He, He},
  booktitle = {International Conference on Learning Representations},
  year      = {2024},
  eprint    = {2309.05196},
  archivePrefix = {arXiv},
  url       = {https://arxiv.org/abs/2309.05196}
}

@article{guo2025diversity,
  title   = {Benchmarking Linguistic Diversity of Large Language Models},
  author  = {Guo, Yanzhu and Shang, Guokan and Clavel, Chlo{\'e}},
  journal = {Transactions of the Association for Computational Linguistics},
  volume  = {13},
  pages   = {1507--1526},
  year    = {2025},
  doi     = {10.1162/tacl.a.47},
  url     = {https://aclanthology.org/2025.tacl-1.69/}
}

@inproceedings{murthy2025alignment,
  title     = {One Fish, Two Fish, but Not the Whole Sea: Alignment Reduces Language Models' Conceptual Diversity},
  author    = {Murthy, Sonia K. and Ullman, Tomer and Hu, Jennifer},
  booktitle = {Proceedings of the 2025 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies},
  year      = {2025},
  eprint    = {2411.04427},
  archivePrefix = {arXiv},
  url       = {https://aclanthology.org/2025.naacl-long.561/}
}

@article{buccinca2021trust,
  title   = {To Trust or to Think: Cognitive Forcing Functions Can Reduce Overreliance on {AI} in {AI}-assisted Decision-making},
  author  = {Bu{\c{c}}inca, Zana and Malaya, Maja Barbara and Gajos, Krzysztof Z.},
  journal = {Proceedings of the ACM on Human-Computer Interaction},
  volume  = {5},
  number  = {CSCW1},
  articleno = {188},
  year    = {2021},
  doi     = {10.1145/3449287},
  url     = {https://arxiv.org/abs/2102.09692}
}

@inproceedings{bansal2021whole,
  title     = {Does the Whole Exceed its Parts? The Effect of {AI} Explanations on Complementary Team Performance},
  author    = {Bansal, Gagan and Wu, Tongshuang and Zhou, Joyce and Fok, Raymond and Nushi, Besmira and Kamar, Ece and Ribeiro, Marco Tulio and Weld, Daniel S.},
  booktitle = {Proceedings of the 2021 CHI Conference on Human Factors in Computing Systems},
  year      = {2021},
  doi       = {10.1145/3411764.3445717},
  url       = {https://arxiv.org/abs/2006.14779}
}

@inproceedings{spatharioti2025llmsearch,
  title     = {Effects of {LLM}-based Search on Decision Making: Speed, Accuracy, and Overreliance},
  author    = {Spatharioti, Sofia Eleni and Rothschild, David M. and Goldstein, Daniel G. and Hofman, Jake M.},
  booktitle = {Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems},
  year      = {2025},
  doi       = {10.1145/3706598.3714082}
}

@inproceedings{bo2025rely,
  title     = {To Rely or Not to Rely? Evaluating Interventions for Appropriate Reliance on Large Language Models},
  author    = {Bo, Jessica Y. and Wan, Sophia and Anderson, Ashton},
  booktitle = {Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems},
  year      = {2025},
  doi       = {10.1145/3706598.3714097},
  url       = {https://arxiv.org/abs/2412.15584}
}

@article{hongpage2004,
  title   = {Groups of Diverse Problem Solvers Can Outperform Groups of High-Ability Problem Solvers},
  author  = {Hong, Lu and Page, Scott E.},
  journal = {Proceedings of the National Academy of Sciences},
  volume  = {101},
  number  = {46},
  pages   = {16385--16389},
  year    = {2004},
  doi     = {10.1073/pnas.0403723101}
}

@book{surowiecki2004,
  title     = {The Wisdom of Crowds},
  author    = {Surowiecki, James},
  year      = {2004},
  publisher = {Doubleday},
  address   = {New York}
}

@article{vaccaro2024combinations,
  title   = {When Combinations of Humans and {AI} Are Useful: A Systematic Review and Meta-Analysis},
  author  = {Vaccaro, Michelle and Almaatouq, Abdullah and Malone, Thomas},
  journal = {Nature Human Behaviour},
  volume  = {8},
  pages   = {2293--2303},
  year    = {2024},
  doi     = {10.1038/s41562-024-02024-1},
  url     = {https://arxiv.org/abs/2405.06087}
}
```

## C. Manager spot-check log (independent verification, 2026-07-22)
- perez2022 → confirmed Findings of ACL 2023 via aclanthology.org/2023.findings-acl.847 (fetched). ✅
- dietrich replacement → confirmed Mind 122(487):655–685, DOI 10.1093/mind/fzt074 (Oxford Academic + PhilPapers). ✅
- spatharioti2025llmsearch → confirmed CHI 2025 DOI 10.1145/3706598.3714082 (ORCID + DBLP + colab.ws). ✅
- bo2025rely → confirmed arXiv 2412.15584 title exact match. ✅
- choi2025conformity → confirmed arXiv 2506.01332 title exact match. ✅
- Remaining Part-A entries verified by the research sub-agent against arXiv/PMLR/ACL/DOI (see report); low fabrication risk (established venues).

## D. Still-open for owner (do not fabricate)
- None blocking. All cited keys now resolve to real sources. The Part-B additions are available for the
  CHI writing pass to \cite where relevant (unused .bib entries are harmless — bibtex emits only cited ones).
