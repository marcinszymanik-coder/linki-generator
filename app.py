import re
import streamlit as st

def generate_regex():
    st.set_page_config(page_title="Generator Regex", page_icon="🔍")
    st.title("Generator Regex z linków")

    # Wzorzec do wyłuskiwania ID z URL
    id_pattern = re.compile(r'/(\d+)-')

    uploaded_file = st.file_uploader("Wgraj plik z linkami (np. linki.txt)", type=["txt"])

    if uploaded_file is not None:
        # utf-8-sig usuwa ewentualny BOM; errors="ignore" chroni przed błędami kodowania
        content = uploaded_file.getvalue().decode("utf-8-sig", errors="ignore")

        # findall na całym tekście – działa dla tabulatorów, spacji i nowych linii
        ids = set(id_pattern.findall(content))

        if not ids:
            st.warning("Nie znaleziono żadnych ID w podanym pliku.")
            return

        sorted_ids = sorted(ids, key=int)
        regex_string = f".*/({'|'.join(sorted_ids)})-.*"

        st.success(f"Wygenerowano regex! Znalezione ID: {len(sorted_ids)}")
        st.code(regex_string, language="regex")

        st.download_button(
            label="Pobierz jako regex.txt",
            data=regex_string,
            file_name="regex.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    generate_regex()
