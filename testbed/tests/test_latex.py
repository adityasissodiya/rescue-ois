"""The paper's testbed numbers come out of the committed results."""

from pathlib import Path

from aas_testbed.latex import MACROS, write_latex

RESULTS = Path(__file__).resolve().parents[1] / "results"


def test_every_macro_resolves(tmp_path):
    written = {p.name: p for p in write_latex(RESULTS, tmp_path)}
    macros = written["testbed_macros.tex"].read_text()
    for m in MACROS:
        assert f"\\newcommand{{\\{m.name}}}" in macros
    assert "--" not in macros.split("\n", 2)[2]  # no macro came out empty
    assert written["tab_policy_costs.tex"].read_text().count(r"\\") == 7
