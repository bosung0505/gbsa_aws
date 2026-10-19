from unittest.mock import Mock
from uuid import uuid4

from interview_evidence.recruiting_assistant.application import ReadOnlyRecruitingPipelineReader


def test_assistant_reader_never_invokes_legacy_backfill_or_decision_methods():
    repository = Mock(spec=["list_recruiting_stages", "list_invitations"])
    context, position = object(), uuid4()
    reader = ReadOnlyRecruitingPipelineReader(repository)
    assert (
        reader.list_recruiting_stages(context, position)
        is repository.list_recruiting_stages.return_value
    )
    assert reader.list_invitations(context, position) is repository.list_invitations.return_value
    assert reader.list_recruiting_stages(context) is repository.list_recruiting_stages.return_value
    assert repository.method_calls == [
        ("list_recruiting_stages", (context, position), {}),
        ("list_invitations", (context, position), {}),
        ("list_recruiting_stages", (context, None), {}),
    ]
