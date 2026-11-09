# ARGOS Project Handoff — Verified Work and Evidence

**Purpose:** Give another AI or collaborator an accurate, evidence-bounded account of what exists in the ARGOS repository, what has been demonstrated, and what remains incomplete.  
**Repository:** `Projet_de_fin_d_Etude`  
**Handoff prepared:** 7 November 2026  
**Working directory:** repository root, `pfe/`

## 1. How to read this handoff

This is a repository handoff, not a product claim or legal opinion. “Implemented” means code or a file exists. “Tested” means a recorded test or execution exists. “Demonstrated” may use mocks, synthetic data, local services, or a test identity; the scope is stated. “Not verified” means the repository does not prove it. A document saying that a future step is planned is not evidence that it was completed.

The user also provided two attachments: a validation-draft PDF and a mentorship submission-template DOCX. The PDF included a generic telecom/education example after the ARGOS draft. That example was treated as instructions about report structure, not as ARGOS facts. The template’s suggested claims and hypotheticals were not treated as evidence. The official organizer page was checked separately.

## 2. Project overview

ARGOS is an existing Flask logistics/IoT application for tracking containers and black boxes. It has a web interface, authentication and role checks, PostgreSQL persistence, Redis-related telemetry components, IoT ingestion/validation, deterministic alert rules, position and route services, and experimental AI/agent capabilities. For the AI for Good submission, the project was repositioned around **ARGOS Transit Agents**: a policy-coordination demonstration using staged synthetic cargo events and four simulated institutional roles. IoT telemetry is an optional evidence source; it is not the submission’s core policy claim.

The submission demonstration must not be described as a deployed customs platform, an official government agent, legal compliance, a production-grade AI system, or field-validated prediction.

## 3. Existing ARGOS application: verified architecture from repository review

### Stack and data flow

- Backend: Python/Flask application, created through `create_app()` in `app/` and launched through `app.py` / `wsgi.py`.
- Interface: Jinja templates under `app/templates/`, CSS and native JavaScript under `app/static/`.
- Persistence: PostgreSQL via SQLAlchemy/psycopg; migrations are SQL files under `migrations/`.
- Telemetry cache/queue components use Redis. Compose includes web, worker, database and Redis-related services.
- ESP32/Arduino firmware is under `firmware/argos_esp32/`.
- The repository inspection documents the intended telemetry path: authenticated device request → validation and normalization → device/box association and sequence checks → storage/audit/event rules → API/dashboard display.

The above describes code and architecture, not that every external service or physical device was operationally validated. The physical ESP32 was not connected in the documented checks.

### IoT contract and simulation boundary

`docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md` records the inspected telemetry contract: UUID `messageId`, telemetry `type`, device and box identifiers, UTC timestamp, sequence, position, sensors, modes, and a quality/provenance object. The backend checks device/box association and sequence. Provenance values include `FIELD` and `SYNTHETIC`.

The terrestrial simulator was intentionally designed not to send synthetic readings to the operational IoT ingestion endpoint, because that endpoint may persist operational readings and trigger alerts/notifications. Simulation data should remain isolated and labelled synthetic. A synthetic `deviceUid` has no live device key. The direct Wi-Fi telemetry bridge also writes to operational storage and was excluded from the simulator.

### Routes, ETA, map and limitations

- The app has planned-route storage and route monitoring. Corridor deviation is geometric and is not a probability of theft or damage.
- ETA is a deterministic estimate based on remaining route distance and a median of recent GPS speeds. Traffic, weather, queues, border delays and future stops are not modelled; stale/no position or zero speed may make the estimate unavailable.
- Leaflet displays API-provided positions. During the documented UI checks, the positions endpoint returned zero positions; screenshots show an empty state, not fabricated coordinates.
- The UI’s public OSRM routing call is not a certified heavy-truck route, a real-time traffic source, or a validation of truck restrictions.
- The existing operational alert engine is deterministic rule logic, not a trained predictive model.

See `docs/ARCHITECTURE_EXISTANTE.md`, `docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md`, and `docs/SIMULATEUR_DOUALA_BERTOUA.md` for fuller details and commands.

