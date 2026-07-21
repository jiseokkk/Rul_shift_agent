"""End-to-end orchestrator.

    python run_all.py --agent rule   # full pipeline, no LLM (fast, deterministic)
    python run_all.py --agent llm    # full pipeline with vLLM + local Qwen

Stages: fit features -> train RUL -> build packets -> baselines -> agent
        -> evaluate -> ablation -> figures.
Use --skip_train once the RUL model exists.
"""
import argparse
import subprocess
import sys

PY = sys.executable


def run(mod, *args):
    print(f"\n########## {mod} {' '.join(args)} ##########")
    subprocess.run([PY, mod, *args], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["rule", "llm"], default="rule")
    ap.add_argument("--skip_train", action="store_true")
    ap.add_argument("--gpu_mem", type=float, default=0.90)
    args = ap.parse_args()

    run("preprocess.py")                      # fit Tier-1 feature models
    if not args.skip_train:
        run("train_rul.py")                   # train the LSTM RUL tool
    run("build_decisions.py")                 # decision-point packets
    run("baselines.py")                       # threshold + CUSUM (+ inject signal)
    if args.agent == "llm":
        run("agent.py", "--agent", "llm", "--gpu_mem", str(args.gpu_mem))
    run("agent.py", "--agent", "rule")        # always produce the rule reference
    run("evaluate.py")
    run("ablation.py")
    run("make_figures.py")
    run("make_report.py")
    print("\n[run_all] complete.")


if __name__ == "__main__":
    main()
