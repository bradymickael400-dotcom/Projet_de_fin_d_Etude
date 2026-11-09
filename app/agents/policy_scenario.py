"""Scénarios institutionnels synthétiques, cloisonnés et traçables pour la démo."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agents.registry import build_registry


AGENTS = {
    "A1_OPERATOR": {
        "role": "operator",
        "mandate": "Rôle simulé d’opérateur logistique; décrit les faits ARGOS et les vérifications opérationnelles.",
    },
    "A2_CUSTOMS_PORT": {
        "role": "customs_port",
        "mandate": "Rôle simulé douane-port; examine les éléments déclaratifs et de transfert qui lui sont communiqués.",
    },
    "A3_DATA_PROTECTION": {
        "role": "data_protection",
        "mandate": "Rôle simulé de revue données/cybersécurité; examine les catégories de données et le partage proposé.",
    },
    "A4_POLICY_ADVISER": {
        "role": "legal_adviser",
        "mandate": "Rôle simulé de conseil neutre; rapproche les analyses et distingue comparateur international et règle nationale.",
    },
}


SCENARIO = {
    "scenario_id": "silent_container_v1",
    "title": "Le conteneur silencieux — scénario synthétique",
    "jurisdiction": "Cameroon; cross-border transit is out of scope",
    "origin": "Douala",
    "destination": "yard intérieur au Cameroun",
    "steps": [
        {"step": "T0", "event_id": "EV-T0", "facts": {
            "operator": ["Fret pharmaceutique fictif déclaré; boîtier ARGOS installé."],
            "customs_port": ["Déclaration fictive enregistrée; scellé douanier indiqué intact."],
            "data_protection": [],
        }},
        {"step": "T1", "event_id": "EV-T1", "facts": {
            "operator": ["Sortie du port enregistrée; dernier état du scellé indiqué intact."],
            "customs_port": ["Heure fictive de sortie du terminal enregistrée."],
            "data_protection": [],
        }},
        {"step": "T2", "event_id": "EV-T2", "facts": {
            "operator": ["Ouverture de porte, hausse de température, GPS imprécis puis perte de signal; données SIMULATED."],
            "customs_port": [],
            "data_protection": [],
        }},
        {"step": "T3", "event_id": "EV-T3", "facts": {
            "operator": ["L’opérateur demande s’il peut transmettre l’historique de localisation du conducteur et du véhicule à la douane et à l’assureur."],
            "customs_port": ["Une demande d’information est signalée; aucune donnée personnelle n’est transmise dans cette simulation."],
            "data_protection": ["Catégories demandées: localisation du conducteur et du véhicule; destinataires proposés: douane et assureur; finalité, fondement invoqué et durée de conservation non fournis."],
        }},
        {"step": "T4", "event_id": "EV-T4", "facts": {
            "operator": ["Une lecture tardive simulée de la mémoire du boîtier situe l’événement dans le yard intérieur."],
            "customs_port": ["Le point de contrôle intérieur enregistre un scellé brisé; chaîne de garde et heure exacte restent à confirmer."],
            "data_protection": [],
        }},
        {"step": "T5", "event_id": "EV-T5", "facts": {
            "operator": ["Le délai de conservation fictif du produit pharmaceutique approche; une inspection conjointe est proposée."],
            "customs_port": ["Une inspection humaine est proposée; aucune décision de saisie ou de responsabilité n’est simulée."],
            "data_protection": ["La demande de localisation demeure en attente de validation de la finalité, du fondement, des destinataires et de la durée au regard des extraits nationaux disponibles."],
        }},
    ],
}


def _assess(agent_id: str, step: dict, trace_id: str, root: Path, registry, identity, provider=None) -> dict:
    agent = AGENTS[agent_id]
    partition = agent["role"]
    facts = step["facts"].get(partition.replace("customs_port", "customs_port"), [])
    if partition == "legal_adviser":
        facts = [
            f"{result['agent_id']}: {result['assessment']}"
            for result in step.get("independent_assessments", [])
        ]
    queries = {
        "operator": "container tracking route temperature sensor event",
        "customs_port": "customs transit risk management declaration seal",
        "data_protection": "données personnelles localisation transfert finalité conservation consentement",
        "legal_adviser": "customs transit risk management appeal",
    }
    query = (
        "données personnelles localisation transfert finalité conservation consentement"
        if partition == "legal_adviser" and step["step"] == "T3"
        else queries[partition]
    )
    policy_agent_id = {
        "operator": "policy_operator",
        "customs_port": "policy_customs_port",
        "data_protection": "policy_data_protection",
        "legal_adviser": "policy_adviser",
    }[partition]
    retrieval = registry.execute(policy_agent_id, {"query": query}, identity, trace_id) if facts or agent_id == "A4_POLICY_ADVISER" else None
    hits = ((retrieval.data or {}).get("passages") or []) if retrieval else []
    primary_national_verified = any(
        hit.get("source", "").startswith("cameroon_") for hit in hits
    )
    uncertainty = "high" if not hits else "medium"
    if not facts and agent_id != "A4_POLICY_ADVISER":
        assessment = "Aucun fait de cet événement n’a été transmis à ce rôle à cette étape."
        recommendation = "Ne pas compléter les faits à partir d’hypothèses; attendre une information autorisée."
    elif agent_id == "A1_OPERATOR":
        assessment = "Faits opérationnels observés: " + " ".join(facts)
        recommendation = "Conserver les mesures horodatées et vérifier capteur, point GPS, état du scellé et chaîne de garde avec les acteurs concernés."
    elif agent_id == "A2_CUSTOMS_PORT":
        assessment = "Éléments douane-port communiqués: " + " ".join(facts)
        recommendation = "Rapprocher les déclarations et journaux de contrôle; faire confirmer la chaîne de garde par les agents habilités."
    elif agent_id == "A3_DATA_PROTECTION":
        assessment = "Revue du partage demandé: " + (" ".join(facts) if facts else "aucune demande personnelle nouvelle communiquée.")
        recommendation = (
            "Mettre le transfert en attente: la finalité, la base, le périmètre, les destinataires et la durée ne sont pas établis dans les informations reçues."
            if facts else "Ne partager aucune donnée personnelle sans demande précise et revue humaine documentée."
        )
    else:
        assessment = "Les avis reçus sont des analyses de rôles simulés; ils ne déterminent ni droit applicable ni responsabilité."
        recommendation = "Distinguer faits, comparateurs internationaux et droit camerounais; demander une vérification juridique nationale avant toute conclusion."

    if agent_id == "A4_POLICY_ADVISER":
        policy_gap = (
            "national_rule_not_verified_in_local_corpus"
            if not primary_national_verified
            else "sector_responsibility_or_applicability_requires_human_review"
        )
    elif agent_id == "A3_DATA_PROTECTION" and step["step"] == "T3":
        policy_gap = "sharing_basis_and_implementation_require_human_review"
    else:
        policy_gap = None
    result = {
        "trace_id": trace_id,
        "step": step["step"],
        "agent_id": agent_id,
        "status": "success" if hits else "insufficient_evidence",
        "retrieval_agent_id": policy_agent_id,
        "agent_version": "1.0.0-simulated",
        "origin": "SIMULATED",
        "input_event_ids": [step["event_id"]],
        "visible_facts": facts,
        "retrieved_passages": hits,
        "assessment": assessment,
        "recommended_action": recommendation,
        "responsible_actor": "Opérateur humain habilité; rôle exact à confirmer dans les textes applicables.",
        "unknowns": [
            ("Les extraits camerounais sont partiels; texte complet, règles d’application et applicabilité aux faits à valider." if primary_national_verified else "Aucun extrait camerounais pertinent n’a été retrouvé dans le corpus autorisé."),
            "Horodatages et chaîne de garde du scénario sont fictifs.",
        ],
        "uncertainty": uncertainty,
        "policy_gap_flag": policy_gap,
        "reasoning_summary": "Résumé d’audit fondé sur les seuls faits visibles et passages retournés; aucune chaîne de pensée privée n’est enregistrée.",
        "human_review_status": "PENDING",
        "national_source_verified": primary_national_verified,
    }
    result["llm_status"] = "not_requested"
    if provider is not None:
        try:
            generated = provider.assess_policy_agent(result)
            result.update({
                "assessment": generated["assessment"],
                "recommended_action": generated["recommendation"],
                "unknowns": generated["unknowns"],
                "uncertainty": generated["uncertainty"],
                "policy_gap_flag": generated["policy_gap_flag"],
                "reasoning_summary": generated["reasoning_summary"],
                "llm_status": "generated",
            })
        except Exception:
            # L'échec du fournisseur ne fait pas échouer le parcours déterministe.
            result["llm_status"] = "fallback_after_provider_error"
    return result


def run_policy_scenario(scenario_id: str = "silent_container_v1", root=None, provider=None, identity=None) -> dict:
    """Rejoue un scénario de démonstration sans LLM ni données réelles."""
    if scenario_id != SCENARIO["scenario_id"]:
        raise ValueError("Scénario inconnu")
    corpus_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2] / "knowledge_base" / "documents"
    registry = build_registry(include_institutional=True, knowledge_root=corpus_root)
    actor_identity = identity or {"role": "superadmin", "user_id": "local-policy-scenario"}
    trace_id = str(uuid4())
    timeline = []
    history = []
    for source_step in SCENARIO["steps"]:
        step = dict(source_step)
        assessments = []
        for agent_id in ("A1_OPERATOR", "A2_CUSTOMS_PORT", "A3_DATA_PROTECTION"):
            assessments.append(_assess(agent_id, step, trace_id, corpus_root, registry, actor_identity, provider))
        step["independent_assessments"] = assessments
        adviser = _assess("A4_POLICY_ADVISER", step, trace_id, corpus_root, registry, actor_identity, provider)
        adviser["visible_facts"] = [
            item["assessment"] for item in assessments
        ]
        timeline.append({
            "step": step["step"],
            "event_id": step["event_id"],
            "origin": "SIMULATED",
            "independent_assessments": assessments,
            "adviser_reconciliation": adviser,
            "data_transfer": {
                "status": "BLOCKED_PENDING_HUMAN_REVIEW" if step["step"] == "T3" else "NO_PERSONAL_DATA_TRANSFER",
                "reason": "Scénario de démonstration: une personne doit valider la finalité, le fondement, les destinataires, la durée et les garanties avant tout partage.",
            },
            "human_gate": "PENDING",
        })
        history.extend(assessments + [adviser])
    return {
        "trace_id": trace_id,
        "scenario_id": SCENARIO["scenario_id"],
        "title": SCENARIO["title"],
        "jurisdiction": SCENARIO["jurisdiction"],
        "origin": SCENARIO["origin"],
        "destination": SCENARIO["destination"],
        "synthetic": True,
        "provider_mode": "gemini_assisted" if provider is not None else "deterministic_fallback",
        "agents": AGENTS,
        "timeline": timeline,
        "agents_consulted": list(AGENTS),
        "sources": sorted({hit["source"] for item in history for hit in item["retrieved_passages"]}),
        "limitations": [
            "Toutes les informations opérationnelles du scénario sont synthétiques.",
            "La recherche est lexicale et ne constitue ni un avis juridique ni une preuve d’applicabilité.",
            "Seuls des extraits sélectionnés de la loi camerounaise n° 2024/017 sont indexés; la loi complète et ses textes d’application ne le sont pas.",
            "Les rôles A1–A4 sont simulés et ne représentent aucune administration réelle.",
        ],
    }
