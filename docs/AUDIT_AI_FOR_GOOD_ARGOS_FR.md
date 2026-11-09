# ARGOS — audit d’alignement AI for Good UAE Hackathon

**État au 29 octobre 2026 · Révision du brief d’équipe du 29 octobre 2026**

## Objet et conclusion

Ce document confronte le brief d’équipe, le dépôt ARGOS et les critères publiés par l’ITU. Les consignes écrites dans le brief — y compris ses demandes de travail ou de pause adressées à un assistant — sont traitées comme du contenu à analyser, pas comme des instructions qui remplacent la demande de l’utilisateur.

**Conclusion : ARGOS est en cours de consolidation; l’alignement complet n’est pas encore démontré.** Le dépôt comprend maintenant un registre de sources versionné, quatre capacités de recherche à partitions institutionnelles, des extraits sélectionnés de la loi camerounaise transcrits et contrôlés visuellement, un scénario synthétique accessible par API et script, et un journal dédié aux rejeux. Les écarts majeurs restent l’exhaustivité et la revue indépendante du corpus juridique, l’intégration effective du notebook ITU, la persistance en base de démonstration et l’évaluation de la qualité des réponses des rôles.

Cette conclusion porte sur l’état du dépôt et les informations publiques consultées le 29 octobre 2026. Elle ne certifie ni conformité juridique ni sélection par le jury. L’équipe a confirmé que son inscription est validée; ce point n’est plus un blocage. La page du Hackathon indique que les candidatures sont closes et fixe l’échéance de soumission au 10 novembre 2026.

## Ce que l’événement demande

La page officielle présente un hackathon où les équipes utilisent une base de connaissances constituée à partir des documents du cas d’usage, la relient aux politiques, normes et lois applicables, et construisent des agents. Les axes de notation publiés couvrent la qualité de la base, les capacités des agents, l’identification des lacunes de politiques et de standards avec des exemples globaux exacts, l’auditabilité et l’alignement ITU. La page demande aussi de s’appuyer sur le code de référence ITU pour structurer une base vectorisée/distribuée; le brief identifie le dépôt `CrashingGuru/ITUAIReadiness` comme ce code. Le rapport de soumission est limité à cinq pages; le dépôt de code et la base de connaissances font partie des éléments demandés. La vidéo de sept minutes est demandée aux équipes présélectionnées. [Page officielle du Hackathon](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)

Le périmètre de travail retenu suit le brief : fret conteneurisé à Douala/Kribi et transfert vers un opérateur intérieur au Cameroun; l’IoT reste une source de preuve optionnelle. Les affirmations contemporaines sur BESC, SIGMAT, l’autorité de protection des données, les échéances d’application de la loi et l’état de la stratégie IA restent des **hypothèses à vérifier dans des sources primaires**; elles ne doivent pas être présentées comme des faits avant cette vérification.

Le FAQ de la page officielle indique que la précision du prototype n’est pas un critère de notation. Cela rend inutile de faire de l’entraînement d’un classifieur prédictif le chantier principal. Le dépôt possède déjà un artefact expérimental entraîné sur des scénarios synthétiques, non chargé en production; il ne constitue ni un modèle terrain ni une base juridique. Le brief a raison de privilégier des événements de scénario synthétiques et étiquetés `SIMULATED` pour cette soumission. Les crédits Sandbox sont réservés aux équipes sélectionnées; le parcours doit donc rester démontrable sans eux.

## État observé dans ARGOS

