# Corpus documentaire ARGOS

Déposez ici uniquement des documents que l'organisation est autorisée à utiliser
(`.md`, `.txt` ou `.rst`). Le moteur RAG lit le contenu local, conserve le chemin
et les lignes comme provenance, et n'invente pas de corpus. Les textes doivent
être associés à `knowledge_base/source_register.json`, avec autorité, juridiction,
version/date, URL, licence, état de vérification et partitions d'accès.

Les capacités institutionnelles ne consultent que les chemins déclarés comme
`VERIFIED_PRIMARY_REFERENCE`, `VERIFIED_PRIMARY_EXCERPT_MANUALLY_TRANSCRIBED` ou `VERIFIED_SUMMARY_OF_PRIMARY` dans ce manifeste. Un catalogue d'URL ou une source
`TO_VERIFY` n'est pas traité comme un texte ingéré. Les documents de l'équipe et
événements synthétiques restent explicitement séparés des sources de droit.

L'Accord OMC présent dans le corpus est un résumé borné d'extraits officiels
cités, destiné à une comparaison internationale. Il ne démontre pas à lui seul
l'applicabilité au Cameroun. La loi camerounaise n° 2024/017 dispose maintenant
d'extraits sélectionnés transcrits et contrôlés visuellement depuis le scan officiel.
Il ne s'agit ni du texte complet ni d'une validation juridique indépendante; les
agents doivent préciser ces limites et renvoyer aux articles/pages utilisés.

Le corpus transport contient maintenant des synthèses bornées pour le secteur
ferroviaire camerounais, le Code communautaire de la Marine marchande CEMAC,
l'Acte OHADA sur le transport routier et des repères douaniers CEMAC, enregistrés
avec leur provenance dans `../source_register.json`. Le PDF scanné de la loi
ferroviaire est archivé dans `../source_files/`. Un inventaire de recherche
`cameroon_transport_law_map.md` liste aussi les textes et procédures à compléter;
son statut `TO_VERIFY` l'empêche d'être présenté comme une source juridique
vérifiée aux capacités institutionnelles.
