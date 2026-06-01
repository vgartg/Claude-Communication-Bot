"""Agent profiles loaded from a YAML file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    system: str
    workdir: str | None = None


class AgentRegistry:
    def __init__(self, agents: list[Agent], default_id: str):
        self._agents = {a.id: a for a in agents}
        if default_id not in self._agents:
            raise ValueError(f"Default agent '{default_id}' is not defined")
        self.default_id = default_id

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    @property
    def default(self) -> Agent:
        return self._agents[self.default_id]

    def all(self) -> list[Agent]:
        return list(self._agents.values())


def load_registry(path: Path) -> AgentRegistry:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    agents = [
        Agent(
            id=item["id"],
            name=item.get("name", item["id"]),
            system=(item.get("system") or "").strip(),
            workdir=(item.get("workdir") or None),
        )
        for item in data["agents"]
    ]
    if not agents:
        raise ValueError("No agents defined")
    default_id = data.get("default_agent", agents[0].id)
    return AgentRegistry(agents, default_id)
