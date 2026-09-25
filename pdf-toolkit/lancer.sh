#!/usr/bin/env bash
# Lance PDF Toolkit sous Linux / macOS (cree l'environnement au premier lancement)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Première installation, patiente quelques minutes..."
  python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt || exit 1
fi
.venv/bin/python app.py
