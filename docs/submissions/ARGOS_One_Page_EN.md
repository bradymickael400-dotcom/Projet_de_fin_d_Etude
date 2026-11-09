# ARGOS — container tracking and event review

**Team ARGOS · Project overview · AI for Good Sandbox Hackathon**

## Why ARGOS

During a shipment, container location, sensor readings, and updates from different parties often arrive separately. ARGOS brings them together so the team responsible for the shipment can see what happened and check an alert in context.

## What the application does

An ESP32 device sends GPS positions and available readings, such as temperature, shock, or door opening. The API checks each message and links it to the right tracking unit. Configured rules trigger alerts. The notification stays brief; the container details show the reading, time, location, and trigger.

For an active route, ARGOS estimates arrival using the remaining distance along the planned route and recent GPS speeds. It is an indicative calculation: it does not account for traffic, future stops, or delays at borders and terminals.

## The demonstration: one journey, six stages

The fully simulated scenario follows a pharmaceutical shipment from Douala to an inland yard. It shows a declaration and seal, terminal exit, a door and temperature alert with an uncertain GPS fix, a location-sharing request, a late reading at the yard, and a proposed inspection. When location sharing is requested, the scenario pauses for human review because the information provided is not enough to approve it.

| Simulated role | What it sees and reviews |
|---|---|
| Operator | Readings, position, route, and transport checks. |
| Customs-port | Declaration, seal, and information shared with the role. |
| Data and cybersecurity | Data involved and the sharing request. |
| Neutral adviser | Available sources and unresolved points. |

The coordinator releases facts in stages. The roles do not represent any administration. A person remains responsible for operational decisions.

## How the agents are controlled

Each role searches its own document partition. Agents cite retrieved passages; when the corpus does not answer, they report that information is missing. The trace records the facts, sources, uncertainty, and human-review status. The replay works without an external provider; Gemini is optional.

The corpus contains selected excerpts from Cameroon’s Law No. 2024/017, transcribed and visually checked against the official scan, and a bounded summary of the WTO Trade Facilitation Agreement. These documents do not amount to a complete legal analysis. ITU‑T Y.3172 and AI Ready are used to describe the architecture; ARGOS claims neither certification nor a readiness score.

## Technology and current status

The prototype uses Python and Flask, PostgreSQL/TimescaleDB, Redis, Leaflet, an ESP32 device, and local keyword-based document search. The logistic classifier trained on synthetic scenarios is experimental and does not generate the application’s alerts. The local document control met 12 expected source-presence or source-absence checks; that result does not measure legal accuracy.
