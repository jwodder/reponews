from datetime import datetime, timezone
from typing import Optional
import pytest
from reponews.qmanager import (
    PAGE_SIZE,
    NewIssueoidsQuery,
    OwnersReposQuery,
    ViewersReposQuery,
)
from reponews.types import Affiliation, IssueoidType, NewIssueoidEvent, Repository, User
from reponews.util import NotFoundError


def test_viewers_repos_query() -> None:
    q = (
        "query(\n"
        "    $page_size: Int!,\n"
        "    $affiliations: [RepositoryAffiliation!],\n"
        "    $cursor: String\n"
        ") {\n"
        "    viewer {\n"
        "        repositories(\n"
        "            ownerAffiliations: $affiliations,\n"
        "            orderBy: {field: NAME, direction: ASC},\n"
        "            first: $page_size,\n"
        "            after: $cursor\n"
        "        ) {\n"
        "            nodes {\n"
        "                id\n"
        "                nameWithOwner\n"
        "                owner {\n"
        "                    login\n"
        "                }\n"
        "                name\n"
        "                url\n"
        "                description\n"
        "                descriptionHTML\n"
        "            }\n"
        "            pageInfo {\n"
        "                endCursor\n"
        "                hasNextPage\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    manager = ViewersReposQuery(
        affiliations=[Affiliation.OWNER, Affiliation.ORGANIZATION_MEMBER]
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "page_size": PAGE_SIZE,
            "affiliations": ["OWNER", "ORGANIZATION_MEMBER"],
            "cursor": None,
        },
    )
    repos = manager.parse_response(
        {
            "data": {
                "viewer": {
                    "repositories": {
                        "nodes": [
                            {
                                "id": "id:viewer/repo",
                                "nameWithOwner": "viewer/repo",
                                "owner": {"login": "viewer"},
                                "name": "repo",
                                "url": "https://github.com/viewer/repo",
                                "description": "My Very Special Repo(tm)",
                                "descriptionHTML": (
                                    "<div>My Very Special Repo(tm)</div>"
                                ),
                            },
                            {
                                "id": "id:viewer/project",
                                "nameWithOwner": "viewer/project",
                                "owner": {"login": "viewer"},
                                "name": "project",
                                "url": "https://github.com/viewer/project",
                                "description": "My big ol' project",
                                "descriptionHTML": "<div>My big ol' project</div>",
                            },
                            {
                                "id": "id:org/workspace",
                                "nameWithOwner": "org/workspace",
                                "owner": {"login": "org"},
                                "name": "workspace",
                                "url": "https://github.com/viewer/workspace",
                                "description": "Where we all work",
                                "descriptionHTML": "<div>Where we all work</div>",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0001",
                            "hasNextPage": True,
                        },
                    }
                }
            }
        }
    )
    assert repos == [
        Repository(
            id="id:viewer/repo",
            fullname="viewer/repo",
            owner="viewer",
            name="repo",
            url="https://github.com/viewer/repo",
            description="My Very Special Repo(tm)",
            descriptionHTML="<div>My Very Special Repo(tm)</div>",
        ),
        Repository(
            id="id:viewer/project",
            fullname="viewer/project",
            owner="viewer",
            name="project",
            url="https://github.com/viewer/project",
            description="My big ol' project",
            descriptionHTML="<div>My big ol' project</div>",
        ),
        Repository(
            id="id:org/workspace",
            fullname="org/workspace",
            owner="org",
            name="workspace",
            url="https://github.com/viewer/workspace",
            description="Where we all work",
            descriptionHTML="<div>Where we all work</div>",
        ),
    ]
    assert manager.cursor == "cursor:0001"
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "page_size": PAGE_SIZE,
            "affiliations": ["OWNER", "ORGANIZATION_MEMBER"],
            "cursor": "cursor:0001",
        },
    )
    repos = manager.parse_response(
        {
            "data": {
                "viewer": {
                    "repositories": {
                        "nodes": [
                            {
                                "id": "id:viewer/test",
                                "nameWithOwner": "viewer/test",
                                "owner": {"login": "viewer"},
                                "name": "test",
                                "url": "https://github.com/viewer/test",
                                "description": None,
                                "descriptionHTML": "<div></div>",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    }
                }
            }
        }
    )
    assert repos == [
        Repository(
            id="id:viewer/test",
            fullname="viewer/test",
            owner="viewer",
            name="test",
            url="https://github.com/viewer/test",
            description=None,
            descriptionHTML="<div></div>",
        )
    ]
    assert manager.cursor == "cursor:0002"
    assert not manager.has_next_page


def test_owners_repos_query() -> None:
    q = (
        "query(\n"
        "    $owner: String!,\n"
        "    $page_size: Int!,\n"
        "    $cursor: String\n"
        ") {\n"
        "    repositoryOwner(login: $owner) {\n"
        "        repositories(\n"
        "            orderBy: {field: NAME, direction: ASC},\n"
        "            first: $page_size,\n"
        "            after: $cursor\n"
        "        ) {\n"
        "            nodes {\n"
        "                id\n"
        "                nameWithOwner\n"
        "                owner {\n"
        "                    login\n"
        "                }\n"
        "                name\n"
        "                url\n"
        "                description\n"
        "                descriptionHTML\n"
        "            }\n"
        "            pageInfo {\n"
        "                endCursor\n"
        "                hasNextPage\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    manager = OwnersReposQuery(owner="repo.owner")
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {"owner": "repo.owner", "page_size": PAGE_SIZE, "cursor": None},
    )
    repos = manager.parse_response(
        {
            "data": {
                "repositoryOwner": {
                    "repositories": {
                        "nodes": [
                            {
                                "id": "id:repo.owner/repo",
                                "nameWithOwner": "repo.owner/repo",
                                "owner": {"login": "repo.owner"},
                                "name": "repo",
                                "url": "https://github.com/repo.owner/repo",
                                "description": "My Very Special Repo(tm)",
                                "descriptionHTML": (
                                    "<div>My Very Special Repo(tm)</div>"
                                ),
                            },
                            {
                                "id": "id:repo.owner/project",
                                "nameWithOwner": "repo.owner/project",
                                "owner": {"login": "repo.owner"},
                                "name": "project",
                                "url": "https://github.com/repo.owner/project",
                                "description": "My big ol' project",
                                "descriptionHTML": "<div>My big ol' project</div>",
                            },
                            {
                                "id": "id:org/workspace",
                                "nameWithOwner": "org/workspace",
                                "owner": {"login": "org"},
                                "name": "workspace",
                                "url": "https://github.com/repo.owner/workspace",
                                "description": "Where we all work",
                                "descriptionHTML": "<div>Where we all work</div>",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0001",
                            "hasNextPage": True,
                        },
                    }
                }
            }
        }
    )
    assert repos == [
        Repository(
            id="id:repo.owner/repo",
            fullname="repo.owner/repo",
            owner="repo.owner",
            name="repo",
            url="https://github.com/repo.owner/repo",
            description="My Very Special Repo(tm)",
            descriptionHTML="<div>My Very Special Repo(tm)</div>",
        ),
        Repository(
            id="id:repo.owner/project",
            fullname="repo.owner/project",
            owner="repo.owner",
            name="project",
            url="https://github.com/repo.owner/project",
            description="My big ol' project",
            descriptionHTML="<div>My big ol' project</div>",
        ),
        Repository(
            id="id:org/workspace",
            fullname="org/workspace",
            owner="org",
            name="workspace",
            url="https://github.com/repo.owner/workspace",
            description="Where we all work",
            descriptionHTML="<div>Where we all work</div>",
        ),
    ]
    assert manager.cursor == "cursor:0001"
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {"owner": "repo.owner", "page_size": PAGE_SIZE, "cursor": "cursor:0001"},
    )
    repos = manager.parse_response(
        {
            "data": {
                "repositoryOwner": {
                    "repositories": {
                        "nodes": [
                            {
                                "id": "id:repo.owner/test",
                                "nameWithOwner": "repo.owner/test",
                                "owner": {"login": "repo.owner"},
                                "name": "test",
                                "url": "https://github.com/repo.owner/test",
                                "description": None,
                                "descriptionHTML": "<div></div>",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    }
                }
            }
        }
    )
    assert repos == [
        Repository(
            id="id:repo.owner/test",
            fullname="repo.owner/test",
            owner="repo.owner",
            name="test",
            url="https://github.com/repo.owner/test",
            description=None,
            descriptionHTML="<div></div>",
        )
    ]
    assert manager.cursor == "cursor:0002"
    assert not manager.has_next_page


def test_owners_repos_query_not_found() -> None:
    manager = OwnersReposQuery(owner="DNE")
    with pytest.raises(NotFoundError):
        manager.parse_response({"data": {"repositoryOwner": None}})


def test_owners_repos_query_no_repos() -> None:
    manager = OwnersReposQuery(owner="newbie")
    assert (
        manager.parse_response(
            {
                "data": {
                    "repositoryOwner": {
                        "repositories": {
                            "nodes": [],
                            "pageInfo": {
                                "endCursor": None,
                                "hasNextPage": False,
                            },
                        }
                    }
                }
            }
        )
        == []
    )
    assert manager.cursor is None
    assert not manager.has_next_page


def test_new_issueoid_query() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $pullRequests_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            pullRequests(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $pullRequests_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo, types=[IssueoidType.PR], cursors={IssueoidType.PR: "cursor:0001"}
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "pullRequests_cursor": "cursor:0001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "a.contributor",
                                    "url": "https://github.com/a.contributor",
                                    "name": "A. Contributor",
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-04T12:15:07Z",
                                "number": 1,
                                "title": "Add a feature",
                                "url": "https://github.com/viewer/repo/pull/1",
                            },
                            {
                                "author": {
                                    "login": "prbot",
                                    "url": "https://github.com/apps/prbot",
                                },
                                "createdAt": "2021-07-04T12:34:56Z",
                                "number": 2,
                                "title": "Automated pull request",
                                "url": "https://github.com/viewer/repo/pull/2",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": True,
                        },
                    }
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.PR,
            number=1,
            title="Add a feature",
            url="https://github.com/viewer/repo/pull/1",
            author=User(
                login="a.contributor",
                url="https://github.com/a.contributor",
                name="A. Contributor",
                is_me=False,
            ),
        ),
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.PR,
            number=2,
            title="Automated pull request",
            url="https://github.com/viewer/repo/pull/2",
            author=User(
                login="prbot",
                url="https://github.com/apps/prbot",
                name="prbot",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {IssueoidType.PR: "cursor:0002"}
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "pullRequests_cursor": "cursor:0002",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "new-user",
                                    "url": "https://github.com/new-user",
                                    "name": None,
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-05T01:02:03Z",
                                "number": 4,
                                "title": "What am I doing?",
                                "url": "https://github.com/viewer/repo/pull/4",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0003",
                            "hasNextPage": False,
                        },
                    }
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 5, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.PR,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/pull/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name="new-user",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {IssueoidType.PR: "cursor:0003"}
    assert not manager.has_next_page


def test_new_issueoid_query_no_events() -> None:
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo, types=[IssueoidType.PR], cursors={IssueoidType.PR: "cursor:0001"}
    )
    assert (
        manager.parse_response(
            {
                "data": {
                    "node": {
                        "pullRequests": {
                            "nodes": [],
                            "pageInfo": {
                                "endCursor": None,
                                "hasNextPage": False,
                            },
                        }
                    }
                }
            }
        )
        == []
    )
    assert manager.cursors == {IssueoidType.PR: "cursor:0001"}
    assert not manager.has_next_page