| Domaine | État vérifié dans le dépôt | Conséquence pour la soumission |
|---|---|---|
| Base documentaire | Le registre de sources contient un résumé borné de l’Accord OMC et des extraits sélectionnés des articles 9–16, 19, 21, 22 et 25 de la loi camerounaise n° 2024/017, transcrits depuis le scan officiel et contrôlés visuellement. Ce n’est pas le texte complet et les extraits n’ont pas été relus indépendamment par un juriste. | ARGOS démontre une première recherche nationale avec provenance; l’exhaustivité, les textes d’application et la validité juridique restent à vérifier. |
| Recherche | `app/knowledge/rag.py` effectue une recherche lexicale locale dans `.md`, `.txt` et `.rst`, renvoie jusqu’à cinq passages avec chemin et lignes. Le score est lexical, pas une pertinence calibrée. | Bon socle de provenance, mais pas l’ingestion vectorisée/distribuée décrite par l’ITU ni la recherche d’articles juridiques. Vérifier et intégrer le format/code ITU de référence. |
| Catalogue réglementaire | Le code retourne explicitement `TO_VERIFY` pour l’applicabilité. Un enregistrement de catalogue ou une date de vérification ne prouve pas que le texte complet a été ingéré ni que son statut juridique est confirmé. | Chaque constat doit citer le texte et le passage exacts, avec juridiction, version et statut contrôlés. |
| Agents | Les capacités produit comprennent `iot_monitor`, `gps_route`, `risk_assessor`, `knowledge_retriever`, `transport_regulatory` et `port_intelligence`. Quatre capacités `policy_*` ont été ajoutées, chacune avec mandat simulé, faits visibles et chemins de sources autorisés séparés. | Les rôles peuvent être rejoués séparément; leurs résultats restent une simulation et leur qualité juridique n’est pas validée par un tiers. |
| Scénarios et décisions | Les outils de risque et de route sont principalement déterministes. La documentation montre des tests avec fournisseur simulé et journalisation des traces; elle précise que cela ne prouve pas le fonctionnement d’un service externe ou de PostgreSQL en production. | Il faut présenter des relectures étape par étape, les informations vues par chaque rôle, les citations, les divergences et l’intervention humaine. |
| Journalisation | Une migration crée `ai_agent_runs`; le schéma documenté conserve des références d’acteur, statut, agents et sources, sans texte de question ni chaîne de pensée. L’état réel de la migration et du journal en environnement de soumission n’a pas été vérifié ici. | Ajouter un résumé de justification exploitable, les passages, incertitudes et statut de revue humaine; produire une trace de démonstration reproductible. |
| Y.3172 | Le rapport bilingue reprend désormais `C = Collector / collecteur` et décrit les composants ARGOS associés aux nœuds. | Le mapping situe l’architecture; il ne vaut pas certification et le runtime n’implémente pas un système de gestion ML conforme à Y.3172. [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en) |
| AI Readiness | Les rapports mentionnent AI Readiness 2.0, mais ne produisent pas une évaluation structurée étayée par des preuves. | Cartographier les dimensions pertinentes avec composants et preuves réelles; ne pas inventer de score. [Rapport ITU AI Ready](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf) |
| Données d’entraînement | Le dépôt distingue déjà les scénarios synthétiques des données terrain. Aucun corpus d’entraînement de règles douanières n’est un substitut à la base documentaire. | Garder le classifieur en travail futur. Construire et évaluer le corpus de politiques et des scénarios d’essai. |
| Produit existant | L’application ARGOS suit des conteneurs et télémétrie, calcule des événements/ETA et applique des contrôles d’accès. | Conserver l’IoT comme source de preuve optionnelle dans les scénarios; le repositionner derrière la démonstration de connaissance et de coordination. |

### Les quatre agents du brief sont une cible, pas un état existant

Le brief propose : (A1) opérateur/logisticien, (A2) douane et autorité portuaire, (A3) protection des données et cybersécurité, (A4) conseiller juridique neutre, avec un coordinateur déterministe. Le scénario ARGOS met en œuvre une première version de ces rôles : les recherches de politique sont séparées par partition, les faits transmis varient par rôle, et le partage de localisation passe en attente de revue humaine. Le corpus demeure étroit, les désaccords ne sont pas encore évalués sur un jeu de référence, et les rôles sont **simulés**; ils ne représentent ni n’engagent officiellement une administration.

### Points du brief à ne pas reprendre tels quels

