from __future__ import annotations
from textwrap import indent

INDENT = " " * 4
SINGLE_LINE_CUTOFF = 40


class Object:
    def __init__(self, name: str, args: dict[str, str], *fields: str | Object) -> None:
        self.name = name
        self.args = args
        self.fields = fields

    def __str__(self) -> str:
        s = self.name
        if self.args:
            argslist = [f"{k}: {v}" for k, v in self.args.items()]
            if len(", ".join(argslist)) > SINGLE_LINE_CUTOFF:
                s += "(\n" + ",\n".join(INDENT + a for a in argslist) + "\n)"
            else:
                s += "(" + ", ".join(argslist) + ")"
        s += " {\n"
        for f in self.fields:
            s += indent(str(f).rstrip(), INDENT) + "\n"
        s += "}\n"
        return s


def mkissueoid_connection(name: str) -> Object:
    return Object(
        name,
        {
            "orderBy": "{field: CREATED_AT, direction: ASC}",
            "first": "$page_size",
            "after": f"${name}_cursor",
        },
        Object(
            "nodes",
            {},
            Object("author", {}, *ACTOR_FIELDS),
            "createdAt",
            "number",
            "title",
            "url",
        ),
        Object("pageInfo", {}, "endCursor", "hasNextPage"),
    )


def mklastconn(name: str) -> Object:
    return Object(
        name,
        {
            "orderBy": "{field: CREATED_AT, direction: ASC}",
            "last": "1",
        },
        Object("pageInfo", {}, "endCursor"),
    )


ACTOR_FIELDS: list[str | Object] = [
    "login",
    "url",
    Object("... on User", {}, "name", "isViewer"),
]

OWNER_FIELDS: list[str | Object] = [
    "login",
    "url",
    Object("... on User", {}, "name", "isViewer"),
    Object("... on Organization", {}, "name"),
]

USER_FIELDS = ["login", "url", "name", "isViewer"]

REPO_FIELDS: list[str | Object] = [
    "id",
    "nameWithOwner",
    Object("owner", {}, *OWNER_FIELDS),
    "name",
    "url",
    "description",
    "descriptionHTML",
]

ISSUE_CONNECTION = mkissueoid_connection("issues")

ISSUE_LAST_CONNECTION = mklastconn("issues")

PR_CONNECTION = mkissueoid_connection("pullRequests")

PR_LAST_CONNECTION = mklastconn("pullRequests")

DISCUSSION_CONNECTION = mkissueoid_connection("discussions")

DISCUSSION_LAST_CONNECTION = mklastconn("discussions")

RELEASE_CONNECTION = Object(
    "releases",
    {
        "orderBy": "{field: CREATED_AT, direction: ASC}",
        "first": "$page_size",
        "after": "$releases_cursor",
    },
    Object(
        "nodes",
        {},
        "name",
        "tagName",
        Object("author", {}, *USER_FIELDS),
        "createdAt",
        "description",
        "descriptionHTML",
        "isPrerelease",
        "isDraft",
        "url",
    ),
    Object("pageInfo", {}, "endCursor", "hasNextPage"),
)

RELEASE_LAST_CONNECTION = mklastconn("releases")

TAG_CONNECTION = Object(
    "tags: refs",
    {
        "refPrefix": '"refs/tags/"',
        "orderBy": "{field: TAG_COMMIT_DATE, direction: ASC}",
        "first": "$page_size",
        "after": "$tags_cursor",
    },
    Object(
        "nodes",
        {},
        "name",
        Object(
            "target",
            {},
            "__typename",
            Object(
                "... on Tag",
                {},
                Object(
                    "tagger",
                    {},
                    "date",
                    Object("user", {}, *USER_FIELDS),
                ),
            ),
            Object(
                "... on Commit",
                {},
                "committedDate",
                Object("author", {}, Object("user", {}, *USER_FIELDS)),
            ),
        ),
    ),
    Object("pageInfo", {}, "endCursor", "hasNextPage"),
)

TAG_LAST_CONNECTION = Object(
    "tags: refs",
    {
        "refPrefix": '"refs/tags/"',
        "orderBy": "{field: TAG_COMMIT_DATE, direction: ASC}",
        "last": "1",
    },
    Object("pageInfo", {}, "endCursor"),
)

STAR_CONNECTION = Object(
    "stargazers",
    {
        "orderBy": "{field: STARRED_AT, direction: ASC}",
        "first": "$page_size",
        "after": "$stargazers_cursor",
    },
    Object("edges", {}, "starredAt", Object("user: node", {}, *USER_FIELDS)),
    Object("pageInfo", {}, "endCursor", "hasNextPage"),
)

STAR_LAST_CONNECTION = Object(
    "stargazers",
    {
        "orderBy": "{field: STARRED_AT, direction: ASC}",
        "last": "1",
    },
    Object("pageInfo", {}, "endCursor"),
)

FORK_CONNECTION = Object(
    "forks",
    {
        "orderBy": "{field: CREATED_AT, direction: ASC}",
        "first": "$page_size",
        "after": "$forks_cursor",
    },
    Object("nodes", {}, "createdAt", *REPO_FIELDS),
    Object("pageInfo", {}, "endCursor", "hasNextPage"),
)

FORK_LAST_CONNECTION = mklastconn("forks")
