import pytest
from reponews.types import IssueoidType, NewDiscussionEvent, NewIssueEvent, NewPREvent


def test_all_issueoid_types() -> None:
    assert list(IssueoidType) == [
        IssueoidType.ISSUE,
        IssueoidType.PR,
        IssueoidType.DISCUSSION,
    ]


@pytest.mark.parametrize(
    "obj,name,value,api_name,event_cls",
    [
        (IssueoidType.ISSUE, "ISSUE", "issue", "issues", NewIssueEvent),
        (IssueoidType.PR, "PR", "pr", "pullRequests", NewPREvent),
        (
            IssueoidType.DISCUSSION,
            "DISCUSSION",
            "discussion",
            "discussions",
            NewDiscussionEvent,
        ),
    ],
)
def test_issueoid_type(
    obj: IssueoidType, name: str, value: str, api_name: str, event_cls: type
) -> None:
    assert obj.name == name
    assert obj.value == value
    assert obj.api_name == api_name
    assert obj.event_cls is event_cls
    assert obj is IssueoidType[name]
    # <https://github.com/python/mypy/issues/10573>
    assert obj is IssueoidType(value)  # type: ignore[call-arg]
