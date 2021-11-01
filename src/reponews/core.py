from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
import json
from operator import attrgetter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set
from eletter import compose
from pydantic import BaseModel, Field
from . import log
from .client import Client, NotFoundError
from .config import Configuration
from .types import (
    Event,
    IssueoidType,
    NewIssueoidEvent,
    RepoRenamedEvent,
    Repository,
    RepoTrackedEvent,
    RepoUntrackedEvent,
)

CursorDict = Dict[IssueoidType, Optional[str]]


class RepoState(BaseModel):
    repo: Repository
    cursors: CursorDict = Field(default_factory=dict)

    def for_json(self) -> Any:
        return {
            "repo": self.repo.dict(),
            "cursors": {k.value: v for k, v in self.cursors.items()},
        }


class State(BaseModel):
    path: Path
    old_state: Dict[str, RepoState]
    new_state: Dict[str, RepoState] = Field(default_factory=dict)
    state_events: List[Event] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> State:
        try:
            with path.open() as fp:
                state = json.load(fp)
        except FileNotFoundError:
            state = {}
        return cls(path=path, old_state=state)

    def get_cursors(self, repo: Repository) -> CursorDict:
        try:
            return self.old_state[repo.id].cursors
        except KeyError:
            return {}

    def set_cursors(self, repo: Repository, cursors: CursorDict) -> None:
        try:
            old = self.old_state.pop(repo.id)
        except KeyError:
            log.info("Now tracking %s", repo.fullname)
            self.state_events.append(
                RepoTrackedEvent(
                    timestamp=datetime.now().astimezone(),
                    repo=repo,
                )
            )
        else:
            if old.repo.fullname != repo.fullname:
                log.info(
                    "Repository renamed: %s → %s", old.repo.fullname, repo.fullname
                )
                self.state_events.append(
                    RepoRenamedEvent(
                        timestamp=datetime.now().astimezone(),
                        repo=repo,
                        old_fullname=old.repo.fullname,
                    )
                )
        self.new_state[repo.id] = RepoState(repo=repo, cursors=cursors)

    def get_state_events(self) -> Iterator[Event]:
        yield from self.state_events
        now = datetime.now().astimezone()
        for repo_state in self.old_state.values():
            log.info(
                "Did not encounter or fetch activity for %s; no longer tracking",
                repo_state.repo.fullname,
            )
            yield RepoUntrackedEvent(timestamp=now, repo=repo_state.repo)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({k: v.for_json() for k, v in self.new_state.items()})
        )


@dataclass
class RepoNews:
    config: Configuration
    state: State
    client: Client = field(init=False)

    def __post_init__(self) -> None:
        self.client = Client(
            api_url=self.config.api_url,
            token=self.config.get_auth_token(),
        )

    def __enter__(self) -> RepoNews:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.client.close()

    @classmethod
    def from_config(cls, config: Configuration) -> RepoNews:
        return cls(config=config, state=State.from_file(config.state_file))

    @classmethod
    def from_config_file(cls, path: Path) -> RepoNews:
        return cls.from_config(Configuration.from_toml_file(path))

    def get_new_events(self) -> List[Event]:
        events: List[Event] = []
        for repo in self.get_repositories():
            cursors = self.state.get_cursors(repo)
            for it in self.config.active_issueoid_types():
                new_events, cursors[it] = self.client.get_new_issueoid_events(
                    repo, it, cursors.get(it)
                )
                if not self.config.activity.my_activity:
                    events2: List[NewIssueoidEvent] = []
                    for ev in new_events:
                        if ev.author.is_me:
                            log.info(
                                "%s %s #%d was created by current user;"
                                " not reporting",
                                ev.repo.fullname,
                                ev.type.value,
                                ev.number,
                            )
                        else:
                            events2.append(ev)
                    new_events = events2
                events.extend(new_events)
            self.state.set_cursors(repo, cursors)
        events.extend(self.state.get_state_events())
        events.sort(key=attrgetter("timestamp"))
        return events

    def get_repositories(self) -> Iterator[Repository]:
        seen: Set[str] = set()
        for repo in self._get_repositories():
            if self.config.is_repo_excluded(repo):
                log.info("Repo %s is excluded by config; skipping", repo.fullname)
            elif repo.id in seen:
                log.info(
                    "Repo %s fetched more than once; not getting events again",
                    repo.fullname,
                )
            else:
                seen.add(repo.id)
                yield repo

    def _get_repositories(self) -> Iterator[Repository]:
        yield from self.client.get_affiliated_repos(self.config.repos.affiliations)
        for owner in self.config.get_included_repo_owners():
            try:
                yield from self.client.get_user_repos(owner)
            except NotFoundError:
                log.warning("User %s does not exist!", owner)
        for (owner, name) in self.config.get_included_repos():
            try:
                yield self.client.get_repo(owner, name)
            except NotFoundError:
                log.warning("Repo %s/%s does not exist!", owner, name)

    def compose_email(self, events: List[Event]) -> EmailMessage:
        return compose(
            subject=self.config.subject,
            from_=self.config.sender.as_py_address()
            if self.config.sender is not None
            else None,
            to=[self.config.recipient.as_py_address()],
            text="\n\n".join(map(str, events)),
        )

    def save_state(self) -> None:
        log.info("Saving state ...")
        self.state.save()