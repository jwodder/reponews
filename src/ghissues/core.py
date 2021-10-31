from __future__ import annotations
from datetime import datetime
from email.message import EmailMessage
import json
from operator import attrgetter
from pathlib import Path
from typing import Dict, Iterator, List, Optional
from eletter import compose
from pydantic import BaseModel, Field
from .client import Client
from .config import Configuration
from .types import Event, IssueoidType, RepoRemovedEvent, Repository


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

    @classmethod
    def from_file(cls, path: Path) -> State:
        try:
            with path.open() as fp:
                state = json.load(fp)
        except FileNotFoundError:
            state = {}
        return cls(path=path, old_state=state)

    def get_repo_state(self, repo: Repository) -> Optional[RepoState]:
        return self.old_state.get(repo.id)

    def set_repo_state(self, repo: Repository, state: RepoState) -> None:
        ### TODO: Make the registration of a new ID here be what causes a
        ### NewRepoEvent
        self.old_state.pop(repo.id, None)
        state.fullname = repo.fullname
        self.new_state[repo.id] = state

    def get_removal_events(self) -> Iterator[RepoRemovedEvent]:
        now = datetime.now().astimezone()
        for repo_state in self.old_state.values():
            yield RepoRemovedEvent(
                timestamp=now,
                repo_fullname=repo_state.fullname,
            )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({k: v.dict() for k, v in self.new_state.items()})
        )


class GHIssues(BaseModel):
    config: Configuration
    state: State

    @classmethod
    def from_config(cls, config: Configuration) -> GHIssues:
        return cls(config=config, state=State.from_file(config.state_file))

    @classmethod
    def from_config_file(cls, path: Path) -> GHIssues:
        return cls.from_config(Configuration.from_toml_file(path))

    def get_new_events(self) -> List[Event]:
        events: List[Event] = []
        with Client(
            api_url=self.config.api_url,
            token=self.config.get_github_token(),
        ) as gh:
            user = gh.get_user()
            for repo in gh.get_user_repos(
                user, affiliations=self.config.repos.affiliations
            ):
                repo_state = self.state.get_repo_state(repo)
                if repo_state is None:
                    repo_state = RepoState(fullname=repo.fullname)
                    events.append(repo.new_event)
                for it in self.config.active_issueoid_types():
                    cursor = repo_state.get_cursor(it)
                    new_events, new_cursor = gh.get_new_issueoid_events(
                        repo, it, cursor
                    )
                    repo_state.set_cursor(it, new_cursor)
                    if not self.config.activity.my_activity:
                        new_events = [ev for ev in new_events if ev.author != user]
                    events.extend(new_events)
                self.state.set_repo_state(repo, repo_state)
            ### TODO: Honor "include" and "exclude"
        events.extend(self.state.get_removal_events())
        events.sort(key=attrgetter("timestamp"))
        return events

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
        self.state.save()
