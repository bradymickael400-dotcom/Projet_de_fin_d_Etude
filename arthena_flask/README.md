# Arthena — Architecture Flask

Squelette de développement prêt à l'emploi pour reconstruire la plateforme
Arthena (prototype HTML) en application Flask multi-rôles, avec base de
données, authentification, et API JSON pour la carte/le classement.

## 1. Arborescence du projet

```
arthena_flask/
├── app/
│   ├── __init__.py            # application factory (create_app)
│   ├── config.py              # config par environnement (dev/test/prod)
│   ├── extensions.py          # instances db, migrate, login_manager, csrf, cors
│   │
│   ├── models/                # UN fichier par domaine métier
│   │   ├── user.py            # User (parent/enseignant/admin/superadmin)
│   │   ├── school.py          # School, SchoolClass, SchoolEvent, SchoolDocument,
│   │   │                      # PendingSchoolRequest
│   │   ├── student.py         # Student
│   │   ├── teacher.py         # Teacher, Schedule, table d'assoc. teacher_school
│   │   ├── academic.py        # Note, Presence, Remark (signalement)
│   │   ├── requests.py        # EnrollmentRequest, TeacherApplication, Message
│   │   ├── payment.py         # Payment
│   │   └── notification.py    # Notification
│   │
│   ├── auth/                  # blueprint : connexion/inscription/déconnexion
│   ├── parent/                # blueprint : carte, élèves, classement, paiement
│   ├── teacher/                # blueprint : multi-écoles, appel, notes, signalement
│   ├── school_admin/          # blueprint : classes, candidatures, inscriptions, bilan
│   ├── superadmin/            # blueprint : supervision, classement, validation écoles
│   ├── api/                   # endpoints JSON (carte Leaflet, classement AJAX)
│   │
│   ├── services/              # LOGIQUE MÉTIER pure, réutilisable et testable
│   │   ├── ranking.py         # calcul du score / classement national
│   │   ├── geo.py             # distance Haversine, écoles à proximité
│   │   ├── notifications.py   # création de notifications
│   │   └── payments.py        # intégration Mobile Money (à brancher en prod)
│   │
│   ├── utils/
│   │   ├── decorators.py      # @role_required('admin', 'superadmin')
│   │   ├── errors.py          # pages 401/403/404/500
│   │   └── cli.py             # commande `flask seed-db`
│   │
│   ├── templates/             # un sous-dossier par rôle + base.html commun
│   └── static/{css,js,img}/
│
├── migrations/                 # généré par `flask db init` (Alembic)
├── tests/                      # pytest : test_auth.py, test_ranking.py, conftest.py
├── instance/                   # config locale + fichiers uploadés (non versionné)
├── requirements.txt
├── .env.example
├── run.py                      # lancement local (flask run / python run.py)
└── wsgi.py                     # point d'entrée production (gunicorn wsgi:app)
```

**Pourquoi cette segmentation ?**
- **Un blueprint par rôle** (`parent`, `teacher`, `school_admin`, `superadmin`)
  reproduit exactement les 4 espaces du prototype HTML : chacun a ses propres
  routes, templates et permissions (`@role_required`), sans se marcher dessus.
- **`services/` sépare la logique métier des routes** : le calcul du
  classement national ou la distance Haversine ne dépendent pas de Flask et
  sont testables unitairement (`tests/test_ranking.py`), puis réutilisés à la
  fois par les vues HTML et par l'API JSON.
- **`models/` un fichier par domaine** évite un unique `models.py` de 800
  lignes et suit le découpage déjà présent dans le prototype (écoles, élèves,
  enseignants, notes/présences, demandes, paiements, notifications).
- **`api/`** isole les routes JSON consommées par le JS (carte Leaflet,
  classement dynamique, appel/notes en AJAX) du rendu HTML classique.

## 2. Étapes de mise en route

```bash
# 1. Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Copier le fichier d'environnement
cp .env.example .env
# → éditer .env : SECRET_KEY, DATABASE_URL (SQLite par défaut en dev)

# 4. Initialiser la base de données (migrations Alembic)
flask db init          # une seule fois
flask db migrate -m "initial schema"
flask db upgrade

# 5. Peupler la base avec les comptes de démonstration
flask seed-db
# → crée parent@demo.cm / admin@demo.cm / prof@demo.cm / super@demo.cm (mdp: demo123)

# 6. Lancer le serveur de développement
flask run
# ou : python run.py
# → http://127.0.0.1:5000
```

