from __future__ import annotations
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from operator import attrgetter
from pathlib import Path
from types import TracebackType
from typing import Dict
from eletter import compose
from pydantic import BaseModel, Field, TypeAdapter
from . import client
from .config import Configuration
from .types import (
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
from .util import MAIL_USER_AGENT, NotFoundError, UserError, log


class RepoState(BaseModel):
    repo: Repository
    cursors: CursorDict = Field(default_factory=dict)


state_adapter = TypeAdapter(Dict[str, RepoState])


@dataclass
class State:
    path: Path
    old_state: dict[str, RepoState]
    new_state: dict[str, RepoState] = field(init=False, default_factory=dict)
    state_events: list[Event] = field(init=False, default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> State:
        try:
            with path.open(encoding="utf-8") as fp:
                state = state_adapter.validate_json(fp.read())
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
        self.path.write_bytes(state_adapter.dump_json(self.new_state))


@dataclass
class RepoNews:
    config: Configuration
    state: State
    client: client.Client = field(init=False)

    def __post_init__(self) -> None:
        self.client = client.Client(
            api_url=str(self.config.api_url),
            token=self.config.get_auth_token(),
        )

    def __enter__(self) -> RepoNews:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.client.__exit__(exc_type, exc_val, exc_tb)

    @classmethod
    def from_config(cls, config: Configuration) -> RepoNews:
        return cls(config=config, state=State.from_file(config.state_file))

    @classmethod
    def from_config_file(cls, path: Path) -> RepoNews:
        return cls.from_config(Configuration.from_toml_file(path))

    def get_new_activity(self) -> list[Event]:
        events: list[Event] = []
        for repo, is_affiliated in self.get_repositories():
            activity = self.config.get_repo_activity_prefs(repo, is_affiliated)
            types = activity.get_activity_types()
            if not types:
                log.info("No tracked activity configured for %s", repo)
                continue
            new_events, cursors = self.client.get_new_repo_activity(
                repo, types, self.state.get_cursors(repo)
            )
            events2: list[RepoActivity]
            if not activity.my_activity:
                events2 = []
                for ev in new_events:
                    if ev.is_mine:
                        log.info("<%s> was created by current user; not reporting", ev)
                    else:
                        events2.append(ev)
                new_events = events2
            if activity.releases and (not activity.prereleases or not activity.drafts):
                events2 = []
                for ev in new_events:
                    if isinstance(ev, NewReleaseEvent):
                        if not activity.prereleases and ev.isPrerelease:
                            log.info("<%s> is prerelease; not reporting", ev)
                        elif not activity.drafts and ev.isDraft:
                            log.info("<%s> is draft release; not reporting", ev)
                        else:
                            events2.append(ev)
                    else:
                        events2.append(ev)
                new_events = events2
            if activity.releases and activity.tags and not activity.released_tags:
                events2 = []
                release_tags = set()
                tag_events: list[NewTagEvent] = []
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

    def get_repositories(self) -> Iterator[tuple[Repository, bool]]:
        seen: set[str] = set()
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

    def _get_repositories(self) -> Iterator[tuple[Repository, bool]]:
        for repo in self.client.get_affiliated_repos(self.config.repos.affiliations):
            yield (repo, True)
        for owner in self.config.get_included_repo_owners():
            try:
                for repo in self.client.get_owner_repos(owner):
                    yield (repo, False)
            except NotFoundError:
                log.warning("User %s does not exist!", owner)
        for owner, name in self.config.get_included_repos():
            try:
                yield (self.client.get_repo(owner, name), False)
            except NotFoundError:
                log.warning("Repository %s/%s does not exist!", owner, name)

    def dump_repo_prefs(self) -> dict[str, dict]:
        prefs: dict[str, dict] = {}
        for repo, is_affiliated in self.get_repositories():
            activity = self.config.get_repo_activity_prefs(repo, is_affiliated)
            prefs[str(repo)] = activity.model_dump(mode="json")
        return prefs

    def compose_email_body(self, events: list[Event]) -> str:
        return "\n\n".join(ev.render() for ev in events)

    def compose_email(self, events: list[Event]) -> EmailMessage:
        if self.config.recipient is None:
            raise UserError(
                "reponews.recipient must be set when constructing an e-mail"
            )
        return compose(
            subject=self.config.subject,
            from_=(
                self.config.sender.as_py_address()
                if self.config.sender is not None
                else None
            ),
            to=[self.config.recipient.as_py_address()],
            text=self.compose_email_body(events),
            headers={"User-Agent": MAIL_USER_AGENT},
        )

    def save_state(self) -> None:
        log.info("Saving state ...")
        self.state.save()
