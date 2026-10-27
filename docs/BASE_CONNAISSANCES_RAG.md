# Base de connaissances et RAG

Le moteur `app/knowledge/rag.py` fournit une récupération lexicale locale sans nouvelle dépendance. Il lit les fichiers `.md`, `.txt` et `.rst` sous `KNOWLEDGE_BASE_PATH`, ignore les liens symboliques, borne le nombre et la taille des fichiers, découpe sur les paragraphes et renvoie jusqu'à cinq passages classés par recouvrement lexical.

Chaque passage contient son texte, un chemin relatif, les lignes source et un score lexical indicatif. Ce score n'est ni une probabilité ni une pertinence calibrée. Les références retournées sont jointes à la réponse API et fournies au LLM pour citation. Aucun document réglementaire n'a été ajouté : le seul fichier livré dans le répertoire du corpus explique le processus d'ajout. Aucune réponse réglementaire sourcée n'est donc démontrée.

Avant tout corpus de production, vérifier pour chaque document l'autorité, la juridiction, la version, la date de révision, la licence et le statut courant. Le moteur ne vérifie pas automatiquement ces métadonnées ou la validité juridique; cette tâche reste à établir avant d'émettre des recommandations de conformité.
