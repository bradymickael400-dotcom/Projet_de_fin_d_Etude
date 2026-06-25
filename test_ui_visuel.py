#!/usr/bin/env python3
"""
Test E2E visuel avec Playwright (non-headless)
Usage: python test_ui_visuel.py --url http://127.0.0.1:5001

Ce script automatise visuellement le flux décrit :
- connexion superadmin
- navigation vers 'Ventes & Attribution'
- création d'une entreprise + conteneurs
- déconnexion et reconnexion avec le compte créé
- vérification de la présence des conteneurs

Remarques : ajoute des pauses `time.sleep(1)` pour observer les actions.
"""
import time
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_ADMIN_USER = "superadmin"
BASE_ADMIN_PWD  = "admin123"


def run(base_url: str, company_name: str, login: str, password: str, qty: int, container_ids: list[str]):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(10000)

        try:
            print(f"Ouvrir {base_url}")
            page.goto(base_url)
            time.sleep(1)

            # Connexion superadmin
            page.fill('#login-username', BASE_ADMIN_USER)
            page.fill('#login-password', BASE_ADMIN_PWD)
            time.sleep(1)
            page.click("button:has-text('Connexion Sécurisée')")
            time.sleep(2)

            # Naviguer vers Ventes/Attribution (nav id 'nav-sell')
            page.click('#nav-sell')
            time.sleep(1)

            # Remplir le formulaire de vente
            page.fill('#sell-qty', str(qty))
            time.sleep(1)

            # Attendre que les champs d'ID conteneur soient créés
            for i in range(qty):
                sel = f'#sell-container-id-{i}'
                page.wait_for_selector(sel)
                page.fill(sel, container_ids[i])
                time.sleep(1)

            page.fill('#sell-company', company_name)
            page.fill('#sell-location', 'Douala, Cameroon')
            page.fill('#sell-phone', '+237650000000')
            page.fill('#sell-login', login)
            page.fill('#sell-password', password)
            page.fill('#sell-email', f'{login}@example.test')
            page.fill('#sell-niu', 'NIU-TEST-123')
            # choisir abonnement
            page.select_option('#sell-sub', 'monthly')
            time.sleep(1)

            # Cliquer sur Valider
            page.click("button:has-text('Valider la Vente & Créer le Compte')")
            # attendre retour / confirmation
            time.sleep(3)

            # Ouvrir avatar -> Paramètres puis Déconnexion
            page.click('.user-avatar')
            time.sleep(1)
            # Le bouton Déconnexion existe dans la page Paramètres
            page.click("button:has-text('Déconnexion')")
            time.sleep(2)

            # Reconnexion avec le compte créé
            page.fill('#login-username', login)
            page.fill('#login-password', password)
            time.sleep(1)
            page.click("button:has-text('Connexion Sécurisée')")
            time.sleep(3)

            # Vérifier la présence des conteneurs : naviguer vers 'containers'
            page.click('#nav-containers')
            time.sleep(2)

            # Chercher les IDs des conteneurs sur la page
            page_text = page.content()
            found = all(cid in page_text for cid in container_ids)
            if found:
                print('Vérification réussie : conteneurs trouvés dans l interface.')
            else:
                print('Attention : certains conteneurs introuvables dans l interface.')

        except PlaywrightTimeoutError as e:
            print('Timeout lors d une action Playwright:', e)
        finally:
            print('Fin du test visuel — laisser le navigateur ouvert quelques secondes...')
            time.sleep(5)
            context.close()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:5002', help='Base URL de l application')
    parser.add_argument('--company', default='TestCo UI', help='argos')
    parser.add_argument('--login', default='testco', help='argos')
    parser.add_argument('--password', default='testpass123', help='Mot de passe du compte entreprise')
    parser.add_argument('--qty', type=int, default=2, help='Nombre de boîtes à créer')
    parser.add_argument('--containers', nargs='+', default=['CONT-TEST-1','CONT-TEST-2'], help='IDs des conteneurs')
    args = parser.parse_args()
    if len(args.containers) < args.qty:
        print('Veuillez fournir autant d IDs de conteneurs que la quantité (--containers)')
    else:
        run(args.url, args.company, args.login, args.password, args.qty, args.containers)
