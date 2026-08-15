"""Token handler and syntax highlighting rules for JSON and Dart."""

import tkinter as tk
from pygments import lex
from pygments.lexers import DartLexer, JsonLexer
from pygments.token import Token

TOKEN_COLORS = {
    Token.Keyword: "#569CD6",  # Blue (class, final, return, import)
    Token.Keyword.Type: "#4EC9B0",  # Teal (String, int, double, bool)
    Token.Name.Class: "#4EC9B0",  # Teal class names
    Token.Name.Function: "#DCDCAA",  # Yellow functions (fromJson, toJson)
    Token.String: "#CE9178",  # Orange/Brown strings
    Token.Number: "#B5CEA8",  # Light green numbers
    Token.Comment: "#6A9955",  # Green comments
    Token.Operator: "#D4D4D4",  # Operators (+, =, ?, :)
    Token.Punctuation: "#808080",  # Brackets and commas
    Token.Name.Variable: "#9CDCFE",  # Blue variables/fields
    Token.Name.Tag: "#569CD6",  # JSON Keys
}


class TokenHighlighter:

    def __init__(self):
        self.json_lexer = JsonLexer()
        self.dart_lexer = DartLexer()

    @staticmethod
    def setup_text_tags(text_widget: tk.Text):
        """Configure color tags in the Tkinter Text widget."""
        for token, color in TOKEN_COLORS.items():
            text_widget.tag_config(str(token), foreground=color)

    def apply_highlighting(self, text_widget: tk.Text, code: str, lexer):
        """Parse code using Pygments and apply color tags dynamically."""
        y_scroll = text_widget.yview()
        x_scroll = text_widget.xview()

        text_widget.delete("1.0", tk.END)

        for token_type, value in lex(code, lexer):
            tag_name = None
            curr = token_type
            while curr:
                if curr in TOKEN_COLORS:
                    tag_name = str(curr)
                    break
                curr = curr.parent

            if tag_name:
                text_widget.insert(tk.END, value, tag_name)
            else:
                text_widget.insert(tk.END, value)

        text_widget.yview_moveto(y_scroll[0])
        text_widget.xview_moveto(x_scroll[0])