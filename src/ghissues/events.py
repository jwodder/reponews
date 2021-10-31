from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from .util import IssueoidType


class Repository(BaseModel):
    id: str
    owner: str
    name: str
    fullname: str
    created: datetime
    url: str

    @property
    def new_event(self) -> NewRepoEvent:
        return NewRepoEvent(
            timestamp=self.created,
            repo_fullname=self.fullname,
            url=self.url,
        )


class Event(BaseModel):
    timestamp: datetime  # Used for sorting
    repo: Repository


class NewIssueoidEvent(Event):
    type: IssueoidType
    repo: Repository
    number: int
    title: str
    author: str
    url: str

    def __str__(self) -> str:
        return (
            f"[{self.repo.fullname}] {self.type.value.upper()} #{self.number}:"
            f" {self.title} (@{self.author})\n<{self.url}>"
        )


class NewRepoEvent(Event):
    url: str

    def __str__(self) -> str:
        return f"Now tracking repository {self.repo.fullname}\n<{self.url}>"


class RepoRemovedEvent(Event):
    def __str__(self) -> str:
        ### TODO: Distinguish between the case when a repository has been
        ### deleted and when the user's config no longer indicates it should be
        ### tracked
        return f"Repository {self.repo.fullname} not found; no longer tracking"
