# Frontend

Interface web de Yimba, à venir. Le framework n'est pas encore choisi ; cette page fixe ce qui ne dépend pas de ce choix.

## Ce que le frontend consomme

- L'API du backend : `http://localhost:8800` en local, schéma OpenAPI sur `/openapi.json` (documentation sur `/docs`).
  Générer le client TypeScript depuis ce schéma plutôt que l'écrire à la main, pour qu'il suive l'API.
- L'authentification : `POST /auth/register`, puis `POST /auth/login` qui renvoie un jeton d'accès (15 min, à envoyer
  en `Authorization: Bearer <jeton>`) et un jeton de rafraîchissement (30 jours). Avant l'expiration, `POST /auth/refresh`
  donne une nouvelle paire (le jeton de rafraîchissement ne sert qu'une fois) ; `POST /auth/logout` ferme la session.
  Garder le jeton d'accès en mémoire plutôt que dans `localStorage`.
- CORS : ajouter l'origine du frontend à `CORS_ALLOW_ORIGINS` dans `.env` (par exemple `http://localhost:5173`).

## Quand il sera créé

1. Le générer dans ce dossier (`frontend/`) avec son propre gestionnaire de paquets et son fichier de verrouillage.
2. Ajouter un `Dockerfile` en plusieurs étapes : construction avec Node, puis service des fichiers statiques
   (nginx ou Caddy) ou serveur Node si le framework fait du rendu côté serveur ; et son `.dockerignore` en liste
   blanche, comme `backend/.dockerignore` (sources, manifeste et verrou du gestionnaire de paquets seulement :
   ni `node_modules`, ni `.env`).
3. Ajouter le service `frontend` à `docker-compose.yaml` (`build: ./frontend`), lié à `127.0.0.1` comme les autres.
4. Ajouter `.github/workflows/frontend.yaml`, déclenché seulement sur `frontend/**` (lint, tests, construction de
   l'image), sur le modèle de `backend.yaml`.
5. Ajouter ses commandes au `Makefile` de la racine (`$(MAKE) -C frontend ...`).
