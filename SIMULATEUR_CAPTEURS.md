# Simulateur ARGOS avec les capteurs de l'ordinateur

Le script `scripts/simulate_argos_box.py` crée et enrôle automatiquement une
boîte, puis envoie sa télémétrie à ARGOS. Il tente de mesurer le niveau sonore
du microphone avec ALSA, PulseAudio ou PipeWire. Il surveille aussi les commandes
du firmware et peut utiliser la webcam comme détecteur d'ouverture de porte. La
position suit un trajet de démonstration Yaoundé–Awaé–Ayos–Abong-Mbang–Doumé–Bertoua.

## 1. Démarrer la plateforme

À la racine du projet :

```bash
cp -n .env.example .env
```

Dans `.env`, définir au minimum un mot de passe, par exemple :

```dotenv
INITIAL_ADMIN_LOGIN=superadmin
INITIAL_ADMIN_PASSWORD=un-mot-de-passe-solide
```

Puis lancer :

```bash
./start-argos.sh
```

La plateforme locale est disponible sur <http://localhost:5002>. Pour vérifier
les services :

```bash
docker compose ps
```

## 2. Préparer et tester les capteurs

Le simulateur doit être lancé **sur l'ordinateur hôte**, pas dans le conteneur
Docker, afin d'accéder au microphone et à `/sys`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/simulate_argos_box.py --check-sensors
```

Le test active brièvement la webcam. L'image reste dans la mémoire du processus :
elle n'est ni enregistrée ni envoyée à ARGOS.

Autoriser l'accès au microphone dans les réglages de confidentialité du système
si le test indique `microphone inaccessible`. Sous Linux, les sources peuvent
être inspectées avec :

```bash
arecord -L
pactl list short sources
```

Exemples de sélection :

```bash
python scripts/simulate_argos_box.py --check-sensors --audio-backend pulse
python scripts/simulate_argos_box.py --check-sensors --audio-device plughw:0,0
```

### Limite concernant la température

Une sonde CPU, GPU, NVMe ou ACPI mesure la température d'un composant, pas celle
de la pièce. Le simulateur utilise automatiquement une vraie sonde ambiante IIO
ou une sonde `hwmon` explicitement étiquetée `ambient`/`air`. Sans cela, il garde
une température simulée et l'annonce clairement.

Pour une sonde USB/IIO connue :

```bash
python scripts/simulate_argos_box.py --check-sensors \
  --temperature-source /sys/bus/iio/devices/iio:device0/in_temp_input
```

Pour une démonstration avec une température ambiante mesurée séparément :

```bash
python scripts/simulate_argos_box.py --check-sensors --ambient-temperature 26.5
```

La température interne de l'ordinateur peut être utilisée à titre indicatif avec
`--allow-system-temperature`, mais elle ne doit pas être présentée comme une
température ambiante.

### Tester l'ouverture de porte avec la webcam

Par convention de simulation demandée :

- webcam visible et éclairée : porte fermée ;
- webcam complètement recouverte : porte ouverte ;
- mode sécurité actif et porte ouverte : alarme active.

Deux images sombres consécutives sont exigées par défaut pour limiter les faux
positifs. Test :

```bash
python scripts/simulate_argos_box.py --check-sensors --no-microphone
```

La commande affiche la luminosité moyenne entre 0 et 255. Pour choisir une autre
caméra ou ajuster le seuil :

```bash
python scripts/simulate_argos_box.py --check-sensors \
  --camera-device /dev/video2 \
  --camera-dark-threshold 15 \
  --camera-confirmations 2
```

`--no-camera` désactive complètement cette fonctionnalité. Sur Linux, l'utilisateur
doit avoir accès à `/dev/video*` et `ffmpeg` doit être installé.

## 3. Lancer le simulateur

Avec le compte administrateur défini dans `.env` :

```bash
python scripts/simulate_argos_box.py \
  --base-url http://127.0.0.1:5002 \
  --username superadmin \
  --password 'un-mot-de-passe-solide' \
  --duration 1800 \
  --interval 2
```

Pour un test d'une minute, remplacer `--duration 1800` par `--duration 60`.
Interrompre proprement avec `Ctrl+C`. Le terminal affiche le numéro de la boîte,
l'UID du dispositif, les sources physiques détectées et chaque envoi HTTP.

## 4. Voir les données dans ARGOS

1. Ouvrir <http://localhost:5002> et se connecter.
2. Ouvrir **Statistiques** dans le menu.
3. Dans **Temps Réel**, repérer l'UID et le numéro de boîte affichés par le
simulateur. Les colonnes **Température** et **Son** sont actualisées.
4. Ouvrir **Événements** pour voir les mesures persistées et les éventuelles
   alertes déclenchées par les seuils.
5. Le superadministrateur peut aussi ouvrir la liste des **Boîtes noires** pour
   retrouver la boîte créée par la simulation.
6. Dans **Mes Boîtes Noires**, cliquer sur **Consulter** pour afficher la carte
   historique. Un choc supérieur à 5 G est produit près d'Abong-Mbang : le point
   et le segment concernés apparaissent en rouge et sont cliquables.

## 5. Tester les commandes du firmware

Pendant que le simulateur fonctionne, ouvrir la fiche du conteneur ou de la boîte
dans ARGOS. Les interrupteurs de contrôle permettent d'envoyer les commandes de
sécurité, écoute audio, enregistrement audio et détection de flamme. Le simulateur :

1. récupère les commandes en attente à chaque cycle ;
2. applique leur état à la télémétrie suivante ;
3. renvoie un accusé d'exécution à ARGOS ;
4. affiche `[COMMANDE] ... appliquée` dans le terminal.

Les commandes prises en charge sont `ASSIGN_CONTAINER`, `CLEAR_CONTAINER`,
`SET_DISTANCE_THRESHOLD`, `SET_SECURITY_MODE`, `SET_AUDIO_LISTENING`,
`SET_AUDIO_RECORDING`, `SET_FLAME_DETECTION`, `REQUEST_POSITION`,
`REQUEST_STATUS` et `TRIGGER_LOCAL_ALERT`. Les commandes audio modifient les
modes publiés par le firmware simulé ; la mesure du niveau sonore continue à
provenir du microphone.

Pour associer un son au choc d'Abong-Mbang, activer **Enregistrer les sons** dans
la modale **Consulter** avant que le trajet atteigne cette ville. Le simulateur
capture alors environ une seconde au moment du choc et l'envoie dans le stockage
privé ARGOS. Un clic sur l'événement ouvre toutes ses mesures et un lecteur audio
qui télécharge le fichier avec l'authentification de l'utilisateur connecté.

Une vérification directe de l'API est possible avec le jeton de connexion :

```bash
curl -H "Authorization: Bearer VOTRE_JETON" \
  "http://127.0.0.1:5002/api/stats/live"
```
