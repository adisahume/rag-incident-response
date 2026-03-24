import json
import csv

with open("evaluation/results.csv", "r") as f:
    reader = csv.DictReader(f)
    results = list(reader)

# Convert scores to floats
for r in results:
    for key in ['rag_correctness','rag_completeness','rag_actionability','rag_total','rag_time',
                'bm25_correctness','bm25_completeness','bm25_actionability','bm25_total','bm25_time',
                'notool_correctness','notool_completeness','notool_actionability','notool_total','notool_time']:
        r[key] = float(r[key])

# ── 1. Overall averages ──
print("=" * 55)
print("TABLE 1 — Overall Average Scores (use in paper)")
print("=" * 55)
print(f"{'Metric':<20} {'RAG':>8} {'BM25':>8} {'No-Tool':>8}")
print(f"{'-'*55}")

metrics = [
    ('Correctness /5',  'correctness'),
    ('Completeness /5', 'completeness'),
    ('Actionability /5','actionability'),
    ('TOTAL /15',       'total'),
    ('Avg Time (s)',    'time'),
]
for label, key in metrics:
    rag  = sum(r[f'rag_{key}'] for r in results) / len(results)
    bm25 = sum(r[f'bm25_{key}'] for r in results) / len(results)
    nt   = sum(r[f'notool_{key}'] for r in results) / len(results)
    print(f"{label:<20} {rag:>8.2f} {bm25:>8.2f} {nt:>8.2f}")

# ── 2. RAG wins vs losses ──
print(f"\n{'='*55}")
print("TABLE 2 — RAG vs BM25 head to head (per incident)")
print("=" * 55)
rag_wins = sum(1 for r in results if r['rag_total'] > r['bm25_total'])
bm25_wins = sum(1 for r in results if r['bm25_total'] > r['rag_total'])
ties = sum(1 for r in results if r['rag_total'] == r['bm25_total'])
print(f"RAG wins  : {rag_wins}/20")
print(f"BM25 wins : {bm25_wins}/20")
print(f"Ties      : {ties}/20")

# ── 3. Performance by category ──
print(f"\n{'='*55}")
print("TABLE 3 — RAG vs BM25 by incident category")
print("=" * 55)
categories = {}
for r in results:
    cat = r['category']
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(r)

print(f"{'Category':<20} {'Count':>6} {'RAG':>8} {'BM25':>8} {'No-Tool':>8} {'Winner':>8}")
print(f"{'-'*55}")
for cat, rows in sorted(categories.items()):
    rag_avg  = sum(r['rag_total'] for r in rows) / len(rows)
    bm25_avg = sum(r['bm25_total'] for r in rows) / len(rows)
    nt_avg   = sum(r['notool_total'] for r in rows) / len(rows)
    winner = "RAG" if rag_avg >= bm25_avg else "BM25"
    print(f"{cat:<20} {len(rows):>6} {rag_avg:>8.2f} {bm25_avg:>8.2f} {nt_avg:>8.2f} {winner:>8}")

# ── 4. Cases where RAG failed vs BM25 succeeded ──
print(f"\n{'='*55}")
print("TABLE 4 — Cases where BM25 beat RAG (analyze these)")
print("=" * 55)
for r in results:
    if r['bm25_total'] > r['rag_total']:
        diff = r['bm25_total'] - r['rag_total']
        print(f"  Incident {r['incident_id']:>2} — {r['company']:<25} {r['category']:<15} BM25 won by {diff:.0f} pts")

# ── 5. Correctness specifically ──
print(f"\n{'='*55}")
print("TABLE 5 — Correctness scores per incident")
print("=" * 55)
print(f"{'#':<4} {'Company':<25} {'RAG':>6} {'BM25':>6} {'NoTool':>8}")
print(f"{'-'*55}")
for r in results:
    print(f"{r['incident_id']:<4} {r['company']:<25} {r['rag_correctness']:>6} {r['bm25_correctness']:>6} {r['notool_correctness']:>8}")