## 4. Agent and LLM work completed

### Operational tool registry and orchestration

The repository contains an explicit capability registry and orchestrator. Main operational capabilities include:

- `iot_monitor`: latest sensor reading, age and quality for an authorized box.
- `gps_route`: hybrid position and route/corridor information.
- `risk_assessor`: deterministic assessment that consumes `iot_monitor` and `gps_route` results.
- `knowledge_retriever`: local lexical document search, returning source path, lines and lexical score.
- Additional registered capabilities include port intelligence, transport/regulatory lookup and regional data inventory.

The shared result envelope includes agent ID, message ID, timestamp, status, result data, provenance and error. The trace ID correlates a conversation’s tool calls.

`GeminiToolProvider` supports multiple tool calls in a response, calls registered handlers, returns their results to the provider and requests a final synthesis. The loop is bounded. Server-side authorization and selected-box scope are checked; browser-provided operational context is not trusted as the source of telemetry. The Flask `/api/ai/chat` path is integrated with the registry. The legacy `/api/ai/deepseek` path is documented as an alias to the same orchestration path.

### Security and audit design

- API authentication defaults to denying requests without a signed token except for explicitly public endpoints; routes/capabilities also enforce role and box scope.
- Forged `X-Role`/`X-User-Id` headers were rejected with 401 in a recorded check.
- Client-provided `contextData` and `systemPrompt` are not accepted as operational evidence or system instructions by the orchestrated route.
- `migrations/20261027_ai_agent_runs.sql` adds an audit table for agent runs/results and source references without storing raw user question text or model chain-of-thought.
- Security controls are not a full security audit. `docs/ARCHITECTURE_EXISTANTE.md` notes broad CORS configuration as a remaining concern.

### What the agent tests prove and do not prove

The phase evidence records tests using a simulated Gemini HTTP transport and controlled/mocked database or service dependencies. They prove orchestration contracts and access-scope logic. They do not prove a live Gemini response, live production PostgreSQL behavior, or accuracy of legal answers. A real Gemini attempt returned upstream HTTP 503 and ARGOS HTTP 502; no successful real-provider tool call was demonstrated.

See `docs/INTERCONNEXION_AGENTS.md`, `docs/PHASE2_POINT_CONTROLE.md`, `docs/PHASE4_POINT_CONTROLE.md`, and `docs/TESTS_ET_PREUVES.md`.

## 5. User interface work and recorded validation

The phase reports record these UI changes:

- GPS map reads the authorized positions API and uses API-backed labels; it provides loading, error and empty states and creates no demo markers.
- Global AI assistant sends the user message and optional selected box ID through the authenticated API; it displays agents, statuses, tool exchanges, sources and trace ID.
- Keyboard behavior, small-screen layout, reduced-motion preference, map attribution and empty states were checked.
- Dashboard KPI display was revised to be visible; a fixed fictional notification count was removed.
- Browser checks used local Flask/Chromium/Playwright. In some capture runs a test superadmin identity was injected into the local capture process. This does not validate production login.

Recorded phase checks include:

- Phase 2: 4 Python tests passed with simulated provider (historical phase report).
- Phase 3: 4 Python tests and 3 JS tests passed; browser screenshot check reported no JS errors and a 320 px mobile panel fit (historical phase report).
- Phase 4: 16 root ARGOS Python tests, 6 JS tests, syntax checks and a local browser/API path passed in the documented environment. A local Flask request used a test tool provider and real handlers returning `empty` for IoT/GPS data and successfully read back its audit trace.
- The direct production-like Gemini request failed with 503/502.
- The project-wide pytest collection did not pass: the separate `arthena_flask` suite failed collection because `flask_migrate` was unavailable, and there was a package-name collision involving `app`.
- `pip-audit` and Bandit were not run because the executables were absent.

These are historical test results in the phase documents, not a claim that this handoff reran tests. No tests were run as part of compiling this handoff.

