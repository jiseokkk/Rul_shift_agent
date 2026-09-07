"""GT 격리 (CLAUDE.md 규칙 2): Agent 경로 코드는 evaluation 을 import 하지 않고 manifest 를 열지 않는다."""
import os
import re

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "agent_rul")
# config.py 는 manifest_csv *경로* 를 정의만 한다 (규칙 8). 여는 곳은 evaluation/gt.py 뿐이라 여기서 제외.
AGENT_PATH_FILES = ["data.py", "utils.py",
                    *[os.path.join("reference", f) for f in os.listdir(os.path.join(SRC, "reference"))],
                    *[os.path.join("tools", f) for f in os.listdir(os.path.join(SRC, "tools"))],
                    *[os.path.join("agent", f) for f in os.listdir(os.path.join(SRC, "agent"))]]


def _py_files():
    for rel in AGENT_PATH_FILES:
        if rel.endswith(".py"):
            yield rel, open(os.path.join(SRC, rel), "r", encoding="utf-8").read()


def test_no_evaluation_import_in_agent_path():
    pat = re.compile(r"^\s*(from\s+\S*evaluation|import\s+\S*evaluation)", re.M)
    bad = [rel for rel, src in _py_files() if pat.search(src)]
    assert not bad, f"evaluation 을 import 하는 Agent 경로 파일: {bad}"


def test_no_manifest_or_true_rul_access_in_agent_path():
    pat = re.compile(r"manifest_csv|\[\"true_rul\"\]|\['true_rul'\]|onset_cycle|sigma_mult")
    bad = []
    for rel, src in _py_files():
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
        # docstring 안의 설명은 허용: 실제 코드 줄만 검사
        code = re.sub(r'"""[\s\S]*?"""', "", code)
        if pat.search(code):
            bad.append(rel)
    assert not bad, f"GT 필드에 접근하는 Agent 경로 파일: {bad}"


def test_load_scenario_whitelists_spec_fields():
    from agent_rul import data
    assert set(data._SPEC_ALLOWED) == {"scenario_id", "unit", "flight_class", "life_cycles"}
