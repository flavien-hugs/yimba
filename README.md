# yimba-api

Yimba est une plateforme de **veille d'opinion et d'émotions en ligne** : elle collecte des publications par des API
officielles, les analyse (langue, sentiment, émotion) et alerte quand l'opinion se dégrade, pour éclairer la décision.

L'architecture est décrite dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Sources

Uniquement des API officielles : ni scraping, ni revendeur de données. Une source sans identifiants est ignorée.

| Source | API | Identifiants (`.env`) | Ce qui est collecté | Limites |
|---|---|---|---|---|
| `news` | Google News RSS + flux RSS ajoutés | aucun (`NEWS_EXTRA_FEEDS`) | articles | — |
| `youtube` | YouTube Data API v3 | `YOUTUBE_API_KEY` | vidéos et commentaires des premières vidéos | 10 000 unités/jour, ~106 par mot-clé : fréquence 6 h ou 24 h |
| `bluesky` | AT Protocol | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | publications | — |

Les réponses brutes des API sont gardées dans `raw_items` (une ligne par publication, mise à jour à chaque passage) pour
pouvoir corriger une conversion après coup ; elles contiennent des données personnelles en clair et sont supprimées après
`RAW_RETENTION_DAYS` jours sans être revues.

## Démarrage

Prérequis : Python 3.12, [Poetry](https://python-poetry.org), Docker.

```sh
cp .env.example .env         # puis renseigner les valeurs
make run                     # api + worker + beat + flower + postgres + redis, migrations incluses (service migrate)
```

L'API écoute sur `http://localhost:8800` (documentation sur `/docs`), Flower (suivi des tâches Celery) sur
`http://localhost:5555` avec `FLOWER_BASIC_AUTH`.

Suivi des erreurs avec GlitchTip (open source, compatible Sentry), optionnel :

```sh
docker compose --profile observability up -d    # http://localhost:8000, créer un compte puis un projet
# puis SENTRY_DSN=http://<clé>@glitchtip:8000/<projet> dans .env (hôte « glitchtip » vu des conteneurs)
```

En local, sans Docker :

```sh
make install
poetry run yimba db-upgrade          # DATABASE_URL pointe par défaut sur un fichier SQLite
poetry run yimba api --reload
poetry run yimba worker              # nécessite Redis
poetry run yimba beat
poetry run yimba flower              # http://localhost:5555
poetry run yimba collect <watch_id> news   # collecter une source tout de suite, sans file d'attente
```

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

## Qualité

```sh
make check          # black, isort, flake8, règles d'architecture, tests
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/yimba_test make tests   # tests sur PostgreSQL
```

## Ce qui reste à faire avant la production

- Valider le contrat avec le service d'authentification (`AuthServiceAccessControl`, voir sa docstring).
- Valider les collecteurs YouTube et Bluesky avec de vrais identifiants (testés sur les formats documentés des API).
- Remplacer l'analyse par lexique par un modèle multilingue évalué sur un corpus français et nouchi annoté.
- Rapports PDF et nuage de mots (anciens gabarits conservés dans `legacy/`).
- Conformité données personnelles (ARTCI) : durée de conservation des mentions, droit d'effacement (les données brutes
  sont déjà purgées après `RAW_RETENTION_DAYS`).
