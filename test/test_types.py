from datetime import datetime, timezone
import pytest
from reponews.types import (
    ActivityType,
    Event,
    NewDiscussionEvent,
    NewForkEvent,
    NewIssueEvent,
    NewPREvent,
    NewReleaseEvent,
    NewStarEvent,
    NewTagEvent,
    RepoActivity,
    RepoRenamedEvent,
    Repository,
    RepoTrackedEvent,
    RepoUntrackedEvent,
    User,
)

REPO = Repository(
    id="id:viewer/repo",
    nameWithOwner="viewer/repo",
    owner=User(
        login="viewer",
        url="https://github.com/viewer",
        name="Vid Ewer",
        isViewer=True,
    ),
    name="repo",
    url="https://github.com/viewer/repo",
    description="My Very Special Repo(tm)",
    descriptionHTML="<div>My Very Special Repo(tm)</div>",
)

USER = User(
    login="luser", url="https://github.com/luser", name="Linux User", isViewer=False
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


@pytest.mark.parametrize(
    "ev,s",
    [
        (
            NewIssueEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                number=42,
                title="I found a bug!",
                author=USER,
                url="https://github.com/viewer/repo/issues/42",
            ),
            "[viewer/repo] ISSUE #42: I found a bug! (@luser)\n"
            "<https://github.com/viewer/repo/issues/42>",
        ),
        (
            NewPREvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                number=43,
                title="I fixed the bug",
                author=USER,
                url="https://github.com/viewer/repo/pull/43",
            ),
            "[viewer/repo] PR #43: I fixed the bug (@luser)\n"
            "<https://github.com/viewer/repo/pull/43>",
        ),
        (
            NewDiscussionEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                number=44,
                title="Where do bugs come from?",
                author=USER,
                url="https://github.com/viewer/repo/discussions/44",
            ),
            "[viewer/repo] DISCUSSION #44: Where do bugs come from? (@luser)\n"
            "<https://github.com/viewer/repo/discussions/44>",
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.0 — Initial release",
                tagName="v1.0.0",
                author=USER,
                description=(
                    "Our first full release!  New in this version:\n"
                    "\n"
                    "- Added a feature\n"
                    "- Fixed a bug"
                ),
                descriptionHTML=(
                    "<p>Our first full release!  New in this version:</p>\n"
                    "<ul>\n"
                    "<li>Added a feature</li>\n"
                    "<li>Fixed a bug</li>\n"
                    "</ul>"
                ),
                isDraft=False,
                isPrerelease=False,
                url="https://github.com/viewer/repo/releases/tag/v1.0.0",
            ),
            "[viewer/repo] RELEASE v1.0.0: v1.0 — Initial release (@luser)\n"
            "<https://github.com/viewer/repo/releases/tag/v1.0.0>\n"
            "> Our first full release!  New in this version:\n"
            "> \n"
            "> - Added a feature\n"
            "> - Fixed a bug",
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name=None,
                tagName="v1.0.0a1",
                author=None,
                description=None,
                descriptionHTML=None,
                isDraft=True,
                isPrerelease=True,
                url="https://github.com/viewer/repo/releases/tag/v1.0.0a1",
            ),
            "[viewer/repo] RELEASE v1.0.0a1 [draft] [prerelease]\n"
            "<https://github.com/viewer/repo/releases/tag/v1.0.0a1>",
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="Empty description",
                tagName="v1.0.1",
                author=USER,
                description="",
                descriptionHTML="",
                isDraft=False,
                isPrerelease=False,
                url="https://github.com/viewer/repo/releases/tag/v1.0.1",
            ),
            "[viewer/repo] RELEASE v1.0.1: Empty description (@luser)\n"
            "<https://github.com/viewer/repo/releases/tag/v1.0.1>",
        ),
        (
            NewTagEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.2.3",
                user=USER,
            ),
            "[viewer/repo] TAG v1.2.3 (@luser)\n"
            "<https://github.com/viewer/repo/releases/tag/v1.2.3>",
        ),
        (
            NewTagEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.2.3",
                user=None,
            ),
            "[viewer/repo] TAG v1.2.3\n"
            "<https://github.com/viewer/repo/releases/tag/v1.2.3>",
        ),
        (
            NewStarEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                user=USER,
            ),
            "★ @luser starred viewer/repo",
        ),
        (
            NewForkEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                fork=Repository(
                    id="id:forker/repo",
                    nameWithOwner="forker/repo",
                    owner=User(
                        login="forker",
                        url="https://github.com/forker",
                        name="Fabian Orker",
                        isViewer=False,
                    ),
                    name="repo",
                    url="https://github.com/forker/repo",
                    description="My Very Special Repo(tm)",
                    descriptionHTML="<div>My Very Special Repo(tm)</div>",
                ),
            ),
            "@forker forked viewer/repo\n<https://github.com/forker/repo>",
        ),
        (
            RepoTrackedEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
            ),
            "Now tracking repository viewer/repo\n"
            "<https://github.com/viewer/repo>\n"
            "> My Very Special Repo(tm)",
        ),
        (
            RepoTrackedEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=Repository(**{**dict(REPO), "description": None}),
            ),
            "Now tracking repository viewer/repo\n<https://github.com/viewer/repo>",
        ),
        (
            RepoUntrackedEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
            ),
            "No longer tracking repository viewer/repo",
        ),
        (
            RepoRenamedEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                old_repo=Repository(
                    id="id:viewer/test",
                    nameWithOwner="viewer/test",
                    owner=User(
                        login="viewer",
                        url="https://github.com/viewer",
                        name="Vid Ewer",
                        isViewer=True,
                    ),
                    name="test",
                    url="https://github.com/viewer/test",
                    description="This is a test.",
                    descriptionHTML="<div>This is a test.</div>",
                ),
            ),
            "Repository renamed: viewer/test → viewer/repo",
        ),
    ],
)
def test_event_render(ev: Event, s: str) -> None:
    assert ev.render() == s


