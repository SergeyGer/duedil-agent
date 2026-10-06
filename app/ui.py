"""TEMPORARY diagnostic entry point (see the commit message).

Streamlit Community Cloud serves this instead of the real UI and stays blank, so this
script answers one question: does the platform run *any* Streamlit script, and if so,
where does the app's own import graph stop?

Every line below is written to stdout *before* the next step, so whatever is missing
from the Cloud log is the culprit.
"""

import os
import sys
import traceback

import streamlit as st

st.write("diag step 1: entrypoint executed")
st.write(f"diag step 2: python {sys.version.split()[0]} | cwd={os.getcwd()}")
st.write(f"diag step 3: sys.path[:3]={sys.path[:3]}")

try:
    import app  # noqa: F401

    st.write("diag step 4: import app -> ok")
except Exception:
    st.error("diag step 4 FAILED: import app")
    st.code(traceback.format_exc())

try:
    import app.graph  # noqa: F401

    st.write("diag step 5: import app.graph -> ok")
except Exception:
    st.error("diag step 5 FAILED: import app.graph")
    st.code(traceback.format_exc())

try:
    import app.i18n  # noqa: F401
    import app.parser  # noqa: F401
    import app.report  # noqa: F401

    st.write("diag step 6: report/parser/i18n -> ok")
except Exception:
    st.error("diag step 6 FAILED")
    st.code(traceback.format_exc())

try:
    from app.ui_real import main

    st.write("diag step 7: real UI module imported")
    main()
    st.write("diag step 8: real UI rendered")
except Exception:
    st.error("diag step 7/8 FAILED: the real UI raised")
    st.code(traceback.format_exc())
