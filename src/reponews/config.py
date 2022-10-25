from __future__ import annotations
from collections import defaultdict
from email.headerregistry import Address as PyAddress
import json
import os
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union
from ghrepo import GH_REPO_RGX, GH_USER_RGX
from mailbits import parse_address
from pydantic import AnyHttpUrl, BaseModel, Field, parse_obj_as, validator
from pydantic.validators import str_validator
from .types import ActivityType, Affiliation, Repository
from .util import UserError, get_default_state_file, mkalias

if sys.version_info[:2] >= (3, 11):
    from tomllib import load as toml_load
else:
    from tomli import load as toml_load

if sys.version_info[:2] >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator


class Address(BaseModel):
    name: Optional[str]
    address: str

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield str_validator
        yield cls._parse

    @classmethod
    def _parse(cls, value: str) -> Address:
        addr = parse_address(value)
        return cls(name=addr.display_name or None, address=addr.addr_spec)

    def as_py_address(self) -> PyAddress:
        return PyAddress(self.name or "", addr_spec=self.address)


class RepoSpec(BaseModel):
    owner: str
    name: Optional[str]

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield str_validator
        yield cls._parse

    @classmethod
    def _parse(cls, value: str) -> RepoSpec:
        m = re.fullmatch(
            rf"(?P<owner>{GH_USER_RGX})/(?:\*|(?P<name>{GH_REPO_RGX}))", value
        )
        if m:
            return cls(owner=m["owner"], name=m["name"])
        else:
            raise ValueError(f"Invalid repo spec: {value!r}")


class RepoSpecKey(str):
    # Like RepoSpec, but usable as a key in a dict that can be JSONified by
    # pydantic.  (We're not using RepoSpec itself as such a key because we want
    # RepoSpecs to be expanded into dicts when JSONified.)
    owner: str
    name: Optional[str]

    def __init__(self, s: str) -> None:
        owner, name = s.split("/")
        self.owner = owner
        self.name = None if name == "*" else name

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield str_validator
        yield cls._validate
        yield cls

    @classmethod
    def _validate(cls, value: str) -> str:
        if re.fullmatch(
            rf"(?P<owner>{GH_USER_RGX})/(?:\*|(?P<name>{GH_REPO_RGX}))", value
        ):
            return value
        else:
            raise ValueError(f"Invalid repo spec: {value!r}")

    @classmethod
    def parse(cls, s: str) -> RepoSpecKey:
        return parse_obj_as(cls, s)


class BaseConfig(BaseModel):
    class Config:
        alias_generator = mkalias
        allow_population_by_field_name = True
        extra = "forbid"

        # <https://github.com/samuelcolvin/pydantic/issues/1241>
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)


class PartialActivityPrefs(BaseConfig):
    issues: Optional[bool] = None
    pull_requests: Optional[bool] = None
    discussions: Optional[bool] = None
    releases: Optional[bool] = None
    tags: Optional[bool] = None
    released_tags: Optional[bool] = None
    stars: Optional[bool] = None
    forks: Optional[bool] = None
    my_activity: Optional[bool] = None


class ActivityPrefs(PartialActivityPrefs):
    issues: bool = True
    pull_requests: bool = True
    discussions: bool = True
    releases: bool = True
    tags: bool = True
    released_tags: bool = False
    stars: bool = True
    forks: bool = True
    my_activity: bool = False

    def get_activity_types(self) -> List[ActivityType]:
        types: List[ActivityType] = []
        if self.issues:
            types.append(ActivityType.ISSUE)
        if self.pull_requests:
            types.append(ActivityType.PR)
        if self.discussions:
            types.append(ActivityType.DISCUSSION)
        if self.releases:
            types.append(ActivityType.RELEASE)
        if self.tags:
            types.append(ActivityType.TAG)
        if self.stars:
            types.append(ActivityType.STAR)
        if self.forks:
            types.append(ActivityType.FORK)
        return types

    def update(self, prefs: PartialActivityPrefs) -> None:
        pd = dict(prefs)
        for field_name in self.__fields__.keys():
            v = pd[field_name]
            if v is not None:
                assert isinstance(v, bool)
                setattr(self, field_name, v)


class RepoActivityPrefs(PartialActivityPrefs):
    include: bool = True


class ActivityConfig(PartialActivityPrefs):
    affiliated: PartialActivityPrefs = Field(default_factory=PartialActivityPrefs)
    repo: Dict[RepoSpecKey, RepoActivityPrefs] = Field(default_factory=dict)


