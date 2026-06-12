"""LIVE generation of funnel-specific 'try something like' suggestions — the production version of the
round-1 hand-authored data/suggestions.json. For each funnel with an opener rec it assembles:
  funnel's own page-1 copy  +  the niche's winning pattern  +  real winner openers as exemplars
into a prompt, and asks Claude for 2 tailored opener questions constrained to the funnel's real offer.

Run modes:
  python generate_suggestions.py            # calls the API if ANTHROPIC_API_KEY works, else falls back
  python generate_suggestions.py --dry      # never calls; just writes the assembled prompts (verifiable here)
Outputs: data/suggestions.json (merged) and always data/suggestion_prompts.jsonl (audit/offline).
Guardrails are IN THE PROMPT: A/B-test framing, real-offer-only, funnel's own language."""
import sys, json, re, numpy as np, pandas as pd
from pathlib import Path
import recommend as R
D=Path(__file__).parent
DRY="--dry" in sys.argv
MODEL="claude-sonnet-4-5"
clean=lambda s: re.sub(r"\s+"," ",str(s)).replace(" | "," ").strip()

ct=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","content_text"]).set_index("campaignVersionId")
# winner exemplars per niche: top-CVR funnels that open WITH a question
_ex={}
def exemplars(niche,k=3):
    if niche in _ex: return _ex[niche]
    g=R.F[(R.F.niche==niche)&(R.F.lp_has_question==1)].sort_values("cvr",ascending=False).head(40)
    out=[]
    for cid in g.campaignVersionId:
        if cid in ct.index:
            t=clean(ct.loc[cid,"content_text"])[:110]
            if len(t)>30: out.append(t)
        if len(out)>=k: break
    _ex[niche]=out; return out

def build_prompt(cvid):
    r=R.recommend(cvid)
    if not r: return None
    op=next((x for x in r["exp"] if x.get("feat")=="opener"),None)
    if not op: return None
    snippet=clean(ct.loc[cvid,"content_text"])[:400] if cvid in ct.index else ""
    win=R.NWIN.get(r["niche"]); pct_q=int(round(100*float(win.get("lp_has_question",0)))) if win is not None else None
    ex="\n".join(f"  - {e}" for e in exemplars(r["niche"]))
    prompt=(f"You improve the page-1 opener of a Perspective lead-gen funnel.\n"
        f"FUNNEL: \"{r['niche']}\" niche.\nCurrent page-1 copy (opens with a static hero/intro):\n  {snippet}\n\n"
        f"In this niche, ~{pct_q}% of the best-converting funnels open with ONE interactive question instead of a static hero. "
        f"Real openers from top funnels in this niche:\n{ex}\n\n"
        f"Write 2 page-1 opener QUESTIONS tailored to THIS funnel's actual offer, each with 3-4 short answer options, "
        f"in the funnel's own language. Constraints: use ONLY the funnel's real offer (do NOT invent discounts, prices or claims); "
        f"keep each question one line.\nReturn STRICT JSON: "
        f'{{"current":"<=8-word description of the current opener","try":["“Question?” → opt · opt · opt","…"]}}')
    return {"cvid":cvid,"niche":r["niche"],"prompt":prompt}

def call_api(prompt):
    import anthropic
    c=anthropic.Anthropic()
    m=c.messages.create(model=MODEL,max_tokens=400,
        messages=[{"role":"user","content":prompt}])
    txt=m.content[0].text
    return json.loads(re.search(r"\{.*\}",txt,re.S).group(0))

# target = the demo funnels that currently get an opener rec
demo=json.loads((D/"data/demo_data.json").read_text())
targets=[x["id"] for x in demo]
prompts=[p for p in (build_prompt(c) for c in targets) if p]
(D/"data/suggestion_prompts.jsonl").write_text("\n".join(json.dumps(p,ensure_ascii=False) for p in prompts))
print(f"assembled {len(prompts)} opener prompts -> data/suggestion_prompts.jsonl")

if DRY:
    print("--dry: skipping API. Sample assembled prompt:\n"); print(prompts[0]["prompt"][:700] if prompts else "(none)")
    sys.exit(0)

sug=json.loads((D/"data/suggestions.json").read_text()) if (D/"data/suggestions.json").exists() else {}
ok=0
for p in prompts:
    try:
        sug[p["cvid"]]={"opener":call_api(p["prompt"])}; ok+=1
    except Exception as e:
        print(f"  [skip {p['cvid']}] {type(e).__name__}: {str(e)[:80]}")
if ok:
    (D/"data/suggestions.json").write_text(json.dumps(sug,ensure_ascii=False,indent=2))
    print(f"generated {ok}/{len(prompts)} live suggestions -> data/suggestions.json")
else:
    print("no live generations (no working API key here). Keeping in-session suggestions.json; "
          "run this where ANTHROPIC_API_KEY is set, or use the prompts file.")
