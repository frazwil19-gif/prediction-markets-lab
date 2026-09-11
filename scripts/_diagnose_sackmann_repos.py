#!/usr/bin/env python3
"""One-shot diagnostic: find out where JeffSackmann's tennis data repos
actually live right now.

Confirmed by the previous run (2026-09-11): `git ls-remote` and
`api.github.com` both report a clean "repository not found" for
JeffSackmann/tennis_atp and /tennis_wta -- not a rate limit, not a
wrong branch name, a genuinely missing repo at that exact path. This
script checks whether the account itself still exists and, if so,
searches GitHub for whatever tennis-named repos it actually owns now.

Run from a GitHub Actions runner (unrestricted internet access) --
does not run from this project's own test suite or CI gate.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "PredictionMarketsLab-diagnostic/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"_http_error": exc.code, "_message": str(exc)}
    except Exception as exc:
        return {"_error": str(exc)}


def main() -> None:
    print("--- does the JeffSackmann account itself still exist? ---")
    user = get_json("https://api.github.com/users/JeffSackmann")
    print({k: user.get(k) for k in ("login", "type", "message", "_http_error", "_error")})

    print()
    print("--- repos owned by JeffSackmann with 'tennis' in the name ---")
    search1 = get_json("https://api.github.com/search/repositories?q=user:JeffSackmann+tennis")
    if "items" in search1:
        print(f"total_count={search1.get('total_count')}")
        for item in search1["items"]:
            print(f"  {item['full_name']}  (default_branch={item.get('default_branch')}, "
                  f"archived={item.get('archived')}, private={item.get('private')})")
    else:
        print("no 'items' key -- raw response (truncated):")
        print(json.dumps(search1, indent=2)[:1500])

    print()
    print("--- ALL repos owned by JeffSackmann (unfiltered, in case naming changed entirely) ---")
    all_repos = get_json("https://api.github.com/users/JeffSackmann/repos?per_page=100")
    if isinstance(all_repos, list):
        print(f"{len(all_repos)} repos found:")
        for item in all_repos:
            print(f"  {item['full_name']}  (default_branch={item.get('default_branch')}, "
                  f"archived={item.get('archived')})")
    else:
        print("not a list -- raw response (truncated):")
        print(json.dumps(all_repos, indent=2)[:1500])

    print()
    print("--- any repo anywhere on GitHub named exactly 'tennis_atp' (in case it moved owners) ---")
    search2 = get_json("https://api.github.com/search/repositories?q=tennis_atp+in:name")
    if "items" in search2:
        print(f"total_count={search2.get('total_count')}")
        for item in search2["items"][:10]:
            print(f"  {item['full_name']}  (stars={item.get('stargazers_count')}, "
                  f"default_branch={item.get('default_branch')})")
    else:
        print("no 'items' key -- raw response (truncated):")
        print(json.dumps(search2, indent=2)[:1500])


if __name__ == "__main__":
    main()