class ReposConfig(BaseConfig):
    affiliations: List[Affiliation] = Field(default_factory=lambda: list(Affiliation))
    include: List[RepoSpec] = Field(default_factory=list)
    exclude: List[RepoSpec] = Field(default_factory=list)


class RepoInclusions(BaseModel):
    included_owners: Set[str] = Field(default_factory=set)
    excluded_owners: Set[str] = Field(default_factory=set)
    included_repos: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set)
    )
    excluded_repos: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set)
    )

    @classmethod
    def from_repos_config(
        cls, repos_config: ReposConfig, preffed_repos: List[RepoSpecKey]
    ) -> RepoInclusions:
        rinc = cls()
        for rs in repos_config.include + [
            RepoSpec(owner=r.owner, name=r.name) for r in preffed_repos
        ]:
            if rs.name is None:
                rinc.included_owners.add(rs.owner)
            else:
                rinc.included_repos[rs.owner].add(rs.name)
        for rs in repos_config.exclude:
            if rs.name is None:
                rinc.excluded_owners.add(rs.owner)
                rinc.included_owners.discard(rs.owner)
                rinc.included_repos.pop(rs.owner, None)
            else:
                rinc.excluded_repos[rs.owner].add(rs.name)
                rinc.included_repos[rs.owner].discard(rs.name)
        return rinc

    def get_included_repo_owners(self) -> List[str]:
        return sorted(self.included_owners)

    def get_included_repos(self) -> List[Tuple[str, str]]:
        return [
            (owner, n)
            for owner, names in sorted(self.included_repos.items())
            if owner not in self.included_owners
            for n in sorted(names)
        ]

    def is_repo_excluded(self, repo: Repository) -> bool:
        return (
            repo.owner.login in self.excluded_owners
            or repo.name in self.excluded_repos[repo.owner.login]
        )


class Configuration(BaseConfig):
    recipient: Optional[Address] = None
    sender: Optional[Address] = None
    subject: str = "[reponews] New activity on your GitHub repositories"
    auth_token: Optional[str] = None
    auth_token_file: Optional[Path] = None
    # The default is implemented as a factory in order to make it easy to test
    # with a fake $HOME:
    state_file: Path = Field(default_factory=get_default_state_file)
    api_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "https://api.github.com/graphql")
    activity: ActivityConfig = Field(default_factory=ActivityConfig)
    repos: ReposConfig = Field(default_factory=ReposConfig)

    @validator("auth_token_file", "state_file")
    def _expand_path(cls, v: Optional[Path]) -> Optional[Path]:  # noqa: B902, U100
        return v.expanduser() if v is not None else v

    @classmethod
    def from_toml_file(cls, filepath: Union[str, Path]) -> Configuration:
        with open(filepath, "rb") as fp:
            data = toml_load(fp).get("reponews", {})
        basedir = Path(filepath).parent
        config = cls.parse_obj(data)
        if config.auth_token_file is not None:
            config.auth_token_file = basedir / config.auth_token_file
        config.state_file = basedir / config.state_file
        return config

    def get_auth_token(self) -> str:
        if self.auth_token is not None:
            return self.auth_token
        elif self.auth_token_file is not None:
            return self.auth_token_file.read_text().strip()
        elif os.environ.get("GITHUB_TOKEN"):
            return os.environ["GITHUB_TOKEN"]
        elif os.environ.get("GH_TOKEN"):
            return os.environ["GH_TOKEN"]
        else:
            raise UserError(
                "GitHub OAuth token not set.  Specify in config file or via"
                " GITHUB_TOKEN or GH_TOKEN environment variable."
            )

    def get_repo_activity_prefs(
        self, repo: Repository, is_affiliated: bool
    ) -> ActivityPrefs:
        prefs = ActivityPrefs()
        prefs.update(self.activity)
        if is_affiliated:
            prefs.update(self.activity.affiliated)
        for spec in [f"{repo.owner}/*", str(repo)]:
            try:
                p = self.activity.repo[RepoSpecKey.parse(spec)]
            except KeyError:
                pass
            else:
                prefs.update(p)
        return prefs

    @cached_property
    def inclusions(self) -> RepoInclusions:
        return RepoInclusions.from_repos_config(
            self.repos, [r for r, pref in self.activity.repo.items() if pref.include]
        )

    def get_included_repo_owners(self) -> List[str]:
        return self.inclusions.get_included_repo_owners()

    def get_included_repos(self) -> List[Tuple[str, str]]:
        return self.inclusions.get_included_repos()

    def is_repo_excluded(self, repo: Repository) -> bool:
        return self.inclusions.is_repo_excluded(repo)

    def for_json(self) -> Any:
        return json.loads(self.json())