- Les affirmations datées sur BESC, SIGMAT, CAMCIS/SYDONIA, la loi 2024/017, l’autorité de contrôle, la stratégie nationale IA et les dates OMC sont explicitement rapportées dans le brief à partir de sources secondaires ou de vérifications incomplètes. Avant citation, obtenir le document primaire et le passage pertinent; sinon inscrire `TO_VERIFY` ou écarter l’hypothèse.
- Le brief appelle « exigence » certains éléments d’architecture (quatre agents, scénarios en six étapes, cible de 30–40 sources). Ce sont des choix de conception proposés par l’équipe, pas des obligations explicitement établies par la page officielle. La qualité et la pertinence des preuves comptent davantage que le volume brut de documents.
- La page de l’événement parle de traces de raisonnement/auditabilité. ARGOS peut conserver un **résumé de justification** (faits utilisés, règles/passages cités, conclusion, incertitudes, outil appelé, approbation humaine), sans enregistrer la chaîne de pensée interne privée du modèle.
- L’équipe a confirmé l’inscription. Les crédits Sandbox ne sont pas présumés disponibles; le scénario fonctionne sans eux. Confirmer l’heure du mentorat sur l’invitation et demander aux organisateurs les précisions encore ouvertes sur les traces attendues.

## Matrice des écarts et critères de clôture

| ID / priorité | Écart et impact | Action et dépendances | Preuve d’acceptation |
|---|---|---|---|
| G0 — P0 | **Base juridique nationale partielle.** Les articles 9–16, 19, 21, 22 et 25 de la loi n° 2024/017 sont transcrits depuis le scan officiel et contrôlés visuellement, mais le texte complet et les règles d’application ne sont pas intégrés ni revus par un juriste indépendant. | Obtenir une version texte complète contrôlable; valider la transcription, le statut et les textes d’application; intégrer les textes douaniers, portuaires et régionaux pertinents. | Corpus complet versionné avec page/article, relecture indépendante et statut actuel; les réponses distinguent l’extrait partiel de la conclusion juridique. |
| G1 — P0 | **Intégration ITU partielle.** Le notebook officiel de référence est inspecté; ARGOS produit maintenant un export partitionné, mais n’exécute pas FAISS dans le serveur et n’a pas d’index hébergé par l’ITU. | Utiliser l’exporteur avec le notebook pour générer séparément les index vectoriels, documenter leur emplacement et leurs contrôles; garder le RAG local comme mode autonome. | Import Colab reproduit pour chaque partition non vide avec empreintes et citations; aucun hébergement ITU n’est revendiqué sans confirmation. |
| G3 — P0 | **Rôles institutionnels en première version.** Les capacités `policy_*` filtrent les sources par partition, mais ne représentent pas des administrations et ne rendent pas d’avis juridique validé. | Compléter les partitions par corpus vérifié, les faits visibles par rôle, les transferts, révisions et revues humaines. Les outils IoT/GPS/risque restent des capacités de l’opérateur. | Traces indépendantes par étape avec entrées, citations visibles, inconnues, informations non transmises, divergences et décision humaine. |
| G4 — P1 | **Lacunes juridiques non établies.** Une absence dans le catalogue ARGOS ne prouve pas une absence dans le droit. | Pour chaque lacune retenue, citer un texte camerounais/régional ou établir explicitement le périmètre de recherche; ajouter un comparateur mondial primaire et son passage. Tester les hypothèses du brief, ne pas les présupposer. | Registre de 4 à 8 lacunes solides avec deux preuves traçables, ou état « non démontré »; aucun constat juridique sans citation exacte. |
| G5 — P1 | **Scénario progressif présent; escalade et évaluation manquent.** `silent_container_v1` rejoue six étapes synthétiques et place le partage de localisation en attente de revue humaine. | Ajouter le scénario d’escalade et des sorties attendues/réelles; faire ressortir la révision des avis après T4 et vérifier le blocage des transferts. | Rejeu montrant citations, changement d’analyse après nouvel événement, refus correct faute de source et validation humaine. |
| G6 — P1 | **Audit de scénario implémenté; persistance en base à confirmer.** Le rejeu produit une trace complète en JSON; la migration de stockage dédiée n’est pas appliquée/vérifiée sur la base de démonstration. | Appliquer la migration et vérifier droits, durée de conservation, accès et export; réviser le schéma si la politique de conservation exige une purge. | Trace lue depuis la base de démo, puis rejouée depuis un clone propre; accès limité à l’acteur autorisé et rétention documentée. |
| G7 — P1 | **Mapping de normes erroné ou trop déclaratif.** `C = Connectivité` dans les rapports contredit Y.3172; mentionner une norme ne prouve pas conformité. | Corriger `C = Collector / collecteur`; relier SRC, C, PP, M, P, D et SINK à des composants présents; distinguer Y.3172 de AI Readiness; créer une table de preuves/limites, sans score non calculé. | Rapport et démo cohérents avec la recommandation Y.3172 et les dimensions du cadre AI Ready; toute revendication de conformité est retirée sauf preuve. |
| G8 — P1 | **Évaluation de récupération initiale; exactitude juridique et qualité des réponses non évaluées.** Le contrôle courant contient douze requêtes et satisfait 12/12 attentes déclarées de présence/absence de source. | Étendre les cas aux contradictions, versions obsolètes, erreurs de citation, injection documentaire et comparaison des sorties déterministes/Gemini; obtenir une revue métier/juridique indépendante. | Rapport attendu/réel, rappel de sources, refus correct, erreurs observées et revue indépendante; ne pas présenter le 12/12 comme précision juridique. |
| G9 — P1 | **Rapport bilingue au format du modèle produit; identification de l’équipe et revue du dépôt restent à finaliser.** Les deux PDF reprennent la structure et le tableau du formulaire, corrigent `C = Collector` et font deux pages. Les champs responsable, membres et coordonnées restent à compléter par l’équipe. | Vérifier l’identité des membres, les droits d’auteur/licences et l’accès public au dépôt; relire le contenu et faire valider les affirmations juridiques. | Versions finales FR/EN ≤ 5 pages, champs équipe remplis, lien accessible, rapport et preuves reproductibles. |
| G10 — P2 | **Démonstration externe optionnelle.** Le mode Gemini est implémenté mais n’a pas été appelé pendant cette consolidation; les crédits Sandbox et API ne sont pas présumés. | Garder la sortie déterministe disponible; documenter les appels réels Gemini uniquement s’ils sont exécutés sur des faits synthétiques; confirmer auprès des organisateurs le niveau de preuve attendu pour le notebook de référence et les traces. | Démo locale sans crédits externes, plus démonstration Gemini si configurée; modes et provenance distincts. |
| G11 — P2 | **Perspectives transversales du cadre ITU non étayées.** Inclusion, intégration, infrastructure et énergie ne sont pas quantifiées par une simple mention. | Pour les dimensions pertinentes, fournir une preuve courte : français/anglais, interaction humaine, rôle des petites entreprises, coût/latence consommés si mesurés, limites de connectivité et options hors ligne. | Table de correspondance aux perspectives officielles avec preuve ou lacune assumée pour chacune; aucune mesure inventée. |

