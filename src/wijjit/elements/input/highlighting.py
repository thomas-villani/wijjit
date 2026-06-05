"""Syntax highlighting theme definitions and token-to-style mapping.

This module provides theme definitions for syntax highlighting in the CodeEditor
element. It maps Pygments token types to cell styling attributes.

The themes are designed to work well in terminal environments with both light
and dark backgrounds.
"""

from typing import TypedDict

from pygments.token import (  # type: ignore[import-untyped]
    Comment,
    Error,
    Generic,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
    Whitespace,
)


class TokenStyle(TypedDict, total=False):
    """Style definition for a token type.

    Attributes
    ----------
    fg_color : tuple of (int, int, int), optional
        Foreground RGB color
    bg_color : tuple of (int, int, int), optional
        Background RGB color
    bold : bool, optional
        Whether text should be bold
    italic : bool, optional
        Whether text should be italic
    underline : bool, optional
        Whether text should be underlined
    """

    fg_color: tuple[int, int, int] | None
    bg_color: tuple[int, int, int] | None
    bold: bool
    italic: bool
    underline: bool


# Token type hierarchy for fallback matching
# When a specific token type isn't found, we traverse up the hierarchy
TOKEN_HIERARCHY: dict[type, type | None] = {
    # Comments
    Comment.Hashbang: Comment,
    Comment.Multiline: Comment,
    Comment.Preproc: Comment,
    Comment.PreprocFile: Comment,
    Comment.Single: Comment,
    Comment.Special: Comment,
    Comment: Token,
    # Errors
    Error: Token,
    # Generic
    Generic.Deleted: Generic,
    Generic.Emph: Generic,
    Generic.Error: Generic,
    Generic.Heading: Generic,
    Generic.Inserted: Generic,
    Generic.Output: Generic,
    Generic.Prompt: Generic,
    Generic.Strong: Generic,
    Generic.Subheading: Generic,
    Generic.Traceback: Generic,
    Generic: Token,
    # Keywords
    Keyword.Constant: Keyword,
    Keyword.Declaration: Keyword,
    Keyword.Namespace: Keyword,
    Keyword.Pseudo: Keyword,
    Keyword.Reserved: Keyword,
    Keyword.Type: Keyword,
    Keyword: Token,
    # Literals
    Literal.Date: Literal,
    Literal: Token,
    # Names
    Name.Attribute: Name,
    Name.Builtin: Name,
    Name.Builtin.Pseudo: Name.Builtin,
    Name.Class: Name,
    Name.Constant: Name,
    Name.Decorator: Name,
    Name.Entity: Name,
    Name.Exception: Name,
    Name.Function: Name,
    Name.Function.Magic: Name.Function,
    Name.Label: Name,
    Name.Namespace: Name,
    Name.Other: Name,
    Name.Property: Name,
    Name.Tag: Name,
    Name.Variable: Name,
    Name.Variable.Class: Name.Variable,
    Name.Variable.Global: Name.Variable,
    Name.Variable.Instance: Name.Variable,
    Name.Variable.Magic: Name.Variable,
    Name: Token,
    # Numbers
    Number.Bin: Number,
    Number.Float: Number,
    Number.Hex: Number,
    Number.Integer: Number,
    Number.Integer.Long: Number.Integer,
    Number.Oct: Number,
    Number: Literal,
    # Operators
    Operator.Word: Operator,
    Operator: Token,
    # Punctuation
    Punctuation.Marker: Punctuation,
    Punctuation: Token,
    # Strings
    String.Affix: String,
    String.Backtick: String,
    String.Char: String,
    String.Delimiter: String,
    String.Doc: String,
    String.Double: String,
    String.Escape: String,
    String.Heredoc: String,
    String.Interpol: String,
    String.Other: String,
    String.Regex: String,
    String.Single: String,
    String.Symbol: String,
    String: Literal,
    # Text and whitespace
    Text: Token,
    Text.Whitespace: Text,
    Whitespace: Text,
    # Root
    Token: None,
}


# Theme definitions
# Each theme maps token types to styles