Relevant evidence: `docs/PHASE2_POINT_CONTROLE.md`, `docs/PHASE3_POINT_CONTROLE.md`, `docs/PHASE4_POINT_CONTROLE.md`, `docs/TESTS_ET_PREUVES.md`; screenshots under `docs/phase3/captures/` and `docs/phase4/captures/`.

## 6. Predictive ML work: present but experimental

There is a logistic-regression artifact and training/evaluation script, but this classifier is not loaded by operational alerts. The latest report `reports/argos_ai_for_good/central_africa_model_validation_v2.json` says:

- Two synthetic datasets: 240 samples across four scenarios and 61 samples in one additional scenario.
- Total: 301 synthetic samples, 216 stable and 85 simulated anomalies, five scenarios.
- Leave-one-scenario-out mean: accuracy 87.37%, precision 100%, recall 55.29%, measured against synthetic labels.
- The artifact is `models/argos_demo_anomaly_logistic_v2.json`.
- The report explicitly says this demonstrates a pipeline and does not measure real shipment performance.

Do not describe this as a production model, validated regional anomaly detector, failure predictor, delay predictor, or model behind the live alerts.

Supporting files: `scripts/train_demo_anomaly_model.py`, `datasets/argos_demo_two_routes.json`, `datasets/argos_central_africa_60min.json`, `reports/argos_ai_for_good/central_africa_model_validation_v2.json`, `docs/INVENTAIRE_AGENTS_MODELES.md`.

## 7. AI for Good submission work completed

### Attachments reviewed and interpretation

- `ARGOS_report_validation_draft (2).pdf` was read. It included an ARGOS Transit Agents validation draft with planned/unverified claims and a second, generic telecom/education example appended afterward.
- `1.31oct.AI for Good Hackathon Submission Template (2).docx` was read. Its example text is telecom complaint handling and smart classroom. For ARGOS, it supplies the expected report structure and prompts: use case, use-case requirements, Y.3172 and AI Readiness mapping, policy mapping, error scenarios, and policy/standards gaps.
- Template examples and draft hypotheses were not copied into ARGOS as facts.

### Official submission requirements checked online on 7 November 2026

The official ITU AI for Good UAE hackathon page states:

- Maximum five pages for the technical report.
- GitHub repository and knowledge base of policies, regulations and strategies are submission materials.
- Demo video is optional initially (up to seven minutes) and required for shortlisted teams.
- Published submission deadline: 10 November 2026.
- Evaluation covers knowledge-base quality, agent ability in simulated scenarios, policy/standards gap quality and global examples, auditability, and Y.3172/AI Readiness alignment.
- The page asks teams to focus on domain-specific gaps and relevant global policy examples, not unsupported country-specific recommendations.

Primary page: <https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/>. These requirements were checked on the date above; recheck at submission.

### Submission drafts generated

- `docs/submissions/ARGOS_Mentorship_Template_Draft_EN.md` is the English editable working source with evidence notes and reproducibility references.
- `docs/submissions/ARGOS_Mentorship_Template_Draft_FR.md` is the earlier French working draft. It has not yet been updated to match all detailed source verification in the English final report.
- `docs/submissions/ARGOS_AI_for_Good_Final_EN.docx` and `.pdf` are a detailed English report. The PDF was rendered and checked with `pdfinfo` and `pdftotext`; it is three A4 pages, beneath the five-page maximum.
- The English final report includes use case, requirements/evidence table, Y.3172 and AI Readiness mapping, source status, scenario evidence, gap matrix, conclusion and references.
- Team names/contact details remain placeholders; public repository access has not been verified. It is therefore a detailed submission draft, not a fully filled final submission package.

The source-generation code for that PDF was temporary under `/tmp`; it is not a committed project build script. The DOCX is included as an editable artifact.

## 8. Policy knowledge base and source status

`knowledge_base/source_register.json` currently lists six source-register entries (count includes a research inventory explicitly marked `TO_VERIFY`):

