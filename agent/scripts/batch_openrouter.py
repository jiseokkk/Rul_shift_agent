"""OpenRouter Batch API 로 판정을 미리 받아 판정 캐시에 넣는다 (정가의 50%, 결과는 24시간 안, 보통 1시간 안).

판정이 memoryless(각 cycle 프롬프트는 도구 통계에만 의존)라서 dry-run 으로 프롬프트를 전부 만든 뒤 한꺼번에 제출할 수 있다.
결과는 artifacts/cache/decisions/<model|seed 해시>/<prompt_hash>.json 에 동기 호출과 같은 형식으로 들어가고,
이후 run.py 는 캐시만 읽어 decisions.csv 를 만든다 (남은 미스만 동기 호출·정가).

  # 0) .env 에 OPENROUTER_API_KEY. 요청 본문 점검만 (키·비용 없음)
  python agent/scripts/batch_openrouter.py submit  --scenarios sample_or500 --job or500 --test 20 --build-only
  # 1) 시험 20건: 스키마 강제·reasoning 토큰 0·비용 확인 (≈ $0.01)
  python agent/scripts/batch_openrouter.py submit  --scenarios sample_or500 --job or500_test --test 20
  python agent/scripts/batch_openrouter.py collect --job or500_test --wait
  # 2) 본 제출 (캐시에 이미 있는 프롬프트는 건너뜀 → 재실행이 곧 재제출)
  python agent/scripts/batch_openrouter.py submit  --scenarios sample_or500 --job or500
  python agent/scripts/batch_openrouter.py status  --job or500
  python agent/scripts/batch_openrouter.py collect --job or500 --wait
  # 3) 캐시 재생 → decisions.csv → 평가
  python agent/scripts/run.py --scenarios sample_or500 --llm llm_openrouter --tag or500
  python agent/scripts/evaluate.py --latest

job 디렉터리: runs/_batches/<job>/  requests.jsonl(제출 본문) · batches.json(배치 id) · results/<id>.json(원본 응답) · failed.jsonl · summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

from _bootstrap import AGENT, load_cfg
from src.data.inputs import AGENT_ROOT, load_scenario_list
from src.llm.client import request_body, resolve_api_key, usage_from_dict
from src.llm.post_check import ParseError, parse, post_check
from src.runner.cache import DecisionCache, prompt_hash
from src.runner.record import make_run_id
from src.runner.stream import run as run_stream

BATCHES_URL = "https://openrouter.ai/api/v1/batches"
TERMINAL = ("completed", "failed", "cancelled", "expired")


def job_dir(name: str) -> Path:
    d = AGENT / "runs" / "_batches" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def headers(cfg: dict) -> dict:
    return {"Authorization": f"Bearer {resolve_api_key(cfg)}", "Content-Type": "application/json"}


def make_cache(cfg: dict) -> DecisionCache:
    return DecisionCache(AGENT_ROOT / "artifacts" / "cache" / "decisions", cfg["model"], int(cfg.get("seed", 42)))


def cached_ok(cache: DecisionCache, key: str) -> bool:
    rec = cache.get(key)
    return rec is not None and rec.get("error") is None


def read_prompt_file(p: Path) -> tuple[str, str]:
    """record.save_prompt 형식('### SYSTEM\\n{system}\\n\\n### USER\\n{user}\\n')을 되돌린다. 해시 대조로 검증."""
    txt = p.read_text(encoding="utf-8")
    head, user = txt.split("\n\n### USER\n", 1)
    system = head[len("### SYSTEM\n"):]
    return system, user[:-1] if user.endswith("\n") else user


def collect_prompts(dry_dir: Path) -> tuple[dict[str, tuple[str, str]], int]:
    df = pd.read_csv(dry_dir / "decisions.csv", usecols=["unit", "scenario_id", "cycle", "prompt_hash"])
    out: dict[str, tuple[str, str]] = {}
    for r in df.drop_duplicates("prompt_hash").itertuples(index=False):
        system, user = read_prompt_file(dry_dir / "prompts" / f"u{r.unit}__{r.scenario_id}__c{r.cycle}.txt")
        key = prompt_hash(system, user)
        assert key == r.prompt_hash, f"프롬프트 파일 파싱이 해시와 다름: u{r.unit} {r.scenario_id} c{r.cycle}"
        out[key] = (system, user)
    return out, len(df)


def load_meta(jd: Path) -> dict:
    p = jd / "batches.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"batches": []}


def save_meta(jd: Path, meta: dict) -> None:
    (jd / "batches.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def get_batch(cfg: dict, batch_id: str) -> dict:
    r = requests.get(f"{BATCHES_URL}/{batch_id}", headers=headers(cfg), timeout=300)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- submit
def cmd_submit(a):
    acfg, lcfg = load_cfg("agent"), load_cfg(a.llm)
    jd = job_dir(a.job)
    prev = sorted(d for d in (AGENT / "runs").glob(f"*_{a.job}_batchprep_dry_*") if (d / "decisions.csv").exists())
    if a.dry_run_id:
        dry_dir = AGENT / "runs" / a.dry_run_id
    elif prev and not a.fresh_prompts:
        dry_dir = prev[-1]
        print(f"이전 dry-run 재사용: runs/{dry_dir.name} (다시 만들려면 --fresh-prompts)")
    else:
        scen = load_scenario_list(a.scenarios)
        run_id = make_run_id(lcfg["model"], f"{a.job}_batchprep_dry", int(lcfg.get("seed", 42)))
        print(f"dry-run 으로 프롬프트 생성: {len(scen)} 시나리오 → runs/{run_id}")
        run_stream(scen, acfg, lcfg, run_id, AGENT / "runs", dry_run=True, tag=a.job)
        dry_dir = AGENT / "runs" / run_id
    prompts, n_dec = collect_prompts(dry_dir)
    cache = make_cache(lcfg)
    todo = [k for k in prompts if not cached_ok(cache, k)]
    if a.test:
        todo = todo[:a.test]
    print(f"판정 {n_dec:,} → 고유 프롬프트 {len(prompts):,} → 캐시에 없는 제출 대상 {len(todo):,}"
          + (f" (--test {a.test})" if a.test else ""))
    if not todo:
        print("제출할 것이 없다. 캐시가 이미 채워져 있으면 run.py 로 재생하면 된다.")
        return
    seed = int(lcfg.get("seed", 42))
    reqs = []
    for k in todo:
        body, extra = request_body(lcfg, *prompts[k], seed)
        reqs.append({"custom_id": k, "body": {**body, **extra}})
    with open(jd / "requests.jsonl", "w", encoding="utf-8") as f:
        for r in reqs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    chars = sum(len(prompts[k][0]) + len(prompts[k][1]) for k in todo)
    print(f"입력 ≈ {chars / 3.8 / 1e6:.2f}M 토큰 (문자/3.8 추정). 요청 본문 → {jd / 'requests.jsonl'}")
    sample = json.loads(json.dumps(reqs[0]))
    for m in sample["body"]["messages"]:
        m["content"] = m["content"][:60] + " ..."
    print("첫 요청 본문:", json.dumps(sample, ensure_ascii=False, indent=1))
    if a.build_only:
        print("--build-only: 제출하지 않음")
        return

    meta = load_meta(jd)
    meta.update({"model": lcfg["model"], "seed": seed, "llm_cfg": a.llm, "dry_run_dir": str(dry_dir), "scenarios": a.scenarios})
    hdr = headers(lcfg)
    for i in range(0, len(reqs), a.chunk):
        chunk = reqs[i:i + a.chunk]
        payload = {"endpoint": "/v1/chat/completions", "model": lcfg["model"], "completion_window": "24h", "requests": chunk}
        r = requests.post(BATCHES_URL, headers=hdr, json=payload, timeout=900)
        if r.status_code >= 300:
            print(f"제출 실패 (HTTP {r.status_code}): {r.text[:1000]}")
            save_meta(jd, meta)
            sys.exit(1)
        b = r.json()
        meta["batches"].append({"batch_id": b["id"], "n": len(chunk), "status": b.get("status"),
                                "custom_ids": [x["custom_id"] for x in chunk], "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S")})
        save_meta(jd, meta)
        print(f"  batch {b['id']}: {len(chunk)} 건 제출, status={b.get('status')}")
    print(f"총 {len(meta['batches'])} 배치. 다음: status / collect --wait")


# ---------------------------------------------------------------- status
def cmd_status(a):
    lcfg = load_cfg(a.llm)
    meta = load_meta(job_dir(a.job))
    for b in meta["batches"]:
        r = get_batch(lcfg, b["batch_id"])
        print(f"{b['batch_id']}  n={b['n']}  status={r.get('status')}  counts={r.get('request_counts')}")


# ---------------------------------------------------------------- collect
def extract(item: dict) -> tuple[str | None, dict, str | None, str | None]:
    """결과 항목 → (content, usage, finish_reason, error). OpenAI 식 {status_code, body} 포장과 직접 본문 둘 다 처리."""
    if item.get("error"):
        return None, {}, None, json.dumps(item["error"], ensure_ascii=False)[:300]
    resp = item.get("response") or {}
    body = resp.get("body", resp)
    if body.get("error"):
        return None, {}, None, json.dumps(body["error"], ensure_ascii=False)[:300]
    try:
        ch = body["choices"][0]
        return ch["message"].get("content") or "", body.get("usage") or {}, ch.get("finish_reason"), None
    except (KeyError, IndexError, TypeError) as e:
        return None, {}, None, f"unexpected result shape: {type(e).__name__}: {json.dumps(body)[:300]}"


def cmd_collect(a):
    lcfg = load_cfg(a.llm)
    jd = job_dir(a.job)
    meta = load_meta(jd)
    if not meta["batches"]:
        print("batches.json 이 비어 있다. submit 부터.")
        return
    cache = make_cache(lcfg)
    (jd / "results").mkdir(exist_ok=True)
    tot, failed, samples = Counter(), [], []
    tok = Counter()
    pending = list(meta["batches"])
    while pending:
        still = []
        for b in pending:
            bid = b["batch_id"]
            r = get_batch(lcfg, bid)
            st = r.get("status")
            if st not in TERMINAL:
                still.append(b)
                print(f"{bid}: {st} {r.get('request_counts') or ''}")
                continue
            (jd / "results" / f"{bid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            b["status"] = st
            results = r.get("results") or []
            print(f"{bid}: {st}, 결과 {len(results)} 건")
            for item in results:
                cid = item.get("custom_id")
                content, usage, finish, err = extract(item)
                if err is not None:
                    failed.append({"custom_id": cid, "kind": "api", "detail": err})
                    tot["api_error"] += 1
                    continue
                u = usage_from_dict(usage)
                for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                    tok[k] += int(u[k] or 0)
                tok["cost"] += float(u["cost"] or 0.0)
                if finish and finish != "stop":
                    tot[f"finish_{finish}"] += 1
                try:
                    d = parse(content)
                    d, flags = post_check(d)
                except ParseError as e:
                    failed.append({"custom_id": cid, "kind": "parse", "detail": f"{e} | finish={finish} | {content[:200]}"})
                    tot["parse_error"] += 1
                    continue
                rec = {"degraded": d.degraded, "suspected_sensors": d.suspected_sensors, "confidence": d.confidence,
                       "rationale": d.rationale, "flags": flags, "n_retries": 0, "latency_ms": 0,
                       "prompt_tokens": u["prompt_tokens"], "completion_tokens": u["completion_tokens"], "error": None, "raw": content,
                       "reasoning_tokens": u["reasoning_tokens"], "cost": u["cost"], "batch_id": bid}
                if not a.no_cache:
                    cache.put(cid, rec)
                tot["ok"] += 1
                if len(samples) < 3:
                    samples.append({"custom_id": cid, "decision": d.model_dump(), "flags": flags, "usage": u, "finish": finish})
        save_meta(jd, meta)
        pending = still
        if pending and a.wait:
            print(f"  {len(pending)} 배치 대기 중… {a.poll}s 후 재확인")
            time.sleep(a.poll)
        elif pending:
            print(f"{len(pending)} 배치가 아직 끝나지 않았다. --wait 로 기다리거나 나중에 다시 collect.")
            break

    n = tot["ok"] + tot["parse_error"] + tot["api_error"]
    summary = {"ok": tot["ok"], "parse_error": tot["parse_error"], "api_error": tot["api_error"],
               "finish_reasons_not_stop": {k: v for k, v in tot.items() if k.startswith("finish_")},
               "tokens_total": dict(tok), "tokens_per_call": {k: (v / max(n, 1)) for k, v in tok.items() if k != "cost"},
               "cost_usd": tok["cost"], "cached": not a.no_cache, "cache_dir": str(cache.dir), "samples": samples}
    (jd / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(jd / "failed.jsonl", "w", encoding="utf-8") as f:
        for x in failed:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"\n수집: ok {tot['ok']:,} · parse 실패 {tot['parse_error']:,} · API 오류 {tot['api_error']:,}"
          + (f" · finish≠stop {summary['finish_reasons_not_stop']}" if summary["finish_reasons_not_stop"] else ""))
    if n:
        print(f"호출당 토큰: prompt {tok['prompt_tokens'] / n:.0f} · completion {tok['completion_tokens'] / n:.0f} · "
              f"reasoning {tok['reasoning_tokens'] / n:.0f} · 비용 합계 ${tok['cost']:.4f}"
              + (" (usage.cost 미반환)" if not tok["cost"] else ""))
        if tok["reasoning_tokens"]:
            print("!! reasoning 토큰이 0 이 아니다. llm_openrouter.yaml 의 reasoning_effort 를 확인할 것.")
    for s in samples[:2]:
        print("sample:", json.dumps(s, ensure_ascii=False)[:400])
    if failed:
        print(f"실패 {len(failed)} 건 → {jd / 'failed.jsonl'}. 같은 submit 명령을 다시 실행하면 캐시에 없는 것만 재제출된다.")
    print(f"캐시 → {cache.dir}. 다음: run.py --scenarios ... --llm {a.llm} --tag ...")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--scenarios", default="sample_or500")
    s.add_argument("--dry-run-id", default=None, help="이미 만든 dry-run 디렉터리 이름을 재사용")
    s.add_argument("--job", required=True)
    s.add_argument("--llm", default="llm_openrouter")
    s.add_argument("--test", type=int, default=None, help="앞 n개 프롬프트만 제출 (시험용)")
    s.add_argument("--chunk", type=int, default=5000, help="배치 하나당 요청 수")
    s.add_argument("--build-only", action="store_true", help="제출하지 않고 requests.jsonl 만 만든다")
    s.add_argument("--fresh-prompts", action="store_true", help="같은 job 의 이전 dry-run 이 있어도 프롬프트를 다시 만든다")
    s.set_defaults(fn=cmd_submit)
    s = sub.add_parser("status")
    s.add_argument("--job", required=True)
    s.add_argument("--llm", default="llm_openrouter")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("collect")
    s.add_argument("--job", required=True)
    s.add_argument("--llm", default="llm_openrouter")
    s.add_argument("--wait", action="store_true", help="끝날 때까지 폴링")
    s.add_argument("--poll", type=int, default=60, help="폴링 간격 초")
    s.add_argument("--no-cache", action="store_true", help="캐시에 쓰지 않고 요약만 (시험 배치 점검용)")
    s.set_defaults(fn=cmd_collect)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
