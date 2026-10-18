---
source_document: CPEONS D2_D3 TT INFORMATIQUE.pdf
id: situation_04
title: Mise en œuvre et sécurisation d'un réseau local (6e)
type: situation_apprentissage
index: 4
tags:
- situation d'apprentissage
- projet pratique
- pédagogie active
- évaluation
summary: Mise en situation concrète et exemple guidé d'apprentissage pratique pour
  illustrer les compétences.
---

> [📑 Manifest Index](../00_AGENT_MANIFEST.md)

# Exemple de Situation d'Apprentissage 4 : Mise en œuvre et sécurisation d'un réseau local (6e)

# EXEMPLE DE SITUATION D'APPRENTISSAGE

 Savoir-faire disciplinaires o Câbler o Utiliser un logiciel de simulation de réseaux

## **Attitudes :**

o Définir les acronymes spécifiques à l'informatique o Utiliser les termes anglais techniques courants o Communiquer en utilisant le vocabulaire spécifique et le langage adéquat o Respecter les règles et les consignes d'hygiène, de sécurité et d'environnement

## Consignes

Un client demande la mise en place d'un serveur Proxy pour sa structure de travail.

Il t'est demandé de préparer le travail et de tester celui-ci avant sa mise en service en tenant compte du réseau déjà en place dans cette structure.

## Documents fournis aux élèves

Dans ce cas il s'agit plus exactement d'un logiciel Simulateur de réseau v10.3

## Commentaires

Le professeur veillera à faire émerger auprès des élèves les étapes ainsi que les éléments indispensables pour mener à bien cette tâche. Après avoir réalisé le schéma du réseau existant dans cette structure, les élèves construiront celui-ci ainsi que son propre serveur Proxy attaché à un nom de domaine. Les élèves paramètrent ce serveur et en définissent les règles d'accès pour répondre aux demandes du client.

Le professeur demandera aux élèves de réaliser, avant de commencer à résoudre cette tâche, de rechercher à domicile le rôle et les fonctionnalités d'un serveur Proxy. Ils synthétiseront ces recherches dans un document personnel d'au moins une page.

Il est donc indispensable lors de la construction de la demande du client de baliser au mieux les demandes, celles-ci peuvent en effet varier en fonction de la planification de cette séquence.

Il convient également de faire prendre conscience aux élèves de l'importance de vérifier leur travail, en faisant appel à un condisciple par exemple, avant de valider les produits qui seront remis au demandeur.

A titre indicatif, nous reprenons ici une possible structure de travail à mettre en place lors de la préparation et de la réalisation de cette tâche.

① Demander aux élèves de rappeler quelles sont les fonctionnalités d'un serveur Proxy dans un réseau d'entreprise :

- Centraliser les accès au web
- Journaliser ces accès
- Interdire certaines plages horaires
- Autoriser ou interdire certains sites (liste blanche / noire)
- Servir de cache

Ces rôles sont repris ici dans le simulateur, en activant le *Serveur Proxy*. Le navigateur devra définir ce serveur Proxy pour l'utiliser. Il convient lors de l'animation du groupe classe à ce que la proposition d'un élève soit validée par le groupe classe et non le professeur. Ainsi le professeur ne se place plus en seul détenteur du savoir mais comme facilitateur à l'émergence des apprentissages.

② Mise en place des stations, du serveur, et de leurs connexions à Internet

Réalisez le réseau suivant dans le Simulateur de réseau :

![](_page_73_Diagram_2.jpeg)

Paramétrage de la station « SiteWeb » :

- Activer son *Serveur Web* et son *Serveur SQL*.
- Modifier sa carte réseau en carte d'accès distant.
- La placer en adressage dynamique et la relier au FAI Orange (avec un câble Télécom).
- Enfin, l'éteindre et la rallumer pour obtenir l'adresse 203.1.1.2/24 :

## ③ Création d'un nom de domaine

Définissez le nom de domaine « lesite.fr » associé au serveur web dans le composant Internet :

## ④ Activer le serveur Proxy

Sur la station St4, activez le *Serveur Proxy* (menu contextuel, Fonctionnalités, Serveur Proxy).

Dans l'onglet *Sites*, vérifiez que *Liste noire* est coché.

Dans l'onglet *Cache*, augmentez la taille du cache à 3 fichiers :

⑤ Définir le Proxy à utiliser dans le navigateur Internet

Ouvrez le navigateur de la station St1, et définissez le Proxy avec la carte gauche du routeur St4 (cliquez dessus pour obtenir son adresse IP : 10.4.4.4).

![](_page_76_Picture_3.jpeg)

## ⑥ Vérifier l'accès au site web

Dans le navigateur de la station St1, tapez l'adresse « *lesite.fr »* et observer les réponses du site web, ainsi que son bon affichage.

![](_page_76_Picture_8.jpeg)

## ⑦ Vérifier que le cache du Proxy est bien utilisé

Demandez à nouveau la même page dans le navigateur de la station St1 et vérifiez si le cache du Proxy est bien utilisé. Visualisez ensuite le contenu du cache et les accès effectués sur le serveur Proxy :

![](_page_77_Picture_2.jpeg)

## ⑧ Sécuriser les accès

Pour cela, utilisez l'onglet *Sites* pour définir une liste blanche comprenant « *lesite.fr »*, ou l'onglet *Horaires* pour Autoriser ou Interdire une ou plusieurs plages horaires.

![](_page_77_Picture_5.jpeg)

## ⑨ Vérifier la sécurité des accès

Selon la nature du blocage, le message du serveur Proxy diffère :

Sources

- http [://fr.lagache.free.fr/netsim/index.php](http://fr.lagache.free.fr/netsim/index.php?lang=fr) ?lang=fr

- https [://fr.wikipedia.org/wiki/Proxy](https://fr.wikipedia.org/wiki/Proxy)

| Le site                                   | « | lesite.fr | »      | est autorisé (liste |
|-------------------------------------------|---|-----------|--------|---------------------|
| connecter                                 |   | en        | dehors | des heures          |
| Le site « monsite.fr » ne fait pas partie |   |           |        |                     |

Les enseignants de l'OBG sont tenus de travailler en interdisciplinarité : les professeurs de cours techniques se mettent d'accord avec leurs collègues de cours pratiques pour assurer une progression logique des apprentissages. Ceci peut se réaliser en établissant une planification globale des situations d'apprentissage spécifiques ou communes aux différents cours.

Les professeurs de cours de la formation commune sont invités à parcourir le programme, à se concerter avec leurs collègues des cours techniques et pratiques ; on obtiendra ainsi la mise en valeur légitime de ces cours en leur adjoignant du sens.

Dans les programmes du CPEONS, on définit :

- **Une situation d'apprentissage**[1](#page-79-2) comme un dispositif qui met en projet un élève pour qu'il accomplisse une tâche dans des conditions données, avec un matériel et/ou les outils appropriés, en mobilisant des ressources opportunes pour rencontrer les exigences de la consigne.
- **Les ressources** comme l'ensemble des savoirs, savoir-faire, attitudes et stratégies qui seront actualisés, découverts, mobilisés au cours de l'apprentissage et qui s'avèrent incontournables lors de la réalisation de tâches relevant des compétences visées.
- **Une séquence d'apprentissage** comme un ensemble intégré et articulé de situations d'apprentissage.

Il est important que l'élève construise sa démarche de résolution.

---
> [📑 Manifest Index](../00_AGENT_MANIFEST.md)
