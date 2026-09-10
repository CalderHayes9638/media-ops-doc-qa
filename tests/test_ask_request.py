import pytest
from pydantic import ValidationError

from doc_qa_service import AskRequest


def test_area_must_be_a_known_pipeline_stage():
    assert AskRequest(question="when do job retries stop?", area="processing").top_k == 8
    with pytest.raises(ValidationError):
        AskRequest(question="when do job retries stop?", area="archival")


def test_short_questions_are_rejected():
    with pytest.raises(ValidationError):
        AskRequest(question="why?")
