from __future__ import annotations
from collections.abc import Iterator
import json
from typing import Any
import ghreq
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


class Client(ghreq.Client):
    def __init__(self, api_url: str, token: str) -> None:
        super().__init__(graphql_url=api_url, token=token, user_agent=HTTP_USER_AGENT)

    def query(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        data = self.graphql(query=query, variables=variables)
        if err := data.get("errors"):
            try:
                # TODO: Figure out how to handle multi-errors where some of the
                # errors are NOT_FOUND
                if err[0]["type"] == "NOT_FOUND":
                    raise NotFoundError(err[0]["message"])
            except (AttributeError, LookupError, TypeError, ValueError):
                pass
            raise GraphQLError(err)
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


class GraphQLError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(errors)

    def __str__(self) -> str:
        try:
            lines = []
            if len(self.errors) == 1:
                lines.append("GraphQL API error:")
            else:
                lines.append("GraphQL API errors:")
            first = True
            for e in self.errors:
                if first:
                    first = False
                else:
                    lines.append("---")
                for k, v in e.items():
                    k = k.title()
                    if isinstance(v, str | int | bool):
                        lines.append(f"{k}: {v}")
                    else:
                        lines.append(k + ": " + json.dumps(v, sort_keys=True))
            return "\n".join(lines)
        except Exception:
            return "MALFORMED GRAPHQL ERROR:\n" + json.dumps(
                self.errors, sort_keys=True, indent=True
            )