### Travail réalisé dans cette consolidation

- L’inscription est marquée **confirmée par l’équipe**; la ligne correspondante n’est plus un blocage de la feuille de route.
- Le manifeste [`knowledge_base/source_register.json`](../knowledge_base/source_register.json) distingue le résumé OMC dérivé d’une source primaire des extraits camerounais transcrits depuis le scan officiel.
- [`wto_trade_facilitation_selected_articles.md`](../knowledge_base/documents/wto_trade_facilitation_selected_articles.md) ajoute un résumé sourcé et limité des articles 4, 7 section 4, 10.4 et 11. C’est un comparateur international, pas un avis d’applicabilité nationale.
- `app/knowledge/sources.py` et l’option de filtrage dans `app/knowledge/rag.py` appliquent des partitions par source vérifiée; `app/agents/institutional.py` enregistre les quatre capacités `policy_*` et retourne `insufficient_evidence` si aucun passage autorisé ne correspond.
- `app/agents/policy_scenario.py` fournit six étapes, quatre rôles simulés, des faits `SIMULATED`, la mise en attente d’un transfert de localisation au T3, des résumés de justification et une revue humaine en attente. Le scénario est accessible par `POST /api/ai/policy-scenarios/silent_container_v1/run` et par `scripts/run_policy_scenario.py`.
- `migrations/20261102_policy_scenario_runs.sql` et `app/agents/policy_scenario_audit.py` ajoutent une trace JSON par rejeu; il faut appliquer la migration à la base de démonstration pour obtenir une persistance confirmée.
- Le dépôt ITU et son notebook Colab ont été inspectés. `scripts/export_itu_readiness_kb.py` fournit maintenant une passerelle d’export par partition avec manifeste et SHA-256; le mode vectoriel est généré dans Colab et n’est ni exécuté dans Flask ni hébergé sur un service ITU. Voir [la note d’intégration](ITU_AI_READINESS_REFERENCE_INTEGRATION.md).
- `scripts/evaluate_policy_kb.py` applique douze requêtes de contrôle; l’exécution locale a satisfait les attentes de présence/absence définies. Cette mesure porte uniquement sur la récupération attendue de sources, pas sur une validation juridique générale.
- Les rapports du modèle sont rendus en [`ARGOS_Template_Structure_FR.pdf`](submissions/ARGOS_Template_Structure_FR.pdf) et [`ARGOS_Template_Structure_EN.pdf`](submissions/ARGOS_Template_Structure_EN.pdf); chaque PDF de soumission tient en deux pages, conserve le tableau à quatre colonnes et utilise une mise en page noir et blanc. Les fichiers `.md` restent les sources éditables.
- Le PDF officiel de la loi n° 2024/017 est scanné et l’extraction automatique est inutilisable. Les extraits retenus ont été transcrits manuellement depuis les pages imprimées 2–3 et 7–10 et contrôlés visuellement; le reste de la loi n’est pas indexé et la revue juridique indépendante reste à faire.

