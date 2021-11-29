from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
import json
from operator import attrgetter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple
from eletter import compose
from pydantic import BaseModel, Field
from . import client
from .config import Configuration
from .types import (
    ActivityType,
    CursorDict,
    Event,
    NewReleaseEvent,
    NewTagEvent,
    RepoActivity,
    RepoRenamedEvent,
    Repository,
    RepoTrackedEvent,
    RepoUntrackedEvent,
)
from .util import NotFoundError, UserError, log


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
            log.info("State file not found; treating as empty")
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
            log.info("Now tracking %s", repo)
            self.state_events.append(
                RepoTrackedEvent(
                    timestamp=datetime.now().astimezone(),
                    repo=repo,
                )
            )
        else:
            if old.repo.nameWithOwner != repo.nameWithOwner:
                log.info("Repository renamed: %s → %s", old.repo, repo)
                self.state_events.append(
                    RepoRenamedEvent(
                        timestamp=datetime.now().astimezone(),
                        repo=repo,
                        old_repo=old.repo,
                    )
                )
        self.new_state[repo.id] = RepoState(repo=repo, cursors=cursors)

    def get_state_events(self) -> Iterator[Event]:
        yield from self.state_events
        now = datetime.now().astimezone()
        for repo_state in self.old_state.values():
            log.info(
                "Did not encounter or fetch activity for %s; no longer tracking",
                repo_state.repo,
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
    client: client.Client = field(init=False)

    def __post_init__(self) -> None:
        self.client = client.Client(
            api_url=self.config.api_url,
            token=self.config.get_auth_token(),
        )

    def __enter__(self) -> RepoNews:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        self.client.__exit__(exc_type, exc_value, exc_tb)

    @classmethod
    def from_config(cls, config: Configuration) -> RepoNews:
        return cls(config=config, state=State.from_file(config.state_file))

    @classmethod
    def from_config_file(cls, path: Path) -> RepoNews:
        return cls.from_config(Configuration.from_toml_file(path))

    def get_new_activity(self) -> List[Event]:
        events: List[Event] = []
        for repo, is_affiliated in self.get_repositories():
            activity = self.config.get_repo_activity_prefs(repo, is_affiliated)
            types = activity.get_activity_types()
            if not types:
                log.info("No tracked activity configured for %s", repo)
                continue
            new_events, cursors = self.client.get_new_repo_activity(
                repo, types, self.state.get_cursors(repo)
            )
            events2: List[RepoActivity]
            if not activity.my_activity:
                events2 = []
                for ev in new_events:
                    if ev.is_mine:
                        log.info("<%s> was created by current user; not reporting", ev)
                    else:
                        events2.append(ev)
                new_events = events2
            if (
                ActivityType.RELEASE in types
                and ActivityType.TAG in types
                and not activity.released_tags
            ):
                events2 = []
                release_tags = set()
                tag_events: List[NewTagEvent] = []
                for ev in new_events:
                    if isinstance(ev, NewTagEvent):
                        tag_events.append(ev)
                    else:
                        if isinstance(ev, NewReleaseEvent):
                            release_tags.add(ev.tagName)
                        events2.append(ev)
                for ev in tag_events:
                    if ev.name in release_tags:
                        log.info(
                            "Tag %s also present as a release; not reporting", ev.name
                        )
                    else:
                        events2.append(ev)
                new_events = events2
            events.extend(new_events)
            self.state.set_cursors(repo, cursors)
        events.extend(self.state.get_state_events())
        events.sort(key=attrgetter("timestamp"))
        return events

    def get_repositories(self) -> Iterator[Tuple[Repository, bool]]:
        seen: Set[str] = set()
        for repo, is_affiliated in self._get_repositories():
            if self.config.is_repo_excluded(repo):
                log.info("Repo %s is excluded by config; skipping", repo)
            elif repo.id in seen:
                log.info(
                    "Repo %s fetched more than once; not getting events again", repo
                )
            else:
                seen.add(repo.id)
                yield (repo, is_affiliated)

    def _get_repositories(self) -> Iterator[Tuple[Repository, bool]]:
        for repo in self.client.get_affiliated_repos(self.config.repos.affiliations):
            yield (repo, True)
        for owner in self.config.get_included_repo_owners():
            try:
                for repo in self.client.get_owner_repos(owner):
                    yield (repo, False)
            except NotFoundError:
                log.warning("User %s does not exist!", owner)
        for (owner, name) in self.config.get_included_repos():
            try:
                yield (self.client.get_repo(owner, name), False)
            except NotFoundError:
                log.warning("Repository %s/%s does not exist!", owner, name)

    def dump_repo_prefs(self) -> Dict[str, dict]:
        prefs: Dict[str, dict] = {}
        for repo, is_affiliated in self.get_repositories():
            activity = self.config.get_repo_activity_prefs(repo, is_affiliated)
            prefs[str(repo)] = activity.dict()
        return prefs

    def compose_email_body(self, events: List[Event]) -> str:
        return "\n\n".join(ev.render() for ev in events)

    def compose_email(self, events: List[Event]) -> EmailMessage:
        if self.config.recipient is None:
            raise UserError(
                "reponews.recipient must be set when constructing an e-mail"
            )
        return compose(
            subject=self.config.subject,
            from_=self.config.sender.as_py_address()
            if self.config.sender is not None
            else None,
            to=[self.config.recipient.as_py_address()],
            text=self.compose_email_body(events),
        )

    def save_state(self) -> None:
        log.info("Saving state ...")
        self.state.save()
