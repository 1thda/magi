# app.py
import streamlit as st

from extract import extract_text
from summarize import MODELS, summarize_all

st.title("Magi")

uploaded_file = st.file_uploader("Upload a research article PDF", type="pdf")

if uploaded_file is not None:
    try:
        text = extract_text(uploaded_file)
    except Exception:
        st.error(
            "Couldn't read this PDF — it may be corrupt or not a valid PDF file."
        )
        st.stop()

    if not text:
        st.error(
            "Couldn't extract any text from this PDF. "
            "Scanned/image-only PDFs aren't supported yet."
        )
    else:
        with st.spinner("Summarizing with all models..."):
            results = summarize_all(text)

        columns = st.columns(len(MODELS))
        for column, model in zip(columns, MODELS):
            with column:
                st.subheader(model)
                result = results[model]
                if result.ok:
                    st.code(result.text, language=None)
                else:
                    st.error(f"{model} failed: {result.text}")
