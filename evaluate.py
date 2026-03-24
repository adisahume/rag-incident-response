import json
import os
import time
import csv
from dotenv import load_dotenv
from openai import OpenAI
from chain import query_rag
from baselines import query_bm25_with_response, query_no_tool

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Scoring rubric ───────────────────────────────────────────
def score_response(incident, response, condition_name):
    """
    Ask GPT to score the response on 3 dimensions (1-5 each).
    We use GPT as the judge because manual scoring 60 responses
    is impractical, and GPT-as-judge is a standard eval technique.
    """
    prompt = f"""
You are evaluating the quality of an AI-generated incident response.

ORIGINAL INCIDENT:
{incident['description']}

KNOWN ROOT CAUSE (ground truth):
{incident.get('root_cause', 'Not specified')}

KNOWN RESOLUTION (ground truth):
{incident.get('resolution', 'Not specified')}

AI RESPONSE TO EVALUATE:
{response}

Score the response on these 3 dimensions. Return ONLY a JSON object, no explanation:

{{
  "correctness": <1-5>,
  "completeness": <1-5>,
  "actionability": <1-5>,
  "correctness_reason": "<one sentence>",
  "completeness_reason": "<one sentence>",
  "actionability_reason": "<one sentence>"
}}

Scoring guide:
- correctness  : 5=root cause matches ground truth exactly, 3=partially correct, 1=completely wrong
- completeness : 5=covers symptoms+root cause+resolution+escalation, 3=covers some, 1=very incomplete  
- actionability: 5=specific steps an engineer can execute immediately, 3=somewhat vague, 1=no actionable steps

Return only the JSON, no markdown.
"""
    try:
        response_obj = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = response_obj.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        scores = json.loads(text)
        return scores
    except Exception as e:
        print(f"      ⚠️  Scoring failed: {e}")
        return {
            "correctness": 0,
            "completeness": 0,
            "actionability": 0,
            "correctness_reason": "scoring failed",
            "completeness_reason": "scoring failed",
            "actionability_reason": "scoring failed"
        }

# ── Run evaluation ───────────────────────────────────────────
with open("data/test_set.json", "r") as f:
    test_set = json.load(f)

print(f"Running evaluation on {len(test_set)} test incidents")
print(f"3 conditions × 20 incidents = 60 total responses")
print(f"Estimated time: ~15 minutes")
print(f"Estimated cost: ~$0.30\n")

results = []

for i, incident in enumerate(test_set):
    print(f"\n[{i+1}/20] {incident['company']} — {incident.get('category','?')} / {incident.get('severity','?')}")

    # Build the query from the incident's symptoms
    # We use symptoms only — not root cause or resolution
    # (those are the ground truth we're testing against)
    query = incident.get('symptoms', incident.get('description', ''))
    if query == 'Not specified':
        query = incident.get('description', '')

    row = {
        "incident_id": i + 1,
        "company": incident['company'],
        "category": incident.get('category', ''),
        "severity": incident.get('severity', ''),
        "query": query[:200],
        "ground_truth_root_cause": incident.get('root_cause', '')[:200],
        "ground_truth_resolution": incident.get('resolution', '')[:200],
    }

    # ── Condition A: RAG ──
    print(f"  Running RAG...", end=' ')
    start = time.time()
    try:
        rag_result = query_rag(query)
        rag_time = round(time.time() - start, 2)
        rag_scores = score_response(incident, rag_result['response'], "RAG")

        row['rag_response'] = rag_result['response'][:500]
        row['rag_retrieved'] = ", ".join([m['company'] for m in rag_result['retrieved_incidents']])
        row['rag_top_score'] = rag_result['retrieved_incidents'][0]['score'] if rag_result['retrieved_incidents'] else 0
        row['rag_correctness'] = rag_scores['correctness']
        row['rag_completeness'] = rag_scores['completeness']
        row['rag_actionability'] = rag_scores['actionability']
        row['rag_total'] = rag_scores['correctness'] + rag_scores['completeness'] + rag_scores['actionability']
        row['rag_time'] = rag_time
        print(f"✅ scores: {rag_scores['correctness']}/{rag_scores['completeness']}/{rag_scores['actionability']} time: {rag_time}s")
    except Exception as e:
        print(f"❌ {e}")
        row.update({'rag_correctness': 0, 'rag_completeness': 0, 'rag_actionability': 0, 'rag_total': 0, 'rag_time': 0})

    time.sleep(1)

    # ── Condition B: BM25 ──
    print(f"  Running BM25...", end=' ')
    start = time.time()
    try:
        bm25_result = query_bm25_with_response(query)
        bm25_time = round(time.time() - start, 2)
        bm25_scores = score_response(incident, bm25_result['response'], "BM25")

        row['bm25_response'] = bm25_result['response'][:500]
        row['bm25_retrieved'] = ", ".join([m['company'] for m in bm25_result['retrieved_incidents']])
        row['bm25_top_score'] = bm25_result['retrieved_incidents'][0]['score'] if bm25_result['retrieved_incidents'] else 0
        row['bm25_correctness'] = bm25_scores['correctness']
        row['bm25_completeness'] = bm25_scores['completeness']
        row['bm25_actionability'] = bm25_scores['actionability']
        row['bm25_total'] = bm25_scores['correctness'] + bm25_scores['completeness'] + bm25_scores['actionability']
        row['bm25_time'] = bm25_time
        print(f"✅ scores: {bm25_scores['correctness']}/{bm25_scores['completeness']}/{bm25_scores['actionability']} time: {bm25_time}s")
    except Exception as e:
        print(f"❌ {e}")
        row.update({'bm25_correctness': 0, 'bm25_completeness': 0, 'bm25_actionability': 0, 'bm25_total': 0, 'bm25_time': 0})

    time.sleep(1)

    # ── Condition C: No Tool ──
    print(f"  Running No-Tool...", end=' ')
    start = time.time()
    try:
        notool_result = query_no_tool(query)
        notool_time = round(time.time() - start, 2)
        notool_scores = score_response(incident, notool_result['response'], "NoTool")

        row['notool_response'] = notool_result['response'][:500]
        row['notool_correctness'] = notool_scores['correctness']
        row['notool_completeness'] = notool_scores['completeness']
        row['notool_actionability'] = notool_scores['actionability']
        row['notool_total'] = notool_scores['correctness'] + notool_scores['completeness'] + notool_scores['actionability']
        row['notool_time'] = notool_time
        print(f"✅ scores: {notool_scores['correctness']}/{notool_scores['completeness']}/{notool_scores['actionability']} time: {notool_time}s")
    except Exception as e:
        print(f"❌ {e}")
        row.update({'notool_correctness': 0, 'notool_completeness': 0, 'notool_actionability': 0, 'notool_total': 0, 'notool_time': 0})

    results.append(row)
    time.sleep(2)

