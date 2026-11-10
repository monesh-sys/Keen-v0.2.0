import io

from keen.compiler.pipeline import run_source


def run(source, **kwargs):
    """Run KEEN source and return everything it printed."""
    out = io.StringIO()
    run_source(source, write=out.write, **kwargs)
    return out.getvalue()
