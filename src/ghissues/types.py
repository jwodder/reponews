from collections import namedtuple
from dataclasses import dataclass
from typing import ClassVar

# The `timestamp` attributes of the following classes are used for sorting:


@dataclass
class NewIssueoidEvent:
    type_name: ClassVar[str]
    timestamp: str
    repo_fullname: str
    number: int
    title: str
    author: str
    url: str

    def __str__(self):
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


class NewRepoEvent(namedtuple("NewRepoEvent", "timestamp repo_fullname url")):
    def __str__(self):
        return f"Now tracking repository {self.repo_fullname}\n" f"<{self.url}>"


class RepoRemovedEvent(namedtuple("RepoRemovedEvent", "timestamp repo_fullname")):
    def __str__(self):
        return f"Repository {self.repo_fullname} not found; no longer tracking"
