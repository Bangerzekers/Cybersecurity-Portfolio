# Audit de sécurité Microsoft Entra ID

> **Projet de laboratoire simulé :** les constats ci-dessous sont des exemples.

## 1. Résumé

Ce projet présente une méthode d’audit de sécurité d’un environnement Microsoft Entra ID de laboratoire.

L’audit porte sur :

- les comptes à privilèges ;
- l’authentification multifacteur ;
- les accès conditionnels ;
- les comptes inactifs ;
- les applications et consentements ;
- le principe du moindre privilège.

## 2. Objectifs

- Réduire le risque de compromission des comptes.
- Identifier les privilèges excessifs.
- Vérifier la couverture MFA.
- Repérer les comptes dormants.
- Proposer un plan de remédiation priorisé.

## 3. Périmètre

- Utilisateurs
- Groupes
- Rôles Entra ID
- Méthodes d’authentification
- Conditional Access
- Applications d’entreprise
- Comptes invités

## 4. Contrôles

| Contrôle | Risque | Priorité |
|---|---|---|
| Comptes administrateurs sans MFA | Compromission privilégiée | Critique |
| Trop de Global Administrators | Élévation d’impact | Haute |
| Comptes inactifs actifs | Utilisation frauduleuse | Haute |
| Invités anciens | Accès persistant | Moyenne |
| Absence de comptes d’urgence | Blocage administratif | Haute |
| Accès conditionnel incomplet | Contournement des protections | Haute |

## 5. Exemples PowerShell

> Adapter les commandes au module Microsoft Graph installé et aux autorisations disponibles.

### Connexion à Microsoft Graph

```powershell
Connect-MgGraph -Scopes `
    "User.Read.All", `
    "Directory.Read.All", `
    "RoleManagement.Read.Directory", `
    "AuditLog.Read.All"
```

### Lister les utilisateurs

```powershell
Get-MgUser -All |
    Select-Object DisplayName, UserPrincipalName, AccountEnabled, UserType
```

### Rechercher les comptes désactivés

```powershell
Get-MgUser -All -Property DisplayName,UserPrincipalName,AccountEnabled |
    Where-Object { $_.AccountEnabled -eq $false } |
    Select-Object DisplayName, UserPrincipalName
```

### Lister les rôles

```powershell
Get-MgDirectoryRole -All |
    Select-Object DisplayName, Id
```

## 6. Résultats

| Constat | Risque | Recommandation | Priorité |
|---|---|---|---|
| Deux comptes administrateurs sans MFA | Compromission privilégiée | Imposer le MFA | Critique |
| Cinq Global Administrators | Privilèges excessifs | Réduire leur nombre | Haute |
| Trois comptes inactifs depuis 90 jours | Réutilisation frauduleuse | Désactiver après validation | Haute |

## 7. Plan de remédiation

### Priorité critique

- Imposer le MFA aux comptes privilégiés.
- Réduire le nombre de Global Administrators.
- Révoquer les accès manifestement non légitimes.

### Priorité haute

- Désactiver les comptes inactifs.
- Réviser les comptes invités.
- Mettre en place des accès conditionnels adaptés.
- Séparer les comptes administratifs des comptes bureautiques.

### Priorité moyenne

- Mettre en place une revue périodique.
- Documenter les exceptions.
- Vérifier les consentements applicatifs.
- Améliorer les alertes sur les changements de privilèges.

## 8. Conclusion

Résumer le niveau de maturité, les risques principaux et les actions à réaliser dans les trente prochains jours.
