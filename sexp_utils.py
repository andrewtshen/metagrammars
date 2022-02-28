from sexpdata import loads, dumps, Symbol # Everything we need to read SyGuS files (.sl)


"""
==================================================================
|Helper Functions for working with different s-expressions (sexp)|
==================================================================
"""


def remove_sexp_comments(contents: list):
    """
    Remove all comments from contents of sexp.
    Returns resulting sexp.
    """
    return [ line for line in contents if line and line[0] != ';' ]


def get_sexp(filename: str):
    """
    Reads a (.sl) using sexpdata to parse through the information.
    Returns a list of Symbols.
    """
    try:
        with open(filename, 'r') as f:
            contents = f.readlines()
            return loads('(' + ''.join(remove_sexp_comments(contents)) + ')')
    except:
        raise ValueError("Error with reading filename: ", filename)


def export_sexp_raw(sexp):
    """
    Returns sexp with replaced special character #.
    """
    return dumps(sexp).replace('\\#', '#')


def export_sexp(sexp):
    """
    Returns sexp ready to write back as SyGuS problem (.sl file).
    """
    return export_sexp_raw(sexp)[1:-1]


def create_symbol(term: str):
    """
    Returns a Symbol containing term.
    """
    return loads(term)


def starts_with_symbol(test_symbol, symbol):
    return type(test_symbol) == list and dumps(test_symbol[0]) == symbol
