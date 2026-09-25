"""
PDF Toolkit — boîte à outils PDF 100 % locale (type iLovePDF, mais hors-ligne).

Lancer :  python app.py
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QRunnable, QSize, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import (QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QPalette,
                           QPen, QPixmap, QShortcut, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox,
                               QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListView, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

import pdf_ops as ops

UR = Qt.ItemDataRole.UserRole
LAST_DIR = str(Path.home())

POS9 = [("Haut gauche", "haut-gauche"), ("Haut centre", "haut-centre"), ("Haut droite", "haut-droite"),
        ("Milieu gauche", "milieu-gauche"), ("Centre", "milieu-centre"), ("Milieu droite", "milieu-droite"),
        ("Bas gauche", "bas-gauche"), ("Bas centre", "bas-centre"), ("Bas droite", "bas-droite")]
POS6 = [p for p in POS9 if not p[1].startswith("milieu")]

QSS = """
QLabel#h1 { font-size: 22px; font-weight: 600; }
QLabel#muted { color: #6b7280; }
QLabel#info { color: #2563eb; }
QPushButton { padding: 6px 14px; }
QPushButton#primary { background: #2563eb; color: white; border: none; border-radius: 6px;
                      padding: 9px 26px; font-weight: 600; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#primary:disabled { background: #9ca3af; }
