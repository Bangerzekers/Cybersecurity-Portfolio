# Guide de réalisation

Les résultats présents dans ce portfolio sont des **exemples de laboratoire simulés**. Ils ne doivent pas être présentés comme une expérience professionnelle réelle. Le but est de montrer une méthode, puis de remplacer progressivement les exemples par tes propres résultats.

## Projet SOC Sentinel

### Exemple de scénario
- Compte fictif : `paul.lab`
- Poste : `WIN11-LAB01`
- Adresse IP privée : `192.168.56.20`
- 18 échecs de connexion à 09:12
- Connexion réussie à 09:14
- Lancement de PowerShell à 09:16
- Compte désactivé à 09:20
- Mot de passe réinitialisé à 09:28

### Conclusion d'exemple
- Classification : vrai positif simulé
- Sévérité : moyenne
- Compromission : probable dans le scénario
- Impact : faible, environnement isolé

### Comment reproduire
1. Crée une machine virtuelle Windows.
2. Utilise un compte de test.
3. Provoque plusieurs échecs de connexion.
4. Connecte-toi ensuite correctement.
5. Lance une commande PowerShell bénigne comme `Get-Process`.
6. Vérifie les événements 4625, 4624 et 4688.
7. Envoie les journaux dans Sentinel ou analyse-les localement.
8. Exécute les requêtes KQL du dépôt.
9. Fais trois à cinq captures anonymisées.
10. Remplace les heures et résultats fictifs par les tiens.

### Ce qu'il faut savoir expliquer
- Les événements 4625 correspondent aux échecs de connexion.
- L'événement 4624 correspond à une connexion réussie.
- L'événement 4688 permet d'examiner les processus lancés.
- C'est la corrélation entre les événements qui rend le scénario suspect.
- Le MFA, la révocation des sessions et la réinitialisation du mot de passe réduisent le risque.

## Projet Entra ID

### Résultats simulés
| Constat | Risque | Recommandation | Priorité |
|---|---|---|---|
| Deux comptes administrateurs sans MFA | Compromission privilégiée | Imposer le MFA | Critique |
| Cinq Global Administrators | Privilèges excessifs | Réduire leur nombre | Haute |
| Trois comptes inactifs depuis 90 jours | Réutilisation frauduleuse | Désactiver après validation | Haute |
| Quatre invités anciens | Accès externe persistant | Réaliser une revue d'accès | Moyenne |
| Authentification héritée autorisée | Contournement des protections modernes | La bloquer | Haute |

### Comment reproduire
1. Utilise un tenant Microsoft de test.
2. Crée quelques comptes fictifs.
3. Vérifie les rôles administratifs.
4. Vérifie l'état du MFA.
5. Recherche les comptes inactifs et invités.
6. Examine les politiques d'accès conditionnel.
7. Classe chaque constat selon son impact et sa probabilité.
8. Propose une remédiation réaliste.

### Ce qu'il faut savoir expliquer
- Les comptes administrateurs doivent être séparés des comptes quotidiens.
- Le nombre de Global Administrators doit rester limité.
- Le MFA réduit le risque lié au vol de mot de passe.
- Les invités et comptes inactifs doivent être revus régulièrement.
- L'authentification héritée peut contourner des protections modernes.

## Projet gestion des vulnérabilités

### Résultats simulés
| Vulnérabilité | CVSS | Exposition | Impact | Priorité |
|---|---:|---|---|---|
| Serveur web obsolète | 8.1 | Réseau local | Compromission possible | Haute |
| SSH avec mot de passe | 6.5 | Réseau local | Bruteforce possible | Haute |
| En-têtes HTTP absents | 4.3 | Réseau local | Protection navigateur réduite | Moyenne |
| Paquets système non à jour | 7.5 | Local/réseau | Exploitation variable | Haute |

### Résultat avant/après simulé
| Indicateur | Avant | Après |
|---|---:|---:|
| Vulnérabilités critiques | 0 | 0 |
| Vulnérabilités hautes | 3 | 0 |
| Vulnérabilités moyennes | 1 | 1 |
| Services exposés | 2 | 2 |

### Comment reproduire
1. Crée deux machines virtuelles sur un réseau isolé.
2. Utilise une cible volontairement vulnérable.
3. Lance `nmap -sV -O <IP_DU_LAB>`.
4. Lance un scan OpenVAS, Greenbone ou Nessus Essentials.
5. Garde trois ou quatre vulnérabilités intéressantes.
6. Vérifie les versions et la documentation officielle.
7. Corrige par mise à jour, durcissement ou restriction réseau.
8. Relance le scan.
9. Compare les résultats avant et après.
10. Documente le risque résiduel.

### Ce qu'il faut savoir expliquer
- Un scanner produit des hypothèses qu'il faut confirmer.
- Le CVSS ne tient pas compte de tout le contexte métier.
- Une vulnérabilité exposée à Internet est souvent plus urgente.
- Une mesure compensatoire réduit temporairement le risque.
- Le rescannage confirme l'efficacité de la correction.

## Formulation CV

> Portfolio cybersécurité personnel : investigation SOC avec Microsoft Sentinel et KQL, audit Microsoft Entra ID, gestion des vulnérabilités et remédiation en laboratoire.

## Formulation entretien

> J'ai construit ces projets dans un laboratoire personnel pour démontrer ma méthode. Je peux expliquer l'environnement, les hypothèses, les outils, les décisions prises et les limites de chaque scénario.