## 3. Prochaines étapes de développement (ordre conseillé)

1. **Auth & modèles** (déjà scaffoldés) — vérifier `flask seed-db` puis se
   connecter avec chaque rôle de démo.
2. **Espace Parent** : brancher `templates/parent/*.html` sur le design du
   prototype (carte Leaflet dynamique via `/api/v1/schools/nearby`, onglets
   élève : notes/présences/pension/remarques).
3. **Espace Enseignant** : appel (`POST /enseignant/appel`), saisie de notes
   (`POST /enseignant/notes`), signalement (`POST /enseignant/signalement`),
   candidature multi-écoles (`/enseignant/postuler`).
4. **Espace Admin école** : validation des candidatures/inscriptions, gestion
   des classes et plannings, soumission de bilan (`/ecole/bilan`) qui met à
   jour `taux_reussite` et donc le classement national.
5. **Espace Super Admin** : validation des documents MINESEC, approbation des
   nouvelles écoles (`/superadmin/demandes-ecoles/<id>/approuver`).
6. **Paiement Mobile Money** : remplacer la simulation dans
   `services/payments.py` par les API réelles MTN MoMo Collections / Orange
   Money, avec un webhook de confirmation dans `api/routes.py`.
7. **Upload de documents** (CV, bulletins, pièces MINESEC) : utiliser
   `app.config["UPLOAD_FOLDER"]`, valider extension/taille, stocker le chemin
   en base (`SchoolDocument`, `TeacherApplication.cv_path`).
8. **Notifications temps réel** : `services/notifications.py` écrit déjà en
   base ; ajouter du polling AJAX ou Flask-SocketIO pour le badge en direct.
9. **Déploiement** : passer en PostgreSQL (`DATABASE_URL`), lancer via
   `gunicorn -w 4 wsgi:app`, servir les fichiers statiques via Nginx/CDN.

## 4. Tests

```bash
pytest
```

## 5. Démarrage complet avec Docker et Cloudflare

Copier d'abord `.env.example` vers `.env`, puis définir au minimum
`POSTGRES_PASSWORD` et une `SECRET_KEY` aléatoire d'au moins 32 caractères.
Docker Compose lance PostgreSQL, applique les migrations, démarre Gunicorn, puis
ouvre un Quick Tunnel Cloudflare :

```bash
cp .env.example .env
# Modifier .env sans jamais le publier dans Git
./docker-start.sh
```

Les données de démonstration sont désactivées par défaut
(`SEED_DEMO_DATA=false`). La base PostgreSQL est conservée dans le volume
`arthena_pgdata`. Une base SQLite historique doit être migrée explicitement
avant de remplacer une instance déjà utilisée.

Adresses et commandes utiles :

```bash
./docker-urls.sh              # URL locale et URL Cloudflare
docker compose -f compose.yml logs -f
docker compose -f compose.yml down
```

Le port local par défaut est `5006`. Pour le modifier :

```bash
ARTHENA_PORT=5010 ./docker-start.sh
```

L'URL `trycloudflare.com` est temporaire et change lorsque le conteneur du tunnel
est recréé.

### Envoi des notifications par Gmail

Créer un mot de passe d'application Gmail (ne jamais utiliser le mot de passe
principal), puis renseigner dans `.env` :

```dotenv
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=adresse@gmail.com
MAIL_PASSWORD=mot_de_passe_application
MAIL_DEFAULT_SENDER=adresse@gmail.com
```

Redémarrer le service et vérifier l'envoi :

```bash
docker compose -f compose.yml up -d --build
docker compose -f compose.yml exec web flask test-email destinataire@example.com
```

Les notifications d'inscription, de validation/refus, de notes, d'absences, de
remarques et de paiement confirmé sont alors enregistrées dans l'application et
envoyées par e-mail. Si SMTP est indisponible, l'action métier reste enregistrée
et l'erreur d'envoi est journalisée.

`tests/test_ranking.py` vérifie la formule du classement national (55 %
taux de réussite, 30 % satisfaction parents, 15 % effectif plafonné,
configurable dans `app/config.py`). `tests/test_auth.py` couvre la connexion.
