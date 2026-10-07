import re
import streamlit as st

def generate_regex():
    st.set_page_config(page_title="Generator Regex", page_icon="🔍")
    st.title("Generator Regex z linków")
    
    # Wzorzec do wyłuskiwania ID z URL
    id_pattern = re.compile(r'/(\d+)-')
    
    # Upload pliku zamiast lokalnego odczytu
    uploaded_file = st.file_uploader("Wgraj plik z linkami (np. linki.txt)", type=["txt"])
    
    if uploaded_file is not None:
        ids = set()
        
        # Odczyt pliku w pamięci
        content = uploaded_file.getvalue().decode("utf-8").splitlines()
        
        for line in content:
            match = id_pattern.search(line)
            if match:
                ids.add(match.group(1))
                
        if not ids:
            st.warning("Nie znaleziono żadnych ID w podanym pliku.")
            return

        # Sortowanie ID i generowanie regexa
        sorted_ids = sorted(list(ids), key=int)
        regex_string = f".*/({'|'.join(sorted_ids)})-.*"
        
        st.success("Wygenerowano regex!")
        
        # Wyświetlenie wyniku na ekranie
        st.code(regex_string, language="regex")
        
        # Przycisk do pobrania wyniku
        st.download_button(
            label="Pobierz jako regex.txt",
            data=regex_string,
            file_name="regex.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    generate_regex()