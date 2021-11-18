import pytest
from reponews.types import (
    ActivityType,
    NewDiscussionEvent,
    NewForkEvent,
    NewIssueEvent,
    NewPREvent,
    NewReleaseEvent,
    NewStarEvent,
    NewTagEvent,
)


def test_all_activity_types() -> None:
    assert list(ActivityType) == [
        ActivityType.ISSUE,
        ActivityType.PR,
        ActivityType.DISCUSSION,
        ActivityType.RELEASE,
        ActivityType.TAG,
        ActivityType.STAR,
        ActivityType.FORK,
    ]


@pytest.mark.parametrize(
    "obj,name,value,api_name,event_cls",
    [
        (ActivityType.ISSUE, "ISSUE", "issue", "issues", NewIssueEvent),
        (ActivityType.PR, "PR", "pr", "pullRequests", NewPREvent),
        (
            ActivityType.DISCUSSION,
            "DISCUSSION",
            "discussion",
            "discussions",
            NewDiscussionEvent,
        ),
        (
            ActivityType.RELEASE,
            "RELEASE",
            "release",
            "releases",
            NewReleaseEvent,
        ),
        (
            ActivityType.TAG,
            "TAG",
            "tag",
            "tags",
            NewTagEvent,
        ),
        (
            ActivityType.STAR,
            "STAR",
            "star",
            "stargazers",
            NewStarEvent,
        ),
        (
            ActivityType.FORK,
            "FORK",
            "fork",
            "forks",
            NewForkEvent,
        ),
    ],
)
def test_activity_type(
    obj: ActivityType, name: str, value: str, api_name: str, event_cls: type
) -> None:
    assert obj.name == name
    assert obj.value == value
    assert obj.api_name == api_name
    assert obj.event_cls is event_cls
    assert obj is ActivityType[name]
    # <https://github.com/python/mypy/issues/10573>
    assert obj is ActivityType(value)  # type: ignore[call-arg]
