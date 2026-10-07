# Yimba

Yimba est une plateforme de **veille d'opinion et d'émotions en ligne** : elle collecte des publications par des API
officielles, les analyse (langue, sentiment, émotion) et alerte quand l'opinion se dégrade, pour éclairer la décision.

## Organisation du dépôt

```
yimba/
├── backend/             API, workers de collecte et d'analyse (Python) — voir backend/README.md
├── frontend/            interface web (à venir) — voir frontend/README.md
├── analytics/           dbt (marts), Pandera (qualité), Superset (tableaux de bord)
├── docs/                architecture (docs/ARCHITECTURE.md)
├── legacy/              anciens gabarits de rapports, conservés pour référence
├── docker-compose.yaml  toute la pile, services optionnels derrière des profils
├── .env.example         configuration de la pile (copier en .env)
└── Makefile             commandes communes (make help)
```

Chaque application a ses dépendances, son image Docker et son workflow de CI, déclenché seulement quand ses fichiers
changent.

## Démarrage

Prérequis : Docker Engine 25 et Compose 2.24, ou plus récents. La pile de base tient dans 2 CPU et 1 Go de RAM ; prévoir 2 Go de
plus avec le modèle transformers. Pour développer le backend sans Docker : Python 3.12 et
[Poetry](https://python-poetry.org) (voir `backend/README.md`).

**1. Configurer**

```sh
cp .env.example .env
```

À renseigner au minimum dans `.env` :

| Variable | Pourquoi |
|---|---|
| `POSTGRES_PASSWORD` | mot de passe de la base |
| `AUTHOR_HASH_SALT` | sel des empreintes d'auteurs ; obligatoire en production, à ne plus jamais changer |
| `API_AUTH_URL_BASE` | adresse du service d'authentification : chaque requête de l'API y vérifie le jeton |
| `CORS_ALLOW_ORIGINS` | origines autorisées (le frontend) |
| `FLOWER_BASIC_AUTH` | identifiants de Flower, si on le lance |

La presse (`news`, `gdelt`) se collecte sans clé. YouTube, Bluesky, Facebook et Instagram s'activent en renseignant
leurs identifiants (voir `backend/README.md`).

**2. Lancer**

```sh
make run          # ou : docker compose up -d --build
```

La migration de la base s'applique d'abord, puis l'API, le worker et beat démarrent. L'API écoute sur
`http://localhost:8800` (documentation sur `/docs`, sonde `/@ping`).

**3. Créer une veille**, avec un jeton délivré par le service d'authentification :

```sh
curl -X POST http://localhost:8800/watches \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name": "Santé", "keywords": ["vaccination"], "sources": ["news", "gdelt"], "frequency_minutes": 60}'
```

Beat planifie la collecte dans la minute ; les résultats arrivent sur `/watches/{id}/mentions`, `/stats` et `/alerts`.
Pour collecter tout de suite : `docker compose exec worker python -m yimba.entrypoints.cli collect <watch_id> news`.

**4. Arrêter** : `make down` (les données restent dans les volumes ; `docker compose down -v` les efface).

### Ressources

Valeurs par défaut, mesurées sur la pile en fonctionnement ; chaque conteneur est plafonné (mémoire et CPU) et ses
journaux sont limités à 3 × 10 Mo.

| Service | Mémoire mesurée | Plafond | Réglage |
|---|---|---|---|
| api | ~90 Mo | 384 Mo, 1 CPU | — |
| worker (lexique) | ~120 Mo | `WORKER_MEMORY_LIMIT` (2 Go), `WORKER_CPUS` (2) | `WORKER_CONCURRENCY` (1) |
| worker (transformers) | ~770 Mo | idem | `WORKER_TORCH_THREADS` (2) |
| beat | ~85 Mo | 128 Mo | — |
| postgres | 30 à 120 Mo | 512 Mo | 50 connexions, `shared_buffers` 128 Mo |
| redis | ~10 Mo | 128 Mo | file seulement : ni sauvegarde ni éviction |
| flower (`make monitoring`) | ~85 Mo | 192 Mo | lancé à la demande |
| mlflow (`make mlflow`) | ~370 Mo | 768 Mo | 1 processus web, tâches de fond désactivées (2,2 Go sinon) |
| superset (`make dashboards`) | ~200 Mo | 768 Mo | 1 processus, 4 threads |
| label-studio (`make annotation`) | 250 à 470 Mo | 1 Go | — |
| analytics (`make analytics`) | ponctuel | 512 Mo | `DBT_THREADS` (2) |

Pour traiter plus de veilles en parallèle : augmenter `WORKER_CONCURRENCY` et `WORKER_CPUS` ensemble (avec transformers,
garder `WORKER_TORCH_THREADS × WORKER_CONCURRENCY ≈ WORKER_CPUS`).

## Outils (open source, auto-hébergés, chacun derrière un profil `docker compose`)

| Besoin | Outil (licence) | Lancer | Adresse |
|---|---|---|---|
| Suivi des tâches | Flower (BSD) | `make monitoring` | http://localhost:5555 |
| Erreurs applicatives | GlitchTip (MIT) | `make observability` | http://localhost:8000 |
| Transformations SQL | dbt-core (Apache 2.0) | `make analytics` | schéma `analytics` |
| Qualité des données | Pandera (MIT) + tests dbt | `make analytics` | sortie de la commande |
| Tableaux de bord | Apache Superset (Apache 2.0) | `make dashboards` | http://localhost:8088 |
| Annotation du corpus | Label Studio Community (Apache 2.0) | `make annotation` | http://localhost:8080 |
| Expériences et versions de modèles | MLflow (Apache 2.0) | `make mlflow` | http://localhost:5000 |
| Modèles NLP | transformers (Apache 2.0), torch CPU | `EXTRAS="ml tracking"` (image du worker) puis `ANALYSIS_ENGINE=transformers` | — |

Tous écoutent sur `127.0.0.1` seulement.

**GlitchTip** : créer un compte et un projet, puis `SENTRY_DSN=http://<clé>@glitchtip:8000/<projet>` dans `.env`
(hôte « glitchtip » vu des conteneurs).

**Analytique** : `make analytics` construit et teste les marts avec dbt (`analytics/dbt`), contrôle la fraîcheur des
sources, puis vérifie avec Pandera (`analytics/quality`) les dates manquantes, les langues non reconnues et les sources
en échec des 7 derniers jours. Les marts ne contiennent ni texte ni auteur. Pour relancer toutes les heures :
`ANALYTICS_EVERY_SECONDS=3600 docker compose --profile analytics up -d analytics`.

| Mart | Contenu |
|---|---|
| `fct_sentiment_daily` | mentions par sentiment, jour de publication, veille, source, langue |
| `fct_emotions_daily` | mentions par émotion |
| `fct_collection_health_daily` | collectes réussies / échouées, volumes, dernière erreur, par source |
| `fct_data_quality_daily` | parts de dates manquantes, de langue inconnue, de neutre, sans émotion |
| `fct_alerts`, `dim_watches` | alertes et délai de traitement, veilles |

**Tableaux de bord** : créer le rôle en lecture seule, lancer l'analytique une fois, puis Superset.

```sh
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -v password="'$SUPERSET_READER_PASSWORD'" < analytics/sql/create_superset_reader.sql
make analytics && make dashboards       # la base « Yimba analytics » est déclarée dans Superset
```

**Annotation et évaluation du modèle** : le corpus annoté (français, nouchi) mesure la fiabilité de l'analyse.

```sh
make annotation && make mlflow
cd backend
poetry run yimba annotation config > sentiment.xml           # interface d'étiquetage à coller dans Label Studio
poetry run yimba annotation export <watch_id> --out tasks.json --size 300
# Label Studio : créer un projet, coller sentiment.xml (Settings > Labeling Interface), importer tasks.json,
# annoter, puis Export > JSON. (L'API demande un jeton personnel : les anciens jetons sont désactivés par défaut.)
MLFLOW_TRACKING_URI=http://localhost:5000 poetry run yimba annotation evaluate export.json
MLFLOW_TRACKING_URI=http://localhost:5000 poetry run yimba annotation evaluate export.json --engine transformers
```

Chaque évaluation est enregistrée dans MLflow : moteur, modèle, version du lexique, empreinte du corpus, exactitude,
F1 macro et par classe, matrice de confusion, textes mal classés. L'export n'envoie ni auteur ni lien, et ne pré-remplit
pas les réponses (`--with-predictions` pour le faire, au risque de biaiser le corpus de référence).

**Modèle transformers** : mettre `EXTRAS="ml tracking"` et `ANALYSIS_ENGINE=transformers` dans `.env`, puis
`make run`. Seul le worker reçoit ces dépendances (image `…:dev-ml`, environ 2 Go) ; l'API, beat et Flower gardent
l'image de base (environ 400 Mo). Le modèle est téléchargé une fois dans le volume `models` et chargé une fois par
processus worker. Les évaluations (`yimba annotation evaluate`) se lancent dans le worker :
`docker compose exec worker python -m yimba.entrypoints.cli annotation evaluate /chemin/export.json`.

## Qualité

```sh
make check          # backend : black, isort, flake8, règles d'architecture, tests ; analytics : lint
```

## Ce qui reste à faire avant la production

- Valider le contrat avec le service d'authentification (`AuthServiceAccessControl`, voir sa docstring).
- Valider les collecteurs YouTube, Bluesky, Facebook et Instagram avec de vrais identifiants (testés sur les formats
  documentés des API) ; créer l'application Meta, faire la vérification d'entreprise et l'App Review.
- Annoter un corpus français et nouchi, évaluer lexique et transformers dessus (`yimba annotation`), choisir le moteur.
- Rapports PDF et nuage de mots (anciens gabarits conservés dans `legacy/`).
- Conformité données personnelles (ARTCI) : durée de conservation des mentions, droit d'effacement (les données brutes
  sont déjà purgées après `RAW_RETENTION_DAYS`).
