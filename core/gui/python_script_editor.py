# syntax.py

import sys
import re
from uuid import uuid4
import importlib.util
import traceback
from core.data.log import log_info, log_error, log_debug, log_warning
from PyQt5.QtCore import QRegExp, pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter, QFontMetricsF, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QPlainTextEdit, QMainWindow, QFileDialog, QDockWidget, QSplitter, \
    QCompleter,QSizePolicy, QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox
from functools import partial
from core.analysis.pipeline_scripts.pipeline_script import PipelineScript


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
    'string': format(106,135,89) ,
    'string2': format(98,151,85),
    'comment': format(120,120,120, 'italic'),
    'self': format(204,120,50, 'italic'),
    'numbers': format(104,151,187),
    'decorators': format(165,194,97, 'italic')
}


class PythonScriptEditor(QWidget):
    onReload = pyqtSignal()

    def __init__(self, parent, main_window):
        super(PythonScriptEditor, self).__init__(parent)
        self.main_window = main_window
        self.inner = QMainWindow()
        self.setLayout(QVBoxLayout())
        self.setWindowTitle("Script Editor")
        self.editor = CodePlainTextEditor(self.inner)
        self.output = CodePlainTextEditor(self.inner)
        self.output.setReadOnly(True)

        self.pipeline_script = None #type: PipelineScript

        self.central = QSplitter(Qt.Vertical, self.inner)
        self.central.setMaximumHeight(400)
        self.central.addWidget(self.editor)
        self.central.addWidget(self.output)
        self.highlighter = PythonHighlighter(self.editor.document())

        self.central.setStretchFactor(0, 4)
        self.central.setStretchFactor(1, 1)

        self.inner.setCentralWidget(self.central)
        self.current_file_path = ""
        self.layout().addWidget(self.inner)

        self.m_file = self.inner.menuBar().addMenu("File")
        self.a_new = self.m_file.addAction("New Script")
        self.a_load = self.m_file.addAction("Load")
        self.a_save = self.m_file.addAction("Save")
        self.a_export = self.m_file.addAction("Save As / Export")

        self.a_new.triggered.connect(self.new)
        self.a_load.triggered.connect(partial(self.load, None))
        self.a_save.triggered.connect(partial(self.save, None, False))
        self.a_export.triggered.connect(partial(self.save, None, True))

        if sys.platform == "darwin":
            self.font = QFont("Consolas")
        else:
            self.font = QFont("Lucida Console")
        self.font.setPointSize(10)

        self.toolbar = self.inner.addToolBar("ScriptEditor Toolbar")

        self.a_reload = self.toolbar.addAction("Reload")
        self.a_reload.triggered.connect(self.reload)

        self.editor.setFont(self.font)
        self.editor.setTabStopWidth(int(QFontMetricsF(self.editor.font()).width(' ')) * 4)

    def new(self):
        dialog = NewScriptDialog(self, self.main_window)
        dialog.show()
        # self.load("data/default_pipeline.py")
        #
        # self.current_file_path = ""

    def load(self, pipeline:PipelineScript = None):
        if pipeline is None:
            file_path = QFileDialog.getOpenFileName(self, filter="*.py")[0]
            try:
                with open(file_path, "r") as f:
                    script = f.read()

                dialog = NewScriptDialog(self, self.main_window, script)
                dialog.show()
            except Exception as e:
                self.output.setPlainText(traceback.print_exc())
                pass
        else:
            self.pipeline_script=pipeline
            self.editor.setPlainText(pipeline.script)
            self.reload()

    def save(self, file_path=None, save_as = False):
        if self.pipeline_script is None:
            return
        if save_as:
            file_path = QFileDialog.getSaveFileName(self, caption="Select Path", filter="*.py")[0]
        self.pipeline_script.script = self.editor.toPlainText().replace("\t", "    ")
        self.pipeline_script.save_script(file_path)

    def reload(self):
        self.pipeline_script.script = self.editor.toPlainText().replace("\t", "    ")
        self.pipeline_script.save_script()
        self.editor.setPlainText(self.pipeline_script.script)
        message = self.pipeline_script.import_pipeline()
        self.output.setPlainText(message)
        self.onReload.emit()

    @pyqtSlot(str)
    def print_exception(self, e):
        self.output.setPlainText(e)
        self.raise_()

from PyQt5.QtGui import QTextOption
class CodePlainTextEditor(QPlainTextEdit):
    def __init__(self, parent):
        super(CodePlainTextEditor, self).__init__(parent)
        self.setWordWrapMode(QTextOption.NoWrap)


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


class NewScriptDialog(QDialog):
    def __init__(self, parent, main_window, script=None):
        super(NewScriptDialog, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.lineEdit_Name = QLineEdit("MyAnalysis", self)
        self.lineEdit_Author = QLineEdit("MyHackerPseudonym", self)

        self.btn_OK = QPushButton("OK", self)
        self.layout().addWidget(self.lineEdit_Name)
        self.layout().addWidget(self.lineEdit_Author)
        self.layout().addWidget(self.btn_OK)
        self.btn_OK.clicked.connect(self.on_ok)
        self.main_window = main_window
        self.script = script

    def on_ok(self):
        if self.script is None:
            with open("data/default_pipeline.py", "r") as f:
                script = f.read()

            script = script.replace("%PIPELINE_NAME%", self.lineEdit_Name.text().replace(" ", ""))
            script = script.replace("%AUTHOR%", self.lineEdit_Author.text().replace(" ", ""))
            script = script.replace("%UUID%", str(uuid4()))
        else:
            script = self.script

        pipeline_script = self.main_window.project.create_pipeline_script(name=self.lineEdit_Name.text().replace(" ", ""),
                                                        author=self.lineEdit_Author.text().replace(" ", ""),
                                                        script=script)
        try:
            self.parent().pipeline_script = pipeline_script
            self.parent().editor.setPlainText(pipeline_script.script)
            self.parent().reload()
            self.close()
        except Exception as e:
            log_error("NewScriptDialog", e)
            pass

