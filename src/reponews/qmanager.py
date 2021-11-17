from abc import abstractmethod
from typing import Any, ClassVar, Dict, Generic, List, Optional, Tuple
from pydantic import BaseModel
from .qlobjs import REPO_FIELDS, Object
from .types import ActivityType, Affiliation, CursorDict, RepoActivity, Repository
from .util import BogusEventError, NotFoundError, T, log

PAGE_SIZE = 50


class QueryManager(BaseModel, Generic[T]):
    has_next_page: bool = True

    @abstractmethod
    def make_query(self) -> Tuple[str, Dict[str, Any]]:
        ...

    @abstractmethod
    def parse_response(self, data: Any) -> List[T]:
        ...


class ReposQuery(QueryManager[Repository]):
    PATH: ClassVar[Tuple[str, ...]]
    cursor: Optional[str] = None

    def parse_response(self, data: Any) -> List[Repository]:
        root = data["data"]
        for p in self.PATH:
            root = root[p]
        new_cursor = root["pageInfo"]["endCursor"]
        if new_cursor is not None:
            assert isinstance(new_cursor, str)
            self.cursor = new_cursor
        self.has_next_page = root["pageInfo"]["hasNextPage"]
        return [Repository.from_node(node) for node in root["nodes"]]


class ViewersReposQuery(ReposQuery):
    PATH = ("viewer", "repositories")
    affiliations: List[Affiliation]

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
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


class OwnersReposQuery(ReposQuery):
    PATH = ("repositoryOwner", "repositories")
    owner: str

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
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

    def parse_response(self, data: Any) -> List[Repository]:
        if data["data"]["repositoryOwner"] is None:
            # For some reason, as of 2021-11-01, GitHub handles requests for a
            # nonexistent repositoryOwner by returning `null` instead of
            # responding with a `NOT_FOUND` error like it does for nonexistent
            # users & repositories.
            raise NotFoundError(f"No such repository owner: {self.owner!r}")
        return super().parse_response(data)


class SingleRepoQuery(QueryManager[Repository]):
    owner: str
    name: str

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
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

    def parse_response(self, data: Any) -> List[Repository]:
        self.has_next_page = False
        return [Repository.from_node(data["data"]["repository"])]


class ActivityQuery(QueryManager[RepoActivity]):
    repo: Repository
    types: List[ActivityType]
    cursors: CursorDict

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
        variables: Dict[str, Any] = {"repo_id": self.repo.id}
        variable_defs = {"$repo_id": "ID!"}
        connections: List[Object] = []
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

    def parse_response(self, data: Any) -> List[RepoActivity]:
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
                nodes: List[dict] = next(iter(root.values()), [])
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
