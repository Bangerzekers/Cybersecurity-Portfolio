# Méthodologie d'audit de sécurité Microsoft Entra ID

> **Note de méthodologie :** ce document décrit la démarche que je suivrais pour auditer un tenant Microsoft Entra ID. Ce n'est pas le compte-rendu d'un audit réellement mené.

## 1. Objectifs de l'audit

- Réduire le risque de compromission des comptes
- Identifier les privilèges excessifs
- Vérifier la couverture MFA
- Repérer les comptes dormants
- Proposer un plan de remédiation priorisé

## 2. Périmètre

Utilisateurs, groupes, rôles Entra ID, méthodes d'authentification, Conditional Access, applications d'entreprise, comptes invités.

## 3. Grille de contrôles

| Contrôle | Risque associé | Priorité |
|---|---|---|
| Comptes administrateurs sans MFA | Compromission privilégiée | Critique |
| Trop de Global Administrators | Élévation d'impact en cas de compromission | Haute |
| Comptes inactifs toujours actifs | Utilisation frauduleuse | Haute |
| Comptes invités anciens/non revus | Accès persistant non maîtrisé | Moyenne |
| Absence de comptes d'urgence (break-glass) | Blocage administratif total | Haute |
| Accès conditionnel incomplet | Contournement des protections | Haute |

## 4. Démarche

1. **Inventaire des rôles à privilèges** : lister les Global Admins et rôles sensibles, vérifier que chacun est justifié et couvert par MFA.
2. **Couverture MFA globale** : identifier les comptes (surtout à privilèges) sans MFA activé.
3. **Comptes inactifs** : croiser la dernière date de connexion avec le statut du compte (départ, mutation).
4. **Revue des invités** : accès encore nécessaires ou à révoquer.
5. **Conditional Access** : vérifier l'existence de politiques couvrant au minimum les comptes à privilèges et les connexions à risque.
6. **Priorisation** : classer les constats par risque réel (probabilité × impact), pas seulement par facilité de correction.

## 5. Exemple de commande PowerShell / Microsoft Graph

```powershell
Connect-MgGraph -Scopes "User.Read.All","AuditLog.Read.All"

Get-MgUser -All | Where-Object {
    $_.SignInActivity.LastSignInDateTime -lt (Get-Date).AddDays(-90)
} | Select-Object DisplayName, UserPrincipalName, @{N='DernièreConnexion';E={$_.SignInActivity.LastSignInDateTime}}
```

Cette commande permet d'identifier les comptes sans connexion depuis plus de 90 jours — un point de départ classique pour repérer des comptes dormants à désactiver.

## 6. Plan de remédiation type

1. Activer le MFA obligatoire pour tous les rôles à privilèges (immédiat)
2. Désactiver les comptes inactifs identifiés (court terme)
3. Réduire le nombre de Global Administrators au strict nécessaire (court terme)
4. Mettre en place des comptes d'urgence break-glass exclus des politiques Conditional Access (court terme)
5. Revue trimestrielle des accès invités (processus récurrent)

## Compétences illustrées

IAM, Microsoft Entra ID, MFA, Conditional Access, RBAC, gouvernance des identités, PowerShell/Microsoft Graph.
