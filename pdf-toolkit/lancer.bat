@echo off
REM Lance PDF Toolkit sous Windows (cree/repare l'environnement automatiquement).
REM La fenetre reste ouverte sur toute erreur pour que tu puisses la lire.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo ============================================================
    echo Python est introuvable sur ce poste.
    echo Installe-le depuis https://www.python.org/downloads/
    echo IMPORTANT : coche bien la case "Add python.exe to PATH"
    echo pendant l'installation, puis relance ce fichier.
    echo ============================================================
    pause
    exit /b 1
)

REM Si un .venv existe deja mais que son python.exe ne repond plus
REM ^(ex. Python a ete reinstalle ou deplace ailleurs entre-temps^),
REM il est casse de facon irreparable : on le supprime pour en recreer un neuf.
if exist .venv (
    ".venv\Scripts\python.exe" --version >nul 2>nul
    if errorlevel 1 (
        echo L'environnement existant est casse ^(Python a change d'emplacement^).
        echo Reparation : recreation de l'environnement...
        rmdir /s /q .venv
    )
)

if not exist .venv (
    echo Premiere installation, patiente quelques minutes...
    python -m venv .venv
    if errorlevel 1 (
        echo ============================================================
        echo La creation de l'environnement Python a echoue ^(voir ci-dessus^).
        echo ============================================================
        pause
        exit /b 1
    )
)

REM On verifie que les modules necessaires sont VRAIMENT installes et importables.
REM Si une installation precedente a echoue en cours de route ^(coupure internet,
REM etc.^), on refait l'installation au lieu de lancer une appli cassee.
".venv\Scripts\python.exe" -c "import PySide6, pymupdf, PIL, fontTools" >nul 2>nul
if errorlevel 1 (
    echo Installation ^(ou reparation^) des dependances, patiente quelques minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\pip.exe" install -r requirements.txt
    if errorlevel 1 (
        echo ============================================================
        echo L'installation des dependances a echoue ^(voir le detail ci-dessus^).
        echo Verifie ta connexion internet, ou le proxy si tu es sur un
        echo reseau d'entreprise, puis relance ce fichier.
        echo ============================================================
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -c "import PySide6, pymupdf, PIL, fontTools" >nul 2>nul
    if errorlevel 1 (
        echo ============================================================
        echo Certains modules restent introuvables apres installation.
        echo Supprime le dossier .venv puis relance ce fichier pour repartir
        echo d'un environnement neuf.
        echo ============================================================
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo ============================================================
    echo L'application s'est fermee avec une erreur ^(voir le detail ci-dessus^).
    echo Si l'erreur mentionne un module manquant, supprime le dossier
    echo .venv puis relance ce fichier pour reinstaller proprement.
    echo ============================================================
    pause
)
endlocal
