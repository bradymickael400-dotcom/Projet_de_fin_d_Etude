# Utilisation du code de référence ITU AI Readiness dans ARGOS

**Vérifié le 29 octobre 2026**

Le dépôt [ITUAIReadiness](https://github.com/CrashingGuru/ITUAIReadiness) est public et sous licence MIT. Son README est très court; le dépôt contient notamment `Colab Free Tier LLM Notebook.ipynb` et `simulation/`. L’analyse directe du notebook montre un parcours Colab qui lit PDF/TXT/Markdown, découpe les textes, calcule des embeddings avec `sentence-transformers/all-MiniLM-L6-v2`, crée un index FAISS local et interroge un petit modèle GGUF avec un prompt fondé sur les passages retrouvés. Ce notebook est un exemple de RAG local, pas un service ITU hébergé ni un composant directement déployé dans le serveur ARGOS.

ARGOS l’intègre à son flux par un exporteur qui sélectionne exclusivement les sources du registre marquées `VERIFIED_PRIMARY_REFERENCE`, `VERIFIED_PRIMARY_EXCERPT_MANUALLY_TRANSCRIBED` ou `VERIFIED_SUMMARY_OF_PRIMARY`, crée un dossier de documents séparé pour chaque rôle, et joint un manifeste avec URL, juridiction, statut et empreinte SHA-256 :

```bash
.venv/bin/python scripts/export_itu_readiness_kb.py --output-dir /tmp/argos_itu_export
```

Chaque rôle peut être importé séparément dans l’entrée documentaire du notebook et son index FAISS doit rester séparé. Le notebook seul n’impose ni autorisations ARGOS ni partage conditionnel entre institutions; le serveur ARGOS applique ces partitions avant la recherche. L’exporteur n’envoie aucun document à Google Drive, Colab, Gemini ou un service ITU. Une personne doit choisir l’espace Colab, les paramètres, le modèle local et les conditions de conservation.

Le corpus actuel reste réduit : l’Accord OMC est représenté par un résumé borné de dispositions officielles; la loi camerounaise n° 2024/017 par des extraits sélectionnés transcrits et contrôlés visuellement depuis le scan officiel. Ce n’est ni le texte complet ni une revue juridique indépendante. Seuls ces extraits camerounais sont exportés vers les partitions protection des données et conseiller juridique; ils ne sont pas copiés dans les partitions opérateur ou douane-port.

L’intégration présente une passerelle reproductible vers le workflow de référence; elle ne signifie pas que l’index vectoriel du notebook a déjà été construit, qu’il est hébergé par l’ITU, ou que sa réponse est prête pour un usage réglementaire. Le runtime de démonstration de cette version conserve le RAG lexical local, dont les citations de lignes sont plus faciles à relire. Les douze requêtes de contrôle et le scénario restent reproductibles sans Colab, GPU, compte externe ou crédit Sandbox.