1. Bounded team-authored summary of selected WTO Trade Facilitation Agreement provisions, verified against primary WTO text; Cameroon applicability/notifications are marked for verification in the register.
2. Selected excerpts of Cameroon Law No. 2024/017, manually transcribed from the official scanned copy and visually checked; not the full law and not independently legally reviewed.
3. Summary/reference to Cameroon Railway Law No. 2023/010, primary official source link; full-text and implementing decrees still require review.
4. Summary of CEMAC Merchant Marine Code (2012), with member-state implementation/amendments review needed.
5. Summary of OHADA road freight act, with contractual scope/exclusions requiring review.
6. Summary of CEMAC customs code/container transit with edition/amendments review required.

The register also includes a Cameroon/CEMAC transport-law research map marked `TO_VERIFY`, which should not be counted as a verified legal source. The corpus is not a 30-document comprehensive legal base. The index is local and lexical; passages include source path and line ranges. It is not the ITU notebook’s FAISS vector index.

Local files include:

- `knowledge_base/documents/cameroon_law_2024_017_excerpts.md`
- `knowledge_base/documents/wto_trade_facilitation_selected_articles.md`
- `knowledge_base/documents/cameroon_railway_law_2023_010.md`
- `knowledge_base/documents/cemac_marine_merchant_code_2012.md`
- `knowledge_base/documents/ohada_road_freight_act.md`
- `knowledge_base/documents/cemac_customs_code_container_transit.md`
- `knowledge_base/documents/cameroon_transport_law_map.md`
- `knowledge_base/source_register.json`

### ITU AI Readiness reference code

`docs/ITU_AI_READINESS_REFERENCE_INTEGRATION.md` documents inspection of the public `CrashingGuru/ITUAIReadiness` reference notebook. The repo contains `scripts/export_itu_readiness_kb.py`, which exports eligible verified/summary source records into separated role partitions with a manifest and SHA-256. This is a handoff/export path only. The notebook was not run to produce FAISS indexes, no documents were sent to Colab by the exporter, and no ITU-hosted index exists. The server continues to use local lexical retrieval.

## 9. Policy scenario implementation and actual saved evidence

### Implemented scenario

`app/agents/policy_scenario.py` defines `silent_container_v1`:

- Jurisdiction label: Cameroon; cross-border transit explicitly out of scope.
- Fictional origin: Douala; destination: an inland yard in Cameroon.
- Six synthetic stages T0–T5: declaration/seal; port exit; door/temperature/GPS anomaly; location-sharing request; delayed yard reading and broken seal report; proposed human inspection.
- Four simulated roles: `A1_OPERATOR`, `A2_CUSTOMS_PORT`, `A3_DATA_PROTECTION`, `A4_POLICY_ADVISER`.
- The first three roles receive different facts; A4 reconciles the role assessments.
- At T3, no personal data is transferred and the transfer status is `BLOCKED_PENDING_HUMAN_REVIEW`.
- Human review remains `PENDING`; the scenario does not record an approval or real institutional decision.
- Retrieval is lexical. The trace carries references, line locations, uncertainty, unknowns, a short justification summary, and limitations; it is not a legal opinion.
- The deterministic path works without requesting an LLM. The optional provider branch exists in code but its live-provider quality is unverified.

Run command from repository root:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_policy_scenario.py \
  --scenario silent_container_v1 \
  --output /tmp/silent_container.json
