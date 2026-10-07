# Backend (yimba-api)

API HTTP (FastAPI), workers de collecte et d'analyse (Celery) et planificateur (beat), dans une seule image. Architecture
modulaire, chaque module hexagonal : voir [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

Les commandes ci-dessous se lancent depuis `backend/` ; la pile complète se démarre depuis la racine (`make run`).

## Sources

Uniquement des API officielles : ni scraping, ni revendeur de données. Une source sans identifiants est ignorée.

| Source | API | Identifiants (`.env`) | Ce qui est collecté | Limites |
|---|---|---|---|---|
| `news` | Google News RSS + flux RSS ajoutés | aucun (`NEWS_EXTRA_FEEDS`) | articles | — |
| `gdelt` | GDELT DOC 2.0 (presse mondiale) | aucun (`GDELT_ENABLED`) | titres d'articles des dernières 24 h | une requête toutes les 5 s par adresse IP (nouvel essai automatique) |
| `youtube` | YouTube Data API v3 | `YOUTUBE_API_KEY` | vidéos et commentaires des premières vidéos | 10 000 unités/jour, ~106 par mot-clé : fréquence 6 h ou 24 h |
| `bluesky` | AT Protocol | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | publications | — |
| `facebook` | Graph API (Pages) | `META_ACCESS_TOKEN`, `FACEBOOK_PAGE_IDS` | publications des Pages suivies qui citent un mot-clé, et leurs commentaires | pas de recherche sur tout Facebook ; Pages non gérées : fonctionnalité « Page Public Content Access » |
| `instagram` | Graph API (hashtags) | `META_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID` | publications des dernières 24 h par hashtag | compte professionnel, 30 hashtags distincts par 7 jours, ni commentaires ni auteur |

Les réponses brutes des API sont gardées dans `raw_items` (une ligne par publication, mise à jour à chaque passage) pour
pouvoir corriger une conversion après coup ; elles contiennent des données personnelles en clair et sont supprimées après
`RAW_RETENTION_DAYS` jours sans être revues.

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| POST, GET | `/watches` | créer une veille, lister les siennes |
| GET, PATCH, DELETE | `/watches/{id}` | consulter, modifier, supprimer |
| GET | `/watches/{id}/mentions` | mentions (filtres : source, langue, sentiment, émotion, dates, texte) |
| GET | `/watches/{id}/stats` | totaux et séries (`group_by=day\|source\|language`) |
| GET | `/watches/{id}/alerts` | alertes levées |
| POST | `/watches/{id}/alerts/{alert_id}/acknowledge` | marquer une alerte comme traitée |
| GET | `/@ping` | sonde de vie |

Chaque route exige `Authorization: Bearer <token>` et une permission (voir `appdesc.yml`). Une veille n'est visible que
par son propriétaire.

## Développement

En local, sans Docker (la configuration est lue dans le `.env` de la racine, puis dans `backend/.env` s'il existe) :

```sh
make install                         # poetry install
poetry run yimba db-upgrade          # DATABASE_URL pointe par défaut sur un fichier SQLite
poetry run yimba api --reload
poetry run yimba worker              # nécessite Redis
poetry run yimba beat
poetry run yimba flower              # http://localhost:5555
poetry run yimba collect <watch_id> news   # collecter une source tout de suite, sans file d'attente
```

Vérifications :

```sh
make check          # black, isort, flake8, règles d'architecture, tests
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/yimba_test make tests   # tests sur PostgreSQL
```

## Image Docker (`backend/Dockerfile`)

Une image, trois rôles (`api` par défaut, `worker`, `beat`), construite en deux étapes : Poetry installe les
dépendances verrouillées (`poetry.lock`) dans un environnement isolé, l'image finale ne garde que cet environnement et
le code, déjà compilés en bytecode, et tourne en utilisateur non privilégié. Le contexte de construction ne contient que
le nécessaire (`.dockerignore` en liste blanche : ni `.env`, ni tests, ni `.git`). La CI construit et teste l'image à
chaque push ; la publication sur GHCR n'a lieu qu'après une CI réussie (image de base et variante `-ml`, plus une
étiquette par commit).

