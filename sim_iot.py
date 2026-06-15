import requests
import random
import time

# L'adresse de ton serveur Flask local
URL = "http://127.0.0.1:5002/api/telemetry"

# REMPLACE CECI par un ID_BOITE qui existe réellement dans ta base de données 
# (Par exemple celui que tu viens de vendre/attribuer via le formulaire)
ID_BOITE = "BN-000001" 

print(f"🚀 Lancement de la simulation IoT pour la boîte : {ID_BOITE}")
print("Génération de 25 événements en cours...\n" + "="*50)

for i in range(1, 26):
    # Génération de données aléatoires réalistes
    # Note : On met des bornes qui peuvent dépasser les seuils pour tester les alertes
    payload = {
        "id_boite": ID_BOITE,
        "temperature": round(random.uniform(25.0, 42.0), 1),  # Risque de surchauffe (>32)
        "humidite": round(random.uniform(50.0, 85.0), 1),     # Risque d'humidité (>75)
        "pressions": round(random.uniform(980.0, 1015.0), 1), # Risque de chute (<995)
        "chocs": round(random.uniform(0.0, 8.0), 1),          # Risque de choc (>5)
        "vitesse": round(random.uniform(0.0, 110.0), 1),      # Risque de survitesse (>90)
        "lat": round(random.uniform(3.8, 5.5), 5),            # Coordonnées au Cameroun
        "lon": round(random.uniform(9.7, 11.5), 5)
    }
    
    try:
        # Envoi de la requête POST au format JSON
        response = requests.post(URL, json=payload)
        
        if response.status_code == 201:
            data = response.json()
            alertes = data.get('alerts', [])
            
            # Affichage dans la console
            if alertes:
                print(f"⚠️  [{i}/25] ALERTE DÉCLENCHÉE ! ({len(alertes)} anomalies)")
                for alerte in alertes:
                    print(f"      -> {alerte}")
            else:
                print(f"✅ [{i}/25] Nominal : Temp={payload['temperature']}°C, Choc={payload['chocs']}G")
        else:
            print(f"❌ [{i}/25] Erreur serveur {response.status_code} : {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au serveur. Assure-toi que Flask tourne sur le port 5002.")
        break # Arrête la boucle si le serveur est éteint
        
    # Pause de 2 secondes entre chaque envoi pour simuler le temps réel
    time.sleep(2) 

print("\n" + "="*50)
print("🏁 Simulation terminée ! Va vérifier tes statistiques et événements sur l'application Web.")