THEME_MONOKAI: dict[type, TokenStyle] = {
    # Base text
    Token: {"fg_color": (248, 248, 242)},
    Text: {"fg_color": (248, 248, 242)},
    Whitespace: {"fg_color": (248, 248, 242)},
    # Comments - gray/italic
    Comment: {"fg_color": (117, 113, 94), "italic": True},
    Comment.Preproc: {"fg_color": (166, 226, 46), "italic": False},
    # Keywords - pink/magenta
    Keyword: {"fg_color": (249, 38, 114), "bold": True},
    Keyword.Constant: {"fg_color": (174, 129, 255)},
    Keyword.Namespace: {"fg_color": (249, 38, 114)},
    Keyword.Type: {"fg_color": (102, 217, 239), "italic": True},
    # Names
    Name: {"fg_color": (248, 248, 242)},
    Name.Attribute: {"fg_color": (166, 226, 46)},
    Name.Builtin: {"fg_color": (102, 217, 239)},
    Name.Builtin.Pseudo: {"fg_color": (174, 129, 255)},
    Name.Class: {"fg_color": (166, 226, 46), "bold": True},
    Name.Constant: {"fg_color": (174, 129, 255)},
    Name.Decorator: {"fg_color": (166, 226, 46)},
    Name.Exception: {"fg_color": (166, 226, 46), "bold": True},
    Name.Function: {"fg_color": (166, 226, 46)},
    Name.Function.Magic: {"fg_color": (166, 226, 46), "italic": True},
    Name.Namespace: {"fg_color": (248, 248, 242)},
    Name.Tag: {"fg_color": (249, 38, 114)},
    Name.Variable: {"fg_color": (248, 248, 242)},
    Name.Variable.Magic: {"fg_color": (174, 129, 255)},
    # Literals - numbers and strings
    Literal: {"fg_color": (174, 129, 255)},
    Number: {"fg_color": (174, 129, 255)},
    String: {"fg_color": (230, 219, 116)},
    String.Doc: {"fg_color": (117, 113, 94), "italic": True},
    String.Escape: {"fg_color": (174, 129, 255)},
    String.Interpol: {"fg_color": (248, 248, 242)},
    String.Regex: {"fg_color": (230, 219, 116)},
    # Operators and punctuation
    Operator: {"fg_color": (249, 38, 114)},
    Operator.Word: {"fg_color": (249, 38, 114), "bold": True},
    Punctuation: {"fg_color": (248, 248, 242)},
    # Errors
    Error: {"fg_color": (248, 248, 242), "bg_color": (249, 38, 114)},
    # Generic
    Generic.Deleted: {"fg_color": (249, 38, 114)},
    Generic.Emph: {"italic": True},
    Generic.Error: {"fg_color": (249, 38, 114)},
    Generic.Heading: {"fg_color": (248, 248, 242), "bold": True},
    Generic.Inserted: {"fg_color": (166, 226, 46)},
    Generic.Output: {"fg_color": (117, 113, 94)},
    Generic.Prompt: {"fg_color": (117, 113, 94), "bold": True},
    Generic.Strong: {"bold": True},
    Generic.Subheading: {"fg_color": (117, 113, 94)},
}


THEME_DRACULA: dict[type, TokenStyle] = {
    # Base text - foreground
    Token: {"fg_color": (248, 248, 242)},
    Text: {"fg_color": (248, 248, 242)},
    Whitespace: {"fg_color": (248, 248, 242)},
    # Comments - gray
    Comment: {"fg_color": (98, 114, 164), "italic": True},
    # Keywords - pink
    Keyword: {"fg_color": (255, 121, 198), "bold": True},
    Keyword.Constant: {"fg_color": (189, 147, 249)},
    Keyword.Type: {"fg_color": (139, 233, 253), "italic": True},
    # Names
    Name: {"fg_color": (248, 248, 242)},
    Name.Attribute: {"fg_color": (80, 250, 123)},
    Name.Builtin: {"fg_color": (139, 233, 253)},
    Name.Class: {"fg_color": (80, 250, 123), "bold": True},
    Name.Constant: {"fg_color": (189, 147, 249)},
    Name.Decorator: {"fg_color": (80, 250, 123)},
    Name.Exception: {"fg_color": (80, 250, 123), "bold": True},
    Name.Function: {"fg_color": (80, 250, 123)},
    Name.Tag: {"fg_color": (255, 121, 198)},
    # Literals
    Literal: {"fg_color": (189, 147, 249)},
    Number: {"fg_color": (189, 147, 249)},
    String: {"fg_color": (241, 250, 140)},
    String.Doc: {"fg_color": (98, 114, 164), "italic": True},
    String.Escape: {"fg_color": (255, 121, 198)},
    # Operators
    Operator: {"fg_color": (255, 121, 198)},
    Punctuation: {"fg_color": (248, 248, 242)},
    # Errors
    Error: {"fg_color": (248, 248, 242), "bg_color": (255, 85, 85)},
    # Generic
    Generic.Deleted: {"fg_color": (255, 85, 85)},
    Generic.Inserted: {"fg_color": (80, 250, 123)},
    Generic.Emph: {"italic": True},
    Generic.Strong: {"bold": True},
}


