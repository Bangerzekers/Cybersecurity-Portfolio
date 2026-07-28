# Supervision d'infrastructure — Zabbix & Grafana

> Projet réel, issu de mon activité professionnelle en environnement hospitalier. Aucune donnée sensible, adresse IP réelle ou information identifiante n'est reproduite ci-dessous.

## 1. Contexte

Environnement hospitalier multi-sites : serveurs applicatifs (Linux/Windows), équipements réseau (switches), messagerie (Exchange 365). Besoin d'une supervision centralisée pour détecter rapidement une dégradation ou une panne, avant qu'elle n'impacte les utilisateurs ou, pire, des systèmes liés aux soins.

## 2. Objectif

Superviser la disponibilité et la performance de l'infrastructure (serveurs, switches, services) via Zabbix pour la collecte de métriques et l'alerting, et Grafana pour la visualisation et les tableaux de bord.

## 3. Périmètre supervisé

- Serveurs applicatifs Linux et Windows (charge CPU/RAM, espace disque, disponibilité des services)
- Équipements réseau (switches) : état des interfaces, charge
- Sauvegardes : suivi de la bonne exécution des jobs de sauvegarde sur les serveurs applicatifs

## 4. Démarche

**Collecte (Zabbix)**
- Déploiement d'agents Zabbix sur les serveurs Linux/Windows supervisés
- Supervision SNMP des switches pour les métriques réseau
- Définition de seuils d'alerte adaptés à chaque type de ressource (ex : espace disque < 15%, charge CPU soutenue anormale)

**Visualisation (Grafana)**
- Tableaux de bord par catégorie : infrastructure serveurs, réseau, sauvegardes
- Vue synthétique pour un contrôle rapide quotidien, vue détaillée pour investigation en cas d'alerte

**Traitement des alertes**
- Qualification de l'alerte (dégradation réelle vs pic ponctuel normal)
- Escalade selon la criticité du système concerné (priorité aux systèmes en lien avec les zones cliniques)
- Documentation de l'incident et de la résolution

## 5. Exemple de démarche face à une alerte

1. **Réception** : alerte Zabbix sur un espace disque serveur applicatif sous le seuil défini
2. **Qualification** : vérification de l'évolution de l'espace disque dans le temps via Grafana (croissance brutale ou progressive)
3. **Diagnostic** : identification de la cause (logs non purgés, sauvegarde locale non nettoyée, croissance applicative normale)
4. **Action** : nettoyage, ajustement de rétention, ou remontée si extension de stockage nécessaire
5. **Suivi** : vérification que l'alerte ne se déclenche plus après action corrective

## 6. Bénéfices apportés

- Détection proactive des dégradations avant impact utilisateur
- Visibilité centralisée sur un parc hétérogène (Linux, Windows, réseau)
- Historique de performance exploitable pour anticiper les besoins (stockage, capacité)
- Vérification fiable de la bonne exécution des sauvegardes

## 7. Limites actuelles et pistes d'amélioration

- Peu d'alerting prédictif (basé sur seuils fixes plutôt que sur tendance ou anomalie statistique)
- Pas encore d'intégration avec un outil de ticketing pour automatiser la création d'incidents depuis Zabbix
- Couverture à étendre progressivement aux futurs outils de sécurité réseau (supervision FortiAnalyzer prévue prochainement)

## Compétences démontrées

Zabbix, Grafana, supervision d'infrastructure, SNMP, définition de seuils d'alerte, qualification d'incidents, priorisation par criticité métier, administration serveurs Linux/Windows, gestion de sauvegardes.
