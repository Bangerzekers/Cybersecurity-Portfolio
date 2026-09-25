"""
editor.py — l'éditeur visuel : on ouvre un PDF et on clique dessus pour le modifier
comme un document (texte, images, surlignage, dessin, champs de formulaire…).
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
                               QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget)

import app as A
import pdf_ops as ops

ALIGNS = [("Gauche", 0), ("Centre", 1), ("Droite", 2), ("Justifié", 3)]
MODES = [
    ("select", "Sélectionner", "Clique un texte, une image ou un champ pour le modifier. Clic droit = menu."),
    ("text", "Ajouter texte", "Clique à l'endroit où insérer le texte."),
    ("image", "Ajouter image", "Clique à l'endroit où insérer l'image."),
    ("highlight", "Surligner", "Fais glisser sur les mots à surligner."),
    ("underline", "Souligner", "Fais glisser sur les mots à souligner."),
    ("strikeout", "Barrer", "Fais glisser sur les mots à barrer."),
    ("draw", "Dessiner", "Fais glisser pour dessiner à main levée."),
    ("rect", "Rectangle", "Fais glisser pour tracer un rectangle."),
    ("erase", "Gomme", "Fais glisser sur la zone à effacer définitivement."),
]
DRAG_MODES = {"highlight", "underline", "strikeout", "rect", "erase"}
HINT = {k: h for k, _, h in MODES}


def _contains(rect, x, y, pad=0.0):
    x0, y0, x1, y1 = rect
    return x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad


def _field_label(f):
    tn = (f.get("type_name") or "").lower()
    kind = ("case à cocher" if "check" in tn else "bouton radio" if "radio" in tn else
            "liste déroulante" if "combo" in tn else "liste" if "list" in tn else
            "signature" if "signat" in tn else "bouton" if "push" in tn else "champ de texte")
    return f"{kind} « {f.get('name') or '(sans nom)'} »"


# --------------------------------------------------------------------------- #
#  Boîte de dialogue : propriétés du texte (ajout ou modification)
# --------------------------------------------------------------------------- #
class TextPropsDialog(QDialog):
    def __init__(self, parent, initial: dict, title="Texte"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        self.text = QPlainTextEdit(initial.get("text", ""))
        self.text.setFixedHeight(110)
        self.text.setFocus()
        lay.addWidget(self.text)

        form = QFormLayout()
        self.family = QComboBox()
        self.family.addItems(list(ops.FAMILIES))
        self.family.setCurrentText(initial.get("family", ops._FAM_KEYS[0]))
        self.bold = QCheckBox("Gras")
        self.bold.setChecked(initial.get("bold", False))
        self.italic = QCheckBox("Italique")
        self.italic.setChecked(initial.get("italic", False))
        self.size = QSpinBox()
        self.size.setRange(4, 300)
        self.size.setValue(int(initial.get("size", 12)))
        self.align = QComboBox()
        for label, val in ALIGNS:
            self.align.addItem(label, val)
        self.align.setCurrentIndex(initial.get("align", 0))
        self.color = A.ColorButton(QColor.fromRgbF(*initial.get("color", (0, 0, 0))).name())
        row = QHBoxLayout()
        row.addWidget(self.bold)
        row.addWidget(self.italic)
        form.addRow("Police", self.family)
        form.addRow("", row)
        form.addRow("Taille (pt)", self.size)
        form.addRow("Alignement", self.align)
        form.addRow("Couleur", self.color)
        lay.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self) -> dict:
        return dict(text=self.text.toPlainText(), family=self.family.currentText(),
                    bold=self.bold.isChecked(), italic=self.italic.isChecked(),
                    size=self.size.value(), color=self.color.rgb(), align=self.align.currentData())


# --------------------------------------------------------------------------- #
#  Le canevas : affiche la page et capte les clics / glissés
# --------------------------------------------------------------------------- #
class PageCanvas(QWidget):
    itemClicked = Signal(dict)
    emptyClicked = Signal(float, float)
    dragDone = Signal(str, object)
    deleteRequested = Signal(dict)
    replaceRequested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.mode = "select"
        self.zoom = 1.0
        self.draw_color = (0, 0, 0.8)
        self.draw_width = 2.0
        self._pixmap = None
        self._structure = None
        self._hover = None
        self._press = None
        self._path: list[QPointF] = []
        self._dragging = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # -- données -------------------------------------------------------------
    def set_data(self, pixmap, structure, zoom):
        self._pixmap, self._structure, self.zoom = pixmap, structure, zoom
        self._hover = None
        self.setFixedSize(pixmap.size())
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self._press = None
        self._path = []
        self._dragging = False
        self.setCursor(Qt.CursorShape.CrossCursor if mode != "select" else Qt.CursorShape.ArrowCursor)
        self.update()

    # -- conversions -----------------------------------------------------------
    def _to_pt(self, p: QPointF):
        return (p.x() / self.zoom, p.y() / self.zoom)

    def _rect_to_pt(self, r: QRectF, w, h, min_h=0.0):
        r = r.normalized()
        x0 = max(0.0, min(w, r.left() / self.zoom))
        y0 = max(0.0, min(h, r.top() / self.zoom))
        x1 = max(0.0, min(w, r.right() / self.zoom))
        y1 = max(0.0, min(h, r.bottom() / self.zoom))
        if min_h and (y1 - y0) < min_h:  # glisser bien à l'horizontale le long d'une ligne doit rester efficace
            mid = (y0 + y1) / 2
            y0, y1 = max(0.0, mid - min_h / 2), min(h, mid + min_h / 2)
        return [x0, y0, x1, y1]

    def _hit_test(self, p: QPointF):
        if not self._structure:
            return None
        x, y = self._to_pt(p)
        for f in self._structure["fields"]:
            if _contains(f["rect"], x, y, 1.5):
                return {"kind": "field", **f}
        for im in self._structure["images"]:
            if _contains(im["rect"], x, y):
                return {"kind": "image", **im}
        best = None
        for l in self._structure["lines"]:
            if _contains(l["rect"], x, y, 2.0):
                if best is None or (l["rect"][3] - l["rect"][1]) < (best["rect"][3] - best["rect"][1]):
                    best = l
        return {"kind": "line", **best} if best else None

    # -- souris ----------------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._pixmap is None:
            return
        self._press = e.position()
        self._path = [e.position()]
        self._dragging = False

    def mouseMoveEvent(self, e):
        if self._pixmap is None:
            return
        if e.buttons() & Qt.MouseButton.LeftButton and self._press is not None:
            self._path.append(e.position())
            if (e.position() - self._press).manhattanLength() > 4:
                self._dragging = True
            self.update()
        elif self.mode == "select":
            item = self._hit_test(e.position())

            def _key(it):
                return None if it is None else (it["kind"], it.get("name") or tuple(it["rect"]))

            if _key(item) != _key(self._hover):
                self._hover = item
                self.setCursor(Qt.CursorShape.PointingHandCursor if item else Qt.CursorShape.ArrowCursor)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press is None or self._pixmap is None:
            self._press = None
            return
        end = e.position()
        w, h = self._structure["width"], self._structure["height"]
        if self.mode == "draw":
            if len(self._path) >= 2:
                self.dragDone.emit("draw", [self._to_pt(p) for p in self._path])
        elif self.mode in DRAG_MODES:
            if self._dragging:
                min_h = 8.0 if self.mode in ("highlight", "underline", "strikeout") else 0.0
                rect = self._rect_to_pt(QRectF(self._press, end), w, h, min_h)
                if rect[2] - rect[0] > 1 and rect[3] - rect[1] > 1:
                    self.dragDone.emit(self.mode, rect)
        elif not self._dragging:
            if self.mode == "select":
                item = self._hit_test(end)
                if item:
                    self.itemClicked.emit(item)
            elif self.mode in ("text", "image"):
                x, y = self._to_pt(end)
                self.emptyClicked.emit(x, y)
        self._press = None
        self._path = []
        self._dragging = False
        self.update()

    def contextMenuEvent(self, e):
        item = self._hit_test(QPointF(e.pos()))
        if not item:
            return
        menu = QMenu(self)
        if item["kind"] == "line":
            menu.addAction("Modifier le texte", lambda: self.itemClicked.emit(item))
            menu.addAction("Supprimer le texte", lambda: self.deleteRequested.emit(item))
        elif item["kind"] == "image":
            menu.addAction("Remplacer l'image…", lambda: self.replaceRequested.emit(item))
            menu.addAction("Supprimer l'image", lambda: self.deleteRequested.emit(item))
        elif item["kind"] == "field":
            menu.addAction("Modifier la valeur", lambda: self.itemClicked.emit(item))
            menu.addAction("Vider le champ", lambda: self.deleteRequested.emit(item))
        menu.exec(e.globalPos())

    def leaveEvent(self, e):
        self._hover = None
        self.update()

    # -- affichage ---------------------------------------------------------
    def paintEvent(self, e):
        if not self._pixmap:
            return
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pixmap)
        if self._hover and not self._dragging:
            r = self._hover["rect"]
            pen = QPen(QColor(37, 99, 235), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(r[0] * self.zoom - 2, r[1] * self.zoom - 2,
                              (r[2] - r[0]) * self.zoom + 4, (r[3] - r[1]) * self.zoom + 4))
        if self._dragging and len(self._path) >= 2:
            if self.mode == "draw":
                col = QColor.fromRgbF(*self.draw_color)
                p.setPen(QPen(col, self.draw_width, Qt.PenStyle.SolidLine,
                             Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                path = QPainterPath(self._path[0])
                for pt in self._path[1:]:
                    path.lineTo(pt)
                p.drawPath(path)
            else:
                col = QColor(37, 99, 235) if self.mode != "erase" else QColor(20, 20, 20)
                rect = QRectF(self._press, self._path[-1]).normalized()
                p.setPen(QPen(col, 1.5, Qt.PenStyle.DashLine))
                p.setBrush(QColor(col.red(), col.green(), col.blue(), 60))
                p.drawRect(rect)


# --------------------------------------------------------------------------- #
#  La page « Éditer librement »
# --------------------------------------------------------------------------- #
class EditorPage(A.ToolPage):
    ZOOM_MIN, ZOOM_MAX, ZOOM_STEP = 0.5, 3.0, 0.15

    def __init__(self, win):
        super().__init__(win, "Éditer librement",
                         "Ouvre un PDF et modifie-le directement : clique un texte pour le corriger, "
                         "ajoute du texte ou une image où tu veux, surligne, dessine, ou remplis un formulaire. "
                         "Clic droit sur un élément = modifier / supprimer.")
        self.doc: pymupdf.Document | None = None
        self.path = ""
        self.pw = ""
        self.page_index = 0
        self.zoom = 1.3
        self.undo_stack: list[bytes] = []
        self.redo_stack: list[bytes] = []
        self.dirty = False

        self.src = A.FilePicker()
        self.src.changed.connect(self.open_file)
        top = QHBoxLayout()
        top.addWidget(QLabel("Fichier PDF"))
        top.addWidget(self.src, 1)
        self.body.addLayout(top)

        # -- barre d'outils : navigation, zoom, undo, enregistrer ----------
        bar = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.lbl_page = QLabel("—")
        self.btn_prev.clicked.connect(lambda: self.goto(self.page_index - 1))
        self.btn_next.clicked.connect(lambda: self.goto(self.page_index + 1))
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out.clicked.connect(lambda: self.set_zoom(self.zoom - self.ZOOM_STEP))
        self.btn_zoom_in.clicked.connect(lambda: self.set_zoom(self.zoom + self.ZOOM_STEP))
        self.btn_undo = QPushButton("↶ Annuler")
        self.btn_redo = QPushButton("↷ Rétablir")
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo.clicked.connect(self.redo)
        self.btn_save = QPushButton("Enregistrer sous…")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save_as)
        for w in (self.btn_prev, self.lbl_page, self.btn_next):
            bar.addWidget(w)
        bar.addSpacing(16)
        bar.addWidget(self.btn_zoom_out)
        bar.addWidget(self.btn_zoom_in)
        bar.addSpacing(16)
        bar.addWidget(self.btn_undo)
        bar.addWidget(self.btn_redo)
        bar.addStretch()
        bar.addWidget(self.btn_save)
        self.body.addLayout(bar)

        # -- barre d'outils : modes -----------------------------------------
        mrow = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for key, label, _ in MODES:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self.set_mode(k))
            self.mode_group.addButton(b)
            mrow.addWidget(b)
            if key == "select":
                b.setChecked(True)
        mrow.addStretch()
        self.body.addLayout(mrow)

        # -- barre d'outils : options contextuelles -------------------------
        orow = QHBoxLayout()
        self.opt_family = QComboBox()
        self.opt_family.addItems(list(ops.FAMILIES))
        self.opt_bold = QCheckBox("Gras")
        self.opt_italic = QCheckBox("Italique")
        self.opt_size = QSpinBox()
        self.opt_size.setRange(4, 300)
        self.opt_size.setValue(12)
        self.opt_align = QComboBox()
        for label, val in ALIGNS:
            self.opt_align.addItem(label, val)
        self.opt_color = A.ColorButton("#000000")
        self.opt_width = QSpinBox()
        self.opt_width.setRange(1, 30)
        self.opt_width.setValue(2)
        self.opt_fill = QCheckBox("Rempli")
        self.opt_imgwidth = QSpinBox()
        self.opt_imgwidth.setRange(2, 100)
        self.opt_imgwidth.setValue(25)
        self.opt_imgwidth.setSuffix(" %")
        self._opt_widgets = [
            (QLabel("Police"), self.opt_family), (None, self.opt_bold), (None, self.opt_italic),
            (QLabel("Taille"), self.opt_size), (QLabel("Alignement"), self.opt_align),
            (QLabel("Couleur"), self.opt_color), (QLabel("Épaisseur"), self.opt_width),
            (None, self.opt_fill), (QLabel("Largeur image"), self.opt_imgwidth),
        ]
        for lbl, w in self._opt_widgets:
            if lbl:
                orow.addWidget(lbl)
            orow.addWidget(w)
        orow.addStretch()
        self.body.addLayout(orow)

        self.hint = QLabel(HINT["select"])
        self.hint.setObjectName("muted")
        self.body.addWidget(self.hint)

        # -- canevas -------------------------------------------------------
        self.canvas = PageCanvas()
        self.canvas.itemClicked.connect(self.on_item_clicked)
        self.canvas.emptyClicked.connect(self.on_empty_clicked)
        self.canvas.dragDone.connect(self.on_drag_done)
        self.canvas.deleteRequested.connect(self.on_delete_requested)
        self.canvas.replaceRequested.connect(self.on_replace_requested)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        scroll.setStyleSheet("QScrollArea { background: #d5d9e0; border: 1px solid #d1d5db; }")
        self.body.addWidget(scroll, 1)

        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_as)

        self.set_mode("select")
        self._sync_buttons()

    # -- ouverture / navigation --------------------------------------------
    def open_file(self, path):
        pw = self.win.open_password(path)
        if pw is None:
            return
        try:
            doc = ops.open_pdf(path, pw)
        except ops.PdfError as e:
            return self.win.warn(str(e), critical=True)
        if self.doc:
            self.doc.close()
        self.doc, self.path, self.pw = doc, path, pw
        self.page_index = 0
        self.undo_stack, self.redo_stack, self.dirty = [], [], False
        self.refresh()

    def goto(self, index):
        if self.doc and 0 <= index < self.doc.page_count:
            self.page_index = index
            self.refresh()

    def set_zoom(self, z):
        self.zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, z))
        if self.doc:
            self.refresh()

    def refresh(self):
        if not self.doc:
            self.lbl_page.setText("—")
            self._sync_buttons()
            return
        page = self.doc[self.page_index]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
        pm = A.to_pixmap(pix.width, pix.height, pix.stride, bytes(pix.samples))
        self.canvas.set_data(pm, ops.page_structure(page), self.zoom)
        self.lbl_page.setText(f"Page {self.page_index + 1} / {self.doc.page_count}")
        self._sync_buttons()

    def _sync_buttons(self):
        has_doc = self.doc is not None
        self.btn_prev.setEnabled(has_doc and self.page_index > 0)
        self.btn_next.setEnabled(has_doc and self.doc and self.page_index < self.doc.page_count - 1)
        self.btn_undo.setEnabled(bool(self.undo_stack))
        self.btn_redo.setEnabled(bool(self.redo_stack))
        self.btn_save.setEnabled(has_doc)
        for w in (self.btn_zoom_in, self.btn_zoom_out):
            w.setEnabled(has_doc)

    # -- modes ---------------------------------------------------------------
    def set_mode(self, key):
        self.canvas.set_mode(key)
        self.hint.setText(HINT[key])
        self.canvas.draw_width = self.opt_width.value()
        for lbl, w in self._opt_widgets:
            show = ((w in (self.opt_family, self.opt_bold, self.opt_italic, self.opt_size, self.opt_align)
                    and key == "text")
                   or (w is self.opt_color and key in ("text", "highlight", "underline", "strikeout", "draw", "rect"))
                   or (w is self.opt_width and key in ("draw", "rect"))
                   or (w is self.opt_fill and key == "rect")
                   or (w is self.opt_imgwidth and key == "image"))
            if lbl:
                lbl.setVisible(show)
            w.setVisible(show)
        defaults = {"highlight": "#ffe066", "underline": "#dc2626", "strikeout": "#dc2626",
                   "draw": "#1d4ed8", "rect": "#1d4ed8", "text": "#000000"}
        if key in defaults:
            self.opt_color._c = QColor(defaults[key])
            self.opt_color._paint()
        self.canvas.draw_color = self.opt_color.rgb()

    # -- undo / redo -----------------------------------------------------
    def _snapshot(self):
        if not self.doc:
            return
        self.undo_stack.append(self.doc.write(garbage=1))
        if len(self.undo_stack) > 25:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.dirty = True

    def _drop_snapshot(self):
        if self.undo_stack:
            self.undo_stack.pop()

    def undo(self):
        if not self.undo_stack or not self.doc:
            return
        self.redo_stack.append(self.doc.write(garbage=1))
        data = self.undo_stack.pop()
        self.doc.close()
        self.doc = pymupdf.open(stream=data, filetype="pdf")
        self.refresh()

    def redo(self):
        if not self.redo_stack or not self.doc:
            return
        self.undo_stack.append(self.doc.write(garbage=1))
        data = self.redo_stack.pop()
        self.doc.close()
        self.doc = pymupdf.open(stream=data, filetype="pdf")
        self.refresh()

    # -- actions métier (testables indépendamment des boîtes de dialogue) --
    def _page(self):
        return self.doc[self.page_index]

    def _add_text(self, x, y, text, family, bold, italic, size, color, align):
        if not text.strip():
            return
        self._snapshot()
        ops.add_textbox(self._page(), x, y, text, family, bold, italic, size, color, align)
        self.refresh()

    def _replace_text(self, item, text, family, bold, italic, size, color, align):
        self._snapshot()
        ops.replace_text(self._page(), item["rect"], text, family, bold, italic, size, color, align)
        self.refresh()

    def _erase_line(self, item):
        self._snapshot()
        ops.erase_rect(self._page(), item["rect"])
        self.refresh()

    def _add_image(self, x, y, path):
        self._snapshot()
        try:
            ops.add_image_at(self._page(), x, y, path, self.opt_imgwidth.value())
        except ops.PdfError as e:
            self._drop_snapshot()
            return self.win.warn(str(e))
        self.refresh()

    def _delete_image(self, item):
        self._snapshot()
        ops.delete_image_at(self._page(), item["rect"])
        self.refresh()

    def _replace_image(self, item, path):
        self._snapshot()
        r = item["rect"]
        page = self._page()
        try:
            ops.delete_image_at(page, r)
            ops.add_image_at(page, r[0], r[1], path, 100 * (r[2] - r[0]) / page.rect.width)
        except ops.PdfError as e:
            self._drop_snapshot()
            return self.win.warn(str(e))
        self.refresh()

    def _set_field(self, item, value):
        self._snapshot()
        ops.set_field_value(self._page(), item["name"], value)
        self.refresh()

    def _apply_markup(self, mode, rect):
        self._snapshot()
        n = ops.markup_rect(self._page(), rect, mode, self.opt_color.rgb())
        if n == 0:
            self._drop_snapshot()
            self.win.statusBar().showMessage("Aucun mot dans la zone sélectionnée.", 3000)
            return
        self.refresh()

    def _apply_erase(self, rect):
        self._snapshot()
        ops.erase_rect(self._page(), rect)
        self.refresh()

    def _apply_rect(self, rect):
        self._snapshot()
        ops.add_shape_rect(self._page(), rect, self.opt_color.rgb(), self.opt_width.value(), self.opt_fill.isChecked())
        self.refresh()

    def _apply_draw(self, points):
        self._snapshot()
        ops.add_ink(self._page(), points, self.opt_color.rgb(), self.opt_width.value())
        self.refresh()

    # -- réactions aux gestes de l'utilisateur ------------------------------
    def on_item_clicked(self, item):
        if item["kind"] == "line":
            dlg = TextPropsDialog(self, item, "Modifier le texte")
            if dlg.exec():
                d = dlg.values()
                self._replace_text(item, d["text"], d["family"], d["bold"], d["italic"], d["size"], d["color"], d["align"])
        elif item["kind"] == "image":
            choice = QMessageBox.question(self, "Image", "Remplacer cette image par une autre ?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if choice == QMessageBox.StandardButton.Yes:
                self.on_replace_requested(item)
        elif item["kind"] == "field":
            self._edit_field(item)

    def _edit_field(self, item):
        tn = (item.get("type_name") or "").lower()
        if "check" in tn:
            self._set_field(item, not bool(item.get("value")))
        elif "radio" in tn:
            self._set_field(item, not bool(item.get("value")))
        elif "combo" in tn or "list" in tn:
            choices = item.get("choices") or []
            if choices:
                val, ok = QInputDialog.getItem(self, "Modifier le champ", _field_label(item), choices, 0, False)
            else:
                val, ok = QInputDialog.getText(self, "Modifier le champ", _field_label(item), text=str(item.get("value") or ""))
            if ok:
                self._set_field(item, val)
        elif "signat" in tn or "push" in tn:
            self.win.warn("Ce type de champ (signature / bouton) ne peut pas être modifié ici.")
        else:
            val, ok = QInputDialog.getMultiLineText(self, "Modifier le champ", _field_label(item), str(item.get("value") or ""))
            if ok:
                self._set_field(item, val)

    def on_empty_clicked(self, x, y):
        if self.canvas.mode == "text":
            dlg = TextPropsDialog(self, dict(text="", family=self.opt_family.currentText(),
                                             bold=self.opt_bold.isChecked(), italic=self.opt_italic.isChecked(),
                                             size=self.opt_size.value(), color=self.opt_color.rgb(),
                                             align=self.opt_align.currentData()), "Ajouter du texte")
            if dlg.exec():
                d = dlg.values()
                self._add_text(x, y, d["text"], d["family"], d["bold"], d["italic"], d["size"], d["color"], d["align"])
        elif self.canvas.mode == "image":
            path, _ = QFileDialog.getOpenFileName(self, "Choisir une image", A.LAST_DIR,
                                                  "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
            if path:
                A.LAST_DIR = str(Path(path).parent)
                self._add_image(x, y, path)

    def on_drag_done(self, mode, payload):
        if mode == "draw":
            self._apply_draw(payload)
        elif mode == "erase":
            self._apply_erase(payload)
        elif mode == "rect":
            self._apply_rect(payload)
        else:
            self._apply_markup(mode, payload)

    def on_delete_requested(self, item):
        if item["kind"] == "line":
            self._erase_line(item)
        elif item["kind"] == "image":
            self._delete_image(item)
        elif item["kind"] == "field":
            tn = (item.get("type_name") or "").lower()
            self._set_field(item, "" if ("check" not in tn and "radio" not in tn) else False)

    def on_replace_requested(self, item):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une image", A.LAST_DIR,
                                              "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            A.LAST_DIR = str(Path(path).parent)
            self._replace_image(item, path)

    # -- enregistrer ---------------------------------------------------------
    def save_as(self):
        if not self.doc:
            return self.win.warn("Ouvre d'abord un PDF.")
        stem = Path(self.path).stem if self.path else "document"
        folder = str(Path(self.path).parent) if self.path else None
        out = self.win.ask_save(f"{stem}_modifie.pdf", "PDF (*.pdf)", ".pdf", folder)
        if not out:
            return
        try:
            self.doc.save(out, garbage=3, deflate=True)
        except Exception as e:
            return self.win.warn(f"Enregistrement impossible : {e}", critical=True)
        self.dirty = False
        self.win.notify("Document enregistré.", out)
