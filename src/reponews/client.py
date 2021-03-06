from __future__ import annotations
import json
import platform
from typing import Any, Dict, Iterator, List, Optional, Tuple
import requests
from . import __url__, __version__
from .qmanager import (
    ActivityQuery,
    OwnersReposQuery,
    QueryManager,
    SingleRepoQuery,
    ViewersReposQuery,
)
from .types import ActivityType, Affiliation, CursorDict, RepoActivity, Repository
from .util import NotFoundError, T, log

PAGE_SIZE = 50

USER_AGENT = "reponews/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)


class Client:
    def __init__(self, api_url: str, token: str) -> None:
        self.api_url = api_url
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"bearer {token}"
        self.s.headers["User-Agent"] = USER_AGENT
        # <https://github.blog/2021-11-16-graphql-global-id-migration-update/>
        self.s.headers["X-Github-Next-Global-ID"] = "1"

    def __enter__(self) -> Client:
        return self

    def __exit__(self, _exc_type: Any, _exc_value: Any, _exc_tb: Any) -> None:
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

    def do_managed_query(self, manager: QueryManager[T]) -> Iterator[T]:
        while manager.has_next_page:
            q, variables = manager.make_query()
            data = self.query(q, variables)
            yield from manager.parse_response(data)

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
        manager = ViewersReposQuery(affiliations=affiliations)
        for repo in self.do_managed_query(manager):
            log.info("Found repository %s", repo)
            yield repo

    def get_owner_repos(self, owner: str) -> Iterator[Repository]:
        log.info("Fetching repositories belonging to %s", owner)
        manager = OwnersReposQuery(owner=owner)
        for repo in self.do_managed_query(manager):
            log.info("Found repository %s", repo)
            yield repo

    def get_repo(self, owner: str, name: str) -> Repository:
        log.info("Fetching info for repo %s/%s", owner, name)
        manager = SingleRepoQuery(owner=owner, name=name)
        return next(self.do_managed_query(manager))

    def get_new_repo_activity(
        self, repo: Repository, types: List[ActivityType], cursors: CursorDict
    ) -> Tuple[List[RepoActivity], CursorDict]:
        log.info(
            "Fetching new %s activity for %s", ", ".join(it.value for it in types), repo
        )
        manager = ActivityQuery(repo=repo, types=types, cursors=cursors)
        events: List[RepoActivity] = []
        for ev in self.do_managed_query(manager):
            log.info("Found activity on %s: %s", repo, ev)
            events.append(ev)
        return (events, manager.cursors)


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
