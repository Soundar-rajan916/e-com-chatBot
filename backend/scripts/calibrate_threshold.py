import asyncio
import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.db import async_session_factory, engine
from app.services.embeddings import get_embedder
from app.services.vectorstore import get_vector_store


async def evaluate_scores() -> tuple[list[float], list[float]]:
    eval_file = Path(__file__).resolve().parent.parent / "eval" / "questions.jsonl"
    if not eval_file.exists():
        print(f"Error: {eval_file} not found.")
        return [], []

    questions = []
    with open(eval_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    embedder = get_embedder()
    store = get_vector_store()

    in_scope_scores: list[float] = []
    out_of_scope_scores: list[float] = []

    print(f"Calibrating threshold over {len(questions)} evaluation questions...")

    async with async_session_factory() as session:
        for q in questions:
            text = q["question"]
            intent = q["expected_intent"]
            behavior = q.get("expected_behavior", "")
            is_oos = behavior in ("below_threshold_oos", "zero_products_found") or "unrelated" in behavior

            emb = await embedder.embed_query(text)

            if intent == "policy_question":
                hits = await store.search(session, "policy_chunks", emb, top_k=1)
                top_score = hits[0].score if hits else 0.0
            elif intent == "product_question":
                hits = await store.search(session, "products", emb, top_k=1)
                top_score = hits[0].score if hits else 0.0
            else:
                continue

            if is_oos:
                out_of_scope_scores.append(top_score)
                print(f"  [OOS] {q['id']} ({top_score:.4f}): {text[:50]}...")
            else:
                in_scope_scores.append(top_score)
                print(f"  [IN-SCOPE] {q['id']} ({top_score:.4f}): {text[:50]}...")

    await engine.dispose()
    return in_scope_scores, out_of_scope_scores


def main():
    in_scope, out_of_scope = asyncio.run(evaluate_scores())

    if not in_scope:
        print("No scores collected.")
        return

    in_arr = np.array(in_scope)
    oos_arr = np.array(out_of_scope) if out_of_scope else np.array([0.0])

    print("\n" + "=" * 60)
    print("RAG THRESHOLD CALIBRATION REPORT")
    print("=" * 60)
    print(f"In-scope queries evaluated:     {len(in_arr)}")
    print(f"  Min score:                    {in_arr.min():.4f}")
    print(f"  Max score:                    {in_arr.max():.4f}")
    print(f"  Mean score:                   {in_arr.mean():.4f}")
    print(f"  Median (p50):                 {np.percentile(in_arr, 50):.4f}")
    print(f"  10th percentile (p10):        {np.percentile(in_arr, 10):.4f}")

    print(f"\nOut-of-scope queries evaluated: {len(oos_arr)}")
    print(f"  Min score:                    {oos_arr.min():.4f}")
    print(f"  Max score:                    {oos_arr.max():.4f}")
    print(f"  Mean score:                   {oos_arr.mean():.4f}")
    print(f"  Median (p50):                 {np.percentile(oos_arr, 50):.4f}")

    # Recommended threshold is set between out-of-scope max and in-scope 10th percentile
    recommended = round(float(np.percentile(in_arr, 10) * 0.95), 2)
    # Ensure it's safely above out-of-scope max
    if recommended <= oos_arr.max():
        recommended = round(float((in_arr.min() + oos_arr.max()) / 2.0), 2)

    print("\n" + "-" * 60)
    print(f"RECOMMENDED RAG_MIN_SCORE:      {recommended}")
    print("CURRENT CONFIG RAG_MIN_SCORE:   0.80")
    print("-" * 60)


if __name__ == "__main__":
    main()
