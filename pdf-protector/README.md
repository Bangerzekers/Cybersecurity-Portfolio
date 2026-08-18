[README.md](https://github.com/user-attachments/files/31180096/README.md)

# 🔐 Protecteur de PDF — chiffrement local par mot de passe

Petit outil avec interface graphique permettant de protéger un fichier PDF par mot de passe, entièrement **en local**, sans envoyer le document vers un service ou un serveur tiers.

## 🎯 Contexte / Pourquoi ce projet

De nombreux services en ligne permettent de protéger un PDF par mot de passe, mais nécessitent d'abord de téléverser le document sur une infrastructure externe.

Pour des documents professionnels, administratifs ou potentiellement sensibles, ce fonctionnement peut être indésirable.

Ce projet répond à un besoin simple :

- conserver le document uniquement sur la machine locale ;
- ajouter rapidement un mot de passe d'ouverture ;
- éviter tout transfert vers un service web tiers ;
- proposer une interface accessible à un utilisateur non technique ;
- conserver systématiquement le PDF original.

## ⚙️ Fonctionnalités

- Interface graphique simple avec **Tkinter**
- Sélection du PDF via l'explorateur Windows
- Saisie du mot de passe avec confirmation
- Affichage / masquage du mot de passe
- Avertissement si le mot de passe contient moins de 8 caractères
- Chiffrement moderne du PDF via **pikepdf**
- Création automatique d'une copie suffixée `_protege.pdf`
- Conservation systématique du document original
- Gestion automatique des doublons (`_protege_2.pdf`, `_protege_3.pdf`, etc.)
- Aucun stockage du mot de passe par le programme
- Fonctionnement hors ligne une fois les dépendances installées

## 🧱 Stack technique

| Composant | Rôle |
|---|---|
| Python 3 | Langage principal |
| Tkinter | Interface graphique |
| pikepdf | Lecture, écriture et chiffrement du PDF |
| qpdf | Moteur utilisé par pikepdf pour la manipulation sécurisée des PDF |

## 🔐 Chiffrement

Le programme utilise `pikepdf.Encryption` avec :

```python
R=6
```

Ce mode correspond au chiffrement PDF moderne basé sur **AES-256**.

Le mot de passe demandé lors de l'ouverture du PDF est défini au moment de la création du fichier protégé.

Le mot de passe n'est :

- ni écrit dans un fichier ;
- ni enregistré dans le script ;
- ni transmis sur le réseau.

> En cas de perte du mot de passe, le programme ne fournit aucun mécanisme de récupération. Le fichier original non chiffré est donc volontairement conservé.

## 📥 Installation

Cloner le portfolio :

```bash
git clone https://github.com/Bangerzekers/Cybersecurity-Portfolio.git
cd Cybersecurity-Portfolio/pdf-protector
```

Installer la dépendance :

```powershell
py -m pip install pikepdf
```

## ▶️ Utilisation

Lancer le programme :

```powershell
py protecteur_pdf.py
```

Puis :

1. Cliquer sur **Parcourir...**
2. Sélectionner le PDF à protéger
3. Saisir le mot de passe
4. Confirmer le mot de passe
5. Cliquer sur **PROTÉGER LE PDF**

Un nouveau fichier est créé dans le même dossier :

```text
document.pdf
document_protege.pdf
```

Le document d'origine reste inchangé.

## 🖥️ Raccourci Windows

Le programme peut également être lancé depuis un raccourci Windows sans afficher de console.

Exemple :

```text
"C:\Users\user\AppData\Local\Programs\Python\Python313\pythonw.exe" "C:\chemin\vers\protecteur_pdf.py"
```

Le champ **Démarrer dans** peut pointer vers le dossier contenant le script.

## 🌐 Utilisation du PDF généré

Python et pikepdf sont uniquement nécessaires pour **créer** le fichier protégé.

Une fois généré, le PDF chiffré peut être :

- envoyé par mail ;
- copié sur une clé USB ;
- transféré sur un autre poste ;
- ouvert sous Windows, macOS ou mobile avec un lecteur PDF compatible.

Le poste destinataire n'a pas besoin de Python : seul le mot de passe d'ouverture est nécessaire.

## 🔒 Confidentialité

Le traitement du fichier est local.

Le programme :

- n'effectue aucun upload ;
- n'appelle aucune API externe ;
- ne nécessite aucune connexion réseau pendant la protection ;
- ne conserve pas le mot de passe ;
- ne supprime ni ne remplace le fichier source.

Cette approche réduit l'exposition des documents par rapport à l'utilisation d'un service de traitement PDF en ligne.

## ⚠️ Limites

- Le programme protège actuellement un seul PDF à la fois.
- Un PDF déjà chiffré doit d'abord être ouvert avec son mot de passe avant de pouvoir être retraité.
- La sécurité réelle dépend également de la qualité du mot de passe choisi.
- Le fichier original étant conservé, sa protection et son stockage restent sous la responsabilité de l'utilisateur.

## 📌 Pistes d'amélioration

- Protection de plusieurs PDF par lot
- Générateur de mot de passe fort
- Indicateur visuel de robustesse du mot de passe
- Choix du dossier de sortie
- Glisser-déposer
- Packaging en exécutable Windows avec PyInstaller
- Option de définition distincte du mot de passe propriétaire
- Journalisation locale sans données sensibles

---

Projet développé comme outil personnel de traitement de documents, avec une attention particulière portée à la **confidentialité des données**, à la simplicité d'utilisation et au traitement local.