## Architecture de démonstration actuelle et prochaine étape

```text
Corpus officiel vérifié + événements de scénario (SIMULATED) + télémétrie ARGOS facultative (DEVICE)
                                  │
                        ingestion et provenance
                                  │
               recherche par rôle / article / juridiction
                                  │
  A1 Opérateur   A2 Douane-Port   A3 Données-Cyber   A4 Conseiller neutre
            \          |              |          /
             coordinateur déterministe et règles de partage
                                  │
              synthèse, lacunes, incertitudes, human gate
                                  │
              journal d’audit exportable et rapport de scénario
```

Les noms des administrations ne doivent apparaître que comme rôles simulés, sauf partenariat ou autorisation attesté. L’IoT constitue une preuve d’événement possible; une mesure de capteur n’établit ni responsabilité juridique, ni infraction, ni conformité réglementaire.

## Plan jusqu’à l’échéance publiée

L’échéance de la page officielle est le **10 novembre 2026**. Les étapes ci-dessous supposent une équipe disponible et une inscription confirmée; en cas de refus ou d’accès impossible au code de référence, noter la limite plutôt que de prétendre à l’intégration.

| Date | Livrable concret | Critère de sortie |
|---|---|---|
| 29 oct. — réalisé | Inscription confirmée par l’équipe; périmètre Douala–yard intérieur; premier registre de sources; scénario, agents à partitions et contrôles de récupération. | Démonstration synthétique relançable sans fournisseur externe; questions juridiques non vérifiées étiquetées. |
| 30–31 oct. | Obtenir et valider d’autres textes primaires camerounais/régionaux; vérifier licences; faire relire les extraits de la loi 2024/017 et leur statut par un juriste local. | Sources versionnées, articles/pages, dates et réserves de revue; pas de réponse réglementaire sans passage cité. |
| 1–2 nov. | Appliquer la migration dédiée à la base de démonstration après vérification de la cible; contrôler l’accès aux traces; importer les partitions dans le notebook ITU sur Colab. | Rejeu lu depuis la base, droits d’accès confirmés et index FAISS reproductible pour chaque partition alimentée. |
| 3–4 nov. | Ajouter un scénario de contradiction/escalade et un jeu de résultats attendus; mesurer les refus, citations, fuites inter-partitions et changements après nouvel événement. | Rapport attendu/réel, erreurs recensées et revue des sorties par un opérateur et un spécialiste juridique. |
| 5–6 nov. | Compléter la table de preuves Y.3172/AI Ready; vérifier secrets/licences; condenser et relire le rapport selon le gabarit et la limite de cinq pages. | PDF bilingue conforme au formulaire, champs équipe renseignés, déclarations alignées sur les preuves. |
| 7 nov. | Faire exécuter clone propre et démonstration par une personne n’ayant pas développé le parcours. | Installation, ingestion/export, scénario et récupération reproductibles avec limites affichées. |
| 8–9 nov. | Revue finale des sources, du dépôt et du rapport; soumettre dès que les validations sont acquises. | Liens accessibles, aucun placeholder, preuve d’envoi archivée. |
| 10 nov. | Marge finale selon l’heure limite communiquée par l’organisateur. | Accusé de réception conservé. |

