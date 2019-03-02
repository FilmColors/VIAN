# syntax.py

import sys
import re
import importlib.util
import traceback

from PyQt5.QtCore import QRegExp, pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter, QFontMetricsF, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QPlainTextEdit, QMainWindow, QFileDialog, QDockWidget, QSplitter, QCompleter
from functools import partial

from core.data.creation_events import EVENT_C_SEGMENT, EVENT_C_ANNOTATION, EVENT_C_SCREENSHOT

def format(r, g, b, style=''):
    """Return a QTextCharFormat with the given attributes.
    """
    _color = QColor(r, g, b)

    _format = QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)

    return _format

# Syntax styles that can be shared by all languages
STYLES = {
    'keyword': format(204,120,50, 'bold'),
    'operator': format(255,255,255),
    'brace': format(255,255,255),
    'defclass': format(255,255,255, 'bold'),
    'string': format(165,194,97),
    'string2': format(165,194,97),
    'comment': format(98,151,85, 'italic'),
    'self': format(204,120,50, 'italic'),
    'numbers': format(104,151,187),
    'decorators': format(165,194,97, 'italic')
}


class PythonScriptEditor(QDockWidget):
    onReload = pyqtSignal(str)

    def __init__(self, parent):
        super(PythonScriptEditor, self).__init__(parent)
        self.main_window = parent
        self.inner = QMainWindow()
        self.setWindowTitle("Script Editor")
        self.editor = QPlainTextEdit(self.inner)
        self.output = QPlainTextEdit(self.inner)
        self.output.setReadOnly(True)

        self.central = QSplitter( Qt.Vertical, self.inner)
        self.central.addWidget(self.editor)
        self.central.addWidget(self.output)
        self.highlighter = PythonHighlighter(self.editor.document())

        self.inner.setCentralWidget(self.central)
        self.current_file_path = ""
        QDockWidget.setWidget(self, self.inner)

        self.m_file = self.inner.menuBar().addMenu("File")
        self.a_new = self.m_file.addAction("New Script")
        self.a_load = self.m_file.addAction("Load")
        self.a_save = self.m_file.addAction("Save")

        self.a_new.triggered.connect(self.new)
        self.a_load.triggered.connect(partial(self.load, None))
        self.a_save.triggered.connect(partial(self.save, None, False))

        self.font = QFont("Lucida Console")
        self.font.setPointSize(10)

        self.toolbar = self.inner.addToolBar("ScriptEditor Toolbar")

        self.a_reload = self.toolbar.addAction("Reload")
        self.a_reload.triggered.connect(self.reload)

        self.editor.setFont(self.font)
        self.editor.setTabStopWidth(QFontMetricsF(self.editor.font()).width(' ') * 4)

    def new(self):
        self.load("data/default_pipeline.py")
        self.current_file_path = ""

    def load(self, file_path):
        if file_path is None:
            file_path = QFileDialog.getOpenFileName(self, filter="*.py")[0]

        if file_path == "":
            return
        try:
            with open(file_path, "r") as f:
                self.editor.setPlainText(f.read())
            self.current_file_path = file_path
        except IOError as e:
            print(e)

    def save(self, file_path=None, save_as = False):
        print(file_path, save_as)
        if file_path is not None:
            p = file_path
        elif save_as or self.current_file_path == "":
            p = QFileDialog.getSaveFileName(self, filter="*.py")[0]
            print(p)
        else:
            p = self.current_file_path

        if file_path == "":
            return

        try:
            with open(p, "w") as f:
                f.write(self.editor.toPlainText())
            self.current_file_path = p
        except IOError as e:
            print(e)

    def reload(self):
        self.save()
        if self.current_file_path != "":
            try:
                spec = importlib.util.spec_from_file_location("module.name", self.current_file_path)
                foo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(foo)
                self.output.setPlainText("Successfully imported module")
            except Exception as e:
                self.output.setPlainText(traceback.format_exc())
                pass

        else:
            print("No Module loaded")

    @pyqtSlot(str)
    def print_exception(self, e):
        self.output.setPlainText(e)
        self.raise_()


class PythonHighlighter (QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False', 'as',
    ]
    decorators = [
                 '@segment_created_event',
                 '@screenshot_created_event',
                 '@annotation_created_event',
    ]
    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        '\+', '-', '\*', '/', '//', '\%', '\*\*',
        # In-place
        '\+=', '-=', '\*=', '/=', '\%=',
        # Bitwise
        '\^', '\|', '\&', '\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        '\{', '\}', '\(', '\)', '\[', '\]',
    ]
    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        # Multi-line strings (expression, flag, style)
        # FIXME: The triple-quotes in these two lines will mess up the
        # syntax highlighting from this point onward
        self.tri_single = (QRegExp("'''"), 1, STYLES['string2'])
        self.tri_double = (QRegExp('"""'), 2, STYLES['string2'])

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, STYLES['keyword'])
            for w in PythonHighlighter.keywords]
        rules += [(r'%s' % o, 0, STYLES['operator'])
            for o in PythonHighlighter.operators]
        rules += [(r'%s' % b, 0, STYLES['brace'])
            for b in PythonHighlighter.braces]
        rules += [(r'%s' % b, 0, STYLES['decorators'])
                  for b in PythonHighlighter.decorators]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, STYLES['self']),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, STYLES['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, STYLES['string']),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, STYLES['defclass']),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, STYLES['defclass']),

            # From '#' until a newline
            (r'#[^\n]*', 0, STYLES['comment']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, STYLES['numbers']),
        ]

        # Build a QRegExp for each pattern
        self.rules = [(QRegExp(pat), index, fmt)
            for (pat, index, fmt) in rules]


    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        # Do other syntax formatting
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)


    def match_multiline(self, text, delimiter, in_state, style):
        """Do highlighting of multi-line strings. ``delimiter`` should be a
        ``QRegExp`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.indexIn(text)
            # Move past this match
            add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.indexIn(text, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False