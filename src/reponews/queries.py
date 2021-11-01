from abc import ABC, abstractmethod
from textwrap import dedent, indent
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
)
from pydantic import BaseModel
from . import log
from .types import Affiliation, IssueoidType, NewIssueoidEvent, Repository
from .util import NotFoundError

PAGE_SIZE = 50

T = TypeVar("T")


class QueryManager(ABC, Generic[T]):
    @abstractmethod
    def make_query(self) -> Tuple[str, Dict[str, Any]]:
        ...

    @abstractmethod
    def parse_response(self, data: Any) -> Iterator[T]:
        ...

    @abstractmethod
    def has_next_page(self) -> bool:
        ...

    @abstractmethod
    def get_cursor(self) -> Optional[str]:
        ...


class ReposQuery(QueryManager[Repository], BaseModel):
    PATH: ClassVar[Tuple[str, ...]]
    ROOT: ClassVar[str] = (
        "nodes {\n"
        "    id\n"
        "    nameWithOwner\n"
        "    owner { login }\n"
        "    name\n"
        "    url\n"
        "    description\n"
        "    descriptionHTML\n"
        "}\n"
        "pageInfo {\n"
        "    endCursor\n"
        "    hasNextPage\n"
        "}\n"
    )
    cursor: Optional[str] = None
    hasNextPage: bool = True

    def parse_response(self, data: Any) -> Iterator[Repository]:
        root = data["data"]
        for p in self.PATH:
            root = root[p]
        new_cursor = root["pageInfo"]["endCursor"]
        if new_cursor is not None:
            assert isinstance(new_cursor, str)
            self.cursor = new_cursor
        self.hasNextPage = root["pageInfo"]["hasNextPage"]
        for node in root["nodes"]:
            yield Repository.from_node(node)

    def has_next_page(self) -> bool:
        return self.hasNextPage

    def get_cursor(self) -> Optional[str]:
        return self.cursor


class ViewersReposQuery(ReposQuery):
    PATH = ("viewer", "repositories")
    affiliations: List[Affiliation]

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
        q = dedent(
            """
            query(
                $page_size: Int!,
                $affiliations: [RepositoryAffiliation!],
                $cursor: String
            ) {
                viewer {
                    repositories(
                        ownerAffiliations: $affiliations,
                        orderBy: {field: NAME, direction: ASC},
                        first: $page_size,
                        after: $cursor
                    ) {
        """
            + indent(self.ROOT, " " * 24)
            + """
                    }
                }
            }
            """
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
        q = dedent(
            """
            query($owner: String!, $page_size: Int!, $cursor: String) {
                repositoryOwner(login: $owner) {
                    repositories(
                        orderBy: {field: NAME, direction: ASC},
                        first: $page_size,
                        after: $cursor
                    ) {
        """
            + indent(self.ROOT, " " * 24)
            + """
                    }
                }
            }
            """
        )
        variables = {
            "owner": self.owner,
            "page_size": PAGE_SIZE,
            "cursor": self.cursor,
        }
        return (q, variables)

    def parse_response(self, data: Any) -> Iterator[Repository]:
        if data["data"]["repositoryOwner"] is None:
            # For some reason, as of 2021-11-01, GitHub handles requests for a
            # nonexistent repositoryOwner by returning `null` instead of
            # responding with a `NOT_FOUND` error like it does for nonexistent
            # users & repositories.
            raise NotFoundError(f"No such repository owner: {self.owner!r}")
        return super().parse_response(data)


class NewIssueoidQuery(QueryManager[NewIssueoidEvent], BaseModel):
    repo: Repository
    type: IssueoidType
    cursor: Optional[str]
    hasNextPage: bool = True

    def make_query(self) -> Tuple[str, Dict[str, Any]]:
        variables: Dict[str, Any]
        if self.cursor is None:
            log.debug(
                "No %s cursor set for %s; setting cursor to latest state",
                self.type.value,
                self.repo.fullname,
            )
            q = dedent(
                """
                query($repo_id: ID!) {
                    node(id: $repo_id) {
                        ... on Repository {
                            %s (
                                orderBy: {field: CREATED_AT, direction: ASC},
                                last: 1
                            ) {
                                pageInfo {
                                    endCursor
                                }
                            }
                        }
                    }
                }
                """
                % (self.type.api_name,)
            )
            variables = {"repo_id": self.repo.id}
        else:
            q = dedent(
                """
                query($repo_id: ID!, $page_size: Int!, $cursor: String) {
                    node(id: $repo_id) {
                        ... on Repository {
                            %s (
                                orderBy: {field: CREATED_AT, direction: ASC},
                                first: $page_size,
                                after: $cursor
                            ) {
                                nodes {
                                    author {
                                        login
                                        url
                                        ... on User {
                                            name
                                            isViewer
                                        }
                                    }
                                    createdAt
                                    number
                                    title
                                    url
                                }
                                pageInfo {
                                    endCursor
                                    hasNextPage
                                }
                            }
                        }
                    }
                }
                """
                % (self.type.api_name,)
            )
            variables = {
                "repo_id": self.repo.id,
                "page_size": PAGE_SIZE,
                "cursor": self.cursor,
            }
        return (q, variables)

    def parse_response(self, data: Any) -> Iterator[NewIssueoidEvent]:
        root = data["data"]["node"][self.type.api_name]
        new_cursor = root["pageInfo"]["endCursor"]
        old_cursor = self.cursor
        if new_cursor is not None:
            assert isinstance(new_cursor, str)
            self.cursor = new_cursor
        if old_cursor is None:
            if self.cursor is None:
                log.debug(
                    "No %s events have yet occurred for %s; cursor will remain unset",
                    self.type.value,
                    self.repo.fullname,
                )
            self.hasNextPage = False
        else:
            self.hasNextPage = root["pageInfo"]["hasNextPage"]
            for node in root["nodes"]:
                yield NewIssueoidEvent.from_node(self.type, self.repo, node)

    def has_next_page(self) -> bool:
        return self.hasNextPage

    def get_cursor(self) -> Optional[str]:
        return self.cursor
