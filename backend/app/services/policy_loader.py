import json
from functools import lru_cache
from pathlib import Path

from app.config import Settings, get_settings
from app.models.policy import PolicyTerms


class PolicyNotFoundError(Exception):
    """Raised when the requested policy_id is not in the loaded configuration."""


class MemberNotFoundError(Exception):
    """Raised when a member_id is not in the policy roster."""


class PolicyLoader:
    def __init__(self, policy_path: Path) -> None:
        self._policy_path = policy_path
        self._policy: PolicyTerms | None = None

    def load(self) -> PolicyTerms:
        if self._policy is None:
            raw = json.loads(self._policy_path.read_text(encoding="utf-8"))
            self._policy = PolicyTerms.model_validate(raw)
        return self._policy

    def get_policy(self, policy_id: str) -> PolicyTerms:
        policy = self.load()
        if policy.policy_id != policy_id:
            raise PolicyNotFoundError(f"Policy not found: {policy_id}")
        return policy

    def get_member(self, policy_id: str, member_id: str):
        policy = self.get_policy(policy_id)
        member = policy.get_member(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member {member_id} not found under policy {policy_id}")
        return member

    def reload(self) -> PolicyTerms:
        self._policy = None
        return self.load()


@lru_cache
def get_policy_loader() -> PolicyLoader:
    settings = get_settings()
    return PolicyLoader(settings.policy_terms_path)


def create_policy_loader(settings: Settings | None = None) -> PolicyLoader:
    """Factory for tests — bypasses the cached singleton."""
    cfg = settings or get_settings()
    return PolicyLoader(cfg.policy_terms_path)
