# ARGOS Transit Agents — English submission source

This is the editable source for [ARGOS_AI_for_Good_Final_EN.docx](ARGOS_AI_for_Good_Final_EN.docx) and [ARGOS_AI_for_Good_Final_EN.pdf](ARGOS_AI_for_Good_Final_EN.pdf). The PDF is the five-page submission version. Team/contact details and public repository access still need confirmation.

## Evidence boundary

The central submission claim is a prototype policy-coordination demonstration, not an operational customs system. `silent_container_v1` contains synthetic cargo, people and events. Four role agents are simulated; a deterministic coordinator releases six stages and holds the T3 location-sharing request pending human review. The saved deterministic trace records event IDs, role assessments, retrieved source passages, uncertainty, and review status. It does not make legal decisions or represent real administrations.

The local retrieval control set reports 12/12 expected source-presence/absence outcomes. This does not establish legal answer accuracy or comprehensive retrieval quality. The knowledge base contains a bounded summary of selected WTO Trade Facilitation Agreement provisions and visually checked excerpts of Cameroon Law No. 2024/017, together with selected summaries/references on rail, maritime, road and customs instruments. A source register records provenance and verification status; those labels are not independent legal validation. The full personal-data law, implementing texts and independent legal review remain outstanding.

The separate logistic regression artifact uses 301 synthetic samples from five scenarios. Its leave-one-scenario-out mean precision of 100% and recall of 55.29% are measured only against synthetic labels. The model is not loaded by operational alerts. These figures must not be presented as real-world performance.

## Official references checked 7 November 2026

- The ITU hackathon page calls for a technical report of no more than five pages, a GitHub repository and a knowledge base; it lists a 10 November 2026 submission deadline and gives published evaluation criteria. [Official hackathon page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)
- [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en) is an in-force architectural framework for machine learning in future networks including IMT-2020. The report maps ARGOS components to it; it does not claim certification.
- [ITU AI Ready framework report](https://www.itu.int/epublications/publication/ai-ready-analysis-towards-a-standardized-readiness-framework) provides readiness dimensions and domain metrics. ARGOS has not calculated a readiness score.
- Cameroon accepted the WTO Trade Facilitation Agreement Protocol on 30 November 2018, according to the [WTO member page](https://www.wto.org/english/thewto_e/countries_e/cameroon_e.htm). [The official TFA text](https://www.wto.org/english/docs_e/legal_e/tfa_e.htm) is a comparator and commitment source; exact provision and implementation status must be checked for any specific finding.
- The [CNCC notice of 15 June 2026](https://www.cncc.cm/fr/article/communique-1099) says the BESC requirement for goods in transit is suspended until further notice. It does not, by itself, establish that no replacement mechanism exists.
- The [Presidency of Cameroon law page](https://www.prc.cm/fr/actualites/actes/lois/7588) provides Law No. 2024/017. Only selected excerpts are in the current ARGOS corpus.
- The African Union’s [Continental AI Strategy](https://au.int/en/documents/20240809/continental-artificial-intelligence-strategy) is regional context, not a Cameroon-specific legal requirement.

## Technical evidence files

- Scenario implementation: `app/agents/policy_scenario.py`
- Scenario runner: `scripts/run_policy_scenario.py`
- Deterministic trace: `reports/argos_ai_for_good/evidence/silent_container_v1_deterministic.json`
- Retrieval control evaluation: `reports/argos_ai_for_good/evidence/policy_kb_retrieval_evaluation.json`
- Source provenance: `knowledge_base/source_register.json`
- Experimental model evaluation: `reports/argos_ai_for_good/central_africa_model_validation_v2.json`
- ITU reference workflow notes: `docs/ITU_AI_READINESS_REFERENCE_INTEGRATION.md`

Reproduce the scenario with:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_policy_scenario.py \
  --scenario silent_container_v1 \
  --output /tmp/silent_container.json
```

The final PDF should remain within the organizer’s five-page maximum. Update team names, contact details, and repository visibility only after confirming them; recheck the official organizer instructions and primary sources at submission time.
