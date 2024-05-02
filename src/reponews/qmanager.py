from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Generic
from .qlobjs import REPO_FIELDS, Object
from .types import ActivityType, Affiliation, CursorDict, RepoActivity, Repository
from .util import BogusEventError, NotFoundError, T, log

PAGE_SIZE = 50


@dataclass
class QueryManager(Generic[T]):
    has_next_page: bool = field(init=False, default=True)

    @abstractmethod
    def make_query(self) -> tuple[str, dict[str, Any]]: ...

    @abstractmethod
    def parse_response(self, data: Any) -> list[T]: ...


@dataclass
class ReposQuery(QueryManager[Repository]):
    PATH: ClassVar[tuple[str, ...]]
    cursor: str | None = field(init=False, default=None)

    def parse_response(self, data: Any) -> list[Repository]:
        root = data["data"]
        for p in self.PATH:
            root = root[p]
        new_cursor = root["pageInfo"]["endCursor"]
        if new_cursor is not None:
            assert isinstance(new_cursor, str)
            self.cursor = new_cursor
        self.has_next_page = root["pageInfo"]["hasNextPage"]
        return [Repository.from_node(node) for node in root["nodes"]]


@dataclass
class ViewersReposQuery(ReposQuery):
    PATH: ClassVar[tuple[str, ...]] = ("viewer", "repositories")
    affiliations: list[Affiliation]

    def make_query(self) -> tuple[str, dict[str, Any]]:
        q = str(
            Object(
                "query",
                {
                    "$page_size": "Int!",
                    "$affiliations": "[RepositoryAffiliation!]",
                    "$cursor": "String",
                },
                Object(
                    "viewer",
                    {},
                    Object(
                        "repositories",
                        {
                            "ownerAffiliations": "$affiliations",
                            "orderBy": "{field: NAME, direction: ASC}",
                            "first": "$page_size",
                            "after": "$cursor",
                        },
                        Object("nodes", {}, *REPO_FIELDS),
                        Object("pageInfo", {}, "endCursor", "hasNextPage"),
                    ),
                ),
            )
        )
        variables = {
            "affiliations": [aff.value for aff in self.affiliations],
            "page_size": PAGE_SIZE,
            "cursor": self.cursor,
        }
        return (q, variables)


@dataclass
class OwnersReposQuery(ReposQuery):
    PATH: ClassVar[tuple[str, ...]] = ("repositoryOwner", "repositories")
    owner: str

    def make_query(self) -> tuple[str, dict[str, Any]]:
        q = str(
            Object(
                "query",
                {"$owner": "String!", "$page_size": "Int!", "$cursor": "String"},
                Object(
                    "repositoryOwner",
                    {"login": "$owner"},
                    Object(
                        "repositories",
                        {
                            "orderBy": "{field: NAME, direction: ASC}",
                            "first": "$page_size",
                            "after": "$cursor",
                        },
                        Object("nodes", {}, *REPO_FIELDS),
                        Object("pageInfo", {}, "endCursor", "hasNextPage"),
                    ),
                ),
            )
        )
        variables = {
            "owner": self.owner,
            "page_size": PAGE_SIZE,
            "cursor": self.cursor,
        }
        return (q, variables)

    def parse_response(self, data: Any) -> list[Repository]:
        if data["data"]["repositoryOwner"] is None:
            # For some reason, as of 2021-11-01, GitHub handles requests for a
            # nonexistent repositoryOwner by returning `null` instead of
            # responding with a `NOT_FOUND` error like it does for nonexistent
            # users & repositories.
            raise NotFoundError(f"No such repository owner: {self.owner!r}")
        return super().parse_response(data)


@dataclass
class SingleRepoQuery(QueryManager[Repository]):
    owner: str
    name: str

    def make_query(self) -> tuple[str, dict[str, Any]]:
        q = str(
            Object(
                "query",
                {"$owner": "String!", "$name": "String!"},
                Object(
                    "repository", {"owner": "$owner", "name": "$name"}, *REPO_FIELDS
                ),
            )
        )
        return (q, {"owner": self.owner, "name": self.name})

    def parse_response(self, data: Any) -> list[Repository]:
        self.has_next_page = False
        return [Repository.from_node(data["data"]["repository"])]


@dataclass
class ActivityQuery(QueryManager[RepoActivity]):
    repo: Repository
    types: list[ActivityType]
    cursors: CursorDict

    def make_query(self) -> tuple[str, dict[str, Any]]:
        variables: dict[str, Any] = {"repo_id": self.repo.id}
        variable_defs = {"$repo_id": "ID!"}
        connections: list[Object] = []
        for it in self.types:
            if it in self.cursors:
                connections.append(it.event_cls.CONNECTION)
                variable_defs["$page_size"] = "Int!"
                variables["page_size"] = PAGE_SIZE
                variable_defs[f"${it.api_name}_cursor"] = "String"
                variables[f"{it.api_name}_cursor"] = self.cursors[it]
            else:
                connections.append(it.event_cls.LAST_CONNECTION)
        query = Object(
            "query",
            variable_defs,
            Object(
                "node",
                {"id": "$repo_id"},
                Object("... on Repository", {}, *connections),
            ),
        )
        return (str(query), variables)

    def parse_response(self, data: Any) -> list[RepoActivity]:
        events = []
        self.has_next_page = False
        for it in self.types:
            root = data["data"]["node"][it.api_name]
            pageInfo = root.pop("pageInfo")
            new_cursor = pageInfo["endCursor"]
            if it in self.cursors:
                if pageInfo["hasNextPage"]:
                    self.has_next_page = True
                assert len(root) <= 1
                nodes: list[dict] = next(iter(root.values()), [])
                for node in nodes:
                    try:
                        events.append(it.event_cls.from_node(self.repo, node))
                    except BogusEventError as e:
                        log.debug("Discarding bogus event: %s", e)
                if new_cursor is not None:
                    assert isinstance(new_cursor, str)
                    self.cursors[it] = new_cursor
            else:
                self.cursors[it] = new_cursor
        return events
