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


class RepoState(BaseModel):
    fullname: str
    issues: Optional[str] = None
    prs: Optional[str] = None
    discussions: Optional[str] = None

    ### TODO: Give this a __getitem__/__setitem__ interface instead of these
    ### methods?
    def get_cursor(self, it: IssueoidType) -> Optional[str]:
        if it is IssueoidType.ISSUE:
            return self.issues
        elif it is IssueoidType.PR:
            return self.prs
        elif it is IssueoidType.DISCUSSION:
            return self.discussions
        else:
            raise AssertionError(f"Unhandled IssueoidType: {it!r}")  # pragma: no cover

    def set_cursor(self, it: IssueoidType, cursor: Optional[str]) -> None:
        if it is IssueoidType.ISSUE:
            self.issues = cursor
        elif it is IssueoidType.PR:
            self.prs = cursor
        elif it is IssueoidType.DISCUSSION:
            self.discussions = cursor
        else:
            raise AssertionError(f"Unhandled IssueoidType: {it!r}")  # pragma: no cover


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

    def get_repo_state(self, repo: Repository) -> RepoState:
        try:
            state = self.old_state.pop(repo.id)
        except KeyError:
            log.info("Now tracking %s", repo.fullname)
            state = RepoState(fullname=repo.fullname)
            self.state_events.append(
                RepoTrackedEvent(
                    timestamp=datetime.now().astimezone(),
                    repo=repo,
                )
            )
        else:
            if state.fullname != repo.fullname:
                log.info("Repository renamed: %s → %s", state.fullname, repo.fullname)
                self.state_events.append(
                    RepoRenamedEvent(
                        timestamp=datetime.now().astimezone(),
                        repo=repo,
                        old_fullname=state.fullname,
                    )
                )
                state.fullname = repo.fullname
        self.new_state[repo.id] = state
        return state

    def get_state_events(self) -> Iterator[Event]:
        yield from self.state_events
        now = datetime.now().astimezone()
        for repo_state in self.old_state.values():
            log.info(
                "Did not encounter or fetch activity for %s; no longer tracking",
                repo_state.fullname,
            )
            yield RepoUntrackedEvent(
                timestamp=now,
                repo_fullname=repo_state.fullname,
            )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({k: v.dict() for k, v in self.new_state.items()})
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
            repo_state = self.state.get_repo_state(repo)
            for it in self.config.active_issueoid_types():
                cursor = repo_state.get_cursor(it)
                new_events, new_cursor = self.client.get_new_issueoid_events(
                    repo, it, cursor
                )
                repo_state.set_cursor(it, new_cursor)
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
                log.warning("User %s does not exist on GitHub!", owner)
        for (owner, name) in self.config.get_included_repos():
            try:
                yield self.client.get_repo(owner, name)
            except NotFoundError:
                log.warning("Repo %s/%s does not exist on GitHub!", owner, name)

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
