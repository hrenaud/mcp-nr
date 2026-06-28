# 🔍 Rapport de Review Complète — mcp-nr v2.1.3

**Date** : 2026-06-27
**Version** : 2.1.3 (branch `main`, 2013a5c)
**Couvertures** : Core → 3 MCPs (GreenIT, RGAA, RGESN) → Infrastructure

> **Suivi remédiation** (mis à jour 2026-06-27, branche `fix/infra-parity-and-auth-failsafe`)
>
> Chaque constat est annoté dans la colonne `#` :
>
> - ✅ **Fait** — corrigé et committé
> - ⬜ **À faire** — non encore traité (cf. plan `.superpowers/plans/2026-06-27-review-remediation.md`)
> - 🟦 **Faux positif / vérifié** — analysé, aucune action nécessaire (justification en note)
> - ℹ️ **Info** — constat informatif du rapport, rien à corriger
>
> **En cours de remédiation** (branche `fix/infra-parity-and-auth-failsafe`). Faits : #7, #11, #47 (sortie du spécifique GreenIT de `core` + message `validate_themes` générique) ; convergence infra #19/#41/#44 + fail-safe auth (**hors review**). Le reste **à faire**. Voir [§8 Travaux additionnels](#8-travaux-additionnels-hors-review).

---

## Sommaire

