# AI for Good Sandbox Hackathon — ARGOS, intelligent container tracking and safety in Central Africa

**Team leader:** to be completed · **Members and contact details:** to be completed  
**Repository:** [ARGOS project on GitHub](https://github.com/bradymickael400-dotcom/Projet_de_fin_d_Etude) · **Status:** software prototype connected to a telemetry pipeline; statements below describe code capabilities and reproducible demonstrations, not large-scale operational validation.

## Introduction

A container can pass through several stages, operators, and transport modes without its owner having a continuous view of its location and condition. A delayed position, shock, opening, or change in transport conditions can then be difficult to put in context. ARGOS is designed to bring these signals into one tracking interface and make them understandable to the people responsible for the shipment.

The project responds to a need in Central African logistics: making instrumented-container tracking practical even when carrier, terminal, and international platform data are not consolidated in one system. ARGOS connects an IoT tracking unit to the container, an ingestion server, and a web application. It presents positions, sensor readings, triggering events, the planned route, and, when the required data is available, an estimated arrival time. A person remains responsible for deciding whether to inspect, contact a carrier, or change the shipment plan.

## Description of the use case

An ARGOS unit transmits GPS positions and environmental and security readings. The server validates fields and timestamps, neutralizes measurements that firmware marks as unreliable, and stores events in PostgreSQL. Business rules compare readings with configured thresholds. Route tracking calculates distance from the planned corridor; configured geofences identify zone entries and exits; port context reports measured proximity to reference points.

Each notification is shown at two levels. The list gives a short description of what happened and identifies the container. Its detail view provides the trigger, available readings, time, and information needed to check the event. This keeps the list readable while leaving the cause available for review.

For each container linked to an active route, ARGOS estimates arrival using the remaining distance along the planned route and the median of recent GPS speeds, expressed in km/h. The result provides a projected arrival time, remaining distance, speed used, freshness of the latest position, and an indicative confidence level. The estimate is suspended if no route is configured, the latest position is more than twenty minutes old, or recent speed indicates a stop. It does not account for traffic, future breaks, weather, customs queues, maritime schedules, or handling time. This is a deterministic projection, not a learned prediction.

The repository’s synthetic replays contain four scenarios of 60 samples each, including a road journey in Cameroon and a cold-chain scenario in Douala. These records constitute the training dataset for the first experimental ARGOS classifier, a binary logistic-regression model trained offline. The dataset contains 240 samples (173 stable and 67 labelled simulated anomalies). In leave-one-scenario-out validation, mean recall is 56.3% and mean precision is 100% against the simulated labels only. The model therefore still misses events, and these metrics say nothing about performance on real shipments. The artifact demonstrates a reproducible training pipeline; it is not used by operational alerts.

## Use case requirements

- **SRC — Sources:** an ARGOS unit based on an ESP32, GPS, and sensors available in the configuration; each measurement carries a sequence and timestamp. Quality status accompanies relevant sensors.
- **C — Collector:** ARGOS’s IoT collection point receives messages, checks their association with the box and device, and passes validated events to pre-processing. The network transports messages; it is not Y.3172 node C.
- **PP — Pre-processing:** schema validation, normalization, freshness checks, and setting values to `null` when firmware reports invalid quality. Raw ingestion data and normalized readings are distinguished.
- **M — Methods:** configurable threshold rules, geometric route and geofence calculations, explainable ETA, and an experimental classifier trained offline on synthetic scenarios. The classifier is not loaded in production and does not replace business rules.
- **P — Protection and permissions:** authenticated APIs limit access to units associated with the profile and company. Assistance results are restricted to selected and authorized containers. A complete organizational review of retention and data transfers remains necessary.
- **D — Decision:** the server produces structured events and trace logs. Alerts provide a verifiable trigger; a person reviews the situation and chooses the operational response.
- **SINK — Interface:** the Flask application, Leaflet map, and container views display position, route, ETA, status, and event details.

## Mapping to ITU-T Y.3172, AI Readiness 2.0, and sector references

**ARGOS use-case chain.** SRC covers sensors and other sources; C is the event collector; PP validates and normalizes events before storage; M covers rules, calculations, and specialist tools; P covers access and sharing policies; D distributes results; SINK comprises the people and interfaces receiving them. In ITU-T Y.3172, C means Collector, not connectivity. This mapping locates components; it is not a certification of compliance with the Recommendation.

Existing specialist capabilities include `iot_monitor` for telemetry, `gps_route` for positioning and corridor analysis, `risk_assessor` for deterministic signal assessment, `knowledge_retriever` for local search, `transport_regulatory` for preparing a source review, `port_intelligence` for port references and geofences, and `central_africa_data` for a candidate data inventory. The four policy roles in the scenario are separate from these tools. The operational orchestrator checks selected-container scope and can pass results to Gemini when configured. The ARGOS classifier remains an experimental artifact trained offline on synthetic replays; it is not loaded by operational alerts, and the demo data is not a field dataset.

Local code and controls demonstrate orchestration with a simulated provider, partition-filtered retrieval, a six-step institutional replay, a location transfer pending human review, and twelve corpus-control queries that met their defined expectations. These controls do not demonstrate continuous Gemini availability, field validation, general legal accuracy, or the quality of an exported FAISS index. AI Readiness 2.0 provides assessment dimensions; ARGOS has not calculated a readiness score.

The project’s document catalogue references Cameroon’s Law No. 2024/017 on personal data, SOLAS/VGM, the CTU Code, ISO/IEC 27001, and ISO 28000. Referencing them is not a compliance claim. Access controls are a technical measure; processing purposes, retention, transfers, responsibilities, and procedures for exercising rights require a dedicated legal and organizational review. ARGOS neither measures nor certifies verified gross mass required by SOLAS where applicable. Shock and location alerts do not certify packing or securing under the CTU Code. No ISO certification is claimed for the product.

### Public-policy demonstration and role agents

For the hackathon scenario, ARGOS adds four distinct demonstration roles: logistics operator, customs-port, data protection/cybersecurity, and neutral adviser. These roles are simulated and do not represent any administration. Each retrieval capability can access only document paths that the source register marks as primary and verified for its partition. The `iot_monitor`, `gps_route`, and `risk_assessor` tools remain operational evidence for the operator role; they do not expose another company’s box data.

The `silent_container_v1` scenario replays six fictional stages from Douala to an inland yard: declaration and seal, terminal exit, door/temperature alert and uncertain GPS, a request to share location history, a delayed event at the yard, and a proposal for human inspection. A1–A3 assessments are produced separately from the facts assigned to each role. A4 reconciles their summaries. The location transfer remains blocked pending human review. The deterministic mode works without an external provider; an optional Gemini mode handles each role separately and receives only its permitted facts and passages. The trace retains source references, event IDs, uncertainties, a short justification summary, and review status without private chain-of-thought.

At this version date, the corpus contains a bounded summary of selected WTO Trade Facilitation Agreement provisions and manually transcribed, visually checked excerpts from Cameroon Law No. 2024/017. The full law and implementing rules are not indexed, and no independent legal review has been completed. The twelve-query control set checks retrieval of the Cameroon excerpts and WTO comparator, then checks refusal for unsupported BESC/customs-chain claims. The defined expectations were met by the current lexical search; this does not measure general legal accuracy.

## Error and controversy scenarios

1. **Route deviation.** A position exceeds the configured corridor threshold. ARGOS displays the segment and provides the geometric score, distance, and time in the details. The score is not an incident probability; an operator checks the GPS point, its accuracy, and the route before intervening.
2. **Shock, temperature, opening, or flame.** The system shows the reading and the rule that fired. A sensor may be incorrectly mounted, invalid, or affected by a short peak. The alert prompts a check but does not by itself establish damage, theft, or fire.
3. **Unstable or unavailable ETA.** A stale position, zero speed, missing route, or route far from the corridor may prevent a useful estimate. ARGOS reports the unavailable status or suspends the ETA instead of presenting an arrival time as certain. Any available estimate remains sensitive to stops and unobserved delays.
4. **Port proximity mistaken for official entry.** A radius around a reference point measures indicative proximity; it does not prove crossing an official boundary. Entry is reported only for a configured and enabled geofence polygon, and remains subject to GPS accuracy.
5. **Access to another company’s data.** Authenticated API routes enforce the ownership/association scope of tracking units. Tests check refusals for unselected or unauthorized units. This code-level evidence does not replace an independent security audit.
6. **Personal data and automated decisions.** Positions can reveal driver or company activity. Tracking must be limited to the transport purpose, authorized roles, and a retention period defined by the organization. Risk scores and alerts remain aids to review; no driver sanction or legal decision should rely on them alone.
7. **Unavailable LLM or incorrect answer.** Collection and event rules do not depend on LLM-generated wording. Tool results and their status are logged; users can return to source readings and events. A generated answer is not regulatory evidence.

## Policy and standards gaps

Current limits are explicit: the only trained ARGOS ML model is an experimental classifier based on synthetic scenarios; it has neither representative field labels nor operational use. Its scenario-held-out validation has mean recall of 56.3%, insufficient to drive alerts on its own. There are no false-positive/false-negative measurements from live operations, or ETA validation against observed arrival times. Carrier, AIS, and terminal coverage is narrower than that of international commercial platforms. Several port locations are indicative references rather than certified boundaries. The regulatory corpus and its update process have not been demonstrated to be exhaustive. Technical controls do not prove full legal compliance or ISO certification.

Commercial services such as project44 describe ocean visibility built from carrier integrations, AIS positions, and port events, with estimates across global networks. ARGOS addresses a different scope: container-attached telemetry, environmental and security measurements, explainable events, and company-scoped access in a regional context. No independent benchmark supports a claim of superior performance. This comparison concerns source types and coverage, not the relative accuracy of ETA estimates.

## References

[1] [AI for Good Lab Hackathon — United Arab Emirates, official page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/) · [2] [ITU-T Y.3172, official record](https://www.itu.int/rec/T-REC-Y.3172/en) · [3] [ITU, AI Ready — Analysis Towards a Standardized Readiness Framework](https://www.itu.int/epublications/publication/ai-ready-analysis-towards-a-standardized-readiness-framework) · [4] [Presidency of Cameroon, Law No. 2024/017](https://prc.cm/fr/multimedia/documents/10258-loi-n-2024-017-du-23-12-2024-web) · [5] [IMO, SOLAS and VGM](https://www.imo.org/en/ourwork/safety/pages/verification-of-the-gross-mass.aspx) · [6] [IMO/ILO/UNECE, CTU Code](https://www.imo.org/en/ourwork/safety/pages/ctu-code.aspx) · [7] [project44, Ocean Visibility](https://www.project44.com/platform/visibility/ocean/)
