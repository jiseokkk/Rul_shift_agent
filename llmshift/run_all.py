"""End-to-end orchestrator.

    PYTHONPATH=/home/iai4/Desktop python -m han.Rul_shift_agent.llmshift.run_all --agent rule
    PYTHONPATH=/home/iai4/Desktop python -m han.Rul_shift_agent.llmshift.run_all --agent llm

Stages: fit features -> train RUL -> build packets -> baselines -> agent
        -> evaluate -> ablation -> figures.
Use --skip_train once the RUL model exists.
"""
import argparse
import os
import subprocess
import sys

PY = sys.executable
PKG = "han.Rul_shift_agent"
REPO_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def run(mod, *args):
    print(f"\n########## {mod} {' '.join(args)} ##########")
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_PARENT + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([PY, "-m", f"{PKG}.{mod}", *args], check=True, env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["rule", "llm"], default="rule")
    ap.add_argument("--skip_train", action="store_true")
    ap.add_argument("--gpu_mem", type=float, default=0.90)
    args = ap.parse_args()

    run("core.preprocess")                    # fit Tier-1 feature models
    if not args.skip_train:
        run("core.train_rul")                 # train the LSTM RUL tool
    run("core.build_decisions")               # decision-point packets
    run("baselines.cusum")                    # threshold + CUSUM baseline
    if args.agent == "llm":
        run("llmshift.agent", "--agent", "llm", "--gpu_mem", str(args.gpu_mem))
    run("llmshift.agent", "--agent", "rule")  # always produce the rule reference
    run("core.evaluate")
    run("llmshift.ablation")
    run("llmshift.make_figures")
    run("llmshift.make_report")
    print("\n[run_all] complete.")


if __name__ == "__main__":
    main()
