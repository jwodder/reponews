from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Event:
    timestamp: str  # Used for sorting
    repo_fullname: str


@dataclass
class NewIssueoidEvent(Event):
    type_name: ClassVar[str]
    repo_fullname: str
    number: int
    title: str
    author: str
    url: str

    def __str__(self) -> str:
        return (
            f"[{self.repo_fullname}] {self.type_name} #{self.number}:"
            f" {self.title} (@{self.author})\n<{self.url}>"
        )


class NewIssueEvent(NewIssueoidEvent):
    type_name = "ISSUE"


class NewPREvent(NewIssueoidEvent):
    type_name = "PR"


class NewDiscussEvent(NewIssueoidEvent):
    type_name = "DISCUSSION"


@dataclass
class NewRepoEvent(Event):
    url: str

    def __str__(self) -> str:
        return f"Now tracking repository {self.repo_fullname}\n<{self.url}>"


class RepoRemovedEvent(Event):
    def __str__(self) -> str:
        return f"Repository {self.repo_fullname} not found; no longer tracking"