# ── Save results ─────────────────────────────────────────────
os.makedirs("evaluation", exist_ok=True)

with open("evaluation/results.json", "w") as f:
    json.dump(results, f, indent=2)

# Save as CSV for easy analysis
fieldnames = results[0].keys()
with open("evaluation/results.csv", "w", newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

# ── Print summary ─────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"EVALUATION COMPLETE")
print(f"{'='*60}")

rag_avg_correct   = sum(r['rag_correctness'] for r in results) / len(results)
rag_avg_complete  = sum(r['rag_completeness'] for r in results) / len(results)
rag_avg_action    = sum(r['rag_actionability'] for r in results) / len(results)
rag_avg_total     = sum(r['rag_total'] for r in results) / len(results)
rag_avg_time      = sum(r['rag_time'] for r in results) / len(results)

bm25_avg_correct  = sum(r['bm25_correctness'] for r in results) / len(results)
bm25_avg_complete = sum(r['bm25_completeness'] for r in results) / len(results)
bm25_avg_action   = sum(r['bm25_actionability'] for r in results) / len(results)
bm25_avg_total    = sum(r['bm25_total'] for r in results) / len(results)
bm25_avg_time     = sum(r['bm25_time'] for r in results) / len(results)

nt_avg_correct    = sum(r['notool_correctness'] for r in results) / len(results)
nt_avg_complete   = sum(r['notool_completeness'] for r in results) / len(results)
nt_avg_action     = sum(r['notool_actionability'] for r in results) / len(results)
nt_avg_total      = sum(r['notool_total'] for r in results) / len(results)
nt_avg_time       = sum(r['notool_time'] for r in results) / len(results)

print(f"\n{'Metric':<20} {'RAG':>8} {'BM25':>8} {'No-Tool':>8}")
print(f"{'-'*44}")
print(f"{'Correctness':<20} {rag_avg_correct:>8.2f} {bm25_avg_correct:>8.2f} {nt_avg_correct:>8.2f}")
print(f"{'Completeness':<20} {rag_avg_complete:>8.2f} {bm25_avg_complete:>8.2f} {nt_avg_complete:>8.2f}")
print(f"{'Actionability':<20} {rag_avg_action:>8.2f} {bm25_avg_action:>8.2f} {nt_avg_action:>8.2f}")
print(f"{'TOTAL /15':<20} {rag_avg_total:>8.2f} {bm25_avg_total:>8.2f} {nt_avg_total:>8.2f}")
print(f"{'Avg Time (s)':<20} {rag_avg_time:>8.2f} {bm25_avg_time:>8.2f} {nt_avg_time:>8.2f}")

print(f"\n✅ Saved to evaluation/results.csv and evaluation/results.json")