## Registre initial des sources

Consulté le **29 octobre 2026**. La liste ci-dessous sert à orienter la vérification et ne signifie pas que tous ces textes sont déjà incorporés dans ARGOS.

| Source | Usage dans l’audit | Statut dans ARGOS |
|---|---|---|
| [AI for Good Sandbox Hackathon — UAE, ITU](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/) | Critères, calendrier, format, orientations et accès Sandbox. | Source officielle consultée; inscription de l’équipe confirmée par le responsable ARGOS. |
| [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en) | Vocabulaire de chaîne SRC/C/PP/M/P/D/SINK. | Référence cartographiée de façon erronée dans des rapports (`C`); à corriger. |
| [ITU AI Ready Framework report](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf) | Cadre de préparation et dimensions. | Référencé, mais pas d’évaluation ARGOS basée sur preuves. |
| [Dépôt ITUAIReadiness](https://github.com/CrashingGuru/ITUAIReadiness) | Référence logicielle annoncée par la page de l’événement. | Notebook et licence inspectés; export séparé disponible; index Colab pas encore généré. |
| [Loi camerounaise n° 2024/017 — Présidence du Cameroun](https://www.prc.cm/fr/multimedia/documents/10258-loi-n-2024-017-du-23-12-2024-web) | Texte national candidat pour la protection des données. | Extraits partiels indexés; transcription complète/revue juridique à faire. |
| [Accord de l’OMC sur la facilitation des échanges](https://www.wto.org/English/docs_e/legal_e/tfa-nov14_e.htm) | Comparateur international pour gestion du risque, recours, guichet unique et transit. | Résumé borné indexé avec articles exacts; applicabilité au Cameroun à vérifier. |
| [Convention de Kyoto révisée — OMD](https://www.wcoomd.org/Topics/Facilitation/Instrument%20and%20Tools/Conventions/pf_revised_kyoto_conv) | Comparateur douanier, sous réserve des parties applicables. | À vérifier et intégrer avec statut et licence. |
| [Code des douanes de l’Union européenne — EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=celex%3A32013R0952) | Comparateur de transit/responsabilité; non applicable comme droit camerounais. | À extraire avec articles et juridiction étiquetés comme exemple externe. |

## Décisions d’équipe à prendre sans retarder le travail technique

1. Le cas Douala/Kribi et le transfert intérieur proposé dans le brief deviennent-ils le périmètre de soumission?
2. L’équipe doit-elle obtenir une confirmation écrite additionnelle des instructions de remise, du dépôt et du format final?
3. Qui fournit/valide les sources juridiques, le dépôt public et les droits sur le projet initial?
4. Les rôles A1–A4 restent-ils des institutions simulées, sans représentation officielle?
5. Les organisateurs confirment-ils que des résumés de justification, sources et traces d’outils satisfont l’auditabilité demandée, sans journaliser la chaîne de pensée privée?

## Sources consultées

- [Page officielle AI for Good Sandbox Hackathon UAE](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)
- [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en)
- [ITU AI Ready: Analysis Towards a Standardized Readiness Framework](https://www.itu.int/epublications/publication/ai-ready-analysis-towards-a-standardized-readiness-framework)
- [Présidence du Cameroun — Loi n° 2024/017](https://prc.cm/fr/multimedia/documents/10258-loi-n-2024-017-du-23-12-2024-web)
- [WTO Trade Facilitation Agreement](https://www.wto.org/English/docs_e/legal_e/tfa-nov14_e.htm)
- [WCO Revised Kyoto Convention](https://www.wcoomd.org/Topics/Facilitation/Instrument%20and%20Tools/Conventions/pf_revised_kyoto_conv)
- [Référentiel logiciel ITUAIReadiness](https://github.com/CrashingGuru/ITUAIReadiness)
