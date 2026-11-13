from scripts.run_eval import compute_metrics


def test_compute_metrics_accuracy():
    sample_results = [
        {
            "id": "q1",
            "intent_match": True,
            "behavior_match": True,
            "must_contain_pass": True,
            "lang_match": True,
            "expected_intent": "policy_question",
            "is_oos": False,
            "hit_k": True,
            "latency_ms": 250,
            "cost_inr": 0.05,
        },
        {
            "id": "q2",
            "intent_match": True,
            "behavior_match": True,
            "must_contain_pass": True,
            "lang_match": True,
            "expected_intent": "product_question",
            "is_oos": False,
            "hit_k": True,
            "latency_ms": 350,
            "cost_inr": 0.05,
        },
        {
            "id": "q3",
            "intent_match": False,
            "behavior_match": False,
            "must_contain_pass": False,
            "lang_match": True,
            "expected_intent": "order_status",
            "is_oos": False,
            "hit_k": False,
            "latency_ms": 150,
            "cost_inr": 0.05,
        },
    ]

    metrics = compute_metrics(sample_results)
    assert metrics["total_questions"] == 3
    # 2/3 = 66.67%
    assert metrics["intent_accuracy"] == 66.67
    assert metrics["behavior_accuracy"] == 66.67
    # 2 knowledge questions, both hit -> 100%
    assert metrics["hit_at_k"] == 100.0
    assert metrics["latency_p50_ms"] == 250.0
    assert metrics["total_cost_inr"] == 0.15
