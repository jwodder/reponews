from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from email.headerregistry import Address as PyAddress
from functools import cached_property
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
from ghrepo import GH_REPO_RGX, GH_USER_RGX
import ghtoken  # Module import for mocking purposes
from mailbits import parse_address
from pydantic import AnyHttpUrl, BaseModel, Field, GetCoreSchemaHandler, field_validator
from pydantic.functional_serializers import PlainSerializer
from pydantic_core import CoreSchema, core_schema
from .types import ActivityType, Affiliation, Repository
from .util import UserError, default_api_url, get_default_state_file, mkalias

if sys.version_info[:2] >= (3, 11):
    from tomllib import load as toml_load
else:
    from tomli import load as toml_load

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


@dataclass
class Address:
    name: Optional[str]
    address: str

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._parse,
            handler(str),
            serialization=core_schema.plain_serializer_function_ser_schema(asdict),
        )

    @classmethod
    def _parse(cls, value: str) -> Address:
        addr = parse_address(value)
        return cls(name=addr.display_name or None, address=addr.addr_spec)

    def as_py_address(self) -> PyAddress:
        return PyAddress(self.name or "", addr_spec=self.address)


@dataclass(frozen=True)
class RepoSpec:
    owner: str
    name: Optional[str]

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.parse,
            handler(str),
            serialization=core_schema.plain_serializer_function_ser_schema(asdict),
        )

    @classmethod
    def parse(cls, value: str) -> RepoSpec:
        m = re.fullmatch(
            rf"(?P<owner>{GH_USER_RGX})/(?:\*|(?P<name>{GH_REPO_RGX}))", value
        )
        if m:
            return cls(owner=m["owner"], name=m["name"])
        else:
            raise ValueError(f"Invalid repo spec: {value!r}")

    def __str__(self) -> str:
        return f"{self.owner}/{self.name or '*'}"


class BaseConfig(BaseModel):
    model_config = {
        "alias_generator": mkalias,
        "populate_by_name": True,
        "extra": "forbid",
    }


class PartialActivityPrefs(BaseConfig):
    issues: Optional[bool] = None
    pull_requests: Optional[bool] = None
    discussions: Optional[bool] = None
    releases: Optional[bool] = None
    prereleases: Optional[bool] = None
    drafts: Optional[bool] = None
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
    prereleases: bool = True
    drafts: bool = True
    tags: bool = True
    released_tags: bool = False
    stars: bool = True
    forks: bool = True
    my_activity: bool = False

    def get_activity_types(self) -> list[ActivityType]:
        types: list[ActivityType] = []
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
        for field_name in ActivityPrefs.model_fields:
            if (v := pd[field_name]) is not None:
                assert isinstance(v, bool)
                setattr(self, field_name, v)


class RepoActivityPrefs(PartialActivityPrefs):
    include: bool = True


class ActivityConfig(PartialActivityPrefs):
    affiliated: PartialActivityPrefs = Field(default_factory=PartialActivityPrefs)
    repo: Dict[
        Annotated[RepoSpec, PlainSerializer(lambda s: str(s))], RepoActivityPrefs
    ] = Field(default_factory=dict)


class ReposConfig(BaseConfig):
    affiliations: List[Affiliation] = Field(default_factory=lambda: list(Affiliation))
    include: List[RepoSpec] = Field(default_factory=list)
    exclude: List[RepoSpec] = Field(default_factory=list)


@dataclass
class RepoInclusions:
    included_owners: set[str] = field(default_factory=set)
    excluded_owners: set[str] = field(default_factory=set)
    included_repos: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    excluded_repos: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    @classmethod
    def from_repos_config(
        cls, repos_config: ReposConfig, preffed_repos: list[RepoSpec]
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

    def get_included_repo_owners(self) -> list[str]:
        return sorted(self.included_owners)

    def get_included_repos(self) -> list[tuple[str, str]]:
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
    api_url: AnyHttpUrl = Field(default_factory=default_api_url)
    activity: ActivityConfig = Field(default_factory=ActivityConfig)
    repos: ReposConfig = Field(default_factory=ReposConfig)

    @field_validator("auth_token_file", "state_file")
    @classmethod
    def _expand_path(cls, v: Optional[Path]) -> Optional[Path]:
        return v.expanduser() if v is not None else v

    @classmethod
    def from_toml_file(cls, filepath: str | Path) -> Configuration:
        with open(filepath, "rb") as fp:
            data = toml_load(fp).get("reponews", {})
        basedir = Path(filepath).parent
        config = cls.model_validate(data)
        if config.auth_token_file is not None:
            config.auth_token_file = basedir / config.auth_token_file
        config.state_file = basedir / config.state_file
        return config

    def get_auth_token(self) -> str:
        if self.auth_token is not None:
            return self.auth_token
        elif self.auth_token_file is not None:
            return self.auth_token_file.read_text(encoding="utf-8").strip()
        else:
            try:
                return ghtoken.get_ghtoken(dotenv=False)
            except ghtoken.GHTokenNotFound:
                raise UserError(
                    "GitHub access token not found.  Set via config file,"
                    " GH_TOKEN, GITHUB_TOKEN, gh, hub, or hub.oauthtoken."
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
                p = self.activity.repo[RepoSpec.parse(spec)]
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

    def get_included_repo_owners(self) -> list[str]:
        return self.inclusions.get_included_repo_owners()

    def get_included_repos(self) -> list[tuple[str, str]]:
        return self.inclusions.get_included_repos()

    def is_repo_excluded(self, repo: Repository) -> bool:
        return self.inclusions.is_repo_excluded(repo)