@pytest.mark.parametrize(
    "ev,mine",
    [
        (
            NewIssueEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                number=42,
                title="I found a bug!",
                author=USER,
                url="https://github.com/viewer/repo/issues/42",
            ),
            False,
        ),
        (
            NewPREvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                number=43,
                title="I fixed the bug",
                author=REPO.owner,
                url="https://github.com/viewer/repo/pull/43",
            ),
            True,
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.0 — Initial release",
                tagName="v1.0.0",
                author=USER,
                description=(
                    "Our first full release!  New in this version:\n"
                    "\n"
                    "- Added a feature\n"
                    "- Fixed a bug"
                ),
                descriptionHTML=(
                    "<p>Our first full release!  New in this version:</p>\n"
                    "<ul>\n"
                    "<li>Added a feature</li>\n"
                    "<li>Fixed a bug</li>\n"
                    "</ul>"
                ),
                isDraft=False,
                isPrerelease=False,
                url="https://github.com/viewer/repo/releases/tag/v1.0.0",
            ),
            False,
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name=None,
                tagName="v1.0.0a1",
                author=None,
                description=None,
                descriptionHTML=None,
                isDraft=True,
                isPrerelease=True,
                url="https://github.com/viewer/repo/releases/tag/v1.0.0a1",
            ),
            False,
        ),
        (
            NewReleaseEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="Empty description",
                tagName="v1.0.1",
                author=REPO.owner,
                description="",
                descriptionHTML="",
                isDraft=False,
                isPrerelease=False,
                url="https://github.com/viewer/repo/releases/tag/v1.0.1",
            ),
            True,
        ),
        (
            NewTagEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.2.3",
                user=USER,
            ),
            False,
        ),
        (
            NewTagEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.2.3",
                user=None,
            ),
            False,
        ),
        (
            NewTagEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                name="v1.2.3",
                user=REPO.owner,
            ),
            True,
        ),
        (
            NewStarEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                user=USER,
            ),
            False,
        ),
        (
            NewStarEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                user=REPO.owner,
            ),
            True,
        ),
        (
            NewForkEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                fork=Repository(
                    id="id:forker/repo",
                    nameWithOwner="forker/repo",
                    owner=User(
                        login="forker",
                        url="https://github.com/forker",
                        name="Fabian Orker",
                        isViewer=False,
                    ),
                    name="repo",
                    url="https://github.com/forker/repo",
                    description="My Very Special Repo(tm)",
                    descriptionHTML="<div>My Very Special Repo(tm)</div>",
                ),
            ),
            False,
        ),
        (
            NewForkEvent(
                timestamp=datetime(2021, 11, 18, 15, 28, 2, tzinfo=timezone.utc),
                repo=REPO,
                fork=Repository(
                    id="id:forker/repo",
                    nameWithOwner="forker/repo",
                    owner=REPO.owner,
                    name="repo",
                    url="https://github.com/forker/repo",
                    description="My Very Special Repo(tm)",
                    descriptionHTML="<div>My Very Special Repo(tm)</div>",
                ),
            ),
            True,
        ),
    ],
)
def test_repo_activity_is_mine(ev: RepoActivity, mine: bool) -> None:
    assert ev.is_mine is mine
