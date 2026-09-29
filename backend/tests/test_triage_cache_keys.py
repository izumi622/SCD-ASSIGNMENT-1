def test_field_boundaries_cannot_collide(test_triage_service):
    assert test_triage_service._compute_hash("c", "a|b") != test_triage_service._compute_hash(
        "b|c", "a"
    )


def test_case_and_outer_whitespace_remain_normalized(test_triage_service):
    assert test_triage_service._compute_hash(" Water Leak ", " BLOCK A ") == (
        test_triage_service._compute_hash("water leak", "block a")
    )
