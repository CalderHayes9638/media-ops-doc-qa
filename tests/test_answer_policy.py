from answer_policy import decide


def passage(score: float, title: str) -> dict:
    return {"score": score, "metadata": {"title": title, "doc_id": "proc-02", "text": "..."}}


def test_two_strong_passages_are_answered():
    verdict = decide([passage(0.81, "Job retries"), passage(0.52, "Transcode ladder")])
    assert verdict.status == "answered"
    assert len(verdict.citations) == 2


def test_single_strong_passage_escalates():
    verdict = decide([passage(0.77, "Job retries"), passage(0.31, "Takedowns")])
    assert verdict.status == "escalated"
    assert verdict.citations == [passage(0.77, "Job retries")]


def test_no_matches_escalates():
    assert decide([]).status == "escalated"
