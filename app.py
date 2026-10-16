import re
import streamlit as st
import pytesseract
from PIL import Image

def generate_regex():
    # Ustawienia strony
    st.set_page_config(page_title="Generator Regex", page_icon="🔍")
    st.title("Generator Regex z linków i obrazów")

    # Tworzenie zakładek dla dwóch metod wprowadzania danych
    tab1, tab2 = st.tabs(["Z pliku tekstowego (.txt)", "Ze zrzutu ekranu (OCR)"])

    # Wzorce do wyłuskiwania ID
    id_pattern_txt = re.compile(r'/(\d+)-')
    # Wzorzec dla OCR uwzględnia ewentualne spacje, które Tesseract może dodać przez pomyłkę
    id_pattern_ocr = r'/\s*(\d+)\s*-'

    # ==========================================
    # ZAKŁADKA 1: Plik tekstowy (.txt)
    # ==========================================
    with tab1:
        st.header("Ekstrakcja z pliku .txt")
        uploaded_file_txt = st.file_uploader("Wgraj plik z linkami (np. linki.txt)", type=["txt"])

        if uploaded_file_txt is not None:
            # utf-8-sig usuwa ewentualny BOM; errors="ignore" chroni przed błędami kodowania
            content = uploaded_file_txt.getvalue().decode("utf-8-sig", errors="ignore")

            # findall na całym tekście
            ids = set(id_pattern_txt.findall(content))

            if not ids:
                st.warning("Nie znaleziono żadnych ID w podanym pliku.")
            else:
                # Sortowanie od najmniejszego do największego
                sorted_ids = sorted(ids, key=int)
                regex_string = f".*/({'|'.join(sorted_ids)})-.*"

                st.success(f"Wygenerowano regex! Znalezione unikalne ID: {len(sorted_ids)}")
                st.code(regex_string, language="regex")

                st.download_button(
                    label="Pobierz jako regex.txt",
                    data=regex_string,
                    file_name="regex.txt",
                    mime="text/plain",
                    key="download_txt"
                )

    # ==========================================
    # ZAKŁADKA 2: Zrzut ekranu (OCR)
    # ==========================================
    with tab2:
        st.header("Ekstrakcja ze zrzutu ekranu")
        
        # Sztywno przypisana ścieżka dla Streamlit Cloud (ukryta przed użytkownikiem)
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

        uploaded_file_img = st.file_uploader("Wybierz plik ze zrzutem ekranu", type=['png', 'jpg', 'jpeg'])

        if uploaded_file_img is not None:
            # Wyświetlenie podglądu obrazu
            img = Image.open(uploaded_file_img)
            st.image(img, caption='Wgrany zrzut ekranu', use_container_width=True)
            
            if st.button("Wyciągnij ID i generuj Regex z obrazka"):
                with st.spinner('Analizowanie obrazu (OCR)... To może chwilę potrwać.'):
                    try:
                        # Ekstrakcja tekstu. Konfiguracja --psm 6 zakłada jednolity blok tekstu
                        extracted_text = pytesseract.image_to_string(img, config='--psm 6')
                        found_ids = re.findall(id_pattern_ocr, extracted_text)
                        
                        if found_ids:
                            # Usuwamy duplikaty i sortujemy
                            unique_ids = set(found_ids)
                            sorted_ids_img = sorted(unique_ids, key=int)
                            
                            # Generowanie regex
                            regex_output = f".*/({'|'.join(sorted_ids_img)})-.*"
                            
                            st.success(f"Znaleziono {len(sorted_ids_img)} unikalnych ID!")
                            st.code(regex_output, language='regex')
                            
                            st.download_button(
                                label="Pobierz jako regex_ocr.txt",
                                data=regex_output,
                                file_name="regex_ocr.txt",
                                mime="text/plain",
                                key="download_ocr"
                            )
                            
                            # Podgląd surowego tekstu z OCR w celu diagnozowania problemów
                            with st.expander("Pokaż odczytany surowy tekst z obrazka (Debug)"):
                                st.text(extracted_text)
                        else:
                            st.warning("Nie znaleziono żadnych pasujących ID na tym obrazie.")
                            
                    except Exception as e:
                        st.error(f"Błąd podczas analizy pliku. Upewnij się, że Tesseract jest prawidłowo zainstalowany, a ścieżka jest poprawna. Szczegóły: {e}")

if __name__ == "__main__":
    generate_regex()
