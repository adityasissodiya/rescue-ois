#!/usr/bin/env python3
"""Check the LaTeX prose of the paper against the ASD-STE100 writing rules.

This script is a help for the writer. It is not a certificate of compliance.

Rule checks (always): sentence length, paragraph length, one-sentence paragraphs,
semicolons, contractions, Latin abbreviations, modal verbs that STE does not approve,
perfect tenses, and possible passive voice.

Vocabulary check (only with --dict): each word must be an approved dictionary word, a
declared technical name, a declared technical verb, or a number. The dictionary file is
not in this repository, because ASD holds the copyright. See paper/STE.md.

Not examined: the part of speech of a word, the length of noun clusters, the text in TikZ
figures, mathematics, quoted text, and the bibliography. The cells of tables and the items
of lists are examined, but they do not count as paragraphs.

Usage:
    python3 scripts/ste_check.py [--dict PATH] [--details] [files ...]
With no files, the script reads the files that main.tex loads with \\input.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # the paper/ directory

MAX_WORDS = 25        # STE rule for descriptive text
MAX_SENTENCES = 6     # STE rule for a paragraph
MAX_SINGLE_RATIO = 0.10

DROP_ENVS = ["tikzpicture", "verbatim", "lstlisting", "axis"]
TABLE_ENVS = {"tabular": 1, "tabular*": 2, "tabularx": 2}   # name -> number of arguments
MATH_ENVS = ["equation", "equation*", "align", "align*", "displaymath", "gather", "gather*",
             "multline", "multline*"]
TEXT_CMDS = ["emph", "textbf", "textit", "textsc", "texttt", "textrm", "mbox", "text",
             "pending", "term", "underline", "textsf"]
REF_CMDS = ["cite", "citep", "citet", "cref", "Cref", "ref", "eqref", "autoref", "pageref",
            "url", "path", "file", "nolinkurl"]
SKIP_TOKENS = {"MATH", "REF", "QUOTE", "MACRO", "NUM"}

IRREGULAR = set("""been begun bought brought built chosen cut done drawn driven fallen felt found
forgotten given gone got gotten grown heard held hidden hit kept known laid led left lost made
meant met paid put read run said seen sent set shown shut sold spent stolen stood taken taught
thought told understood won written broken bound caught dealt fed""".split())
BE = r"(?:is|are|was|were|be|been|being|am)"
HAVE = r"(?:has|have|had)"
ADV = r"(?:not\s+|also\s+|then\s+|[a-z]+ly\s+){0,2}"
PART = r"(?:[a-z]+ed|" + "|".join(sorted(IRREGULAR)) + r")"
PASSIVE_RE = re.compile(r"\b" + BE + r"\s+" + ADV + r"(" + PART + r")\b", re.I)
PERFECT_RE = re.compile(r"\b" + HAVE + r"\s+" + ADV + r"(" + PART + r")\b", re.I)
MODAL_RE = re.compile(r"\b(should|could|would|might|may|shall|ought)\b", re.I)
LATIN_RE = re.compile(r"\b(e\.g\.|i\.e\.|etc\.?|et al\.?|cf\.|vs\.?|viz\.|via|versus|per se)(?=\W|$)", re.I)
CONTRACTION_RE = re.compile(r"\b\w+(n't|'re|'ll|'ve|'d)\b|\b(it's|that's|there's|let's)\b", re.I)
NUMBER_WORDS = set("""zero one two three four five six seven eight nine ten eleven twelve twenty
thirty forty fifty sixty hundred thousand million first second third fourth fifth sixth seventh
eighth ninth tenth half""".split())
BRITISH = {"centre": "center", "centres": "centers", "behaviour": "behavior", "metre": "meter",
           "neighbour": "neighbor", "colour": "color", "defence": "defense",
           "programme": "program", "travelled": "traveled", "labelled": "labeled"}


def take_group(s, i):
    """Return (content, index after the closing brace) for the group that starts at s[i] == '{'."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def replace_cmd(s, name, fn):
    """Replace each \\name[opt]{arg} with fn(arg)."""
    pat = re.compile(r"\\" + name + r"\*?(?![A-Za-z])\s*(\[[^\]]*\])?\s*\{")
    out, pos = [], 0
    while True:
        m = pat.search(s, pos)
        if not m:
            out.append(s[pos:])
            break
        arg, end = take_group(s, m.end() - 1)
        out.append(s[pos:m.start()])
        out.append(fn(arg))
        pos = end
    return "".join(out)


def math_token(m):
    """Replace display mathematics. Keep the full stop if the mathematics has one at its end."""
    body = re.sub(r"\\(end|begin)\{[a-z*]+\}|\\\]|\\\[", "", m.group(0)).rstrip()
    body = re.sub(r"(\\,|\\;|\\!|\\ |\s)+$", "", body)
    return " MATH. " if body.endswith(".") else " MATH "


