from __future__ import annotations
from textwrap import indent
from typing import Dict, List, Union

INDENT = " " * 4
SINGLE_LINE_CUTOFF = 40


class Object:
    def __init__(
        self, name: str, args: Dict[str, str], *fields: Union[str, Object]
    ) -> None:
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


ACTOR_FIELDS: List[Union[str, Object]] = [
    "login",
    "url",
    Object("... on User", {}, "name", "isViewer"),
]

OWNER_FIELDS: List[Union[str, Object]] = [
    "login",
    "url",
    Object("... on User", {}, "name", "isViewer"),
    Object("... on Organization", {}, "name"),
]

REPO_FIELDS: List[Union[str, Object]] = [
    "id",
    "nameWithOwner",
    Object("owner", {}, *OWNER_FIELDS),
    "name",
    "url",
    "description",
    "descriptionHTML",
]

ISSUE_CONNECTION = mkissueoid_connection("issues")
PR_CONNECTION = mkissueoid_connection("pullRequests")
DISCUSSION_CONNECTION = mkissueoid_connection("discussions")
