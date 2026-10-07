# Frontend

Interface web de Yimba, d'après la [maquette](https://claude.ai/artifact/LzCxfX1mLoP5v5gwzDY73h). Deux applications
partagent les mêmes paquets :

- **l'application utilisateur** (`/`) : tableau de bord d'une veille, conversations, alertes, création et réglages des
  veilles, compte ;
- **l'administration** (`/admin`) : les comptes (rôle, accès, suppression), réservée aux administrateurs.

## Outils

Le strict nécessaire, pour une construction légère :

| Outil | Rôle |
|---|---|
| [SvelteKit 3](https://svelte.dev/docs/kit) (Svelte 5, Vite 8) | les deux applications, en pages statiques (`adapter-static`, mode SPA) |
| [Tailwind CSS 4](https://tailwindcss.com) | styles ; la palette et les composants de la maquette sont dans `packages/ui/src/theme.css` |
| TypeScript, `svelte-check` | types, y compris ceux de l'API |
| [openapi-typescript](https://openapi-ts.dev) | génère les types de l'API depuis `/openapi.json` (aucun code ajouté au navigateur) |
| Vitest | tests unitaires des paquets |
| Prettier | mise en forme |
| [pnpm](https://pnpm.io) (espaces de travail) | dépendances, version fixée par `packageManager` |

Pas de bibliothèque de composants ni de graphiques : les graphiques sont en SVG, les polices (Outfit, Nunito Sans)
sont servies par l'image, sans appel à un service tiers. Au premier chargement, l'application utilisateur transfère
environ 50 Ko de JavaScript et 7 Ko de CSS (compressés), chaque page charge ensuite son propre morceau.

## Organisation

```
frontend/
├── apps/
│   ├── user/            application utilisateur (base /) : Dockerfile, configuration nginx
│   │   └── src/
│   │       ├── lib/         formulaire de veille, carte de conversation, répartitions, veille courante
│   │       └── routes/      connexion, inscription, (app)/ : accueil, paroles, alertes, veilles/, compte
│   └── admin/           administration (base /admin) : Dockerfile, configuration nginx
│       └── src/routes/      connexion, (admin)/ : comptes
├── packages/
│   ├── api/             client de l'API : types générés, appels, session (jetons), messages d'erreur en français
│   └── ui/              thème Tailwind, composants partagés (logo, bande de pagne, baobab, formulaire de connexion,
│                        graphique, champs), formats français (nombres, dates), libellés
├── nginx/               en-têtes de sécurité communs aux deux images
└── Makefile             make help
```

Les applications importent les paquets par leur nom (`@yimba/api`, `@yimba/ui`) ; ceux-ci sont livrés en source,
compilés par l'application qui les utilise.

## Développer

Prérequis : Node 22.17 ou plus récent et pnpm (n'importe quelle version récente : elle passe d'elle-même à celle du
projet). Le backend doit tourner (`make run` à la racine).

```sh
make install       # dépendances, depuis pnpm-lock.yaml
make dev-user      # http://localhost:5173
make dev-admin     # http://localhost:5174/admin
make check         # mise en forme, types, tests, construction : ce que lance la CI
```

En développement, Vite transmet `/api` au backend (`YIMBA_API_URL`, par défaut `http://localhost:8800`), comme nginx
dans l'image : le navigateur ne parle qu'à une seule origine, il n'y a pas de CORS à régler.

Le premier administrateur se crée en ligne de commande (voir le README de la racine) ; les autres comptes s'inscrivent
sur `/inscription`, puis un administrateur peut leur donner le rôle admin sur `/admin`.

### Quand l'API change

```sh
make api-types     # régénère packages/api/src/schema.d.ts depuis http://localhost:8800/openapi.json
make check         # le compilateur signale chaque appel à adapter
```

## Session

- Le jeton d'accès (15 min) reste en mémoire. Le jeton de rafraîchissement va dans `sessionStorage` (fermé avec
  l'onglet) ou, si « Rester connecté·e » est coché, dans `localStorage`.
- Le jeton d'accès est renouvelé 30 s avant son expiration, ou quand l'API le refuse ; un jeton de rafraîchissement ne
  sert qu'une fois, alors les onglets se relaient par un verrou (Web Locks) pour ne jamais présenter le même deux fois.
- Une session par navigateur : se déconnecter dans un onglet déconnecte les autres, et une nouvelle connexion ferme la
  précédente côté API.
- Changer de mot de passe ferme toutes les sessions (règle de l'API) ; l'application reconnecte aussitôt celle en cours.

## Images

Une image par application, chacune avec son propre `Dockerfile` et son propre constructeur :

| Application | Dockerfile | Image | Adresse locale |
|---|---|---|---|
| utilisateur | `apps/user/Dockerfile` | `ghcr.io/flavien-hugs/yimba-frontend-user` | http://localhost:3000 (`FRONTEND_PORT`) |
| administration | `apps/admin/Dockerfile` | `ghcr.io/flavien-hugs/yimba-frontend-admin` | http://localhost:3001/admin (`ADMIN_PORT`) |

`make run` à la racine les construit et les lance (services `frontend` et `admin`). À la main :
`docker build -f apps/user/Dockerfile -t yimba-frontend-user .` depuis `frontend/` (idem avec `admin`).

- Les deux images n'ont rien en commun que la configuration des en-têtes de sécurité (`nginx/`) : chaque `Dockerfile` a
  son contexte (`apps/<app>/Dockerfile.dockerignore`, en liste blanche, sans les sources de l'autre application), donc
  modifier l'administration ne reconstruit pas l'application utilisateur, et chacune n'installe et ne compile que ses
  paquets.
- Chaque application ouvre l'autre par son adresse extérieure, fixée à la construction : `VITE_ADMIN_URL` (lien
  « Administration » des paramètres) et `VITE_USER_URL` (lien « Aller sur Yimba »), en variables `FRONTEND_ADMIN_URL`
  et `FRONTEND_USER_URL` pour compose. Par défaut : les adresses locales ci-dessus. Derrière un même nom de domaine
  (`/` et `/admin`), les valeurs `/admin/` et `/` du `Dockerfile` conviennent.
- Chaque image a son origine : la connexion d'une application n'ouvre pas l'autre, c'est voulu pour l'administration.
- Construction avec Node, puis nginx non privilégié (port 8080, environ 30 Mo par image, 4 Mo de mémoire).
- `/api/` est transmis à `API_UPSTREAM` (par défaut `api:8800`), résolu à chaque requête : nginx démarre même si l'API
  n'est pas prête.
- Les fichiers versionnés (`_app/immutable`) sont mis en cache pour un an, les pages jamais ; fichiers compressés
  d'avance (gzip).
- Chaque page porte sa Content-Security-Policy (scripts limités à ceux de l'application, par empreinte) ; nginx ajoute
  `frame-ancestors 'none'`, `nosniff` et les autres en-têtes.
- `/healthz` sert la sonde de `docker compose`.

La CI (`.github/workflows/frontend.yaml`) vérifie, construit et publie les deux images (variable de dépôt
`FRONTEND_IMAGE` pour changer le début du nom ; `-user` et `-admin` s'y ajoutent) : `main` → `latest`,
`develop` → `dev`, tag git → même tag.

## Écarts avec la maquette

L'interface suit la maquette (couleurs, typographie, écrans, version mobile). Ce que l'API ne fournit pas encore n'est
pas affiché :

| Maquette | Ici | Il faudrait côté API |
|---|---|---|
| Connexion Google, Microsoft, SSO | courriel et mot de passe | un fournisseur OIDC |
| Compte en attente de validation | le compte est actif dès l'inscription | un état « en attente » et sa validation |
| Mot de passe oublié | changement de mot de passe dans « Mon compte » | l'envoi d'un lien par courriel |
| Carte des régions, « De quoi on parle » | faits, mais depuis le texte : les districts sont reconnus par les noms de lieux cités, les sujets sont les mots qui reviennent le plus (pas des thèmes rédigés) | un lieu et des sujets enregistrés à la collecte, par un modèle |
| « Personnes différentes » | nombre d'alertes à traiter | le décompte des auteurs distincts |
| « Corriger l'analyse » | (le corpus s'annote dans Label Studio) | un retour d'annotation par l'API |
| Alertes par courriel | — | l'envoi de courriels |
| Sources X, TikTok, recherche Google | Facebook, Instagram, YouTube, Bluesky, presse en ligne, presse internationale | de nouveaux collecteurs |
