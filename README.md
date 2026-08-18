[README.md](https://github.com/user-attachments/files/31179075/README.md)
# Portfolio Cybersécurité — Paul Jacquet

Master (Bac+5, RNCP Niveau 7) — Expert en architectures systèmes, réseaux et sécurité informatique (EASRSI), avec une expérience opérationnelle en environnement hospitalier : durcissement Active Directory, gestion des vulnérabilités, supervision d'infrastructure, ainsi qu'une expertise réseau plus large (infrastructure HPE Aruba, VLAN, segmentation) et environnements Microsoft (365, Exchange Online, SharePoint, Power Automate).

Ce portfolio présente deux types de contenu, clairement distingués :

- **Projets réels**, issus de mon activité professionnelle ou personnelle (anonymisés le cas échéant) ;
- **Notes de méthodologie**, où je détaille comment j'aborderais un scénario de sécurité donné (investigation SOC, audit IAM, gestion des vulnérabilités) — utile pour illustrer les compétences acquises durant mon master, même sans lab dédié réalisé pour l'occasion.

Je recherche actuellement un poste 100% cybersécurité (SOC, sécurité réseau) en Suisse, en m'appuyant sur mon master spécialisé et mon expérience opérationnelle en sécurité réseau. Ce portfolio est complété progressivement avec des labs pratiques.

## Projets réels

### 1. Supervision d'infrastructure — Zabbix & Grafana

Supervision de l'infrastructure (serveurs Linux/Windows, équipements réseau, sauvegardes) en environnement hospitalier multi-sites : collecte de métriques via Zabbix, visualisation via Grafana, définition de seuils d'alerte, qualification et traitement des incidents.

**[Consulter le projet](./zabbix-grafana-supervision)**

Compétences démontrées : Zabbix, Grafana, supervision d'infrastructure, SNMP, qualification d'incidents, priorisation par criticité métier.

### 2. Sauvegarde automatisée de configurations réseau — Ansible / HPE Aruba

Automatisation via Ansible du backup de configuration pour un parc de switches HPE Aruba (OS-Switch/ProCurve 2530, 2920, et CX) sur un réseau de management dédié (VLAN), avec inventaire structuré par site, playbooks différenciés selon les modèles, gestion des secrets via Ansible Vault et planification via cron.

**[Consulter le projet](./ansible-aruba-backup)**

Compétences démontrées : administration réseau, Ansible, SSH, gestion de secrets (Vault), segmentation VLAN, automatisation, documentation d'infrastructure, hygiène de sécurité opérationnelle (accès, sauvegarde, traçabilité des changements de config).

### 3. Compresseur de PDF local — sans upload sur un site tiers

Outil avec interface graphique (glisser-déposer) pour compresser des fichiers PDF volumineux localement, sans jamais faire transiter le document sur un serveur externe. Recompression des images embarquées (JPEG, qualité et résolution ajustables sur 3 niveaux), nettoyage de la structure du PDF, rapport de gain avant/après.

**[Consulter le projet](https://github.com/Bangerzekers/Cybersecurity-Portfolio/tree/main/pdf-compressor)**

Compétences démontrées : Python, traitement de fichiers, confidentialité des données par conception (pas d'exfiltration réseau), conception d'interface utilisateur simple pour un outil technique.

## Notes de méthodologie

Ces documents ne décrivent pas un incident réel, mais ma démarche technique face à un scénario donné : requêtes, outils, raisonnement, priorisation. L'objectif est de montrer comment je pense et travaille, en toute transparence sur le fait qu'il s'agit d'un exercice et non d'un vécu.

### 4. Méthodologie d'investigation SOC avec Microsoft Sentinel

Démarche d'investigation face à un scénario de connexions suspectes : collecte de logs, requêtes KQL, triage, qualification, recommandations.

**[Consulter le projet](./methodo-soc-sentinel)** — Compétences : Microsoft Sentinel, KQL, Windows Event Logs, triage, chronologie d'incident.

### 5. Méthodologie d'audit de sécurité Microsoft Entra ID

Démarche d'audit d'un tenant : comptes à privilèges, MFA, accès conditionnels, comptes inactifs, principe du moindre privilège.

**[Consulter le projet](./methodo-audit-entra-id)** — Compétences : IAM, Entra ID, MFA, Conditional Access, RBAC, PowerShell/Graph.

### 6. Méthodologie de gestion des vulnérabilités

Démarche de scan, qualification, priorisation et remédiation sur un système type.

**[Consulter le projet](./methodo-gestion-vulnerabilites)** — Compétences : CVSS, Nmap, scanners de vulnérabilités, priorisation, reporting.

## Compétences techniques

- **Sécurité** : analyse d'événements, investigation, IAM, durcissement, gestion des vulnérabilités, segmentation réseau
- **Réseau** : TCP/IP, DNS, DHCP, VLAN, routage, pare-feu, SSH, équipements HPE Aruba
- **Automatisation** : Ansible, gestion de secrets (Vault), scripting
- **Microsoft** : Microsoft 365, Exchange Online, Entra ID, SharePoint, Power Automate, PowerShell
- **Systèmes** : Windows, Active Directory, postes de travail, support N2
- **Documentation** : procédures, rapports techniques, recommandations

## Formation

Master (Bac+5, RNCP Niveau 7) — Expert en architecture réseaux, spécialité cybersécurité

## Objectif professionnel

Intégrer une équipe de cybersécurité, SOC, IAM ou sécurité réseau en Suisse, en m'appuyant sur mon master spécialisé et mon expérience réseau existante.
