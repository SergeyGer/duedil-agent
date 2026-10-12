"""Static checks on the code the two entry points share.

`app/ui.py` and `app/cli.py` both call into `app/report.py`, and the three evolve
separately. When a caller starts passing a keyword the callee does not accept, the
failure appears at *runtime* — and in the Streamlit UI that means the user sees a
traceback after a pipeline run has already been paid for.

This module walks the AST of `app/` and asserts that every keyword argument passed to a
function defined in this project actually exists in that function's signature. It is the
test that would have caught the `markdown_to_pdf_bytes(memo, model=...)` break before it
reached a deployment.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"


def _signatures() -> dict[str, set[str] | None]:
    """Map every function defined in ``app/`` to the keywords it accepts.

    A value of ``None`` means the function takes ``**kwargs``, so any keyword is legal
    and the call cannot be judged statically — the UI's ``t()`` translation helper is
    exactly that case.
    """

    signatures: dict[str, set[str] | None] = {}
    for path in APP.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            if args.kwarg is not None:
                # One definition taking **kwargs makes calls to this name unjudgeable, so
                # record that and never let a later definition overwrite it.
                signatures.setdefault(node.name, None)
                continue
            names = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
            names.discard("self")
            if signatures.get(node.name, set()) is None:
                continue  # an overload elsewhere accepts anything
            signatures[node.name] = (signatures.get(node.name) or set()) | names
    return signatures


def _calls() -> list[tuple[Path, int, str, set[str]]]:
    """Collect ``(file, line, function name, keyword names)`` for every call with keywords."""

    found = []
    for path in sorted(APP.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.keywords:
                continue
            if any(keyword.arg is None for keyword in node.keywords):
                continue  # **kwargs unpacking cannot be checked statically
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(
                node.func, "id", ""
            )
            if not name:
                continue
            found.append(
                (
                    path,
                    node.lineno,
                    name,
                    {keyword.arg for keyword in node.keywords if keyword.arg},
                )
            )
    return found


def test_every_keyword_argument_matches_a_known_signature():
    signatures = _signatures()
    failures = []
    for path, line, name, keywords in _calls():
        if name not in signatures:
            continue  # third-party (log, get, str...): nothing to compare against
        accepted = signatures[name]
        if accepted is None:
            continue  # accepts **kwargs by design
        unknown = keywords - accepted
        if unknown:
            failures.append(
                f"{path.name}:{line} calls {name}() with "
                f"{', '.join(sorted(unknown))} — accepts {', '.join(sorted(accepted))}"
            )
    assert not failures, "keyword arguments that no definition accepts:\n" + "\n".join(failures)


def test_the_checks_are_actually_looking_at_something():
    """A guard so this module cannot quietly pass by finding no code at all."""

    signatures = _signatures()
    accepted = signatures["markdown_to_pdf_bytes"]
    assert accepted is not None and "model" in accepted
    assert len(_calls()) > 50


def test_report_renderers_accept_the_model_byline():
    """The model travelled through three layers; the bottom one must accept it."""

    signatures = _signatures()
    for name in ("markdown_to_pdf_bytes", "markdown_to_pdf"):
        accepted = signatures[name]
        assert accepted is not None and "model" in accepted, f"{name} lost the model byline"
