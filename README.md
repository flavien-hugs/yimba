# yimba-api

Yimba est une plateforme de **veille d'opinion et d'émotions en ligne** : elle collecte des publications par des API
officielles, les analyse (langue, sentiment, émotion) et alerte quand l'opinion se dégrade, pour éclairer la décision.

L'architecture est décrite dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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

## Démarrage

Prérequis : Python 3.12, [Poetry](https://python-poetry.org), Docker.

```sh
cp .env.example .env         # puis renseigner les valeurs
make run                     # api + worker + beat + flower + postgres + redis, migrations incluses (service migrate)
```

L'API écoute sur `http://localhost:8800` (documentation sur `/docs`), Flower (suivi des tâches Celery) sur
`http://localhost:5555` avec `FLOWER_BASIC_AUTH`.

## Outils (open source, auto-hébergés, chacun derrière un profil `docker compose`)

| Besoin | Outil (licence) | Lancer | Adresse |
|---|---|---|---|
| Suivi des tâches | Flower (BSD) | toujours lancé | http://localhost:5555 |
| Erreurs applicatives | GlitchTip (MIT) | `make observability` | http://localhost:8000 |
| Transformations SQL | dbt-core (Apache 2.0) | `make analytics` | schéma `analytics` |
| Qualité des données | Pandera (MIT) + tests dbt | `make analytics` | sortie de la commande |
| Tableaux de bord | Apache Superset (Apache 2.0) | `make dashboards` | http://localhost:8088 |
| Annotation du corpus | Label Studio Community (Apache 2.0) | `make annotation` | http://localhost:8080 |
| Expériences et versions de modèles | MLflow (Apache 2.0) | `make mlflow` | http://localhost:5000 |
| Modèles NLP | transformers (Apache 2.0), torch CPU | `EXTRAS="ml tracking"` puis `ANALYSIS_ENGINE=transformers` | — |

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

**Modèle transformers** : construire l'image avec `EXTRAS="ml tracking"` et régler `ANALYSIS_ENGINE=transformers`. Le
modèle est téléchargé une fois dans le volume `models` et chargé une fois par processus worker.

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
- Valider les collecteurs YouTube, Bluesky, Facebook et Instagram avec de vrais identifiants (testés sur les formats
  documentés des API) ; créer l'application Meta, faire la vérification d'entreprise et l'App Review.
- Annoter un corpus français et nouchi, évaluer lexique et transformers dessus (`yimba annotation`), choisir le moteur.
- Rapports PDF et nuage de mots (anciens gabarits conservés dans `legacy/`).
- Conformité données personnelles (ARTCI) : durée de conservation des mentions, droit d'effacement (les données brutes
  sont déjà purgées après `RAW_RETENTION_DAYS`).
