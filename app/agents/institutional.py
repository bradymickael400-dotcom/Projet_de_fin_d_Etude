"""Capacités de recherche documentaire séparées par mandat simulé."""

from app.agents.registry import AgentRegistry, AgentResult, AgentSpec
from app.knowledge.rag import search_knowledge
from app.knowledge.sources import source_register, verified_source_paths


AGENT_DEFINITIONS = (
    ("policy_operator", "operator", "Opérateur logistique", "Recherche dans les références autorisées au rôle opérateur."),
    ("policy_customs_port", "customs_port", "Douane et autorité portuaire simulées", "Recherche dans les références douane-port autorisées; ne décide pas au nom d’une administration."),
    ("policy_data_protection", "data_protection", "Protection des données et cybersécurité simulées", "Recherche dans les références de protection des données autorisées; signale les textes nationaux absents."),
    ("policy_adviser", "legal_adviser", "Conseiller juridique neutre simulé", "Recherche dans les sources vérifiées et distingue les comparateurs internationaux du droit national."),
)

APPLICATION_ROLES = frozenset({"superadmin", "owner", "company", "client", "driver", "port_authority"})


def _handler(agent_id, partition, mandate, corpus_root=None):
    def execute(arguments, _identity, _registry):
        query = str(arguments.get("query") or "").strip()
        if not query or len(query) > 1000:
            return AgentResult(agent_id, "invalid", error="query requise (1000 caractères max)")
        paths = verified_source_paths(partition, corpus_root)
        hits = search_knowledge(query, root=corpus_root, allowed_sources=paths, min_overlap=2)
        catalog = {item.get("path"): item for item in source_register(corpus_root) if item.get("path")}
        for hit in hits:
            metadata = catalog.get(hit["source"], {})
            hit.update({
                "title": metadata.get("title"),
                "authority": metadata.get("authority"),
                "jurisdiction": metadata.get("jurisdiction"),
                "official_url": metadata.get("official_url"),
                "verification_status": metadata.get("verification_status"),
                "source_type": metadata.get("source_type"),
                "applicability_to_cameroon": metadata.get("applicability_to_cameroon"),
            })
        status = "success" if hits else "insufficient_evidence"
        return AgentResult(
            agent_id,
            status,
            data={
                "role": partition,
                "mandate": mandate,
                "query": query,
                "passages": hits,
                "limitations": [
                    "Le résultat ne constitue pas un avis juridique.",
                    "Les documents absents ou non vérifiés ne sont pas accessibles à ce rôle.",
                    "Les rôles institutionnels sont simulés et n’engagent aucune administration.",
                ],
            },
            provenance=[{
                "source": hit["source"],
                "line_start": hit["line_start"],
                "line_end": hit["line_end"],
                "score": hit["score"],
                "official_url": hit.get("official_url"),
                "jurisdiction": hit.get("jurisdiction"),
                "verification_status": hit.get("verification_status"),
            } for hit in hits],
        )
    return execute


def register_institutional_agents(registry: AgentRegistry, corpus_root=None) -> None:
    for agent_id, partition, label, description in AGENT_DEFINITIONS:
        registry.register(AgentSpec(
            agent_id=agent_id,
            version="1.0.0",
            mission=f"Rôle de démonstration : {label}.",
            capability=f"policy.search.{partition}",
            description=description,
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            allowed_roles=APPLICATION_ROLES,
            handler=_handler(agent_id, partition, description, corpus_root),
            output_schema={"type": "object", "required": ["role", "passages", "limitations"]},
            tools_or_services=("local verified-source register", "local policy RAG"),
            limitations=("Retrieval is lexical and partitioned by verified sources.", "No national law is considered ingested unless its full text is verified and registered."),
        ))
