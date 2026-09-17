from concurrent.futures import ThreadPoolExecutor

from src.runner.cache import DecisionCache, prompt_hash


def test_prompt_hash_stable_and_sensitive():
    a = prompt_hash("sys", "user")
    assert a == prompt_hash("sys", "user") and a != prompt_hash("sys", "user ") and len(a) == 24


def test_concurrent_put_same_key(tmp_path):
    c = DecisionCache(tmp_path, "m", 1)
    rec = {"degraded": 1, "flags": []}

    def w(_):
        c.put("k", rec)
        return c.get("k")

    with ThreadPoolExecutor(16) as ex:
        outs = list(ex.map(w, range(200)))
    assert all(o == rec for o in outs)
    assert not list(c.dir.glob("*.tmp"))