1. [Core (mcp_ref_core)](#1-core)
2. [MCP GreenIT](#2-mcp-greenit)
3. [MCP RGAA](#3-mcp-rgaa)
4. [MCP RGESN](#4-mcp-rgesen)
5. [Infrastructure (Docker, CI, scripts)](#5-infrastructure)
6. [Violations des règles CLAUDE.md](#6-violations-des-regles-claudemd)
7. [Synthèse et priorités](#7-synthese-et-priorites)

---

## 1. Core (`mcp_ref_core`)

### 1.1 `auth.py` — Gestion des tokens

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #    | Fichier:Ligne   | Problème                                                                                                                                                                                                                                                                                                                                                                                           | Gravité |
| ---- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| ⬜ 1 | auth.py:104-133 | **`DynamicTokenVerifier.__init__`** : `charger_tokens()` échoue silencieusement si le fichier est corrompu (`json.load` lève une exception → logger.error → retourne `{}`). Le verifier est alors vide → **aucun token valide**. _(Note : le fail-safe auth ajouté empêche désormais de **servir** en HTTP sans token — atténue l'impact, mais le chargement silencieux lui-même reste à durcir.)_ | Moyen   |
| ⬜ 2 | auth.py:98-101  | **Import dynamique `AccessToken = None`** : si `fastmcp.server.auth.AccessToken` est introuvable au runtime, `DynamicTokenVerifier.verify_token()` (ligne 127) fait `AccessToken(...)` → **`TypeError: 'NoneType' object is not callable`**.                                                                                                                                                       | Moyen   |
| ⬜ 3 | auth.py:196-208 | **`update()`** ne valide pas `name` (peut être chaîne vide) ni `expires_days` (`<= 0` passe sans rejection). **No-input de validation**.                                                                                                                                                                                                                                                           | Faible  |
| ⬜ 4 | auth.py:160-177 | **`list_all()`** et **`get_by_id()`** : scan linéaire O(n) sur **tous** les tokens du fichier. Si 10 000 tokens, chaque appel est lent.                                                                                                                                                                                                                                                            | Faible  |

<!-- INVALID_SECTION_END -->

### 1.2 `routes.py` — Routes HTTP

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #    | Fichier:Ligne     | Problème                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Gravité  |
| ---- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ⬜ 5 | routes.py:533     | **`_http_homepage`** importe `charger_cache` de `data` **en runtime** (à l'intérieur de la fonction). Si `data.py` n'est pas dans le module path → **`ImportError`**.                                                                                                                                                                                                                                                                                                                     | Faible   |
| ⬜ 6 | routes.py:77-527  | **Template d'installation shell** : `.replace("__MCP_ID__", mcp_id)` injecte une variable utilisateur dans du bash. Si `mcp_id` contient `__` (ex: `my__mcp`), `.replace("__BASE_URL__", ...)` peut être corrompu → **injection de code arbitraire dans le script**. (IDs actuels "greenit"/"rgaa"/"rgesen" sont sûrs.)                                                                                                                                                                   | Moyen    |
| ✅ 7 | routes.py:727-839 | **Définition d'outils en double** : `routes._greenit_tool_definitions()` redéfinit les 9 outils de `greenit_mcp.py`. **18 points de failure** au lieu de 9. _(Fait Task 1 : fonction déplacée dans `greenit_mcp.py`, `core` exposant un défaut neutre. La déduplication restante name/desc/schema vs décorateurs `@mcp.tool` est traitée par Task 3.)_                                                                                                                                    | **Haut** |
| 🟦 8 | routes.py:845-920 | **`_greenit_guide_extra_sections`** défini dans `routes.py` mais **jamais utilisé** par `greenit_mcp.py` (qui ne passe pas de `guide_extra_sections_fn` à `factory.create_mcp()`). Le `/guide` GreenIT n'affiche **PAS** la section EcoIndex. _(Faux positif : vérifié, la section EcoIndex est bien rendue via le défaut du core. Amélioration archi désormais **faite** (Task 1) : `_greenit_guide_extra_sections` déplacée dans `greenit_mcp.py` et injectée explicitement, cf. #13.)_ | **Haut** |

<!-- INVALID_SECTION_END -->

### 1.3 `factory.py` — Factory

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne    | Problème                                                                                                                                                                                  | Gravité |
| ----- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| ⬜ 9  | factory.py:18-20 | **`DynamicTokenVerifier` créé à chaque `create_mcp()`** : si un process recrée l'instance (reload, reimport), les token loaders sont recréés. **Pas de singleton**.                       | Faible  |
| ℹ️ 10 | factory.py:33-51 | **Routes HTTP non注册 si `MCP_TRANSPORT != "http"`** : le transport stdio ne expose **aucune** route HTTP. `--health` marche mais `/guide` et `/` non. **C'est le comportement attendu**. | Info    |

<!-- INVALID_SECTION_END -->

### 1.4 `_helpers.py` — Helpers de validation

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne  | Problème                                                                                                                                                                                                                                                         | Gravité  |
| ----- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ✅ 11 | _helpers.py:26 | **`validate_themes` référence `"rgaa_statistiques"`** dans le message d'erreur : `"Consulter rgaa_statistiques pour la liste complète."`. **Le CORE ne devrait PAS connaître les noms de MCPs spécifiques**. Direct violation de la règle "core = code partagé". | **Haut** |

<!-- INVALID_SECTION_END -->

---

## 2. MCP GreenIT

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne           | Problème                                                                                                                                                                                                                                                                                                                                                                                 | Gravité  |
| ----- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ⬜ 12 | greenit_mcp.py:62       | **`_REFERENTIEL_VERSION` calculé au load time** : `charger_cache().get("meta", {}).get("version", "")`. Si le cache est vide au démarrage → version vide. **Ne se met pas à jour** après un reload.                                                                                                                                                                                      | Faible   |
| 🟦 13 | greenit_mcp.py:73       | **`factory.create_mcp("GreenIT-Referentiel", ...)`** passe `routes._greenit_tool_definitions` mais **ne passe PAS** `_greenit_guide_extra_sections`. Le guide est générique, pas personnalisé. _(Faux positif fonctionnel — cf. #8 : EcoIndex rendu via le défaut core. Amélioration archi désormais **faite** (Task 1) : fn déplacée dans `greenit_mcp.py` et injectée explicitement.)_ | **Haut** |
| ⬜ 14 | greenit_mcp.py:143-808  | **Double `output_schema`** : chaque outil a `@mcp.tool(output_schema=...)` ET une définition dans `routes._greenit_tool_definitions()`. **18 points de failure** au lieu de 9.                                                                                                                                                                                                           | **Haut** |
| ℹ️ 15 | greenit_mcp.py:816-1016 | **8 prompts** : `audit_ecoindex`, `rapport_impact`, `expliquer_fiche`, `fiches_par_lifecycle`, `checklist_ecoindex`, `ressources_comparaison`, `audit_rapide_greenit`, `audit_par_ressource`. ✅ Couverture complète.                                                                                                                                                                    | Info     |
| ⬜ 16 | data.py:14-26           | **`charger_cache()` non thread-safe** : `global _cache` n'est pas protégé par un lock. En HTTP multithread, 2 threads peuvent écrire `_cache` simultanément. **Worst case**: recalcul redondant (harmless mais inefficace).                                                                                                                                                              | Moyen    |

<!-- INVALID_SECTION_END -->

---

## 3. MCP RGAA

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne        | Problème                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Gravité  |
| ----- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ✅ 17 | rgaa_mcp.py:700-738  | **`rgaa_analyser` : AUCUN rate limiting** sur un outil qui fait un `httpx.Client` vers une URL arbitraire. **Vecteur DOS** : un client malveillant peut faire 1000 requêtes/secondes vers des serveurs arbitraires. _(Fait Task 5 : limiteur fenêtre glissante 10 req/60 s + test `test_rate_limit.py`.)_                                                                                                                                                                                                                                                                                               | **Haut** |
| ✅ 18 | rgaa_mcp.py:727      | **`fetcher_html(url)` : 30s de timeout**. Si un serveur répond lentement, le thread est bloqué 30s. Pas de pool de connexions. **DoS passif** par ralentissement. _(Fait Task 5 : timeout par défaut ramené à 10 s, paramétrable.)_                                                                                                                                                                                                                                                                                                                                                                     | Moyen    |
| 🟦 19 | rgaa_mcp.py:40       | **`TOKENS_FILE = str(_BASE_DIR.parent / "tokens" / "tokens.json")`** : le MCP RGAA est dans `rgaa/files/` mais pointe vers `../tokens/`. **Ne fonctionne pas dans Docker** (WORKDIR = `/app`, fichiers dans `/app/files/`, tokens dans `/app/tokens/` → path relatif `../tokens/` résolu depuis `/app` → `/tokens/` → n'existe pas). _(Faux positif : `_BASE_DIR.parent` = `/app` donc `/app/tokens/` — chemin **correct**. En revanche la **divergence greenit** (qui pointait `_BASE_DIR/tokens`) a été corrigée et la parité des 3 MCP est désormais verrouillée par `tests/test_infra_parity.py`.)_ | **Haut** |
| ⬜ 20 | rgaa_mcp.py:44       | **`_REFERENTIEL_VERSION` calculé au load time** comme GreenIT. Idem.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Faible   |
| ⬜ 21 | rgaa_mcp.py:59-180   | **Double `output_schema`** : chaque outil RGAA a `@mcp.tool(output_schema=...)` ET `_rgaa_tool_definitions()`. **20 points de failure**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                | **Haut** |
| ⬜ 22 | analyseur.py:15-19   | **`fetcher_html`** utilise `httpx.Client(timeout=30, follow_redirects=True)` avec `User-Agent: "Mozilla/5.0 RGAA-MCP/1.0"`. **Pas de User-Agent rotation**. Possible blocage par certains serveurs.                                                                                                                                                                                                                                                                                                                                                                                                     | Faible   |
| ⬜ 23 | analyseur.py:59-73   | **Thème 1 (images)** : ne vérifie **que** `alt` manquant. Ne détecte **PAS** : images décoratives sans `role="presentation"` ou `aria-hidden="true"`, images SVG sans `<title>`, `<input type="image">` sans `alt`. **Faux-NC** sur images décoratives actives.                                                                                                                                                                                                                                                                                                                                         | Moyen    |
| ⬜ 24 | analyseur.py:183-204 | **Thème 9 (titres)** : scan de **TOUT** le HTML pour `<h1>`-`<h6>`, puis vérifie sauts de niveau consécutifs. Si un `<h3>` apparaît dans un aside après un `<h1>` dans le body, le test considère cela comme un **saut** h1→h3. **Faux-NC** sur pages multi-sections.                                                                                                                                                                                                                                                                                                                                   | Moyen    |
| ⬜ 25 | analyseur.py:236-247 | **Thème 12 (skip links)** : cherche `a[href^="#"]` dont le texte contient "contenu", "navigation", etc. Si un lien ancre (`#top`) a un texte différent, **faux-NC**. **AUCUN test** dans `test_analyseur.py` pour ce thème.                                                                                                                                                                                                                                                                                                                                                                             | **Haut** |
| ⬜ 26 | analyseur.py         | **Pas de test pour theme 5.7** (table header `scope`). **Pas de test pour theme 12** (skip links). **Pas de test pour theme 8.5** (`<title>` contenu non vide) et **8.6** (meta charset).                                                                                                                                                                                                                                                                                                                                                                                                               | **Haut** |

<!-- INVALID_SECTION_END -->

---

## 4. MCP RGESN

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne             | Problème                                                                                                                                                                              | Gravité |
| ----- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| ℹ️ 27 | rgesn_mcp.py              | **RGESN : pas d'`output_schema` en double** (contrairement à GreenIT et RGAA). Le MCP a **1 seule définition** par outil. **Architecture plus propre**.                               | Info    |
| ⬜ 28 | rgesn_mcp.py              | **Moins de prompts** (7 vs 8 GreenIT / 11 RGAA). Coverage des workflows plus limitée.                                                                                                 | Faible  |
| ℹ️ 29 | rgesn_mcp.py              | **Aucun outil d'analyse** (pas d'équivalent de `rgaa_analyser`). **C'est correct architecturalement** — RGESN est un référentiel consultatif, pas un analyseur.                       | Info    |
| ⬜ 30 | rgesn_mcp.py              | **`_REFERENTIEL_VERSION` calculé au load time** comme les autres.                                                                                                                     | Faible  |
| ⬜ 31 | rgesn/tests/test_rgesn.py | **Manque de tests de coverage** : les 7 tests de `test_rgesn.py` couvrent les fonctionnalités de base mais **pas les cas limites** (fiches inexistantes, paramètres invalides, etc.). | Moyen   |

<!-- INVALID_SECTION_END -->

---

## 5. Infrastructure

### 5.1 `release.sh`

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne    | Problème                                                                                                                                                                                                                                        | Gravité  |
| ----- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ⬜ 32 | release.sh:25-34 | **`preparer_donnees.py` n'est JAMAIS exécuté** : la release bump la version mais **ne met pas à jour les caches de données**. Les 3 MCPs tournent avec des données **périmées** depuis la dernière exécution manuelle de `preparer_donnees.py`. | **Haut** |
| ⬜ 33 | release.sh:47    | **`git add "${MCPS[@]/%//files/*_mcp.py}"`** : glob pattern `{name//pattern/replacement}` qui échoue silencieusement en bash ancien → fallback hardcodé. **Comportement différent entre bash versions**.                                        | Moyen    |
| ⬜ 34 | release.sh       | **Ne met à jour ni `CHANGELOG.md`, ni `.mcp.json`, ni `README.md`** : alors que CLAUDE.md indique "**règle changelog + tag avant chaque release**".                                                                                             | **Haut** |
| ⬜ 35 | release.sh:19    | **Ne vérifie pas la branche courante** : peut tourner sur `feature/foo` et faire un commit+tag. **Devrait vérifier `git branch --show-current == "main"`**.                                                                                     | Moyen    |

<!-- INVALID_SECTION_END -->

### 5.2 `build.sh` / `local-build.sh`

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne     | Problème                                                                                                              | Gravité |
| ----- | ----------------- | --------------------------------------------------------------------------------------------------------------------- | ------- |
| ℹ️ 36 | local-build.sh:10 | **`--ignore=../tests/test_docker_integration.py`** : ✅ bon de ne pas lancer les tests Docker pendant le build local. | Info    |
| ⬜ 37 | build.sh          | **Ne lance pas les tests** avant le build. `local-build.sh` oui, mais `build.sh` non. **Incohérence entre scripts**.  | Faible  |

<!-- INVALID_SECTION_END -->

### 5.3 CI (`ci.yml`)

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne | Problème                                                                                                                                                                                                                                        | Gravité |
| ----- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| ⬜ 38 | ci.yml:43-45  | **Les tests ne couvrent PAS l'analyseur RGAA** : `pytest rgaa/tests/` inclut `test_analyseur.py` qui teste `BeautifulSoup` (HTML statique). **L'analyseur en production** (si Playwright était utilisé pour DOM rendu) **ne serait PAS testé**. | Moyen   |
| ⬜ 39 | ci.yml:67-68  | **Smoke test Docker** : `docker run --rm ${{ matrix.image }} --health`. **Ne vérifie PAS** que le serveur répond sur le port 8000. `--health` est un argument CLI, pas un HTTP health check.                                                    | Moyen   |
| ℹ️ 40 | ci.yml:14-27  | **`extra_deps` vide pour GreenIT et RGESN** : ✅ correct car ils n'utilisent que fastmcp/httpx. **RGAA a `beautifulsoup4 lxml`** : ✅ correct.                                                                                                  | Info    |

<!-- INVALID_SECTION_END -->

### 5.4 Dockerfiles

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne           | Problème                                                                                                                                                                                                                                                                                                                           | Gravité |
| ----- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| ✅ 41 | greenit/Dockerfile:1-24 | **Correct** : copies spécifiques (`greenit_mcp.py`, `data.py`, `greenit_cache.json`), `EXPOSE 8000`, `HEALTHCHECK` sur CLI. ✅ _(Réécrit en forme canonique pour parité avec rgaa/rgesn : `COPY greenit/files/`, `VOLUME /app/tokens`, `PYTHONPATH=/app` ; `shm_size`/Playwright retirés. Verrouillé par `test_infra_parity.py`.)_ | Info    |
| ℹ️ 42 | rgaa/Dockerfile:1-23    | **`ENV PYTHONPATH=/app`** mais script dans `/app/files/` : Python ajoute `/app/files/` à `sys.path[0]` car c'est le script dir. Les imports `from analyseur import ...` **fonctionnent**. ✅ OK.                                                                                                                                   | Info    |
| ℹ️ 43 | rgaa/Dockerfile:9       | **`COPY rgaa/tokens/.gitkeep ./tokens/.gitkeep`** : crée un dossier `tokens/` vide. **Les vrais tokens mountés en VOLUME** par l'utilisateur. ✅ **Correct**.                                                                                                                                                                      | Info    |
| ✅ 44 | rgesn/Dockerfile        | **Non vérifié** (fichier non lu). Supposé similaire à greenit. _(Vérifié + convergé : identique à greenit/rgaa modulo nom/port. Le `docker-compose.yml` rgesn utilisait un **volume nommé vide** → remplacé par le bind-mount `./tokens:/app/tokens` — **cause racine de l'auth désactivée en prod**.)_                            | ✅      |

<!-- INVALID_SECTION_END -->

### 5.5 `.mcp.json`

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| #     | Fichier:Ligne | Problème                                                                                                                                                                                                                                                                                             | Gravité |
| ----- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 🟦 45 | .mcp.json     | **Versions de serveur non synced** entre les 3 MCPs (chaque `.mcp.json` MCP a sa propre version). **Les configs clients pointent vers des versions différentes**. _(Faux positif : `.mcp.json` est gitignored — config cliente locale, pas un artefact versionné du dépôt. Hors périmètre release.)_ | Moyen   |

<!-- INVALID_SECTION_END -->

---

## 6. Violations des règles CLAUDE.md

| #     | Règle CLAUDE.md                                                                                     | Violation                                                                                                                                                                                                                                                     | Gravité  |
| ----- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ⬜ 46 | **Règle d'architecture** : "**Si deux MCPs ont du code quasi-identique → il doit aller dans core**" | **`output_schema`** redéfini dans les 3 MCPs (9 GreenIT + 10 RGAA = **19 définitions** en double). Devrait être dans `routes.py`. _(= #7/#14/#21/#51)_                                                                                                        | **Haut** |
| ✅ 47 | **Règle d'architecture** : "**core = code partagé**"                                                | **`_helpers.validate_themes`** référence `"rgaa_statistiques"` (nom spécifique à RGAA). Le CORE ne connaît **aucun** MCP. _(Fait Task 2 — = #11)_                                                                                                             | **Haut** |
| 🟦 48 | **Règle d'architecture** : "**variables injectées dans routes.py**"                                 | `greenit_mcp.py` ne passe **pas** `_greenit_guide_extra_sections` à `factory.create_mcp()`. Le guide GreenIT est **générique**. _(Faux positif fonctionnel — cf. #8/#13 : section rendue via défaut core ; amélioration archi désormais **faite** (Task 1).)_ | **Haut** |
| ⬜ 49 | **Règle** : "**Règle changelog + tag avant chaque release**"                                        | `release.sh` ne met **pas à jour** `CHANGELOG.md`. _(= #34)_                                                                                                                                                                                                  | **Haut** |
| ⬜ 50 | **Règle** : "**Tests écrits avant implémentation (TDD)**"                                           | **Themes 5.7 et 12 de l'analyseur RGAA : AUCUN test**. Implémentés mais non couverts par les tests. _(= #25/#26)_                                                                                                                                             | **Haut** |
| ⬜ 51 | **Règle** : "**Simplicité d'abord : pas de duplication**"                                           | **19 points de failure** pour `output_schema`. Un seul changement demanderait de modifier 3 fichiers. _(= #46)_                                                                                                                                               | **Haut** |

---

## 7. Synthèse et priorités

### 7.1 Statistiques

| Gravité       | Count  |
| ------------- | ------ |
| 🔴 **Haut**   | 15     |
| 🟡 **Moyen**  | 16     |
| 🟢 **Faible** | 9      |
| ℹ️ **Info**   | 8      |
| **Total**     | **48** |

#### Avancement remédiation (2026-06-27)

| Statut                        | Count | #s                                                                                    |
| ----------------------------- | ----- | ------------------------------------------------------------------------------------- |
| ✅ **Fait**                   | 7     | 7, 11, 17, 18, 41, 44, 47 (+ fail-safe auth & parité infra, **hors review** — cf. §8) |
| ⬜ **À faire**                | 25    | 1-6, 9, 12, 14, 16, 20-26, 28, 30-39, 46, 49-51                                       |
| 🟦 **Faux positif / vérifié** | 5     | 8, 13, 19, 45, 48                                                                     |
| ℹ️ **Info (rien à corriger)** | 6     | 10, 15, 27, 29, 40, 42, 43                                                            |

> Note : seuls **2 lots** sont livrés (branche `fix/infra-parity-and-auth-failsafe`), tous deux issus de l'**incident prod rgesn**, pas de la review. Les **P0/P1/P2** du §7.2 ci-dessous (output_schema, validate_themes, rate limiting, tests analyseur, release.sh…) restent **à faire**.

### 7.2 Top 5 actions prioritaires

<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->

| Priorité | Description                                                                                                                       | #s        |
| -------- | --------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **P0**   | **Déplacer `output_schema` dans core** : extraire les 19 définitions doubles dans `routes.py` comme `register_tool_definitions()` | 7, 14, 21 |
| **P0**   | **Corriger `_helpers.validate_themes`** : remplacer `"rgaa_statistiques"` par un message générique                                | 11        |
| **P0**   | **Ajouter rate limiting à `rgaa_analyser`** : bloquer > 10 requêtes/minute par IP/token                                           | 17        |
| **P1**   | **Fixer le path des tokens dans Docker RGAA** : `../tokens/` résolu depuis `/app` → `/tokens/` (n'existe pas)                     | 19        |
| **P1**   | **Compléter les tests analyseur RGAA** : ajouter tests pour themes 5.7 (scope) et 12 (skip links)                                 | 25        |
| **P1**   | **`release.sh` : mettre à jour CHANGELOG.md + .mcp.json + tokens**                                                                | 33        |
| **P2**   | **Fixer `_greenit_guide_extra_sections`** : le passer à `factory.create_mcp()`                                                    | 13        |
| **P2**   | **Sécuriser `release.sh`** : vérifier branche main + clean tree                                                                   | 35        |

<!-- INVALID_SECTION_END -->

### 7.3 Points forts

- ✅ **Architecture core/MCP bien pensée** : separation claire des responsabilités
- ✅ **8 themes d'analyse RGAA implémentés** (images, cadres, tableaux, liens, HTML title/lang/charset, titres, formulaires, skip links)
- ✅ **30+ tests d'analyseur RGAA** couvrant la majorité des chemins
- ✅ **Gestion d'authentification par tokens** complète (créer, lister, révoquer, valider)
- ✅ **Scripts de release structurellement corrects** (validation version, tests avant bump)
- ✅ **RGESN : architecture plus propre** (pas de double `output_schema`)
- ✅ **Dockerfiles fonctionnels** avec healthcheck

---

## 8. Travaux additionnels (hors review)

Réalisés sur la branche `fix/infra-parity-and-auth-failsafe` suite à l'**incident prod rgesn** (auth désactivée silencieusement). Ces points n'étaient **pas** dans le rapport ci-dessus.

| Statut | Travail                                                                                                                                                                                                                                                                                       | Fichiers                                                                               |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| ✅     | **Fail-safe auth** : en transport HTTP, `run_main` refuse de **servir** sans token valide (au lieu de basculer silencieusement en mode ouvert). Override explicite `MCP_ALLOW_NO_AUTH=1` avec WARNING. Contrôle au moment de servir → `--health` et les commandes CLI tokens restent intacts. | `core/mcp_ref_core/factory.py`, `core/tests/test_factory_core.py` (`TestAuthFailSafe`) |
| ✅     | **Convergence du périmètre infra** : `Dockerfile` + `docker-compose.yml` des 3 MCP rendus identiques (modulo nom/port/deps). greenit aligné sur la forme canonique ; `shm_size`/Playwright retirés.                                                                                           | `greenit/Dockerfile`, `{greenit,rgaa,rgesn}/docker-compose.yml`                        |
| ✅     | **Bind-mount tokens partout** : `rgesn/docker-compose.yml` — volume nommé vide `rgesn_tokens` remplacé par `./tokens:/app/tokens` (**cause racine** de l'auth désactivée en prod).                                                                                                            | `rgesn/docker-compose.yml`                                                             |
| ✅     | **Chemin tokens greenit corrigé** : `TOKENS_FILE` résolu via `_BASE_DIR.parent / "tokens"` comme rgaa/rgesn (divergence réelle, là où #19 visait à tort rgaa).                                                                                                                                | `greenit/files/greenit_mcp.py`                                                         |
| ✅     | **Test de parité infra** : verrouille l'identité Dockerfile/compose/résolution tokens des 3 MCP ; échoue à toute divergence non autorisée.                                                                                                                                                    | `tests/test_infra_parity.py` (4 tests)                                                 |
| ✅     | **CHANGELOG** : sections Sécurité / Corrigé / Ajouté dans `[Unreleased]`.                                                                                                                                                                                                                     | `CHANGELOG.md`                                                                         |

**Validation** : core 25 ✓, parité 4 ✓, greenit 629 ✓, rgesn 164 ✓, rgaa 468 ✓ (4 échecs `TestHealthFlag`/`TestStartupLogging` **préexistants** et environnementaux — interpréteur sans deps en subprocess, passent en CI).

**Reste côté prod** (action manuelle utilisateur, non touchée) : redéployer rgesn sur le NAS avec le bind-mount.

---

_Ce rapport a été généré par review automatique du code source mcp-nr v2.1.3. Annotations de remédiation ajoutées le 2026-06-27._