def test_new_issueoid_query_null_cursor_no_events() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $discussions_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            discussions(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $discussions_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo,
        types=[IssueoidType.DISCUSSION],
        cursors={IssueoidType.DISCUSSION: None},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "discussions_cursor": None,
        },
    )
    assert (
        manager.parse_response(
            {
                "data": {
                    "node": {
                        "discussions": {
                            "nodes": [],
                            "pageInfo": {
                                "endCursor": None,
                                "hasNextPage": False,
                            },
                        }
                    }
                }
            }
        )
        == []
    )
    assert manager.cursors == {IssueoidType.DISCUSSION: None}
    assert not manager.has_next_page


def test_new_issueoid_query_null_cursor_some_events() -> None:
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo,
        types=[IssueoidType.DISCUSSION],
        cursors={IssueoidType.DISCUSSION: None},
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "discussions": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "need-to-know",
                                    "url": "https://github.com/need-to-know",
                                    "name": "Please tell me",
                                    "isViewer": False,
                                },
                                "createdAt": "2021-11-04T19:46:29Z",
                                "number": 42,
                                "title": "How is everybody doing?",
                                "url": "https://github.com/viewer/repo/discussions/42",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:d001",
                            "hasNextPage": False,
                        },
                    }
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 11, 4, 19, 46, 29, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.DISCUSSION,
            number=42,
            title="How is everybody doing?",
            url="https://github.com/viewer/repo/discussions/42",
            author=User(
                login="need-to-know",
                url="https://github.com/need-to-know",
                name="Please tell me",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {IssueoidType.DISCUSSION: "cursor:d001"}
    assert not manager.has_next_page


@pytest.mark.parametrize("new_cursor", [None, "cursor:0001"])
def test_new_issueoid_query_no_cursor(new_cursor: Optional[str]) -> None:
    q = (
        "query($repo_id: ID!) {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            discussions(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                last: 1\n"
        "            ) {\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(repo=repo, types=[IssueoidType.DISCUSSION], cursors={})
    assert manager.has_next_page
    assert manager.make_query() == (q, {"repo_id": "id:viewer/repo"})
    assert (
        manager.parse_response(
            {
                "data": {
                    "node": {
                        "discussions": {
                            "pageInfo": {"endCursor": new_cursor},
                        }
                    }
                }
            }
        )
        == []
    )
    assert manager.cursors == {IssueoidType.DISCUSSION: new_cursor}
    assert not manager.has_next_page


def test_new_issueoid_query_multiple_types() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $issues_cursor: String,\n"
        "    $discussions_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            issues(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $issues_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "            discussions(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $discussions_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo,
        types=[IssueoidType.ISSUE, IssueoidType.DISCUSSION],
        cursors={
            IssueoidType.ISSUE: "cursor:i001",
            IssueoidType.DISCUSSION: "cursor:d001",
        },
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "issues_cursor": "cursor:i001",
            "discussions_cursor": "cursor:d001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "issues": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "bfg",
                                    "url": "https://github.com/bfg",
                                    "name": "Bug Finder General",
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-04T12:15:07Z",
                                "number": 1,
                                "title": "Found a bug",
                                "url": "https://github.com/viewer/repo/issues/1",
                            },
                            {
                                "author": {
                                    "login": "needstuff",
                                    "url": "https://github.com/needstuff",
                                    "name": None,
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-04T12:34:56Z",
                                "number": 2,
                                "title": "I would like to request a feature",
                                "url": "https://github.com/viewer/repo/issues/2",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:i002",
                            "hasNextPage": True,
                        },
                    },
                    "discussions": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "repo-therapist",
                                    "url": "https://github.com/repo-therapist",
                                    "name": "Repository Therapy",
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-05T01:02:03Z",
                                "number": 3,
                                "title": "Let's talk about your code.",
                                "url": "https://github.com/viewer/repo/discussions/3",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:d002",
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=1,
            title="Found a bug",
            url="https://github.com/viewer/repo/issues/1",
            author=User(
                login="bfg",
                url="https://github.com/bfg",
                name="Bug Finder General",
                is_me=False,
            ),
        ),
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=2,
            title="I would like to request a feature",
            url="https://github.com/viewer/repo/issues/2",
            author=User(
                login="needstuff",
                url="https://github.com/needstuff",
                name="needstuff",
                is_me=False,
            ),
        ),
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 5, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.DISCUSSION,
            number=3,
            title="Let's talk about your code.",
            url="https://github.com/viewer/repo/discussions/3",
            author=User(
                login="repo-therapist",
                url="https://github.com/repo-therapist",
                name="Repository Therapy",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {
        IssueoidType.ISSUE: "cursor:i002",
        IssueoidType.DISCUSSION: "cursor:d002",
    }
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "issues_cursor": "cursor:i002",
            "discussions_cursor": "cursor:d002",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "issues": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "new-user",
                                    "url": "https://github.com/new-user",
                                    "name": None,
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-06T01:02:03Z",
                                "number": 4,
                                "title": "What am I doing?",
                                "url": "https://github.com/viewer/repo/issues/4",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:i003",
                            "hasNextPage": False,
                        },
                    },
                    "discussions": {
                        "nodes": [],
                        "pageInfo": {
                            "endCursor": None,
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 6, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/issues/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name="new-user",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {
        IssueoidType.ISSUE: "cursor:i003",
        IssueoidType.DISCUSSION: "cursor:d002",
    }
    assert not manager.has_next_page


@pytest.mark.parametrize("new_cursor", [None, "cursor:d001"])
def test_new_issueoid_query_multiple_types_one_unset_cursor(
    new_cursor: Optional[str],
) -> None:
    q1 = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $issues_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            issues(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $issues_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "            discussions(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                last: 1\n"
        "            ) {\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    q2 = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $issues_cursor: String,\n"
        "    $discussions_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            issues(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $issues_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "            discussions(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $discussions_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                    }\n"
        "                    createdAt\n"
        "                    number\n"
        "                    title\n"
        "                    url\n"
        "                }\n"
        "                pageInfo {\n"
        "                    endCursor\n"
        "                    hasNextPage\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    repo = Repository(
        id="id:viewer/repo",
        fullname="viewer/repo",
        owner="viewer",
        name="repo",
        url="https://github.com/viewer/repo",
        description="My Very Special Repo(tm)",
        descriptionHTML="<div>My Very Special Repo(tm)</div>",
    )
    manager = NewIssueoidsQuery(
        repo=repo,
        types=[IssueoidType.ISSUE, IssueoidType.DISCUSSION],
        cursors={IssueoidType.ISSUE: "cursor:i001"},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q1,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "issues_cursor": "cursor:i001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "issues": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "bfg",
                                    "url": "https://github.com/bfg",
                                    "name": "Bug Finder General",
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-04T12:15:07Z",
                                "number": 1,
                                "title": "Found a bug",
                                "url": "https://github.com/viewer/repo/issues/1",
                            },
                            {
                                "author": {
                                    "login": "needstuff",
                                    "url": "https://github.com/needstuff",
                                    "name": None,
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-04T12:34:56Z",
                                "number": 2,
                                "title": "I would like to request a feature",
                                "url": "https://github.com/viewer/repo/issues/2",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:i002",
                            "hasNextPage": True,
                        },
                    },
                    "discussions": {
                        "pageInfo": {"endCursor": new_cursor},
                    },
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=1,
            title="Found a bug",
            url="https://github.com/viewer/repo/issues/1",
            author=User(
                login="bfg",
                url="https://github.com/bfg",
                name="Bug Finder General",
                is_me=False,
            ),
        ),
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=2,
            title="I would like to request a feature",
            url="https://github.com/viewer/repo/issues/2",
            author=User(
                login="needstuff",
                url="https://github.com/needstuff",
                name="needstuff",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {
        IssueoidType.ISSUE: "cursor:i002",
        IssueoidType.DISCUSSION: new_cursor,
    }
    assert manager.has_next_page
    assert manager.make_query() == (
        q2,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "issues_cursor": "cursor:i002",
            "discussions_cursor": new_cursor,
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "issues": {
                        "nodes": [
                            {
                                "author": {
                                    "login": "new-user",
                                    "url": "https://github.com/new-user",
                                    "name": None,
                                    "isViewer": False,
                                },
                                "createdAt": "2021-07-06T01:02:03Z",
                                "number": 4,
                                "title": "What am I doing?",
                                "url": "https://github.com/viewer/repo/issues/4",
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:i003",
                            "hasNextPage": False,
                        },
                    },
                    "discussions": {
                        "nodes": [],
                        "pageInfo": {
                            "endCursor": None,
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewIssueoidEvent(
            timestamp=datetime(2021, 7, 6, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            type=IssueoidType.ISSUE,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/issues/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name="new-user",
                is_me=False,
            ),
        ),
    ]
    assert manager.cursors == {
        IssueoidType.ISSUE: "cursor:i003",
        IssueoidType.DISCUSSION: new_cursor,
    }
    assert not manager.has_next_page
