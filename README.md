[README.md](https://github.com/user-attachments/files/31180132/README.md)
# Portfolio Cybersécurité — Paul Jacquet

Master (Bac+5, RNCP Niveau 7) — Expert en architectures systèmes, réseaux et sécurité informatique (EASRSI), avec une expérience opérationnelle en environnement hospitalier : durcissement Active Directory, gestion des vulnérabilités, supervision d'infrastructure, ainsi qu'une expertise réseau plus large (infrastructure HPE Aruba, VLAN, segmentation) et environnements Microsoft (365, Exchange Online, SharePoint, Power Automate).

Ce portfolio présente deux types de contenu, clairement distingués :

- **Projets réels**, issus de mon activité professionnelle ou personnelle (anonymisés le cas échéant) ;
- **Notes de méthodologie**, où je détaille comment j'aborderais un scénario de sécurité donné (investigation SOC, audit IAM, gestion des vulnérabilités) afin d'illustrer ma démarche technique et les compétences acquises durant mon master.

> Je recherche actuellement un poste 100% cybersécurité (SOC, sécurité réseau) en Suisse, en m'appuyant sur mon master spécialisé et mon expérience opérationnelle en sécurité réseau. Ce portfolio est complété progressivement avec des projets et labs pratiques.

## Projets réels

### 1. Supervision d'infrastructure — Zabbix & Grafana

Supervision de l'infrastructure (serveurs Linux/Windows, équipements réseau, sauvegardes) en environnement hospitalier multi-sites : collecte de métriques via Zabbix, visualisation via Grafana, définition de seuils d'alerte, qualification et traitement des incidents.

[Consulter le projet](./network-monitoring-zabbix-grafana/)

**Compétences démontrées :** Zabbix, Grafana, supervision d'infrastructure, SNMP, qualification d'incidents, priorisation par criticité métier.

### 2. Sauvegarde automatisée de configurations réseau — Ansible / HPE Aruba

Automatisation via Ansible du backup de configuration pour un parc de switches HPE Aruba (OS-Switch/ProCurve 2530, 2920 et CX) sur un réseau de management dédié (VLAN), avec inventaire structuré par site, playbooks différenciés selon les modèles, gestion des secrets via Ansible Vault et planification via cron.

[Consulter le projet](./ansible-aruba-backups/)

**Compétences démontrées :** administration réseau, Ansible, SSH, gestion de secrets (Vault), segmentation VLAN, automatisation, documentation d'infrastructure, hygiène de sécurité opérationnelle.

### 3. Compresseur de PDF local — sans upload sur un site tiers

Outil avec interface graphique pour compresser des fichiers PDF volumineux localement, sans jamais faire transiter le document sur un serveur externe. Recompression des images embarquées, plusieurs niveaux de compression et rapport de gain avant/après.

[Consulter le projet](./pdf-compressor/)

**Compétences démontrées :** Python, traitement de fichiers, confidentialité des données par conception, interface graphique, automatisation d'une tâche utilisateur.

### 4. Protecteur de PDF local — chiffrement par mot de passe

Outil Python avec interface graphique permettant de protéger un PDF par mot de passe sans envoyer le document vers un service tiers. Le fichier est chiffré localement avec pikepdf, le mot de passe n'est pas stocké et le document original est systématiquement conservé.

[Consulter le projet](./pdf-protector/)

**Compétences démontrées :** Python, Tkinter, chiffrement de documents, pikepdf, gestion sécurisée de données sensibles, confidentialité par conception, conception d'un outil utilisable par un public non technique.

## Notes de méthodologie

Ces documents ne décrivent pas un incident réel, mais ma démarche technique face à un scénario donné : requêtes, outils, raisonnement et priorisation. L'objectif est de montrer comment je pense et travaille, en toute transparence sur le fait qu'il s'agit d'exercices méthodologiques.

### 5. Méthodologie d'investigation SOC avec Microsoft Sentinel

Démarche d'investigation face à un scénario de connexions suspectes : collecte de logs, requêtes KQL, triage, qualification et recommandations.

[Consulter le projet](./soc-sentinel/)

**Compétences :** Microsoft Sentinel, KQL, Windows Event Logs, triage, chronologie d'incident.

### 6. Méthodologie d'audit de sécurité Microsoft Entra ID

Démarche d'audit d'un tenant : comptes à privilèges, MFA, accès conditionnels, comptes inactifs et principe du moindre privilège.

[Consulter le projet](./entra-id-security-audit/)

**Compétences :** IAM, Entra ID, MFA, Conditional Access, RBAC, PowerShell / Microsoft Graph.

### 7. Méthodologie de gestion des vulnérabilités

Démarche de scan, qualification, priorisation et remédiation sur un système type.

[Consulter le projet](./vulnerability-management/)

**Compétences :** CVSS, Nmap, scanners de vulnérabilités, priorisation, remédiation, reporting.

## Compétences techniques

- **Sécurité :** analyse d'événements, investigation, IAM, durcissement, gestion des vulnérabilités, segmentation réseau, confidentialité des données
- **Réseau :** TCP/IP, DNS, DHCP, VLAN, routage, pare-feu, SSH, équipements HPE Aruba
- **Supervision :** Zabbix, Grafana, SNMP, alerting, qualification d'incidents
- **Automatisation / scripting :** Python, PowerShell, Ansible, gestion de secrets avec Ansible Vault
- **Microsoft :** Microsoft 365, Exchange Online, Entra ID, SharePoint, Power Automate, Microsoft Graph
- **Systèmes :** Windows, Active Directory, Linux, postes de travail, support N2
- **Développement d'outils :** Python, Tkinter, traitement de fichiers, outils locaux orientés confidentialité
- **Documentation :** procédures, rapports techniques, recommandations, documentation d'infrastructure

## Formation

**Master (Bac+5, RNCP Niveau 7)** — Expert en architectures systèmes, réseaux et sécurité informatique, spécialité cybersécurité.

## Objectif professionnel

Intégrer une équipe de cybersécurité, SOC ou sécurité réseau en Suisse, en m'appuyant sur mon master spécialisé, mon expérience opérationnelle en environnement hospitalier et mes compétences systèmes/réseaux.
