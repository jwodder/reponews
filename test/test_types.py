import pytest
from reponews.types import IssueoidType


def test_all_issueoid_types() -> None:
    assert list(IssueoidType) == [
        IssueoidType.ISSUE,
        IssueoidType.PR,
        IssueoidType.DISCUSSION,
    ]


@pytest.mark.parametrize(
    "obj,name,value,api_name",
    [
        (IssueoidType.ISSUE, "ISSUE", "issue", "issues"),
        (IssueoidType.PR, "PR", "pr", "pullRequests"),
        (IssueoidType.DISCUSSION, "DISCUSSION", "discussion", "discussions"),
    ],
)
def test_issueoid_type(obj: IssueoidType, name: str, value: str, api_name: str) -> None:
    assert obj.name == name
    assert obj.value == value
    assert obj.api_name == api_name
    assert obj is IssueoidType[name]
    # <https://github.com/python/mypy/issues/10573>
    assert obj is IssueoidType(value)  # type: ignore[call-arg]
