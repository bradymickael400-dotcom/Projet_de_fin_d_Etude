"""Registre et contrat commun des capacités spécialisées ARGOS."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Callable
from uuid import uuid4


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "data": self.data,
            "provenance": self.provenance,
            "error": self.error,
        }


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    version: str
    mission: str
    capability: str
    description: str
    parameters: dict[str, Any]
    allowed_roles: frozenset[str]
    handler: Callable[[dict[str, Any], dict[str, Any], "AgentRegistry"], AgentResult]
    output_schema: dict[str, Any] = field(default_factory=dict)
    tools_or_services: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class AgentRegistry:
    """Registre unique utilisé par l'orchestrateur et la passerelle LLM."""

    def __init__(self):
        self._specs: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        if spec.agent_id in self._specs:
            raise ValueError(f"Agent déjà enregistré: {spec.agent_id}")
        self._specs[spec.agent_id] = spec

    def discover(self) -> list[dict[str, Any]]:
        return [
            {
                "agent_id": spec.agent_id,
                "version": spec.version,
                "mission": spec.mission,
                "capability": spec.capability,
                "description": spec.description,
                "parameters": spec.parameters,
                "output_schema": spec.output_schema,
                "tools_or_services": list(spec.tools_or_services),
                "limitations": list(spec.limitations),
                "allowed_roles": sorted(spec.allowed_roles),
                "availability": "registered",
            }
            for spec in self._specs.values()
        ]

    def execute(
        self, agent_id: str, arguments: dict[str, Any], identity: dict[str, Any],
        correlation_id: str,
    ) -> AgentResult:
        spec = self._specs.get(agent_id)
        if spec is None:
            return AgentResult(agent_id, "unavailable", error="Capacité inconnue")
        if identity.get("role") not in spec.allowed_roles:
            return AgentResult(agent_id, "denied", error="Permission refusée")
        if not isinstance(arguments, dict):
            return AgentResult(agent_id, "invalid", error="Arguments JSON objet requis")
        properties = spec.parameters.get("properties") or {}
        required = spec.parameters.get("required") or []
        if set(arguments) - set(properties):
            return AgentResult(agent_id, "invalid", error="Champ d'argument non autorisé")
        if any(key not in arguments for key in required):
            return AgentResult(agent_id, "invalid", error="Argument obligatoire manquant")
        for key, value in arguments.items():
            expected = properties[key].get("type")
            if expected == "string" and not isinstance(value, str):
                return AgentResult(agent_id, "invalid", error=f"Type invalide: {key}")
            if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                return AgentResult(agent_id, "invalid", error=f"Type invalide: {key}")
        try:
            result = spec.handler(arguments, identity, self)
            if not isinstance(result, AgentResult):
                raise TypeError("Le gestionnaire doit retourner AgentResult")
            return result
        except Exception:
            # Les détails internes restent dans les journaux serveur; ils ne sont
            # pas transmis au LLM ni à l'utilisateur.
            logger.exception("Échec capacité agent_id=%s correlation_id=%s", agent_id, correlation_id)
            return AgentResult(
                agent_id, "error", error="Erreur interne de capacité",
                provenance=[{"correlation_id": correlation_id}],
            )

    def get(self, agent_id: str) -> AgentSpec | None:
        return self._specs.get(agent_id)


def build_registry() -> AgentRegistry:
    from app.agents.specialists import register_specialists

    registry = AgentRegistry()
    register_specialists(registry)
    return registry
