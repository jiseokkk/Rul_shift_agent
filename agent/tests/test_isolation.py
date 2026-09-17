"""정보 차단: tools / llm / runner 는 채점 전용 모듈(data.truth, eval)을 import 하지 않는다."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
FORBIDDEN = ("src.data.truth", "src.eval")


def _imports(py: Path) -> set[str]:
    tree = ast.parse(py.read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def test_agent_side_does_not_import_truth():
    for sub in ("tools", "llm", "runner", "data/inputs.py"):
        p = ROOT / sub
        files = [p] if p.is_file() else list(p.rglob("*.py"))
        for f in files:
            bad = [m for m in _imports(f) if any(m == fb or m.startswith(fb + ".") for fb in FORBIDDEN)]
            assert not bad, f"{f.relative_to(ROOT)} imports {bad}"


def test_prompt_never_contains_scenario_meta():
    src = (ROOT / "llm" / "prompts.py").read_text(encoding="utf-8")
    assert "scenario_id" not in src.split("def build_input")[1].split("return")[0]
