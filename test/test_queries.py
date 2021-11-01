from reponews.queries import PAGE_SIZE, ViewersReposQuery
from reponews.types import Affiliation, Repository


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
        "                owner { login }\n"
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
    assert manager.has_next_page()
    assert manager.make_query() == (
        q,
        {
            "page_size": PAGE_SIZE,
            "affiliations": ["OWNER", "ORGANIZATION_MEMBER"],
            "cursor": None,
        },
    )
    repos = list(
        manager.parse_response(
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
    assert manager.get_cursor() == "cursor:0001"
    assert manager.has_next_page()
    assert manager.make_query() == (
        q,
        {
            "page_size": PAGE_SIZE,
            "affiliations": ["OWNER", "ORGANIZATION_MEMBER"],
            "cursor": "cursor:0001",
        },
    )
    repos = list(
        manager.parse_response(
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
    assert manager.get_cursor() == "cursor:0002"
    assert not manager.has_next_page()