def tables_to_cells(s):
    """Make each cell of a table a block of its own (marked @C@)."""
    for env, nargs in TABLE_ENVS.items():
        start = "\\begin{" + env + "}"
        end = "\\end{" + env + "}"
        out, pos = [], 0
        while True:
            i = s.find(start, pos)
            if i < 0:
                out.append(s[pos:])
                break
            j = i + len(start)
            m = re.match(r"\s*\[[^\]]*\]", s[j:])
            if m:
                j += m.end()
            for _ in range(nargs):
                while j < len(s) and s[j].isspace():
                    j += 1
                if j < len(s) and s[j] == "{":
                    _, j = take_group(s, j)
            k = s.find(end, j)
            k = len(s) if k < 0 else k
            body = s[j:k]
            body = re.sub(r"\\(toprule|midrule|bottomrule|hline)", " ", body)
            body = re.sub(r"\\(cmidrule|addlinespace)(\([^)]*\))?(\[[^\]]*\])?(\{[^}]*\})?", " ", body)
            body = re.sub(r"\\multicolumn\{[^}]*\}\{[^}]*\}", " ", body)
            body = re.sub(r"\\\\(\[[^\]]*\])?", " & ", body)
            cells = [c.strip() for c in body.split("&")]
            out.append(s[pos:i])
            out.append("".join("\n\n@C@ " + c + "\n\n" for c in cells if c))
            pos = k + len(end)
        s = "".join(out)
    return s