QListWidget#sidebar { border: none; background: #eef0f4; font-size: 14px; outline: 0; }
QListWidget#sidebar::item { padding: 9px 16px; }
QListWidget#sidebar::item:selected { background: #dbe6ff; color: #1e3a8a; }
"""


# --------------------------------------------------------------------------- #
#  Tâches en arrière-plan (l'interface ne se fige jamais)
# --------------------------------------------------------------------------- #
class TaskSignals(QObject):
    done = Signal(int, object)
    error = Signal(int, str)


class Task(QRunnable):
    def __init__(self, fn, sig: TaskSignals, tid: int):
        super().__init__()
        self.fn, self.sig, self.tid = fn, sig, tid
        self.setAutoDelete(False)

    def run(self):
        try:
            res = self.fn()
        except ops.PasswordRequired:
            self.sig.error.emit(self.tid, "Ce fichier est protégé par un mot de passe.")
        except (ValueError, ops.PdfError) as e:
            self.sig.error.emit(self.tid, str(e))
        except Exception as e:  # imprévu : on garde la trace dans la console
            traceback.print_exc()
            self.sig.error.emit(self.tid, f"{type(e).__name__} : {e}")
        else:
            self.sig.done.emit(self.tid, res)


# --------------------------------------------------------------------------- #
#  Petits widgets réutilisables
# --------------------------------------------------------------------------- #
class DropLineEdit(QLineEdit):
    dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setReadOnly(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.dropped.emit(urls[0].toLocalFile())


class FilePicker(QWidget):
    changed = Signal(str)

    def __init__(self, filt="PDF (*.pdf)", placeholder="Glisse un fichier ici ou clique sur Parcourir…"):
        super().__init__()
        self.filt = filt
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = DropLineEdit()
        self.edit.setPlaceholderText(placeholder)
        btn = QPushButton("Parcourir…")
        lay.addWidget(self.edit, 1)
        lay.addWidget(btn)
        self.edit.dropped.connect(self.set_path)
        btn.clicked.connect(lambda: self.browse())

    def browse(self):
        global LAST_DIR
        p, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier", LAST_DIR, self.filt)
        if p:
            self.set_path(p)

    def set_path(self, p: str):
        global LAST_DIR
        if p and os.path.isfile(p):
            LAST_DIR = os.path.dirname(p)
            self.edit.setText(p)
            self.changed.emit(p)

    def path(self) -> str:
        return self.edit.text().strip()


class ColorButton(QPushButton):
    def __init__(self, color="#808080"):
        super().__init__()
        self._c = QColor(color)
        self.setFixedWidth(80)
        self._paint()
        self.clicked.connect(lambda: self._pick())

    def _paint(self):
        self.setStyleSheet(f"background:{self._c.name()}; border:1px solid #9ca3af; "
                           f"border-radius:4px; min-height:22px;")

    def _pick(self):
        c = QColorDialog.getColor(self._c, self, "Choisir une couleur")
        if c.isValid():
            self._c = c
            self._paint()

    def rgb(self):
        return (self._c.redF(), self._c.greenF(), self._c.blueF())


class FileList(QListWidget):
    """Liste de fichiers réordonnable par glisser-déposer, qui accepte aussi les fichiers du bureau."""

    def __init__(self, exts=(".pdf",)):
        super().__init__()
        self.exts = tuple(exts)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)

    def add_paths(self, paths):
        for p in paths:
            if p and os.path.isfile(p) and p.lower().endswith(self.exts):
                it = QListWidgetItem(os.path.basename(p))
                it.setData(UR, p)
                it.setToolTip(p)
                self.addItem(it)

    def paths(self):
        return [self.item(i).data(UR) for i in range(self.count())]

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.add_paths([u.toLocalFile() for u in e.mimeData().urls()])
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def move_selected(self, delta: int):
        rows = sorted((self.row(i) for i in self.selectedItems()), reverse=(delta > 0))
        for r in rows:
            nr = r + delta
            if 0 <= nr < self.count() and not self.item(nr).isSelected():
                it = self.takeItem(r)
                self.insertItem(nr, it)
                it.setSelected(True)

    def remove_selected(self):
        for it in self.selectedItems():
            self.takeItem(self.row(it))

    def sort_az(self):
        items = sorted(self.paths(), key=lambda p: os.path.basename(p).lower())
        self.clear()
        self.add_paths(items)


def size_fmt(n: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024


def to_pixmap(w, h, stride, data) -> QPixmap:
    return QPixmap.fromImage(QImage(data, w, h, stride, QImage.Format.Format_RGB888).copy())


# --------------------------------------------------------------------------- #
#  Base des pages
# --------------------------------------------------------------------------- #
class ToolPage(QWidget):
    def __init__(self, win: "MainWindow", title: str, desc: str):
        super().__init__()
        self.win = win
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(26, 22, 26, 22)
        self.body.setSpacing(12)
        t = QLabel(title)
        t.setObjectName("h1")
        d = QLabel(desc)
        d.setObjectName("muted")
        d.setWordWrap(True)
        self.body.addWidget(t)
        self.body.addWidget(d)

    def add_run_button(self, text, slot):
        b = QPushButton(text)
        b.setObjectName("primary")
        b.clicked.connect(lambda: slot())
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(b)
        self.body.addLayout(row)
        return b


class SimpleTool(ToolPage):
    """Un PDF en entrée + quelques réglages -> un fichier (ou un dossier) en sortie."""
    suffix = "_modifie"
    out_kind = "pdf"          # pdf | dir | txt
    run_label = "Lancer"

    def __init__(self, win, title, desc):
        super().__init__(win, title, desc)
        self.src = FilePicker()
        self.src.changed.connect(self._on_src)
        self.info = QLabel("")
        self.info.setObjectName("info")
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.addRow("Fichier PDF", self.src)
        self.form.addRow("", self.info)
        self.body.addLayout(self.form)
        self.build()
        self.body.addStretch()
        self.btn = self.add_run_button(self.run_label, self.on_run)

    # -- à surcharger ------------------------------------------------------
    def build(self):
        pass

    def collect(self) -> dict:
        return {}

    def work(self, path, pw, out, params) -> str:
        raise NotImplementedError

    def on_src_changed(self, path):
        pass

    # -- commun ------------------------------------------------------------
    def _on_src(self, path):
        try:
            i = ops.quick_info(path)
            if i["encrypted"]:
                self.info.setText("Fichier protégé — le mot de passe sera demandé au lancement.")
            else:
                self.info.setText(f"{i['pages']} page(s) · {size_fmt(i['size'])}")
        except Exception as e:
            self.info.setText(f"Lecture impossible : {e}")
        self.on_src_changed(path)

    def ask_output(self, path, params):
        stem, folder = Path(path).stem, str(Path(path).parent)
        if self.out_kind == "dir":
            return self.win.ask_dir(folder)
        if self.out_kind == "txt":
            return self.win.ask_save(f"{stem}.txt", "Texte (*.txt)", ".txt", folder)
        return self.win.ask_save(f"{stem}{self.suffix}.pdf", "PDF (*.pdf)", ".pdf", folder)

    def on_run(self):
        path = self.src.path()
        if not path or not os.path.isfile(path):
            return self.win.warn("Choisis d'abord un fichier PDF.")
        try:
            params = self.collect()
        except ValueError as e:
            return self.win.warn(str(e))
        pw = self.win.open_password(path)
        if pw is None:
            return
        out = self.ask_output(path, params)
        if not out:
            return
        self.win.run_task(lambda: self.work(path, pw, out, params),
                          lambda msg: self.win.notify(msg, out))


# --------------------------------------------------------------------------- #
#  Outils
# --------------------------------------------------------------------------- #
class ListTool(ToolPage):
    """Liste de fichiers ordonnée -> un PDF (fusion, images -> PDF)."""
    exts = (".pdf",)
    filt = "PDF (*.pdf)"
    out_name = "fusion.pdf"
    run_label = "Lancer"

    def __init__(self, win, title, desc):
        super().__init__(win, title, desc)
        self.list = FileList(self.exts)
        self.body.addWidget(self.list, 1)
        bar = QHBoxLayout()
        for text, fn in [("Ajouter…", self.add_dialog), ("Retirer", self.list.remove_selected),
                         ("Monter", lambda: self.list.move_selected(-1)),
                         ("Descendre", lambda: self.list.move_selected(1)),
                         ("Trier A→Z", self.list.sort_az), ("Vider", self.list.clear)]:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            bar.addWidget(b)
        bar.addStretch()
        self.body.addLayout(bar)
        self.opts = QFormLayout()
        self.body.addLayout(self.opts)
        self.build_opts()
        self.add_run_button(self.run_label, self.on_run)

    def build_opts(self):
        pass

    def add_dialog(self):
        global LAST_DIR
        ps, _ = QFileDialog.getOpenFileNames(self, "Ajouter des fichiers", LAST_DIR, self.filt)
        if ps:
            LAST_DIR = os.path.dirname(ps[0])
            self.list.add_paths(ps)

    def resolve(self, files):
        return [(p, "") for p in files]

    def work(self, items, out) -> str:
        raise NotImplementedError

    def on_run(self):
        files = self.list.paths()
        if not files:
            return self.win.warn("La liste est vide : ajoute des fichiers.")
        items = self.resolve(files)
        if items is None:
            return
        out = self.win.ask_save(self.out_name, "PDF (*.pdf)", ".pdf", str(Path(files[0]).parent))
        if not out:
            return
        self.win.run_task(lambda: self.work(items, out), lambda msg: self.win.notify(msg, out))


class MergePage(ListTool):
    out_name = "fusion.pdf"
    run_label = "Fusionner"

    def __init__(self, win):
        super().__init__(win, "Fusionner des PDF",
                         "Ajoute plusieurs PDF (ou glisse-les ici), réordonne-les, puis fusionne-les en un seul fichier.")

    def build_opts(self):
        self.bm = QCheckBox("Ajouter un signet par fichier fusionné")
        self.bm.setChecked(True)
        self.opts.addRow(self.bm)

    def resolve(self, files):
        items = []
        for p in files:
            pw = self.win.open_password(p)
            if pw is None:
                return None
            items.append((p, pw))
        return items

    def work(self, items, out):
        bm = self.bm.isChecked()
        n = ops.merge(items, out, bm)
        return f"{len(items)} fichier(s) fusionné(s) — {n} pages au total."


class ImagesToPdfPage(ListTool):
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp")
    filt = "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp)"
    out_name = "images.pdf"
    run_label = "Créer le PDF"

    def __init__(self, win):
        super().__init__(win, "Images → PDF",
                         "Une image par page. L'orientation des photos de téléphone est corrigée automatiquement.")

    def build_opts(self):
        self.mode = QComboBox()
        self.mode.addItem("Ajuster sur une page A4", "a4")
        self.mode.addItem("Page = taille de l'image", "original")
        self.opts.addRow("Format des pages", self.mode)

    def work(self, items, out):
        mode = self.mode.currentData()
        n = ops.images_to_pdf([p for p, _ in items], out, mode)
        return f"PDF créé : {n} page(s)."


class OrganizePage(ToolPage):
    THUMB = 150

    def __init__(self, win):
        super().__init__(win, "Organiser les pages",
                         "Glisse les miniatures pour réordonner. Pivote, supprime, insère des pages d'un autre PDF "
                         "ou des pages blanches. Double-clic = aperçu agrandi.")
        self.sources: list[tuple[str, str]] = []
        bar = QHBoxLayout()
        for text, fn in [("Ouvrir un PDF…", self.open_new), ("Insérer les pages d'un PDF…", self.add_pdf),
                         ("Page blanche", self.add_blank), ("Pivoter à gauche", lambda: self.rotate(-90)),
                         ("Pivoter à droite", lambda: self.rotate(90)), ("Supprimer", self.delete_sel),
                         ("Tout sélectionner", lambda: self.list.selectAll())]:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            bar.addWidget(b)
        bar.addStretch()
        self.body.addLayout(bar)

        self.list = QListWidget()
        t = self.THUMB
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setIconSize(QSize(t, t))
        self.list.setGridSize(QSize(t + 26, t + 40))
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Snap)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(True)
        self.list.setDropIndicatorShown(True)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setStyleSheet("QListWidget { background: #d5d9e0; } "
                                "QListWidget::item:selected { background: #93b4f5; color: #111827; }")
        self.list.itemDoubleClicked.connect(self.preview)
        m = self.list.model()
        for sig in (m.rowsMoved, m.rowsInserted, m.rowsRemoved):
            sig.connect(lambda *a: self.renumber())
        sc = QShortcut(QKeySequence.StandardKey.Delete, self.list)
        sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        sc.activated.connect(self.delete_sel)
        self.body.addWidget(self.list, 1)
        self.add_run_button("Enregistrer sous…", self.save)

    # -- chargement --------------------------------------------------------
    def _pick(self):
        global LAST_DIR
        p, _ = QFileDialog.getOpenFileName(self, "Choisir un PDF", LAST_DIR, "PDF (*.pdf)")
        if not p:
            return None
        LAST_DIR = os.path.dirname(p)
        pw = self.win.open_password(p)
        return None if pw is None else (p, pw)

    def open_new(self):
        src = self._pick()
        if not src:
            return
        self.list.clear()
        self.sources = []
        self.load(src)

    def add_pdf(self):
        src = self._pick()
        if src:
            self.load(src)

    def load(self, src):
        si = len(self.sources)
        self.sources.append(src)
        path, pw = src
        self.win.run_task(lambda: ops.render_thumbnails(path, pw, self.THUMB),
                          lambda thumbs: self.add_thumbs(si, thumbs))

    def add_thumbs(self, si, thumbs):
        for pi, (w, h, stride, data) in enumerate(thumbs):
            it = QListWidgetItem()
            it.setData(UR, (si, pi))
            it.setData(UR + 1, 0)
            it.setData(UR + 2, to_pixmap(w, h, stride, data))
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            it.setToolTip(f"{os.path.basename(self.sources[si][0])} — page {pi + 1}")
            self.refresh_icon(it)
            self.list.addItem(it)
        self.renumber()

    def add_blank(self):
        pm = QPixmap(int(self.THUMB * 0.707), self.THUMB)
        pm.fill(QColor("white"))
        it = QListWidgetItem()
        it.setData(UR, (-1, 0))
        it.setData(UR + 1, 0)
        it.setData(UR + 2, pm)
        it.setToolTip("Page blanche")
        self.refresh_icon(it)
        self.list.addItem(it)
        self.renumber()

    # -- édition -----------------------------------------------------------
    @staticmethod
    def refresh_icon(it):
        pm, rot = it.data(UR + 2), it.data(UR + 1)
        if rot:
            pm = pm.transformed(QTransform().rotate(rot))
        it.setIcon(QIcon(pm))

    def renumber(self):
        for r in range(self.list.count()):
            self.list.item(r).setText(str(r + 1))

    def rotate(self, deg):
        for it in self.list.selectedItems():
            it.setData(UR + 1, (it.data(UR + 1) + deg) % 360)
            self.refresh_icon(it)

    def delete_sel(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self.renumber()

    def preview(self, it):
        si, pi = it.data(UR)
        if si < 0:
            return
        path, pw = self.sources[si]
        pm = to_pixmap(*ops.render_page(path, pw, pi, 110))
        rot = it.data(UR + 1)
        if rot:
            pm = pm.transformed(QTransform().rotate(rot))
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{os.path.basename(path)} — page {pi + 1}")
        lay = QVBoxLayout(dlg)
        sc = QScrollArea()
        lbl = QLabel()
        lbl.setPixmap(pm)
        sc.setWidget(lbl)
        lay.addWidget(sc)
        dlg.resize(min(pm.width() + 40, 1000), min(pm.height() + 40, 900))
        dlg.exec()

    def save(self):
        n = self.list.count()
        if not n:
            return self.win.warn("Aucune page : ouvre d'abord un PDF.")
        items = []
        for r in range(n):
            it = self.list.item(r)
            si, pi = it.data(UR)
            items.append((si, pi, it.data(UR + 1)))
        first = Path(self.sources[0][0]) if self.sources else Path(LAST_DIR) / "document.pdf"
        out = self.win.ask_save(f"{first.stem}_organise.pdf", "PDF (*.pdf)", ".pdf", str(first.parent))
        if not out:
            return
        sources = list(self.sources)
        self.win.run_task(lambda: ops.build_from_pages(sources, items, out),
                          lambda k: self.win.notify(f"Document enregistré : {k} page(s).", out))


class SplitPage(SimpleTool):
    run_label = "Découper"

    def __init__(self, win):
        super().__init__(win, "Découper / extraire des pages",
                         "Extrais des pages dans un seul fichier, crée un fichier par plage, ou coupe toutes les N pages. "
                         "Plages : 1-3, 5, 8-  (« 5-3 » inverse l'ordre).")

    def build(self):
        self.mode = QComboBox()
        self.mode.addItem("Extraire des pages dans UN fichier", "extract")
        self.mode.addItem("Un fichier PAR plage", "ranges")
        self.mode.addItem("Un fichier toutes les N pages", "every")
        self.spec = QLineEdit()
        self.spec.setPlaceholderText("ex : 1-3, 5, 8-")
        self.n = QSpinBox()
        self.n.setRange(1, 9999)
        self.n.setValue(1)
        self.form.addRow("Mode", self.mode)
        self.form.addRow("Pages", self.spec)
        self.form.addRow("N =", self.n)
        self.mode.currentIndexChanged.connect(lambda _: self._toggle())
        self._toggle()

    def _toggle(self):
        every = self.mode.currentData() == "every"
        self.spec.setEnabled(not every)
        self.n.setEnabled(every)

    def collect(self):
        m = self.mode.currentData()
        if m != "every" and not self.spec.text().strip():
            raise ValueError("Indique les pages à extraire (ex : 1-3, 5).")
        return {"mode": m, "spec": self.spec.text(), "n": self.n.value()}

    def ask_output(self, path, params):
        stem, folder = Path(path).stem, str(Path(path).parent)
        if params["mode"] == "extract":
            return self.win.ask_save(f"{stem}_extrait.pdf", "PDF (*.pdf)", ".pdf", folder)
        return self.win.ask_dir(folder)

    def work(self, path, pw, out, p):
        if p["mode"] == "extract":
            return f"{ops.extract_pages(path, pw, p['spec'], out)} page(s) extraite(s)."
        if p["mode"] == "ranges":
            files = ops.split_by_ranges(path, pw, p["spec"], out)
        else:
            files = ops.split_every(path, pw, p["n"], out)
        return f"{len(files)} fichier(s) créé(s) dans le dossier choisi."


class CompressPage(SimpleTool):
    suffix = "_compresse"
    run_label = "Compresser"

    def __init__(self, win):
        super().__init__(win, "Compresser un PDF",
                         "Réduit la taille du fichier. « Moyen » convient à la plupart des documents.")

    def build(self):
        self.level = QComboBox()
        self.level.addItem("Léger — aucune perte de qualité", "leger")
        self.level.addItem("Moyen — images à ~130 dpi (recommandé)", "moyen")
        self.level.addItem("Fort — images à ~90 dpi, fichier minimal", "fort")
        self.level.setCurrentIndex(1)
        self.form.addRow("Niveau", self.level)

    def collect(self):
        return {"level": self.level.currentData()}

    def work(self, path, pw, out, p):
        before, after = ops.compress(path, pw, out, p["level"])
        if after >= before:
            return f"Ce fichier est déjà optimisé ({size_fmt(before)}) : pas de gain possible avec ce niveau."
        gain = 100 * (1 - after / before)
        return f"{size_fmt(before)} → {size_fmt(after)}  (−{gain:.0f} %)"


class WatermarkPage(SimpleTool):
    suffix = "_filigrane"
    run_label = "Ajouter le filigrane"

    def __init__(self, win):
        super().__init__(win, "Filigrane", "Ajoute un texte en diagonale (ex : CONFIDENTIEL, BROUILLON) sur les pages.")

    def build(self):
        self.text = QLineEdit("CONFIDENTIEL")
        self.size = QSpinBox()
        self.size.setRange(8, 400)
        self.size.setValue(70)
        self.opacity = QSpinBox()
        self.opacity.setRange(5, 100)
        self.opacity.setValue(25)
        self.opacity.setSuffix(" %")
        self.angle = QSpinBox()
        self.angle.setRange(-90, 90)
        self.angle.setValue(45)
        self.angle.setSuffix(" °")
        self.color = ColorButton("#808080")
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("vide = toutes les pages")
        for lbl, w in [("Texte", self.text), ("Taille", self.size), ("Opacité", self.opacity),
                       ("Angle", self.angle), ("Couleur", self.color), ("Pages", self.pages)]:
            self.form.addRow(lbl, w)

    def collect(self):
        return dict(text=self.text.text(), size=self.size.value(), opacity=self.opacity.value() / 100,
                    angle=self.angle.value(), color=self.color.rgb(), pages=self.pages.text())

    def work(self, path, pw, out, p):
        n = ops.add_watermark(path, pw, out, p["text"], p["size"], p["opacity"], p["angle"], p["color"], p["pages"])
        return f"Filigrane ajouté sur {n} page(s)."


class NumberPage(SimpleTool):
    suffix = "_numerote"
    run_label = "Numéroter"

    def __init__(self, win):
        super().__init__(win, "Numéroter les pages", "Ajoute « Page 1 / 10 » (ou le format de ton choix) sur chaque page.")

    def build(self):
        self.pos = QComboBox()
        for label, key in POS6:
            self.pos.addItem(label, key)
        self.pos.setCurrentIndex(POS6.index(("Bas centre", "bas-centre")))
        self.fmt = QLineEdit("Page {n} / {N}")
        self.start = QSpinBox()
        self.start.setRange(0, 9999)
        self.start.setValue(1)
        self.size = QSpinBox()
        self.size.setRange(6, 48)
        self.size.setValue(10)
        self.margin = QSpinBox()
        self.margin.setRange(5, 120)
        self.margin.setValue(28)
        self.skip = QCheckBox("Ne pas numéroter la première page (couverture)")
        for lbl, w in [("Position", self.pos), ("Format", self.fmt), ("Premier numéro", self.start),
                       ("Taille (pt)", self.size), ("Marge (pt)", self.margin)]:
            self.form.addRow(lbl, w)
        self.form.addRow("", self.skip)

    def collect(self):
        return dict(pos=self.pos.currentData(), fmt=self.fmt.text(), start=self.start.value(),
                    size=self.size.value(), margin=self.margin.value(), skip=self.skip.isChecked())

    def work(self, path, pw, out, p):
        n = ops.add_page_numbers(path, pw, out, p["pos"], p["fmt"], p["start"], p["size"], p["margin"], p["skip"])
        return f"{n} page(s) numérotée(s)."


class StampPage(SimpleTool):
    suffix = "_tampon"
    run_label = "Insérer"

    def __init__(self, win):
        super().__init__(win, "Insérer un texte ou une image (tampon, signature)",
                         "Place un texte ou une image PNG/JPG (signature, logo, tampon) à l'endroit voulu. "
                         "Les PNG transparents sont conservés.")

    def build(self):
        self.kind = QComboBox()
        self.kind.addItem("Texte", "text")
        self.kind.addItem("Image", "image")
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Texte à insérer (plusieurs lignes possibles)")
        self.text.setFixedHeight(70)
        self.img = FilePicker("Images (*.png *.jpg *.jpeg *.webp *.bmp)", "Choisis une image (signature, logo…)")
        self.pos = QComboBox()
        for label, key in POS9:
            self.pos.addItem(label, key)
        self.pos.setCurrentIndex(8)
        self.size = QSpinBox()
        self.size.setRange(4, 400)
        self.size.setValue(24)
        self.size_lbl = QLabel("Taille (pt)")
        self.margin = QSpinBox()
        self.margin.setRange(0, 200)
        self.margin.setValue(24)
        self.color = ColorButton("#000000")
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("vide = toutes les pages")
        self.form.addRow("Type", self.kind)
        self.form.addRow("Texte", self.text)
        self.form.addRow("Image", self.img)
        self.form.addRow("Position", self.pos)
        self.form.addRow(self.size_lbl, self.size)
        self.form.addRow("Marge (pt)", self.margin)
        self.form.addRow("Couleur du texte", self.color)
        self.form.addRow("Pages", self.pages)
        self.kind.currentIndexChanged.connect(lambda _: self._toggle())
        self._toggle()

    def _toggle(self):
        is_img = self.kind.currentData() == "image"
        self.text.setEnabled(not is_img)
        self.color.setEnabled(not is_img)
        self.img.setEnabled(is_img)
        self.size_lbl.setText("Largeur (% de la page)" if is_img else "Taille (pt)")
        self.size.setValue(20 if is_img else 24)

    def collect(self):
        if self.kind.currentData() == "image":
            if not self.img.path():
                raise ValueError("Choisis une image.")
            return dict(text="", image=self.img.path(), pos=self.pos.currentData(), size=self.size.value(),
                        margin=self.margin.value(), color=(0, 0, 0), pages=self.pages.text())
        if not self.text.toPlainText().strip():
            raise ValueError("Saisis le texte à insérer.")
        return dict(text=self.text.toPlainText(), image="", pos=self.pos.currentData(), size=self.size.value(),
                    margin=self.margin.value(), color=self.color.rgb(), pages=self.pages.text())

    def work(self, path, pw, out, p):
        n = ops.add_stamp(path, pw, out, p["pages"], p["text"], p["image"], p["pos"], p["size"],
                          p["margin"], 1.0, p["color"])
        return f"Élément inséré sur {n} page(s)."


class ProtectPage(SimpleTool):
    suffix = "_protege"
    run_label = "Appliquer"

    def __init__(self, win):
        super().__init__(win, "Protéger / déprotéger",
                         "Chiffrement AES-256 avec mot de passe d'ouverture, ou copie sans mot de passe "
                         "(tu dois connaître le mot de passe actuel).")

    def build(self):
        self.mode = QComboBox()
        self.mode.addItem("Protéger par mot de passe", "protect")
        self.mode.addItem("Retirer la protection", "unlock")
        self.form.addRow("Action", self.mode)
        self.box = QWidget()
        f = QFormLayout(self.box)
        f.setContentsMargins(0, 0, 0, 0)
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self.owner = QLineEdit()
        self.owner.setEchoMode(QLineEdit.EchoMode.Password)
        self.owner.setPlaceholderText("optionnel (généré aléatoirement si vide)")
        self.p_print = QCheckBox("Autoriser l'impression")
        self.p_print.setChecked(True)
        self.p_copy = QCheckBox("Autoriser la copie du texte")
        self.p_edit = QCheckBox("Autoriser la modification")
        f.addRow("Mot de passe d'ouverture", self.pw1)
        f.addRow("Confirmer", self.pw2)
        f.addRow("Mot de passe propriétaire", self.owner)
        f.addRow("", self.p_print)
        f.addRow("", self.p_copy)
        f.addRow("", self.p_edit)
        self.form.addRow(self.box)
        self.mode.currentIndexChanged.connect(lambda _: self.box.setVisible(self.mode.currentData() == "protect"))

    def collect(self):
        if self.mode.currentData() == "unlock":
            return {"mode": "unlock"}
        if not self.pw1.text():
            raise ValueError("Saisis un mot de passe d'ouverture.")
        if self.pw1.text() != self.pw2.text():
            raise ValueError("Les deux mots de passe ne correspondent pas.")
        return dict(mode="protect", pw=self.pw1.text(), owner=self.owner.text(),
                    print=self.p_print.isChecked(), copy=self.p_copy.isChecked(), edit=self.p_edit.isChecked())

    def ask_output(self, path, params):
        suffix = "_protege" if params["mode"] == "protect" else "_deverrouille"
        return self.win.ask_save(f"{Path(path).stem}{suffix}.pdf", "PDF (*.pdf)", ".pdf", str(Path(path).parent))

    def work(self, path, pw, out, p):
        if p["mode"] == "unlock":
            ops.unlock(path, pw, out)
            return "Copie sans mot de passe créée."
        ops.protect(path, pw, out, p["pw"], p["owner"], p["print"], p["copy"], p["edit"])
        return "PDF chiffré (AES-256). Note bien ton mot de passe : il n'existe aucun moyen de le récupérer."


class RedactPage(SimpleTool):
    suffix = "_caviarde"
    run_label = "Caviarder"

    def __init__(self, win):
        super().__init__(win, "Caviarder (masquer définitivement)",
                         "Les zones sont noircies ET le texte dessous est supprimé du fichier (pas un simple rectangle noir). "
                         "Vérifie toujours le résultat avant de diffuser le document.")

    def build(self):
        self.terms = QPlainTextEdit()
        self.terms.setPlaceholderText("Un terme par ligne (nom, numéro de dossier…)")
        self.terms.setFixedHeight(110)
        self.c_mail = QCheckBox("Adresses e-mail")
        self.c_iban = QCheckBox("IBAN")
        self.c_tel = QCheckBox("Numéros de téléphone")
        self.form.addRow("Termes à masquer", self.terms)
        self.form.addRow("Détection auto", self.c_mail)
        self.form.addRow("", self.c_iban)
        self.form.addRow("", self.c_tel)

    def collect(self):
        presets = [k for k, c in (("email", self.c_mail), ("iban", self.c_iban), ("telephone", self.c_tel))
                   if c.isChecked()]
        terms = self.terms.toPlainText().splitlines()
        if not [t for t in terms if t.strip()] and not presets:
            raise ValueError("Saisis au moins un terme ou coche une détection automatique.")
        return {"terms": terms, "presets": presets}

    def work(self, path, pw, out, p):
        n, missing = ops.redact(path, pw, out, p["terms"], p["presets"])
        msg = f"{n} zone(s) caviardée(s)."
        if missing:
            msg += "\nTermes introuvables : " + ", ".join(missing)
        return msg + "\nPense à vérifier visuellement le résultat."


class TextPage(SimpleTool):
    out_kind = "txt"
    run_label = "Extraire le texte"

    def __init__(self, win):
        super().__init__(win, "Extraire le texte", "Exporte le texte du PDF dans un fichier .txt (une section par page).")

    def work(self, path, pw, out, p):
        n = ops.extract_text(path, pw, out)
        if n == 0:
            return "Aucun texte trouvé : ce PDF est probablement un scan (image). Il faut un OCR (voir README)."
        return f"{n} caractères extraits."


class PdfToImagesPage(SimpleTool):
    out_kind = "dir"
    run_label = "Convertir"

    def __init__(self, win):
        super().__init__(win, "PDF → Images", "Exporte les pages en PNG ou JPG dans un dossier.")

    def build(self):
        self.fmt = QComboBox()
        self.fmt.addItem("PNG (sans perte)", "png")
        self.fmt.addItem("JPG (plus léger)", "jpg")
        self.dpi = QSpinBox()
        self.dpi.setRange(36, 600)
        self.dpi.setValue(150)
        self.dpi.setSuffix(" dpi")
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("vide = toutes les pages")
        self.form.addRow("Format", self.fmt)
        self.form.addRow("Résolution", self.dpi)
        self.form.addRow("Pages", self.pages)

    def collect(self):
        return dict(fmt=self.fmt.currentData(), dpi=self.dpi.value(), pages=self.pages.text())

    def work(self, path, pw, out, p):
        files = ops.pdf_to_images(path, pw, out, p["fmt"], p["dpi"], p["pages"])
        return f"{len(files)} image(s) créée(s)."


class MetadataPage(SimpleTool):
    suffix = "_meta"
    run_label = "Enregistrer"

    def __init__(self, win):
        super().__init__(win, "Métadonnées & nettoyage",
                         "Modifie titre / auteur / sujet / mots-clés, ou supprime tout ce qui peut trahir l'origine du fichier.")

    def build(self):
        self.title_ = QLineEdit()
        self.author = QLineEdit()
        self.subject = QLineEdit()
        self.keywords = QLineEdit()
        self.clean = QCheckBox("Nettoyage complet : supprimer métadonnées, XMP, JavaScript, miniatures, pièces jointes")
        self.form.addRow("Titre", self.title_)
        self.form.addRow("Auteur", self.author)
        self.form.addRow("Sujet", self.subject)
        self.form.addRow("Mots-clés", self.keywords)
        self.form.addRow("", self.clean)

    def on_src_changed(self, path):
        try:
            m = ops.read_metadata(path, self.win.pw_cache.get(path, ""))
        except Exception:
            m = {}
        self.title_.setText(m.get("title", ""))
        self.author.setText(m.get("author", ""))
        self.subject.setText(m.get("subject", ""))
        self.keywords.setText(m.get("keywords", ""))

    def collect(self):
        return dict(clean=self.clean.isChecked(), meta=dict(
            title=self.title_.text(), author=self.author.text(),
            subject=self.subject.text(), keywords=self.keywords.text()))

    def work(self, path, pw, out, p):
        if p["clean"]:
            ops.clean_metadata(path, pw, out)
            return "Fichier nettoyé."
        ops.write_metadata(path, pw, out, p["meta"])
        return "Métadonnées enregistrées."


# --------------------------------------------------------------------------- #
#  Rogner les pages — glisser sur l'aperçu ou saisir les marges
# --------------------------------------------------------------------------- #
class CropCanvas(QLabel):
    dragged = Signal(float, float, float, float)  # marges gauche/haut/droite/bas, en mm

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_pixmap = None
        self.zoom = 1.0
        self.page_w_mm = self.page_h_mm = 0.0
        self.margins = (0.0, 0.0, 0.0, 0.0)
        self._press = None

    def set_page(self, pixmap, zoom, w_pt, h_pt):
        self.page_pixmap = pixmap
        self.zoom = zoom
        self.page_w_mm, self.page_h_mm = w_pt / ops.MM, h_pt / ops.MM
        self.setFixedSize(pixmap.size())
        self.update()

    def set_margins(self, l, t, r, b):
        self.margins = (l, t, r, b)
        self.update()

    def mousePressEvent(self, e):
        if self.page_pixmap is not None:
            self._press = e.position()

    def mouseMoveEvent(self, e):
        if self._press is not None:
            self._live = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        if self._press is None or self.page_pixmap is None:
            return
        rect = QRectF(self._press, e.position()).normalized() if hasattr(self, "_live") else None
        self._press = None
        if rect is None or rect.width() < 6 or rect.height() < 6:
            return
        pw, ph = self.page_pixmap.width(), self.page_pixmap.height()
        l = max(0.0, rect.left()) / self.zoom / ops.MM
        t = max(0.0, rect.top()) / self.zoom / ops.MM
        r = max(0.0, (pw - rect.right())) / self.zoom / ops.MM
        b = max(0.0, (ph - rect.bottom())) / self.zoom / ops.MM
        self.dragged.emit(round(l, 1), round(t, 1), round(r, 1), round(b, 1))

    def paintEvent(self, e):
        if not self.page_pixmap:
            return super().paintEvent(e)
        p = QPainter(self)
        p.drawPixmap(0, 0, self.page_pixmap)
        l, t, r, b = self.margins
        x0, y0 = l * ops.MM * self.zoom, t * ops.MM * self.zoom
        x1 = self.page_pixmap.width() - r * ops.MM * self.zoom
        y1 = self.page_pixmap.height() - b * ops.MM * self.zoom
        p.setPen(QPen(QColor(0, 0, 0, 140), 1))
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRect(0, 0, self.page_pixmap.width(), int(y0))
        p.drawRect(0, int(y1), self.page_pixmap.width(), self.page_pixmap.height() - int(y1))
        p.drawRect(0, int(y0), int(x0), int(y1 - y0))
        p.drawRect(int(x1), int(y0), self.page_pixmap.width() - int(x1), int(y1 - y0))
        p.setPen(QPen(QColor(37, 99, 235), 2, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))


class CropPage(SimpleTool):
    suffix = "_rogne"
    run_label = "Rogner"

    def __init__(self, win):
        super().__init__(win, "Rogner les pages (crop)",
                         "Fais glisser directement sur l'aperçu pour définir la zone à garder, ou saisis les marges "
                         "en millimètres. Les marges grisées seront supprimées de la page.")

    def build(self):
        self.mm = {}
        row = QHBoxLayout()
        for key, label in [("left", "Gauche"), ("top", "Haut"), ("right", "Droite"), ("bottom", "Bas")]:
            s = QDoubleSpinBox()
            s.setRange(0, 500)
            s.setSuffix(" mm")
            s.setDecimals(1)
            s.valueChanged.connect(self._on_spin)
            self.mm[key] = s
            row.addWidget(QLabel(label))
            row.addWidget(s)
        self.form.addRow("Marges", row)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("vide = toutes les pages")
        self.form.addRow("Pages", self.pages)

        self.canvas = CropCanvas()
        self.canvas.dragged.connect(self._on_drag)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setFixedHeight(360)
        scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        scroll.setStyleSheet("QScrollArea { background: #d5d9e0; border: 1px solid #d1d5db; }")
        self.body.addWidget(scroll)

    def on_src_changed(self, path):
        try:
            pw = self.win.pw_cache.get(path, "")
            w, h, stride, data = ops.render_page(path, pw, 0, 100)
            doc = ops.open_pdf(path, pw)
            r = doc[0].rect
            doc.close()
            pm = to_pixmap(w, h, stride, data)
            self.canvas.set_page(pm, w / r.width, r.width, r.height)
            self._sync_canvas()
        except Exception:
            pass

    def _on_spin(self, _=None):
        self._sync_canvas()

    def _sync_canvas(self):
        self.canvas.set_margins(self.mm["left"].value(), self.mm["top"].value(),
                                self.mm["right"].value(), self.mm["bottom"].value())

    def _on_drag(self, l, t, r, b):
        for key, v in zip(("left", "top", "right", "bottom"), (l, t, r, b)):
            self.mm[key].blockSignals(True)
            self.mm[key].setValue(v)
            self.mm[key].blockSignals(False)
        self._sync_canvas()

    def collect(self):
        return dict(left=self.mm["left"].value(), top=self.mm["top"].value(),
                    right=self.mm["right"].value(), bottom=self.mm["bottom"].value(), pages=self.pages.text())

    def work(self, path, pw, out, p):
        n = ops.crop_pages(path, pw, out, p["left"], p["top"], p["right"], p["bottom"], p["pages"])
        return f"{n} page(s) rognée(s)."


# --------------------------------------------------------------------------- #
#  Réparer un PDF corrompu
# --------------------------------------------------------------------------- #
class RepairPage(ToolPage):
    def __init__(self, win):
        super().__init__(win, "Réparer un PDF corrompu",
                         "Pour un fichier endommagé, illisible ou qui refuse de s'ouvrir. "
                         "Reconstruit ce qui peut l'être ; les pages irrécupérables sont signalées.")
        self.src = FilePicker()
        row = QHBoxLayout()
        row.addWidget(QLabel("Fichier PDF"))
        row.addWidget(self.src, 1)
        self.body.addLayout(row)
        self.body.addStretch()
        self.add_run_button("Réparer", self.on_run)

    def on_run(self):
        path = self.src.path()
        if not path or not os.path.isfile(path):
            return self.win.warn("Choisis d'abord un fichier PDF.")
        pw = ""
        if ops.needs_password(path):
            pw = self.win.open_password(path)
            if pw is None:
                return
        out = self.win.ask_save(f"{Path(path).stem}_repare.pdf", "PDF (*.pdf)", ".pdf", str(Path(path).parent))
        if not out:
            return

        def done(result):
            ok, total = result
            if ok < total:
                self.win.notify(f"{ok} page(s) récupérée(s) sur {total}. Les autres étaient trop endommagées.", out)
            else:
                self.win.notify(f"Fichier réparé : {total} page(s) récupérée(s).", out)

        self.win.run_task(lambda: ops.repair(path, pw, out), done)


# --------------------------------------------------------------------------- #
#  Comparer deux PDF
# --------------------------------------------------------------------------- #
class ComparePage(ToolPage):
    def __init__(self, win):
        super().__init__(win, "Comparer deux PDF",
                         "Détecte les différences entre deux versions d'un même document : texte modifié et "
                         "différences visuelles (surlignées en rouge). Utile pour vérifier qu'un PDF n'a pas été altéré.")
        self.a = FilePicker(placeholder="Premier fichier (version A)")
        self.b = FilePicker(placeholder="Second fichier (version B)")
        f = QFormLayout()
        f.addRow("Fichier A", self.a)
        f.addRow("Fichier B", self.b)
        self.body.addLayout(f)
        self.body.addStretch()
        self.add_run_button("Comparer", self.on_run)

    def on_run(self):
        pa, pb = self.a.path(), self.b.path()
        if not pa or not pb or not os.path.isfile(pa) or not os.path.isfile(pb):
            return self.win.warn("Choisis les deux fichiers à comparer.")
        pwa = self.win.open_password(pa)
        if pwa is None:
            return
        pwb = self.win.open_password(pb)
        if pwb is None:
            return
        out_dir = self.win.ask_dir(str(Path(pa).parent))
        if not out_dir:
            return

        def done(r):
            if r["identical"]:
                return self.win.notify("Les deux fichiers sont strictement identiques (octet pour octet).")
            n = len(r["diff_pages"])
            total = max(r["pages_a"] or 0, r["pages_b"] or 0)
            msg = f"{n} page(s) différente(s) sur {total}.\nPages : {', '.join(map(str, r['diff_pages']))}"
            if r["images"]:
                msg += f"\n{len(r['images'])} image(s) de différence enregistrée(s), plus un rapport texte."
            self.win.notify(msg, out_dir)

        self.win.run_task(lambda: ops.compare_pdfs(pa, pwa, pb, pwb, out_dir), done)


# --------------------------------------------------------------------------- #
#  OCR — rendre un PDF scanné cherchable
# --------------------------------------------------------------------------- #
class OcrPage(SimpleTool):
    suffix = "_ocr"
    run_label = "Lancer l'OCR"

    def __init__(self, win):
        super().__init__(win, "OCR — rendre un PDF cherchable",
                         "Ajoute une couche de texte invisible sur un PDF scanné (image) pour pouvoir le "
                         "chercher et copier son contenu. L'apparence du document ne change pas.")
        self._refresh_availability()

    def build(self):
        self.warn_lbl = QLabel()
        self.warn_lbl.setWordWrap(True)
        self.warn_lbl.setStyleSheet("color:#b45309; background:#fffbeb; border:1px solid #fde68a; "
                                    "border-radius:6px; padding:8px;")
        self.warn_lbl.hide()
        self.form.addRow(self.warn_lbl)

        self.lang_list = QListWidget()
        self.lang_list.setFixedHeight(110)
        self.lang_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.form.addRow("Langue(s) du texte", self.lang_list)

        recheck = QPushButton("Vérifier à nouveau la disponibilité de l'OCR")
        recheck.clicked.connect(self._refresh_availability)
        self.form.addRow("", recheck)

        self.force = QCheckBox("Forcer l'OCR même si le PDF contient déjà du texte")
        self.deskew = QCheckBox("Corriger l'inclinaison des pages scannées")
        self.deskew.setChecked(True)
        self.rotate = QCheckBox("Corriger l'orientation (portrait/paysage) automatiquement")
        self.rotate.setChecked(True)
        self.form.addRow("", self.force)
        self.form.addRow("", self.deskew)
        self.form.addRow("", self.rotate)

    def _refresh_availability(self):
        available = ops.ocr_available()
        self.lang_list.clear()
        if not available:
            self.warn_lbl.setText(
                "Tesseract OCR n'est pas installé (ou introuvable) sur ce poste : l'OCR est indisponible.\n"
                "Installe-le puis clique sur « Vérifier à nouveau » — voir le README pour le lien et la marche à suivre.")
            self.warn_lbl.show()
            self.lang_list.setEnabled(False)
        else:
            self.warn_lbl.hide()
            self.lang_list.setEnabled(True)
            langs = ops.ocr_languages() or ["eng"]
            for code in langs:
                it = QListWidgetItem(code)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked if code in ("fra", "eng") else Qt.CheckState.Unchecked)
                self.lang_list.addItem(it)
        self.btn.setEnabled(available)

    def collect(self):
        if not ops.ocr_available():
            raise ValueError("L'OCR n'est pas disponible sur ce poste (Tesseract introuvable).")
        langs = [self.lang_list.item(i).text() for i in range(self.lang_list.count())
                if self.lang_list.item(i).checkState() == Qt.CheckState.Checked]
        if not langs:
            raise ValueError("Coche au moins une langue.")
        return dict(langs="+".join(langs), force=self.force.isChecked(),
                    deskew=self.deskew.isChecked(), rotate=self.rotate.isChecked())

    def work(self, path, pw, out, p):
        ops.ocr_pdf(path, pw, out, p["langs"], p["force"], p["deskew"], p["rotate"])
        return "OCR terminé : le PDF est maintenant cherchable."


# --------------------------------------------------------------------------- #
#  Fenêtre principale
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Toolkit — 100 % local")
        self.resize(1120, 760)
        self.pool = QThreadPool.globalInstance()
        self._tasks: dict[int, tuple] = {}
        self._next_id = 0
        self.pw_cache: dict[str, str] = {}

        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(215)
        self.stack = QStackedWidget()
        lay.addWidget(self.sidebar)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        from editor import EditorPage
        groups = [
            ("ÉDITER", [("Éditer librement", EditorPage)]),
            ("ORGANISER", [("Fusionner", MergePage), ("Organiser les pages", OrganizePage),
                           ("Découper / extraire", SplitPage), ("Rogner (crop)", CropPage)]),
            ("OPTIMISER", [("Compresser", CompressPage)]),
            ("MODIFIER", [("Filigrane", WatermarkPage), ("Numéroter les pages", NumberPage),
                          ("Texte / image / signature", StampPage), ("Métadonnées", MetadataPage)]),
            ("SÉCURITÉ", [("Protéger / déprotéger", ProtectPage), ("Caviarder", RedactPage)]),
            ("CONVERTIR", [("Images → PDF", ImagesToPdfPage), ("PDF → Images", PdfToImagesPage),
                           ("Extraire le texte", TextPage)]),
            ("AVANCÉ", [("OCR (rendre cherchable)", OcrPage), ("Comparer deux PDF", ComparePage),
                       ("Réparer un PDF corrompu", RepairPage)]),
        ]
        self._row_to_page: dict[int, int] = {}
        first_row = None
        for gname, tools in groups:
            head = QListWidgetItem(gname)
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            f = head.font()
            f.setBold(True)
            f.setPointSizeF(max(7.0, f.pointSizeF() - 2))
            head.setFont(f)
            head.setForeground(QColor("#9ca3af"))
            self.sidebar.addItem(head)
            for label, cls in tools:
                self.sidebar.addItem(QListWidgetItem(label))
                row = self.sidebar.count() - 1
                self._row_to_page[row] = self.stack.addWidget(cls(self))
                first_row = row if first_row is None else first_row
        self.sidebar.currentRowChanged.connect(
            lambda r: self.stack.setCurrentIndex(self._row_to_page[r]) if r in self._row_to_page else None)
        self.sidebar.setCurrentRow(first_row)

        self.bar = QProgressBar()
        self.bar.setFixedWidth(160)
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.hide()
        self.statusBar().addPermanentWidget(self.bar)
        self.statusBar().showMessage("Tout est traité sur ton ordinateur — aucun fichier n'est envoyé sur Internet.")

    # -- tâches ------------------------------------------------------------
    def run_task(self, fn, on_done=None):
        tid = self._next_id
        self._next_id += 1
        sig = TaskSignals()
        sig.done.connect(self._task_done)
        sig.error.connect(self._task_error)
        task = Task(fn, sig, tid)
        self._tasks[tid] = (task, sig, on_done)
        self._busy(True)
        self.pool.start(task)

    def _busy(self, on: bool):
        self.bar.setVisible(on)
        self.stack.setEnabled(not on)
        self.sidebar.setEnabled(not on)

    def _task_done(self, tid, result):
        _, _, cb = self._tasks.pop(tid)
        self._busy(bool(self._tasks))
        if cb:
            cb(result)

    def _task_error(self, tid, msg):
        self._tasks.pop(tid, None)
        self._busy(bool(self._tasks))
        self.warn(msg, critical=True)

    # -- dialogues ---------------------------------------------------------
    def warn(self, text, critical=False):
        (QMessageBox.critical if critical else QMessageBox.warning)(self, "PDF Toolkit", text)

    def notify(self, text, path=None):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Terminé")
        box.setText(text)
        b_file = None
        if path and os.path.isfile(path):
            b_file = box.addButton("Ouvrir le fichier", QMessageBox.ButtonRole.ActionRole)
        b_dir = box.addButton("Ouvrir le dossier", QMessageBox.ButtonRole.ActionRole) if path else None
        box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        clicked = box.clickedButton()
        if path and clicked is b_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif path and clicked is b_dir:
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def ask_save(self, default_name, filt, ext, start_dir=None):
        global LAST_DIR
        start = os.path.join(start_dir or LAST_DIR, default_name)
        p, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", start, filt)
        if not p:
            return None
        if not p.lower().endswith(ext):
            p += ext
        LAST_DIR = os.path.dirname(p)
        return p

    def ask_dir(self, start_dir=None):
        global LAST_DIR
        p = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination", start_dir or LAST_DIR)
        if p:
            LAST_DIR = p
        return p or None

    def open_password(self, path: str):
        """Retourne le mot de passe ('' si non protégé) ou None si l'utilisateur annule / erreur."""
        pw = self.pw_cache.get(path, "")
        while True:
            try:
                ops.open_pdf(path, pw).close()
                self.pw_cache[path] = pw
                return pw
            except ops.PasswordRequired:
                pw, ok = QInputDialog.getText(self, "PDF protégé",
                                              f"Mot de passe pour « {os.path.basename(path)} » :",
                                              QLineEdit.EchoMode.Password)
                if not ok:
                    return None
            except Exception as e:
                self.warn(str(e), critical=True)
                return None


def apply_style(app: QApplication):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, color in [(QPalette.ColorRole.Window, "#f9fafb"), (QPalette.ColorRole.WindowText, "#111827"),
                        (QPalette.ColorRole.Base, "#ffffff"), (QPalette.ColorRole.AlternateBase, "#f3f4f6"),
                        (QPalette.ColorRole.Text, "#111827"), (QPalette.ColorRole.Button, "#f3f4f6"),
                        (QPalette.ColorRole.ButtonText, "#111827"), (QPalette.ColorRole.Highlight, "#2563eb"),
                        (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, "#ffffff"),
                        (QPalette.ColorRole.ToolTipText, "#111827"),
                        (QPalette.ColorRole.PlaceholderText, "#9ca3af")]:
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setStyleSheet(QSS)


def main():
    app = QApplication(sys.argv)
    apply_style(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