```

Saved evidence is at `reports/argos_ai_for_good/evidence/silent_container_v1_deterministic.json`. It contains six timeline stages, four agents, synthetic provenance, per-role assessments, retrieved passages, transfer state and human-gate state. Because each stage contains three independent assessments plus an adviser reconciliation, there are 24 stage-level assessment/reconciliation records. Evidence is a saved deterministic replay, not physical shipment telemetry.

Scenario audit-storage code and migration exist at `app/agents/policy_scenario_audit.py` and `migrations/20261102_policy_scenario_runs.sql`. The JSON replay is saved. Application of this specific migration to a submission database and persistent readback were not established by the cited phase evidence; do not claim durable production persistence without checking that environment.

### Retrieval control results

`knowledge_base/ai_for_good_control_queries.json` defines a small set of control queries. `scripts/evaluate_policy_kb.py` produces `reports/argos_ai_for_good/evidence/policy_kb_retrieval_evaluation.json`, whose saved result is 12 passed out of 12 expected presence/absence checks. Checks include retrieval of the bounded WTO summary and Cameroon-law excerpts, and expected no-result cases for national seal handover responsibility and the CNCC BESC notice because those sources were not ingested into the tested local corpus.

The evaluation note explicitly says this is only a small source-presence/absence control set. It is not legal-answer accuracy, comprehensive search quality, or a benchmark of agent correctness.

## 10. Law and policy claims: what has and has not been verified

### Verified primary-source facts used in the English report

- Cameroon’s official Presidency site provides Law No. 2024/017, dated 23 December 2024. Only selected excerpts are present in the local corpus. URL: <https://www.prc.cm/fr/actualites/actes/lois/7588>.
- WTO’s Cameroon member information page records acceptance of the WTO Trade Facilitation Agreement Protocol on 30 November 2018. URL: <https://www.wto.org/english/thewto_e/countries_e/cameroon_e.htm>.
- The CNCC official notice dated 15 June 2026 says the BESC requirement for goods in transit is suspended until further notice and refers to a tripartite Cameroon–Chad–Central African Republic forum and maintaining traceability. URL: <https://www.cncc.cm/fr/article/communique-1099>. This notice does not prove that no replacement exists.
- ITU-T Y.3172 is an in-force Recommendation titled “Architectural framework for machine learning in future networks including IMT-2020.” URL: <https://www.itu.int/rec/T-REC-Y.3172/en>.
- ITU AI Ready report is a readiness analysis/framework, not a certification applied to ARGOS. URL: <https://www.itu.int/epublications/publication/ai-ready-analysis-towards-a-standardized-readiness-framework>.
- The African Union Continental AI Strategy is regional policy context; it is not by itself a Cameroon-specific binding rule. URL: <https://au.int/en/documents/20240809/continental-artificial-intelligence-strategy>.

### Not established and must not be repeated as fact

- That SIGMAT is still being prepared, or that CAMCIS and SYDONIA World are currently non-interoperable.
- That a BESC replacement mechanism does not exist.
- Current legal/operational status of a data-protection supervisory authority, or a claimed implementation deadline for Law No. 2024/017.
- That Cameroon’s national AI strategy omits customs or transport.
- Legal admissibility/status of private ARGOS IoT events next to customs seals.
- Official responsibility allocation at each Douala-to-inland handover.
- That an automated customs profiling rule or appeal route is absent from all applicable instruments.

These were hypotheses in the validation draft/template. Their status should remain open until exact current primary passages are obtained and applicable texts are reviewed.

## 11. Existing submission/report files and their status

The repository contains older English/French submissions, one-page documents, template-structure versions, and a UAE technical report. They are historical artifacts; some predate the current scenario and source register. Prefer the current final English report and this handoff as context, but do not assume every older report was fully updated.

Current English report artifacts:

- `docs/submissions/ARGOS_AI_for_Good_Final_EN.pdf` — generated English report; three A4 pages; checked against the official five-page maximum.
- `docs/submissions/ARGOS_AI_for_Good_Final_EN.docx` — editable source document.
- `docs/submissions/ARGOS_Mentorship_Template_Draft_EN.md` — current concise Markdown source/notes aligned with verified claims.
- `docs/submissions/ARGOS_Mentorship_Template_Draft_FR.md` — working French version, not yet synchronized to all later English report changes.

The PDF includes a reproduction command, project evidence paths, policies/gaps, and official references. It also still has “to be confirmed” team/contact details, says repository visibility must be verified, and labels itself a working draft. Do not call it submission-ready without resolving these items.

## 12. Main remaining work / open items

1. Fill team leader, members, affiliation, email/phone, and verify a public repository URL that works for reviewers.
2. Recheck official competition requirements and deadline immediately before submission.
3. Verify and complete the local source corpus with primary texts, exact article/page metadata, version/date and reuse terms; independently review legal excerpts and conclusions.
4. Do not infer law from corpus absence. For each final gap, pair a precise local/regional source passage with an appropriate primary global comparator and explain applicability limits.
5. If claiming the ITU reference-code/index workflow, actually run the export and notebook/index creation. Current state is export tooling and documentation, not FAISS output or an ITU-hosted knowledge base.
6. Expand scenario evaluation with expected-versus-actual outcomes, answer citation checks, abstention checks, partition leakage checks, late-event reassessment, conflicting-source cases, and human override. The saved 12/12 score is not legal correctness.
7. Consider implementing/testing Scenario B; current English report describes it as a proposed stress scenario, not a completed run.
8. Verify the policy scenario audit migration and persistent readback in the intended demo database if persistence is claimed.
9. Decide whether a real LLM demo is necessary. If attempted, use synthetic data and record provider, model/version, request behavior, failures and output review. The last documented real Gemini attempt failed with 503/502.
10. Physical-device telemetry, actual route testing, live customs/port integrations, real shipment measurements, and independent field metrics remain unproven.
11. Synchronize the French report/source with the final English evidence and citations if both language submissions are needed.

## 13. Useful files by topic

| Topic | Main files |
|---|---|
| Existing system architecture | `docs/ARCHITECTURE_EXISTANTE.md`, `app/modules/iot/`, `app/services/`, `app/routes/` |
| Agent architecture and permissions | `docs/INTERCONNEXION_AGENTS.md`, `app/agents/registry.py`, `app/agents/orchestrator.py`, `app/agents/specialists.py`, `app/security.py` |
| Historical implementation/test records | `docs/PHASE2_POINT_CONTROLE.md`, `docs/PHASE3_POINT_CONTROLE.md`, `docs/PHASE4_POINT_CONTROLE.md`, `docs/TESTS_ET_PREUVES.md` |
| Model status | `docs/INVENTAIRE_AGENTS_MODELES.md`, `reports/argos_ai_for_good/central_africa_model_validation_v2.json`, `models/argos_demo_anomaly_logistic_v2.json` |
| Terrestrial simulation safety boundary | `docs/AUDIT_SIMULATEUR_TERRESTRE_ARGOS.md`, `docs/SIMULATEUR_DOUALA_BERTOUA.md`, `scripts/simulate_argos_box.py`, `app/services/terrestrial_simulation_service.py` |
| Policy knowledge base | `knowledge_base/source_register.json`, `knowledge_base/documents/`, `app/knowledge/rag.py`, `app/knowledge/sources.py` |
| Policy scenario | `app/agents/policy_scenario.py`, `app/agents/policy_scenario_audit.py`, `scripts/run_policy_scenario.py`, `migrations/20261102_policy_scenario_runs.sql` |
| Saved policy evidence | `reports/argos_ai_for_good/evidence/silent_container_v1_deterministic.json`, `reports/argos_ai_for_good/evidence/policy_kb_retrieval_evaluation.json`, `knowledge_base/ai_for_good_control_queries.json` |
| ITU reference export | `docs/ITU_AI_READINESS_REFERENCE_INTEGRATION.md`, `scripts/export_itu_readiness_kb.py` |
| Current English submission | `docs/submissions/ARGOS_AI_for_Good_Final_EN.pdf`, `docs/submissions/ARGOS_AI_for_Good_Final_EN.docx`, `docs/submissions/ARGOS_Mentorship_Template_Draft_EN.md` |

## 14. Instructions for the receiving AI

- Treat this handoff and repository evidence as claims to verify, not as permission to expand claims beyond evidence.
- Preserve the distinction between code-present, test-passed, saved simulation, live external integration, and field-validated behavior.
- Treat all policy-role agents as simulated and all scenario events as synthetic unless provenance explicitly says otherwise.
- Do not present the synthetic classifier’s metrics as real-world metrics or say the classifier powers operational alerts.
- Do not describe the local knowledge base as complete, fully primary-source, independently legally reviewed, or hosted by ITU.
- Do not convert “no matching passage found” into “no law or procedure exists.”
- Do not claim the actual Gemini provider path succeeded; the documented live attempt returned HTTP 503/502.
- Before changing a report, check the actual current files and official submission page, because the handoff status is date-specific.
- Keep open questions visible. Never fill missing team names, contacts, legal positions, test results, or institutional endorsements with guesses.