THEME_GITHUB_LIGHT: dict[type, TokenStyle] = {
    # Base text
    Token: {"fg_color": (36, 41, 47)},
    Text: {"fg_color": (36, 41, 47)},
    Whitespace: {"fg_color": (36, 41, 47)},
    # Comments - gray
    Comment: {"fg_color": (106, 115, 125), "italic": True},
    # Keywords - red
    Keyword: {"fg_color": (207, 34, 46), "bold": True},
    Keyword.Constant: {"fg_color": (5, 80, 174)},
    Keyword.Type: {"fg_color": (207, 34, 46)},
    # Names
    Name: {"fg_color": (36, 41, 47)},
    Name.Attribute: {"fg_color": (5, 80, 174)},
    Name.Builtin: {"fg_color": (5, 80, 174)},
    Name.Class: {"fg_color": (111, 66, 193), "bold": True},
    Name.Constant: {"fg_color": (5, 80, 174)},
    Name.Decorator: {"fg_color": (111, 66, 193)},
    Name.Exception: {"fg_color": (111, 66, 193)},
    Name.Function: {"fg_color": (111, 66, 193)},
    Name.Tag: {"fg_color": (34, 134, 58)},
    # Literals
    Literal: {"fg_color": (5, 80, 174)},
    Number: {"fg_color": (5, 80, 174)},
    String: {"fg_color": (3, 47, 98)},
    String.Doc: {"fg_color": (106, 115, 125), "italic": True},
    String.Escape: {"fg_color": (5, 80, 174)},
    # Operators
    Operator: {"fg_color": (207, 34, 46)},
    Punctuation: {"fg_color": (36, 41, 47)},
    # Errors
    Error: {"fg_color": (207, 34, 46), "bg_color": (255, 235, 233)},
    # Generic
    Generic.Deleted: {"fg_color": (207, 34, 46), "bg_color": (255, 235, 233)},
    Generic.Inserted: {"fg_color": (34, 134, 58), "bg_color": (230, 255, 237)},
    Generic.Emph: {"italic": True},
    Generic.Strong: {"bold": True},
}


THEME_NORD: dict[type, TokenStyle] = {
    # Base text - snow storm
    Token: {"fg_color": (216, 222, 233)},
    Text: {"fg_color": (216, 222, 233)},
    Whitespace: {"fg_color": (216, 222, 233)},
    # Comments - gray
    Comment: {"fg_color": (97, 110, 136), "italic": True},
    # Keywords - frost blue
    Keyword: {"fg_color": (129, 161, 193), "bold": True},
    Keyword.Constant: {"fg_color": (180, 142, 173)},
    Keyword.Type: {"fg_color": (143, 188, 187)},
    # Names
    Name: {"fg_color": (216, 222, 233)},
    Name.Attribute: {"fg_color": (143, 188, 187)},
    Name.Builtin: {"fg_color": (143, 188, 187)},
    Name.Class: {"fg_color": (143, 188, 187), "bold": True},
    Name.Constant: {"fg_color": (180, 142, 173)},
    Name.Decorator: {"fg_color": (208, 135, 112)},
    Name.Exception: {"fg_color": (191, 97, 106)},
    Name.Function: {"fg_color": (136, 192, 208)},
    Name.Tag: {"fg_color": (129, 161, 193)},
    # Literals - aurora
    Literal: {"fg_color": (180, 142, 173)},
    Number: {"fg_color": (180, 142, 173)},
    String: {"fg_color": (163, 190, 140)},
    String.Doc: {"fg_color": (97, 110, 136), "italic": True},
    String.Escape: {"fg_color": (235, 203, 139)},
    # Operators
    Operator: {"fg_color": (129, 161, 193)},
    Punctuation: {"fg_color": (216, 222, 233)},
    # Errors - aurora red
    Error: {"fg_color": (216, 222, 233), "bg_color": (191, 97, 106)},
    # Generic
    Generic.Deleted: {"fg_color": (191, 97, 106)},
    Generic.Inserted: {"fg_color": (163, 190, 140)},
    Generic.Emph: {"italic": True},
    Generic.Strong: {"bold": True},
}


# Theme registry
THEMES: dict[str, dict[type, TokenStyle]] = {
    "monokai": THEME_MONOKAI,
    "dracula": THEME_DRACULA,
    "github-light": THEME_GITHUB_LIGHT,
    "nord": THEME_NORD,
}

# Default theme
DEFAULT_THEME = "monokai"


def get_style_for_token(
    token_type: type, theme_name: str = DEFAULT_THEME
) -> TokenStyle:
    """Get the style for a token type from the specified theme.

    Parameters
    ----------
    token_type : type
        Pygments token type (e.g., Token.Keyword, Token.String)
    theme_name : str, optional
        Name of the theme to use (default: "monokai")

    Returns
    -------
    TokenStyle
        Style dictionary with fg_color, bg_color, bold, italic, underline

    Notes
    -----
    If the exact token type is not found in the theme, it traverses up the
    token hierarchy to find the nearest matching style. If no style is found,
    returns the base Token style.

    Examples
    --------
    >>> style = get_style_for_token(Keyword.Reserved, "monokai")
    >>> style.get("fg_color")
    (249, 38, 114)
    """
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])

    # Try exact match first
    if token_type in theme:
        return theme[token_type]

    # Traverse hierarchy to find parent style
    current = token_type
    while current in TOKEN_HIERARCHY:
        parent = TOKEN_HIERARCHY[current]
        if parent is None:
            break
        if parent in theme:
            return theme[parent]
        current = parent

    # Fallback to base Token style
    return theme.get(Token, {"fg_color": (255, 255, 255)})


def get_available_themes() -> list[str]:
    """Get list of available theme names.

    Returns
    -------
    list of str
        Names of available themes
    """
    return list(THEMES.keys())
