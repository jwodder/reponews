from __future__ import annotations
from collections.abc import Iterator
import json
from time import sleep
from types import TracebackType
from typing import Any, Optional
import requests
from .qmanager import (
    ActivityQuery,
    OwnersReposQuery,
    QueryManager,
    SingleRepoQuery,
    ViewersReposQuery,
)
from .types import ActivityType, Affiliation, CursorDict, RepoActivity, Repository
from .util import HTTP_USER_AGENT, NotFoundError, T, log

PAGE_SIZE = 50

MAX_RETRIES = 5
RETRY_STATUSES = (500, 502, 503, 504)
BACKOFF_FACTOR = 1.25
MAX_BACKOFF = 120


class Client:
    def __init__(self, api_url: str, token: str) -> None:
        self.api_url = api_url
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"bearer {token}"
        self.s.headers["User-Agent"] = HTTP_USER_AGENT
        # <https://github.blog/2021-11-16-graphql-global-id-migration-update/>
        self.s.headers["X-Github-Next-Global-ID"] = "1"

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        self.s.close()

    def query(self, query: str, variables: Optional[dict[str, Any]] = None) -> Any:
        sleeps = retry_sleeps()
        while True:
            try:
                r = self.s.post(
                    self.api_url,
                    json={"query": query, "variables": variables or {}},
                )
            except ValueError:
                # The errors that requests raises when the user supplies bad
                # parameters all inherit ValueError
                raise
            except requests.RequestException as e:
                if (delay := next(sleeps, None)) is not None:
                    log.warning(
                        "GraphQL request failed: %s: %s; waiting %f seconds and"
                        " retrying",
                        type(e).__name__,
                        str(e),
                        delay,
                    )
                    sleep(delay)
                    continue
                else:
                    raise
            if r.status_code in RETRY_STATUSES:
                if (delay := next(sleeps, None)) is not None:
                    log.warning(
                        "GraphQL request returned %d; waiting %f seconds and retrying",
                        r.status_code,
                        delay,
                    )
                    sleep(delay)
                    continue
                else:
                    log.error(
                        "GraphQL request returned %d; out of retries", r.status_code
                    )
                    raise APIException(r)
            elif not r.ok:
                raise APIException(r)
            else:
                break
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
        return data

    def do_managed_query(self, manager: QueryManager[T]) -> Iterator[T]:
        while manager.has_next_page:
            q, variables = manager.make_query()
            data = self.query(q, variables)
            yield from manager.parse_response(data)

    def get_affiliated_repos(
        self, affiliations: list[Affiliation]
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
        self, repo: Repository, types: list[ActivityType], cursors: CursorDict
    ) -> tuple[list[RepoActivity], CursorDict]:
        log.info(
            "Fetching new %s activity for %s", ", ".join(it.value for it in types), repo
        )
        manager = ActivityQuery(repo=repo, types=types, cursors=cursors)
        events: list[RepoActivity] = []
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


def retry_sleeps() -> Iterator[float]:
    for i in range(1, MAX_RETRIES + 1):
        yield min(BACKOFF_FACTOR * 2**i, MAX_BACKOFF)