def latex_to_items(src):
    """Return a list of (kind, text). kind is 'head', 'para', 'item' or 'cell'."""
    s = re.sub(r"(?<!\\)%.*", "", src)
    s = s.replace(r"\&", " and ")
    s = tables_to_cells(s)
    for env in DROP_ENVS:
        e = re.escape(env)
        s = re.sub(r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}", " ", s, flags=re.S)
    for env in MATH_ENVS:
        e = re.escape(env)
        s = re.sub(r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}", math_token, s, flags=re.S)
    s = re.sub(r"\\\[.*?\\\]", math_token, s, flags=re.S)
    s = s.replace(r"\$", " USD ").replace(r"\%", " percent ")
    s = re.sub(r"\$[^$]*\$", " MATH ", s, flags=re.S)
    s = re.sub(r"\\\(.*?\\\)", " MATH ", s, flags=re.S)
    s = re.sub(r"``.*?''", " QUOTE ", s, flags=re.S)
    for name in ("section", "subsection", "subsubsection", "paragraph", "title"):
        s = replace_cmd(s, name, lambda a: "\n\n@H@ " + a + "\n\n")
    s = replace_cmd(s, "caption", lambda a: "\n\n" + a + "\n\n")
    s = replace_cmd(s, "footnote", lambda a: "\n\n" + a + "\n\n")
    s = replace_cmd(s, "label", lambda a: "")
    for name in REF_CMDS:
        s = replace_cmd(s, name, lambda a: " REF ")
    for _ in range(3):
        for name in TEXT_CMDS:
            s = replace_cmd(s, name, lambda a: a)
    # theorem-like environments with a title: \begin{theorem}[Title]
    s = re.sub(r"\\begin\{[a-zA-Z*]+\}\s*\[([^\]]*)\]", lambda m: "\n\n@H@ " + m.group(1) + "\n\n", s)
    s = re.sub(r"\\(begin|end)\{[a-zA-Z*]+\}(\{[^}]*\})?", "\n\n", s)
    s = re.sub(r"\\item\s*(\[([^\]]*)\])?",
               lambda m: "\n\n@I@ " + (m.group(2) + ": " if m.group(2) else ""), s)
    s = s.replace("~", " ").replace("---", " - ").replace("--", "-")
    s = re.sub(r"\\(,|;|:|!| |@|/|-)", " ", s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?(\{\})?", " MACRO ", s)
    s = s.replace("{", "").replace("}", "")
    items = []
    for block in re.split(r"\n\s*\n", s):
        block = re.sub(r"\s+", " ", block).strip()
        if not block or not re.search(r"[A-Za-z]", block.replace("MACRO", "").replace("MATH", "")):
            continue
        if block.startswith("@H@"):
            items.append(("head", block[3:].strip()))
        elif block.startswith("@I@"):
            items.append(("item", block[3:].strip()))
        elif block.startswith("@C@"):
            items.append(("cell", block[3:].strip()))
        else:
            items.append(("para", block))
    return items


def sentences(par):
    out = []
    for chunk in par.split("@I@"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for sent in re.split(r"(?<=[.?!])\s+(?=[A-Z(@\d])", chunk):
            sent = sent.strip()
            if sent:
                out.append(sent)
    return out


def count_words(sent):
    """STE count: text in parentheses is a different sentence; a hyphenated group is one word."""
    inner = re.findall(r"\(([^()]*)\)", sent)
    main = re.sub(r"\([^()]*\)", " ", sent)
    def n(t):
        return len([w for w in re.split(r"[\s/]+", t) if re.search(r"[A-Za-z0-9]", w)])
    return n(main), [n(x) for x in inner]


class Vocabulary:
    def __init__(self, dict_path, names_path, verbs_path):
        self.approved = defaultdict(set)     # form -> set of parts of speech
        self.unapproved = defaultdict(list)  # word -> list of (pos, alternatives)
        for e in json.loads(Path(dict_path).read_text(encoding="utf-8")):
            w = e["word"].lower()
            if e["approved"]:
                for form in [w] + [f.lower() for f in e["forms"]]:
                    self.approved[form].add(e["pos"])
                if e["pos"].startswith("noun"):
                    for p in self.plurals(w):
                        self.approved[p].add("noun")
            else:
                alts = "/".join(a.split(" (")[0] for a in e["alts"][:3])
                self.unapproved[w].append((e["pos"], alts))
        self.names = self.read_list(names_path)
        self.verbs = self.read_list(verbs_path)
        self.name_forms = set(self.names)
        for w in self.names:
            self.name_forms.update(self.plurals(w))
        self.verb_forms = set(self.verbs)
        for w in self.verbs:
            self.verb_forms.update(self.verb_inflections(w))

    @staticmethod
    def read_list(path):
        words = set()
        if path and Path(path).exists():
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                line = line.split("#")[0].strip()
                if line:
                    words.update(w.lower() for w in line.split())
        return words

    @staticmethod
    def plurals(w):
        if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
            return [w[:-1] + "ies"]
        if w.endswith("ch"):
            return [w + "es", w + "s"]      # "switches", but "epochs"
        if w.endswith(("s", "x", "sh")):
            return [w + "es"]
        return [w + "s"]

    @staticmethod
    def verb_inflections(w):
        if w.endswith("e"):
            return [w + "s", w + "d"]
        if w.endswith("y") and w[-2] not in "aeiou":
            return [w[:-1] + "ies", w[:-1] + "ied"]
        return [w + "s", w + "ed", w + "es"]

    def classify(self, token):
        """Return (status, note). status: ok, mixed, declared, unapproved, unknown."""
        t = token.lower()
        t = BRITISH.get(t, t)
        if t in NUMBER_WORDS or len(t) == 1:
            return "ok", ""
        if t.endswith("'s"):
            t = t[:-2]
        if t in self.name_forms or t in self.verb_forms:
            return "declared", ""
        if t in self.approved:
            if t in self.unapproved:
                return "mixed", "; ".join(f"not approved as {p}: use {a}" for p, a in self.unapproved[t])
            return "ok", ""
        if t in self.unapproved:
            return "unapproved", "; ".join(f"({p}) use {a}" for p, a in self.unapproved[t])
        # a plural or a past form of an unapproved word
        for base in (t[:-1], t[:-2], t[:-3] + "y"):
            if len(base) > 2 and base in self.unapproved and base not in self.approved:
                return "unapproved", "; ".join(f"({p}) use {a}" for p, a in self.unapproved[base])
        return "unknown", ""


def default_files():
    main = (HERE / "main.tex").read_text(encoding="utf-8")
    main = re.sub(r"(?<!\\)%.*", "", main)
    files = []
    for name in re.findall(r"\\input\{([^}]+)\}", main):
        p = HERE / (name if name.endswith(".tex") else name + ".tex")
        if p.exists() and "data/" not in name:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dict", dest="dict_path", default=None)
    ap.add_argument("--names", default=str(HERE / "ste" / "technical_names.txt"))
    ap.add_argument("--verbs", default=str(HERE / "ste" / "technical_verbs.txt"))
    ap.add_argument("--details", action="store_true", help="print each finding")
    ap.add_argument("--passive", action="store_true", help="also print possible passive voice")
    ap.add_argument("--unused", action="store_true",
                    help="print the declared technical names and verbs that the text does not use")
    args = ap.parse_args()

    files = [Path(f) for f in args.files] or default_files()
    local_dict = HERE / "ste" / "dict.local.json"
    dict_path = args.dict_path or (str(local_dict) if local_dict.exists() else None)
    vocab = Vocabulary(dict_path, args.names, args.verbs) if dict_path else None

    errors, warnings = [], []
    stats = Counter()
    word_status = defaultdict(Counter)
    notes = {}
    longest = []
    for f in files:
        items = latex_to_items(f.read_text(encoding="utf-8"))
        paragraphs = [t for k, t in items if k == "para"]
        for kind, text in items:
            sents = sentences(text) if kind in ("para", "item") else [text]
            if kind in ("para", "item"):
                stats["sentences"] += len(sents)
                if len(sents) > MAX_SENTENCES:
                    errors.append((f.name, "paragraph", f"{len(sents)} sentences: {text[:90]}..."))
            if kind == "para":
                stats["paragraphs"] += 1
                if len(sents) == 1 and count_words(text)[0] > 6:
                    stats["single"] += 1
                    warnings.append((f.name, "one-sentence paragraph", text[:110]))
            for sent in sents:
                n_main, n_inner = count_words(sent)
                stats["words"] += n_main + sum(n_inner)
                if kind in ("para", "item"):
                    longest.append((n_main, f.name, sent))
                    for n in [n_main] + n_inner:
                        if n > MAX_WORDS:
                            errors.append((f.name, "long sentence", f"{n} words: {sent[:150]}"))
                if ";" in sent:
                    errors.append((f.name, "semicolon", sent[:120]))
                for rx, label in ((CONTRACTION_RE, "contraction"), (LATIN_RE, "Latin abbreviation"),
                                  (MODAL_RE, "modal verb"), (PERFECT_RE, "perfect tense")):
                    for m in rx.finditer(sent):
                        errors.append((f.name, label, f"'{m.group(0)}' in: {sent[:120]}"))
                for m in PASSIVE_RE.finditer(sent):
                    warnings.append((f.name, "possible passive", f"'{m.group(0)}' in: {sent[:120]}"))
                    stats["passive"] += 1
                if vocab:
                    for tok in re.findall(r"[A-Za-z][A-Za-z']*", sent):
                        if tok in SKIP_TOKENS:
                            continue
                        if tok.isupper() and len(tok) > 1:
                            # an abbreviation in capital letters must be a declared technical name
                            if tok.lower() in vocab.name_forms:
                                word_status["declared"][tok.lower()] += 1
                            else:
                                word_status["unknown"][tok] += 1
                            continue
                        status, note = vocab.classify(tok)
                        word_status[status][tok.lower()] += 1
                        if note:
                            notes[tok.lower()] = note
        _ = paragraphs

    single_ratio = stats["single"] / max(1, stats["paragraphs"])
    print(f"files: {len(files)}  paragraphs: {stats['paragraphs']}  sentences: {stats['sentences']}  "
          f"words: {stats['words']}")
    if stats["sentences"]:
        print(f"mean sentence length: {stats['words'] / stats['sentences']:.1f} words;  longest: "
              f"{max(longest)[0] if longest else 0}")
    kinds = Counter(k for _, k, _ in errors)
    print("rule errors:", dict(kinds) if kinds else "none")
    print(f"one-sentence paragraphs: {stats['single']} of {stats['paragraphs']} "
          f"({single_ratio:.0%}; the limit is {MAX_SINGLE_RATIO:.0%})")
    print(f"possible passive voice (for a check by a person): {stats['passive']}")
    if vocab:
        for status in ("unapproved", "unknown", "mixed", "declared"):
            c = word_status[status]
            print(f"words {status}: {len(c)} different, {sum(c.values())} total")
        if word_status["unapproved"]:
            print("\nNOT APPROVED (replace, or declare as a technical name or verb):")
            for w, n in word_status["unapproved"].most_common():
                print(f"  {w} x{n}: {notes.get(w, '')[:110]}")
        if word_status["unknown"]:
            print("\nNOT IN THE DICTIONARY AND NOT DECLARED:")
            print("  " + ", ".join(f"{w} x{n}" for w, n in word_status["unknown"].most_common()))
        if args.unused:
            seen = {w.lower() for w in word_status["declared"]}
            unused = sorted(w for w in vocab.names if not ({w} | set(vocab.plurals(w))) & seen)
            unused += sorted(w for w in vocab.verbs
                             if not ({w} | set(vocab.verb_inflections(w))) & seen)
            print("\nDECLARED BUT NOT USED: " + (", ".join(unused) if unused else "none"))
        if args.details and word_status["mixed"]:
            print("\nAPPROVED FOR ONE PART OF SPEECH ONLY (examine each use):")
            for w, n in word_status["mixed"].most_common():
                print(f"  {w} x{n}: {notes.get(w, '')[:110]}")
    else:
        print("vocabulary: not examined (no dictionary file; see paper/STE.md)")
    if args.details or errors:
        for name, kind, text in errors:
            print(f"ERROR {name}: {kind}: {text}")
    if args.details:
        for name, kind, text in warnings:
            if kind != "possible passive" or args.passive:
                print(f"note  {name}: {kind}: {text}")
    elif args.passive:
        for name, kind, text in warnings:
            if kind == "possible passive":
                print(f"note  {name}: {kind}: {text}")
    bad = len(errors) + (len(word_status["unapproved"]) + len(word_status["unknown"]) if vocab else 0)
    if single_ratio > MAX_SINGLE_RATIO:
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
