from api.safe_match_gate_failure_pair_patch import should_block_top_promotion, is_failure_danger_pair

def test_v132_failure_pairs_registered():
    assert is_failure_danger_pair("lesley", "ixia")
    assert is_failure_danger_pair("yin", "valir")
    assert is_failure_danger_pair("x_borg", "benedetta")
    assert is_failure_danger_pair("floryn", "odette")
    assert is_failure_danger_pair("beatrix", "cici")

def test_weak_reference_blocks_dictionary_top_promotion():
    ref = {"status": "weak", "hero_id": "ixia"}
    fallback = {"hero_id": "lesley"}
    assert should_block_top_promotion(ref, fallback) is True

def test_missing_reference_blocks_dictionary_top_promotion():
    assert should_block_top_promotion(None, {"hero_id": "lesley"}) is True

def test_strong_reference_can_pass():
    ref = {"status": "strong", "hero_id": "akai"}
    fallback = {"hero_id": "grock"}
    assert should_block_top_promotion(ref, fallback) is False
