from datetime import datetime, timezone
from typing import Optional
import pytest
from reponews.qmanager import (
    PAGE_SIZE,
    ActivityQuery,
    OwnersReposQuery,
    SingleRepoQuery,
    ViewersReposQuery,
)
from reponews.types import (
    ActivityType,
    Affiliation,
    NewDiscussionEvent,
    NewForkEvent,
    NewIssueEvent,
    NewPREvent,
    NewReleaseEvent,
    NewStarEvent,
    NewTagEvent,
    Repository,
    User,
)
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
        "                    url\n"
        "                    ... on User {\n"
        "                        name\n"
        "                        isViewer\n"
        "                    }\n"
        "                    ... on Organization {\n"
        "                        name\n"
        "                    }\n"
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
                                "owner": {
                                    "login": "viewer",
                                    "url": "https://github.com/viewer",
                                    "name": "Vid Ewer",
                                    "isViewer": True,
                                },
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
                                "owner": {
                                    "login": "viewer",
                                    "url": "https://github.com/viewer",
                                    "name": "Vid Ewer",
                                    "isViewer": True,
                                },
                                "name": "project",
                                "url": "https://github.com/viewer/project",
                                "description": "My big ol' project",
                                "descriptionHTML": "<div>My big ol' project</div>",
                            },
                            {
                                "id": "id:org/workspace",
                                "nameWithOwner": "org/workspace",
                                "owner": {
                                    "login": "org",
                                    "url": "https://github.com/org",
                                    "name": "The Org Corp",
                                },
                                "name": "workspace",
                                "url": "https://github.com/org/workspace",
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
        ),
        Repository(
            id="id:viewer/project",
            nameWithOwner="viewer/project",
            owner=User(
                login="viewer",
                url="https://github.com/viewer",
                name="Vid Ewer",
                isViewer=True,
            ),
            name="project",
            url="https://github.com/viewer/project",
            description="My big ol' project",
            descriptionHTML="<div>My big ol' project</div>",
        ),
        Repository(
            id="id:org/workspace",
            nameWithOwner="org/workspace",
            owner=User(
                login="org",
                url="https://github.com/org",
                name="The Org Corp",
                isViewer=False,
            ),
            name="workspace",
            url="https://github.com/org/workspace",
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
                                "owner": {
                                    "login": "viewer",
                                    "url": "https://github.com/viewer",
                                    "name": "Vid Ewer",
                                    "isViewer": True,
                                },
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
            nameWithOwner="viewer/test",
            owner=User(
                login="viewer",
                url="https://github.com/viewer",
                name="Vid Ewer",
                isViewer=True,
            ),
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
        "                    url\n"
        "                    ... on User {\n"
        "                        name\n"
        "                        isViewer\n"
        "                    }\n"
        "                    ... on Organization {\n"
        "                        name\n"
        "                    }\n"
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
                                "owner": {
                                    "login": "repo.owner",
                                    "url": "https://github.com/repo.owner",
                                    "name": "Repository Owner",
                                    "isViewer": False,
                                },
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
                                "owner": {
                                    "login": "repo.owner",
                                    "url": "https://github.com/repo.owner",
                                    "name": "Repository Owner",
                                    "isViewer": False,
                                },
                                "name": "project",
                                "url": "https://github.com/repo.owner/project",
                                "description": "My big ol' project",
                                "descriptionHTML": "<div>My big ol' project</div>",
                            },
                            {
                                "id": "id:org/workspace",
                                "nameWithOwner": "org/workspace",
                                "owner": {
                                    "login": "org",
                                    "url": "https://github.com/org",
                                    "name": "The Org Corp",
                                },
                                "name": "workspace",
                                "url": "https://github.com/org/workspace",
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
            nameWithOwner="repo.owner/repo",
            owner=User(
                login="repo.owner",
                url="https://github.com/repo.owner",
                name="Repository Owner",
                isViewer=False,
            ),
            name="repo",
            url="https://github.com/repo.owner/repo",
            description="My Very Special Repo(tm)",
            descriptionHTML="<div>My Very Special Repo(tm)</div>",
        ),
        Repository(
            id="id:repo.owner/project",
            nameWithOwner="repo.owner/project",
            owner=User(
                login="repo.owner",
                url="https://github.com/repo.owner",
                name="Repository Owner",
                isViewer=False,
            ),
            name="project",
            url="https://github.com/repo.owner/project",
            description="My big ol' project",
            descriptionHTML="<div>My big ol' project</div>",
        ),
        Repository(
            id="id:org/workspace",
            nameWithOwner="org/workspace",
            owner=User(
                login="org",
                url="https://github.com/org",
                name="The Org Corp",
                isViewer=False,
            ),
            name="workspace",
            url="https://github.com/org/workspace",
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
                                "owner": {
                                    "login": "repo.owner",
                                    "url": "https://github.com/repo.owner",
                                    "name": "Repository Owner",
                                    "isViewer": False,
                                },
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
            nameWithOwner="repo.owner/test",
            owner=User(
                login="repo.owner",
                url="https://github.com/repo.owner",
                name="Repository Owner",
                isViewer=False,
            ),
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


def test_single_repo_query() -> None:
    q = (
        "query($owner: String!, $name: String!) {\n"
        "    repository(owner: $owner, name: $name) {\n"
        "        id\n"
        "        nameWithOwner\n"
        "        owner {\n"
        "            login\n"
        "            url\n"
        "            ... on User {\n"
        "                name\n"
        "                isViewer\n"
        "            }\n"
        "            ... on Organization {\n"
        "                name\n"
        "            }\n"
        "        }\n"
        "        name\n"
        "        url\n"
        "        description\n"
        "        descriptionHTML\n"
        "    }\n"
        "}\n"
    )
    manager = SingleRepoQuery(owner="repo.owner", name="repo")
    assert manager.has_next_page
    assert manager.make_query() == (q, {"owner": "repo.owner", "name": "repo"})
    repos = manager.parse_response(
        {
            "data": {
                "repository": {
                    "id": "id:repo.owner/repo",
                    "nameWithOwner": "repo.owner/repo",
                    "owner": {
                        "login": "repo.owner",
                        "url": "https://github.com/repo.owner",
                        "name": "Repository Owner",
                        "isViewer": False,
                    },
                    "name": "repo",
                    "url": "https://github.com/repo.owner/repo",
                    "description": "My Very Special Repo(tm)",
                    "descriptionHTML": "<div>My Very Special Repo(tm)</div>",
                },
            }
        }
    )
    assert repos == [
        Repository(
            id="id:repo.owner/repo",
            nameWithOwner="repo.owner/repo",
            owner=User(
                login="repo.owner",
                url="https://github.com/repo.owner",
                name="Repository Owner",
                isViewer=False,
            ),
            name="repo",
            url="https://github.com/repo.owner/repo",
            description="My Very Special Repo(tm)",
            descriptionHTML="<div>My Very Special Repo(tm)</div>",
        ),
    ]
    assert not manager.has_next_page


def test_activity_query() -> None:
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
    manager = ActivityQuery(
        repo=repo, types=[ActivityType.PR], cursors={ActivityType.PR: "cursor:0001"}
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
        NewPREvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            number=1,
            title="Add a feature",
            url="https://github.com/viewer/repo/pull/1",
            author=User(
                login="a.contributor",
                url="https://github.com/a.contributor",
                name="A. Contributor",
                isViewer=False,
            ),
        ),
        NewPREvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            number=2,
            title="Automated pull request",
            url="https://github.com/viewer/repo/pull/2",
            author=User(
                login="prbot",
                url="https://github.com/apps/prbot",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {ActivityType.PR: "cursor:0002"}
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
        NewPREvent(
            timestamp=datetime(2021, 7, 5, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/pull/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {ActivityType.PR: "cursor:0003"}
    assert not manager.has_next_page


def test_activity_query_no_events() -> None:
    repo = Repository(
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
    manager = ActivityQuery(
        repo=repo, types=[ActivityType.PR], cursors={ActivityType.PR: "cursor:0001"}
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
    assert manager.cursors == {ActivityType.PR: "cursor:0001"}
    assert not manager.has_next_page


def test_activity_query_null_cursor_no_events() -> None:
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.DISCUSSION],
        cursors={ActivityType.DISCUSSION: None},
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
    assert manager.cursors == {ActivityType.DISCUSSION: None}
    assert not manager.has_next_page


def test_activity_query_null_cursor_some_events() -> None:
    repo = Repository(
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.DISCUSSION],
        cursors={ActivityType.DISCUSSION: None},
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
        NewDiscussionEvent(
            timestamp=datetime(2021, 11, 4, 19, 46, 29, tzinfo=timezone.utc),
            repo=repo,
            number=42,
            title="How is everybody doing?",
            url="https://github.com/viewer/repo/discussions/42",
            author=User(
                login="need-to-know",
                url="https://github.com/need-to-know",
                name="Please tell me",
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {ActivityType.DISCUSSION: "cursor:d001"}
    assert not manager.has_next_page


@pytest.mark.parametrize("new_cursor", [None, "cursor:0001"])
def test_activity_query_no_cursor(new_cursor: Optional[str]) -> None:
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
    manager = ActivityQuery(repo=repo, types=[ActivityType.DISCUSSION], cursors={})
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
    assert manager.cursors == {ActivityType.DISCUSSION: new_cursor}
    assert not manager.has_next_page


def test_activity_query_multiple_types() -> None:
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.ISSUE, ActivityType.DISCUSSION],
        cursors={
            ActivityType.ISSUE: "cursor:i001",
            ActivityType.DISCUSSION: "cursor:d001",
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
        NewIssueEvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            number=1,
            title="Found a bug",
            url="https://github.com/viewer/repo/issues/1",
            author=User(
                login="bfg",
                url="https://github.com/bfg",
                name="Bug Finder General",
                isViewer=False,
            ),
        ),
        NewIssueEvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            number=2,
            title="I would like to request a feature",
            url="https://github.com/viewer/repo/issues/2",
            author=User(
                login="needstuff",
                url="https://github.com/needstuff",
                name=None,
                isViewer=False,
            ),
        ),
        NewDiscussionEvent(
            timestamp=datetime(2021, 7, 5, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            number=3,
            title="Let's talk about your code.",
            url="https://github.com/viewer/repo/discussions/3",
            author=User(
                login="repo-therapist",
                url="https://github.com/repo-therapist",
                name="Repository Therapy",
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {
        ActivityType.ISSUE: "cursor:i002",
        ActivityType.DISCUSSION: "cursor:d002",
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
        NewIssueEvent(
            timestamp=datetime(2021, 7, 6, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/issues/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {
        ActivityType.ISSUE: "cursor:i003",
        ActivityType.DISCUSSION: "cursor:d002",
    }
    assert not manager.has_next_page


@pytest.mark.parametrize("new_cursor", [None, "cursor:d001"])
def test_activity_query_multiple_types_one_unset_cursor(
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.ISSUE, ActivityType.DISCUSSION],
        cursors={ActivityType.ISSUE: "cursor:i001"},
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
        NewIssueEvent(
            timestamp=datetime(2021, 7, 4, 12, 15, 7, tzinfo=timezone.utc),
            repo=repo,
            number=1,
            title="Found a bug",
            url="https://github.com/viewer/repo/issues/1",
            author=User(
                login="bfg",
                url="https://github.com/bfg",
                name="Bug Finder General",
                isViewer=False,
            ),
        ),
        NewIssueEvent(
            timestamp=datetime(2021, 7, 4, 12, 34, 56, tzinfo=timezone.utc),
            repo=repo,
            number=2,
            title="I would like to request a feature",
            url="https://github.com/viewer/repo/issues/2",
            author=User(
                login="needstuff",
                url="https://github.com/needstuff",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {
        ActivityType.ISSUE: "cursor:i002",
        ActivityType.DISCUSSION: new_cursor,
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
        NewIssueEvent(
            timestamp=datetime(2021, 7, 6, 1, 2, 3, tzinfo=timezone.utc),
            repo=repo,
            number=4,
            title="What am I doing?",
            url="https://github.com/viewer/repo/issues/4",
            author=User(
                login="new-user",
                url="https://github.com/new-user",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {
        ActivityType.ISSUE: "cursor:i003",
        ActivityType.DISCUSSION: new_cursor,
    }
    assert not manager.has_next_page


def test_activity_query_releases() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $releases_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            releases(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $releases_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    name\n"
        "                    tagName\n"
        "                    author {\n"
        "                        login\n"
        "                        url\n"
        "                        name\n"
        "                        isViewer\n"
        "                    }\n"
        "                    createdAt\n"
        "                    description\n"
        "                    descriptionHTML\n"
        "                    isPrerelease\n"
        "                    isDraft\n"
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.RELEASE],
        cursors={ActivityType.RELEASE: "cursor:0001"},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "releases_cursor": "cursor:0001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "releases": {
                        "nodes": [
                            {
                                "name": "v0.1.0 — Initial release",
                                "tagName": "v0.1.0",
                                "author": {
                                    "login": "viewer",
                                    "url": "https://github.com/viewer",
                                    "name": "Vid Ewer",
                                    "isViewer": True,
                                },
                                "createdAt": "2021-11-17T15:15:57Z",
                                "description": None,
                                "descriptionHTML": None,
                                "isPrerelease": False,
                                "isDraft": False,
                                "url": (
                                    "https://github.com/viewer/repo/releases/tag/v0.1.0"
                                ),
                            },
                            {
                                "name": "v0.1.0 — Bug fix",
                                "tagName": "v0.1.1",
                                "author": None,
                                "createdAt": "2021-11-17T16:12:34Z",
                                "description": (
                                    "* Fixed a bug in the thingy.\r\n"
                                    "* Hopefully didn't introduce any new bugs"
                                ),
                                "descriptionHTML": (
                                    "<ul>\n"
                                    "<li>Fixed a bug in the thingy.</li>\n"
                                    "<li>Hopefully didn't introduce any new bugs</li>\n"
                                    "</ul>"
                                ),
                                "isPrerelease": False,
                                "isDraft": False,
                                "url": (
                                    "https://github.com/viewer/repo/releases/tag/v0.1.1"
                                ),
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewReleaseEvent(
            timestamp=datetime(2021, 11, 17, 15, 15, 57, tzinfo=timezone.utc),
            repo=repo,
            name="v0.1.0 — Initial release",
            tagName="v0.1.0",
            author=User(
                login="viewer",
                url="https://github.com/viewer",
                name="Vid Ewer",
                isViewer=True,
            ),
            description=None,
            descriptionHTML=None,
            isPrerelease=False,
            isDraft=False,
            url="https://github.com/viewer/repo/releases/tag/v0.1.0",
        ),
        NewReleaseEvent(
            timestamp=datetime(2021, 11, 17, 16, 12, 34, tzinfo=timezone.utc),
            repo=repo,
            name="v0.1.0 — Bug fix",
            tagName="v0.1.1",
            author=None,
            description=(
                "* Fixed a bug in the thingy.\n"
                "* Hopefully didn't introduce any new bugs"
            ),
            descriptionHTML=(
                "<ul>\n"
                "<li>Fixed a bug in the thingy.</li>\n"
                "<li>Hopefully didn't introduce any new bugs</li>\n"
                "</ul>"
            ),
            isPrerelease=False,
            isDraft=False,
            url="https://github.com/viewer/repo/releases/tag/v0.1.1",
        ),
    ]
    assert manager.cursors == {ActivityType.RELEASE: "cursor:0002"}
    assert not manager.has_next_page


def test_activity_query_releases_no_cursor() -> None:
    q = (
        "query($repo_id: ID!) {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            releases(\n"
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
    manager = ActivityQuery(repo=repo, types=[ActivityType.RELEASE], cursors={})
    assert manager.has_next_page
    assert manager.make_query() == (q, {"repo_id": "id:viewer/repo"})


def test_activity_query_tags() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $tags_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            tags: refs(\n"
        '                refPrefix: "refs/tags/",\n'
        "                orderBy: {field: TAG_COMMIT_DATE, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $tags_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    name\n"
        "                    target {\n"
        "                        __typename\n"
        "                        ... on Tag {\n"
        "                            tagger {\n"
        "                                date\n"
        "                                user {\n"
        "                                    login\n"
        "                                    url\n"
        "                                    name\n"
        "                                    isViewer\n"
        "                                }\n"
        "                            }\n"
        "                        }\n"
        "                        ... on Commit {\n"
        "                            committedDate\n"
        "                            author {\n"
        "                                user {\n"
        "                                    login\n"
        "                                    url\n"
        "                                    name\n"
        "                                    isViewer\n"
        "                                }\n"
        "                            }\n"
        "                        }\n"
        "                    }\n"
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.TAG],
        cursors={ActivityType.TAG: "cursor:0001"},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "tags_cursor": "cursor:0001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "tags": {
                        "nodes": [
                            {
                                "name": "v0.0.0",
                                "target": {
                                    "__typename": "Commit",
                                    "committedDate": "2021-11-17T15:56:48Z",
                                    "author": {
                                        "user": {
                                            "login": "viewer",
                                            "url": "https://github.com/viewer",
                                            "name": "Vid Ewer",
                                            "isViewer": True,
                                        },
                                    },
                                },
                            },
                            {
                                "name": "v0.0.0a0",
                                "target": {
                                    "__typename": "Commit",
                                    "committedDate": "2021-11-17T15:56:50Z",
                                    "author": None,
                                },
                            },
                            {
                                "name": "v0.1.0",
                                "target": {
                                    "__typename": "Tag",
                                    "tagger": {
                                        "date": "2021-11-17T16:04:31Z",
                                        "user": {
                                            "login": "viewer",
                                            "url": "https://github.com/viewer",
                                            "name": "Vid Ewer",
                                            "isViewer": True,
                                        },
                                    },
                                },
                            },
                            {
                                "name": "v0.1.0-tree",
                                "target": {"__typename": "Tree"},
                            },
                            {
                                "name": "v0.0.1a",
                                "target": {
                                    "__typename": "Commit",
                                    "committedDate": None,
                                    "author": None,
                                },
                            },
                            {
                                "name": "v0.1.1",
                                "target": {"__typename": "Tag", "tagger": None},
                            },
                            {
                                "name": "v0.1.2",
                                "target": {
                                    "__typename": "Tag",
                                    "tagger": {
                                        "date": "2021-11-18T00:00:00Z",
                                        "user": None,
                                    },
                                },
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewTagEvent(
            timestamp=datetime(2021, 11, 17, 15, 56, 48, tzinfo=timezone.utc),
            repo=repo,
            name="v0.0.0",
            user=User(
                login="viewer",
                url="https://github.com/viewer",
                name="Vid Ewer",
                isViewer=True,
            ),
        ),
        NewTagEvent(
            timestamp=datetime(2021, 11, 17, 15, 56, 50, tzinfo=timezone.utc),
            repo=repo,
            name="v0.0.0a0",
            user=None,
        ),
        NewTagEvent(
            timestamp=datetime(2021, 11, 17, 16, 4, 31, tzinfo=timezone.utc),
            repo=repo,
            name="v0.1.0",
            user=User(
                login="viewer",
                url="https://github.com/viewer",
                name="Vid Ewer",
                isViewer=True,
            ),
        ),
        NewTagEvent(
            timestamp=datetime(2021, 11, 18, 0, 0, 0, tzinfo=timezone.utc),
            repo=repo,
            name="v0.1.2",
            user=None,
        ),
    ]
    assert manager.cursors == {ActivityType.TAG: "cursor:0002"}
    assert not manager.has_next_page


def test_activity_query_tags_no_cursor() -> None:
    q = (
        "query($repo_id: ID!) {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            tags: refs(\n"
        '                refPrefix: "refs/tags/",\n'
        "                orderBy: {field: TAG_COMMIT_DATE, direction: ASC},\n"
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
    manager = ActivityQuery(repo=repo, types=[ActivityType.TAG], cursors={})
    assert manager.has_next_page
    assert manager.make_query() == (q, {"repo_id": "id:viewer/repo"})


def test_activity_query_stargazers() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $stargazers_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            stargazers(\n"
        "                orderBy: {field: STARRED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $stargazers_cursor\n"
        "            ) {\n"
        "                edges {\n"
        "                    starredAt\n"
        "                    user: node {\n"
        "                        login\n"
        "                        url\n"
        "                        name\n"
        "                        isViewer\n"
        "                    }\n"
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.STAR],
        cursors={ActivityType.STAR: "cursor:0001"},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "stargazers_cursor": "cursor:0001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "stargazers": {
                        "edges": [
                            {
                                "starredAt": "2021-11-17T15:26:39Z",
                                "user": {
                                    "login": "repo.fan",
                                    "url": "https://github.com/repo.fan",
                                    "name": "Fan of Repositories",
                                    "isViewer": False,
                                },
                            },
                            {
                                "starredAt": "2021-11-17T23:45:56Z",
                                "user": {
                                    "login": "starry.user",
                                    "url": "https://github.com/starry.user",
                                    "name": None,
                                    "isViewer": False,
                                },
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewStarEvent(
            timestamp=datetime(2021, 11, 17, 15, 26, 39, tzinfo=timezone.utc),
            repo=repo,
            user=User(
                login="repo.fan",
                url="https://github.com/repo.fan",
                name="Fan of Repositories",
                isViewer=False,
            ),
        ),
        NewStarEvent(
            timestamp=datetime(2021, 11, 17, 23, 45, 56, tzinfo=timezone.utc),
            repo=repo,
            user=User(
                login="starry.user",
                url="https://github.com/starry.user",
                name=None,
                isViewer=False,
            ),
        ),
    ]
    assert manager.cursors == {ActivityType.STAR: "cursor:0002"}
    assert not manager.has_next_page


def test_activity_query_stargazers_no_cursor() -> None:
    q = (
        "query($repo_id: ID!) {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            stargazers(\n"
        "                orderBy: {field: STARRED_AT, direction: ASC},\n"
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
    manager = ActivityQuery(repo=repo, types=[ActivityType.STAR], cursors={})
    assert manager.has_next_page
    assert manager.make_query() == (q, {"repo_id": "id:viewer/repo"})


def test_activity_query_forks() -> None:
    q = (
        "query(\n"
        "    $repo_id: ID!,\n"
        "    $page_size: Int!,\n"
        "    $forks_cursor: String\n"
        ") {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            forks(\n"
        "                orderBy: {field: CREATED_AT, direction: ASC},\n"
        "                first: $page_size,\n"
        "                after: $forks_cursor\n"
        "            ) {\n"
        "                nodes {\n"
        "                    createdAt\n"
        "                    id\n"
        "                    nameWithOwner\n"
        "                    owner {\n"
        "                        login\n"
        "                        url\n"
        "                        ... on User {\n"
        "                            name\n"
        "                            isViewer\n"
        "                        }\n"
        "                        ... on Organization {\n"
        "                            name\n"
        "                        }\n"
        "                    }\n"
        "                    name\n"
        "                    url\n"
        "                    description\n"
        "                    descriptionHTML\n"
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
    manager = ActivityQuery(
        repo=repo,
        types=[ActivityType.FORK],
        cursors={ActivityType.FORK: "cursor:0001"},
    )
    assert manager.has_next_page
    assert manager.make_query() == (
        q,
        {
            "repo_id": "id:viewer/repo",
            "page_size": PAGE_SIZE,
            "forks_cursor": "cursor:0001",
        },
    )
    events = manager.parse_response(
        {
            "data": {
                "node": {
                    "forks": {
                        "nodes": [
                            {
                                "id": "id:archive/repo",
                                "createdAt": "2021-11-17T15:33:53Z",
                                "nameWithOwner": "archive/repo",
                                "owner": {
                                    "login": "archive",
                                    "url": "https://github.com/archive",
                                    "name": "The Repository Archive Org",
                                },
                                "name": "repo",
                                "url": "https://github.com/archive/repo",
                                "description": 'Archive of "My Very Special Repo(tm)"',
                                "descriptionHTML": (
                                    '<div>Archive of "My Very Special Repo(tm)"</div>'
                                ),
                            },
                            {
                                "id": "id:forker/repofork",
                                "createdAt": "2021-11-17T16:43:54Z",
                                "nameWithOwner": "forker/repofork",
                                "owner": {
                                    "login": "forker",
                                    "url": "https://github.com/forker",
                                    "name": "I Fork Repositories",
                                    "isViewer": False,
                                },
                                "name": "repofork",
                                "url": "https://github.com/archive/repofork",
                                "description": "My Very Special Repo(tm)",
                                "descriptionHTML": (
                                    "<div>My Very Special Repo(tm)</div>"
                                ),
                            },
                        ],
                        "pageInfo": {
                            "endCursor": "cursor:0002",
                            "hasNextPage": False,
                        },
                    },
                }
            }
        }
    )
    assert events == [
        NewForkEvent(
            timestamp=datetime(2021, 11, 17, 15, 33, 53, tzinfo=timezone.utc),
            repo=repo,
            fork=Repository(
                id="id:archive/repo",
                nameWithOwner="archive/repo",
                owner=User(
                    login="archive",
                    url="https://github.com/archive",
                    name="The Repository Archive Org",
                    isViewer=False,
                ),
                name="repo",
                url="https://github.com/archive/repo",
                description='Archive of "My Very Special Repo(tm)"',
                descriptionHTML='<div>Archive of "My Very Special Repo(tm)"</div>',
            ),
        ),
        NewForkEvent(
            timestamp=datetime(2021, 11, 17, 16, 43, 54, tzinfo=timezone.utc),
            repo=repo,
            fork=Repository(
                id="id:forker/repofork",
                nameWithOwner="forker/repofork",
                owner=User(
                    login="forker",
                    url="https://github.com/forker",
                    name="I Fork Repositories",
                    isViewer=False,
                ),
                name="repofork",
                url="https://github.com/archive/repofork",
                description="My Very Special Repo(tm)",
                descriptionHTML="<div>My Very Special Repo(tm)</div>",
            ),
        ),
    ]
    assert manager.cursors == {ActivityType.FORK: "cursor:0002"}
    assert not manager.has_next_page


def test_activity_query_forks_no_cursor() -> None:
    q = (
        "query($repo_id: ID!) {\n"
        "    node(id: $repo_id) {\n"
        "        ... on Repository {\n"
        "            forks(\n"
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
    manager = ActivityQuery(repo=repo, types=[ActivityType.FORK], cursors={})
    assert manager.has_next_page
    assert manager.make_query() == (q, {"repo_id": "id:viewer/repo"})
