from __future__ import annotations
import json
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
import requests
from . import log
from .types import Affiliation, IssueoidType, NewIssueoidEvent, Repository

PAGE_SIZE = 50


class Client:
    def __init__(self, api_url: str, token: str) -> None:
        self.api_url = api_url
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"bearer {token}"

    def close(self) -> None:
        self.s.close()

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Any:
        r = self.s.post(
            self.api_url,
            json={"query": query, "variables": variables or {}},
        )
        if not r.ok:
            raise APIException(r)
        data = r.json()
        if data.get("errors"):
            try:
                # TODO: Figure out how to handle multi-errors where some of the
                # errors are NOT_FOUND
                if data["errors"][0]["type"] == "NOT_FOUND":
                    raise NotFoundError(data["errors"][0]["message"])
            except (AttributeError, LookupError, TypeError, ValueError):
                pass
            raise APIException(r)
        return r.json()

    def paginate(
        self, query: str, variables: Dict[str, Any], conn_path: Sequence[str]
    ) -> Tuple[list, Optional[str]]:
        nodes: list = []
        while True:
            data = self.query(query, variables)
            conn = data
            for p in conn_path:
                conn = conn[p]
            nodes.extend(conn["nodes"])
            new_cursor = conn["pageInfo"]["endCursor"]
            assert new_cursor is None or isinstance(new_cursor, str)
            if conn["pageInfo"]["hasNextPage"]:
                variables = {**variables, "cursor": new_cursor}
            else:
                return nodes, new_cursor

    def get_affiliated_repos(
        self, affiliations: List[Affiliation]
    ) -> Iterator[Repository]:
        if not affiliations:
            log.info("No affiliations set; not fetching any affiliated repositories")
            return
        log.info(
            "Fetching repositories with affiliations %s",
            ", ".join(aff.value for aff in affiliations),
        )
        q = """
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
                        nodes {
                            id
                            nameWithOwner
                            owner { login }
                            name
                            url
                            description
                            descriptionHTML
                        }
                        pageInfo {
                            endCursor
                            hasNextPage
                        }
                    }
                }
            }
        """
        variables = {
            "page_size": PAGE_SIZE,
            "affiliations": [aff.value for aff in affiliations],
        }
        for node in self.paginate(q, variables, ("data", "viewer", "repositories"))[0]:
            repo = Repository.from_node(node)
            log.info("Found repository %s", repo.fullname)
            yield repo

    def get_owner_repos(self, owner: str) -> Iterator[Repository]:
        log.info("Fetching repositories belonging to %s", owner)
        q = """
            query($owner: String!, $page_size: Int!, $cursor: String) {
                repositoryOwner(login: $owner) {
                    repositories(
                        orderBy: {field: NAME, direction: ASC},
                        first: $page_size,
                        after: $cursor
                    ) {
                        nodes {
                            id
                            nameWithOwner
                            owner { login }
                            name
                            url
                            description
                            descriptionHTML
                        }
                        pageInfo {
                            endCursor
                            hasNextPage
                        }
                    }
                }
            }
        """
        variables = {"owner": owner, "page_size": PAGE_SIZE}
        for node in self.paginate(
            q, variables, ("data", "repositoryOwner", "repositories")
        )[0]:
            repo = Repository.from_node(node)
            log.info("Found repository %s", repo.fullname)
            yield repo

    def get_repo(self, owner: str, name: str) -> Repository:
        log.info("Fetching info for repo %s/%s", owner, name)
        q = """
            query($owner: String!, $name: String!) {
                repository(owner: $owner, name: $name) {
                    id
                    nameWithOwner
                    owner { login }
                    name
                    url
                    description
                    descriptionHTML
                }
            }
        """
        return Repository.from_node(
            self.query(q, {"owner": owner, "name": name})["data"]["repository"]
        )

    def get_new_issueoid_events(
        self, repo: Repository, it: IssueoidType, cursor: Optional[str]
    ) -> Tuple[List[NewIssueoidEvent], Optional[str]]:
        log.info("Fetching new %s events for %s", it.value, repo.fullname)
        if cursor is None:
            log.debug(
                "No %s cursor set for %s; setting cursor to latest state",
                it.value,
                repo.fullname,
            )
            new_cursor = self.get_latest_issueoid_cursor(repo, it)
            if new_cursor is None:
                log.debug(
                    "No %s events have yet occurred for %s; cursor will remain unset",
                    it.value,
                    repo.fullname,
                )
            return ([], new_cursor)
        q = """
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
        """ % (
            it.api_name,
        )
        variables = {
            "repo_id": repo.id,
            "page_size": PAGE_SIZE,
            "cursor": cursor,
        }
        events: List[NewIssueoidEvent] = []
        nodes, new_cursor = self.paginate(q, variables, ("data", "node", it.api_name))
        for node in nodes:
            ev = NewIssueoidEvent.from_node(type=it, repo=repo, node=node)
            log.info(
                "Found new %s for %s: %r (#%d)",
                it.value,
                repo.fullname,
                ev.title,
                ev.number,
            )
            events.append(ev)
        if new_cursor is None:
            new_cursor = cursor
        return events, new_cursor

    def get_latest_issueoid_cursor(
        self, repo: Repository, it: IssueoidType
    ) -> Optional[str]:
        q = """
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
        """ % (
            it.api_name,
        )
        cursor = self.query(q, {"repo_id": repo.id})["data"]["node"][it.api_name][
            "pageInfo"
        ]["endCursor"]
        assert cursor is None or isinstance(cursor, str)
        return cursor


class APIException(Exception):
    def __init__(self, response: requests.Response):
        self.response = response

    def __str__(self) -> str:
        if self.response.ok:
            msg = "GraphQL API error for URL: {0.url}\n"
        elif 400 <= self.response.status_code < 500:
            msg = "{0.status_code} Client Error: {0.reason} for URL: {0.url}\n"
        elif 500 <= self.response.status_code < 600:
            msg = "{0.status_code} Server Error: {0.reason} for URL: {0.url}\n"
        else:
            msg = "{0.status_code} Unknown Error: {0.reason} for URL: {0.url}\n"
        msg = msg.format(self.response)
        try:
            resp = self.response.json()
        except ValueError:
            msg += self.response.text
        else:
            msg += json.dumps(resp, sort_keys=True, indent=4)
        return msg


class NotFoundError(Exception):
    pass
