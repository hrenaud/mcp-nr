# Guide développeur — MCP GreenIT

Le MCP GreenIT connecte Claude au référentiel des 119 bonnes pratiques d'éco-conception web GreenIT. Vous pouvez explorer les fiches, chercher des recommandations adaptées à votre contexte, et calculer l'EcoIndex d'une page web.

---

## Outils disponibles

### Parcourir le référentiel

**`greenit_lister_fiches`** — Liste toutes les fiches ou filtre par lifecycle, type de ressource, impact ou priorité. Sans filtre, retourne les 119 fiches. Pour le détail d'une fiche, utilisez `greenit_obtenir_fiche_complete`.

```
"Liste toutes les fiches GreenIT"
"Liste les fiches de la phase développement avec un impact >= 4"
"Quelles fiches concernent les économies réseau ?"
```

**`greenit_fiches_prioritaires`** — Fiches triées par score combiné (impact × priorité), filtrable par seuil minimum. Idéal pour identifier les actions à fort effet.

```
"Donne-moi les 10 fiches les plus prioritaires"
"Quelles sont les bonnes pratiques à fort impact et faciles à implémenter ?"
```

**`greenit_chercher_fiche`** — Recherche textuelle avec scoring de pertinence (titre, description, corps, ressources, lifecycle).

```
"Cherche les fiches sur le lazy loading"
"Trouve les recommandations liées aux images"
"Quelles fiches parlent de cache HTTP ?"
```

**`greenit_obtenir_fiche_complete`** — Contenu complet d'une fiche : description détaillée, principes de validation, ressources sauvegardées, cycle de vie.

```
"Donne-moi le détail complet de la fiche RWEB_0049"
"Explique-moi la fiche RWEB_0051 sur le lazy loading"
```

**`greenit_comparer_fiches`** — Compare plusieurs fiches côte à côte avec matrice comparative et classement.

```
"Compare les fiches RWEB_0049, RWEB_0051 et RWEB_0009"
"Quelles différences entre RWEB_0001 et RWEB_0002 ?"
```

**`greenit_obtenir_statistiques`** — Distributions détaillées et top 5 par score combiné.

```
"Donne-moi les statistiques du référentiel GreenIT"
```

**`greenit_lister_lifecycles`** — Les 7 phases du cycle de vie (stratégie, spécification, design, intégration, développement, recette, mise en production) avec leur nombre de fiches. Les identifiants retournés s'utilisent comme filtre `lifecycle` dans `greenit_lister_fiches`.

**`greenit_lister_ressources`** — Les 8 types de ressources sauvegardées (cpu, network, requests, storage, ram, dom, requests, greenhouse) avec leur nombre de fiches. Les identifiants retournés s'utilisent comme filtre `saved_resource` dans `greenit_lister_fiches`.

---

## Calcul EcoIndex avec Playwright

**`greenit_calculer_ecoindex`** — Calcule le score EcoIndex (0-100) et la note (A-G) à partir de 3 métriques : nœuds DOM, requêtes HTTP, poids total en Ko.

Le MCP pilote Playwright automatiquement pour mesurer ces métriques selon le protocole officiel EcoIndex. Demandez simplement à Claude d'auditer une URL :

```
"Calcule l'EcoIndex de https://greenit.fr"

"Utilise Playwright pour mesurer l'EcoIndex de https://mon-site.fr — viewport 1920×1080,
attendre 3 s après chargement, scroller progressivement, attendre 3 s, puis calculer."
```

### Protocole de mesure (appliqué automatiquement par Claude)

1. Ouvrir un contexte Playwright avec viewport **1920×1080** (spec EcoIndex officielle)
2. Naviguer vers la page
3. Attendre **3 secondes**
4. Faire défiler jusqu'en bas **progressivement** (pour déclencher le lazy loading)
5. Attendre **3 secondes**
6. Mesurer : nœuds DOM, requêtes HTTP, poids total en Ko
7. Appeler `greenit_calculer_ecoindex` avec les 3 métriques

### Tableau des grades EcoIndex

| Grade                                                                                                                                          | Score | Couleur |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------- |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#349A47;vertical-align:middle;margin-right:6px"></span>A | > 80  | #349A47 |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#51B84B;vertical-align:middle;margin-right:6px"></span>B | > 70  | #51B84B |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#CADB2A;vertical-align:middle;margin-right:6px"></span>C | > 55  | #CADB2A |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#F6EB15;vertical-align:middle;margin-right:6px"></span>D | > 40  | #F6EB15 |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#FECD06;vertical-align:middle;margin-right:6px"></span>E | > 25  | #FECD06 |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#F99839;vertical-align:middle;margin-right:6px"></span>F | > 10  | #F99839 |
| <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#ED2124;vertical-align:middle;margin-right:6px"></span>G | ≤ 10  | #ED2124 |

---

## Exemples de prompts

```
"Donne moi les bonnes pratiques à appliquer pour réduire l'impact écologique du site greenit.fr"

"Quelles sont les bonnes pratiques prioritaires du référentiel GreenIT ?"

"Calcule l'EcoIndex de https://greenit.fr — utilise Playwright avec le protocole officiel
(viewport 1920×1080, 3 s d'attente avant et après scroll progressif)"

"Compare l'EcoIndex de la page d'accueil et de la page blog de mon-site.fr"

"Quelles fiches GreenIT s'appliquent à un site e-commerce avec beaucoup d'images ?"

"Cherche toutes les fiches sur la réduction des requêtes HTTP et trie-les par priorité"
```

---

## Structure d'une fiche

```json
{
  "num": "RWEB_0051",
  "title": "Utiliser le chargement paresseux",
  "shortDescription": "...",
  "description": "## Description\n\n...",
  "lifecycle": "3-developement",
  "environmental_impact": 5,
  "priority_implementation": 5,
  "saved_resources": ["cpu", "network", "requests"],
  "validations": [
    { "rule": "d'images sans attribut loading=lazy", "maxValue": "0%" }
  ],
  "principes_de_validation": [
    "Le nombre d'images sans attribut loading=lazy est inférieur à 0%"
  ],
  "url": "https://rweb.greenit.fr/fr/fiches/0051"
}
```

Les champs `environmental_impact` et `priority_implementation` sont notés de 1 à 5.
