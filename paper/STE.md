# Simplified Technical English in this draft

The text in `sections/` is written to the rules of ASD-STE100 (Simplified Technical
English, Issue 9) as far as a script and one review can show. **It is not certified.** No
person with STE training has examined it, and the script cannot check the rules that need
judgment. Read this file before you claim compliance to anybody.

STE was made for maintenance documentation. A research paper is descriptive writing, so the
draft follows the rules for descriptive text (for example 25 words per sentence, not 20).

## How to run the check

```
cd paper
python3 scripts/ste_check.py                 # summary; exit code 1 if something fails
python3 scripts/ste_check.py --details       # each finding, and the words to examine by hand
python3 scripts/ste_check.py --passive       # each "be + participle" form
python3 scripts/ste_check.py --unused        # declared technical words that the text does not use
python3 scripts/ste_check.py sections/05_limits.tex   # one file
```

Result on 11 November 2026: 14 files, 167 paragraphs, 826 sentences, 11,123 words, mean
sentence length 13.5 words, longest sentence 25 words. No rule errors, no unapproved word,
no unknown word.

## What the script checks

| Rule | Limit in the script |
|---|---|
| Sentence length | 25 words; text in parentheses counts as its own sentence |
| Paragraph and list-item length | 6 sentences |
| One-sentence paragraphs | not more than 1 in 10 |
| Punctuation | no semicolons |
| Verb forms | no contractions, no perfect tenses (`has done`), no `should could would might may shall ought` |
| Latin abbreviations | none (`e.g.`, `i.e.`, `etc.`, `via`, `versus`) |
| Vocabulary | each word is approved in the dictionary, or is declared in `ste/` as a technical name or verb |

It reads the files that `main.tex` inputs (not `data/`), including headings, captions, list
items and table cells.

## What the script does not check

- **Part of speech and meaning.** A word that the dictionary approves as a noun passes when
  it is used as a verb. The script lists these words ("approved for one part of speech
  only", 19 words, 341 uses). I examined each use on 11 November 2026 and changed two
  (`moves the clock back`, `below the threshold`). Do this again after an edit.
- **Passive voice.** The script only lists forms such as `is done`. 21 are left. All of them
  give a state (`is not done`, `is known`, `is isolated`, `are related`). STE lets descriptive
  text use these, but a reviewer can decide differently.
- Noun clusters of more than three words, one topic for each paragraph, and articles.
- Mathematics, the text in the two TikZ figures, text in quotation marks (quotations from
  sources stay as the source wrote them), and the bibliography.
- `main.tex`: title, names, addresses, keywords, the funding sentence and the draft note.

## The word list

`ste/dict.local.json` is the vocabulary that the script uses: 2,275 entries. It was made from
ste.valaratomics.com, a web page that shows a reproduction of the Issue 9 dictionary table
for review. It is **not** the official dictionary. It lacks some word forms and some nouns,
so a word can fail here and be approved in the standard, or the other way.

The file is copyright material of ASD. It is listed in `.git/info/exclude`: do not commit
it and do not publish it. Without the file the script still checks the writing rules and
prints `vocabulary: not examined`. The official standard is free on request from ASD
(asd-ste100.org). Check the declared words against it before a submission says "STE".

## Technical names and technical verbs

STE lets a writer use words that are not in the dictionary when they are technical names or
technical verbs. The draft declares 169 names in `ste/technical_names.txt` and 9 verbs in
`ste/technical_verbs.txt`, each under the category that I selected for it. These are the
judgment calls a person must confirm:

- Words that are ordinary English but are terms in this paper: `valid` (a certificate with a
  quorum of signatures), `view`, `run`, `design`, `cost`, `real` (real time), `public`
  (public key), `random`, `loyal`, `hostile`, `consent`, `function`, `line`, `call`.
- Abbreviations in capital letters must be declared too (`SCADA`, `CAP`, `TLA`, `TLC`, and
  the design names `NE`, `QO`, `SL`, `TS`).
- `appendix`, `corollary`, `figure` and `hypothesis` show as "not used" because the text
  makes them through `\cref` or uses only the plural.

## Decisions and known deviations

- **Abstract in four paragraphs.** The six-sentence rule needs this. IEEE style wants one
  paragraph: join them at submission and note that the abstract then breaks the rule.
- **Title.** "Command Succession *with* a Hostile Commander", because `under` is not
  approved. `email.md` still says "under".
- **American spelling** (`center`, `color`, `gray`), as in the STE dictionary.
- **Funding sentence** in the acknowledgment keeps the wording of the funders.
- **Frequent replacements**, so that an edit does not bring the words back:

| Not approved or not in the list | Used in the draft |
|---|---|
| need, require | is necessary, must |
| so, therefore, hence | thus |
| any, every, both, another | each, all, the two, a different / a second |
| later, earlier, old | subsequent, previous |
| at least, at most, upper bound | not less than / or more, not more than / or less, maximum |
| single, simple | one, unity of command (the term), short |
| study, evidence, statement | analysis, data / proof, result |
| planned | prepared |
| sees, learns | gets, knows |
| under, over, within, via | with / in, more than, in, through |
| renew (verb) | sign a renewal, get a new lease |
| allow, permit | let, can |
