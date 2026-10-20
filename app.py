import re
import streamlit as st
import pytesseract
from PIL import Image
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

def generate_regex():
    # Ustawienia strony
    st.set_page_config(page_title="Generator Regex & Ekstraktor Linków", page_icon="🔍")
    st.title("Narzędzia SEO & Regex")

    # Tworzenie zakładek dla trzech metod
    tab1, tab2, tab3 = st.tabs(["Z pliku tekstowego (.txt)", "Ze zrzutu ekranu (OCR)", "Z wyszukiwarki (Linki)"])

    # Wzorce do wyłuskiwania ID
    id_pattern_txt = re.compile(r'/(\d+)-')
    # Wzorzec dla OCR uwzględnia ewentualne spacje, które Tesseract może dodać przez pomyłkę
    id_pattern_ocr = r'/\s*(\d+)\s*-'

    # ==========================================
    # ZAKŁADKA 1: Plik tekstowy (.txt)
    # ==========================================
    with tab1:
        st.header("Ekstrakcja ID z pliku .txt")
        uploaded_file_txt = st.file_uploader("Wgraj plik z linkami (np. linki.txt)", type=["txt"])

        if uploaded_file_txt is not None:
            content = uploaded_file_txt.getvalue().decode("utf-8-sig", errors="ignore")
            ids = set(id_pattern_txt.findall(content))

            if not ids:
                st.warning("Nie znaleziono żadnych ID w podanym pliku.")
            else:
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
        st.header("Ekstrakcja ID ze zrzutu ekranu")
        
        # Sztywno przypisana ścieżka dla Streamlit Cloud
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

        uploaded_file_img = st.file_uploader("Wybierz plik ze zrzutem ekranu", type=['png', 'jpg', 'jpeg'])

        if uploaded_file_img is not None:
            img = Image.open(uploaded_file_img)
            st.image(img, caption='Wgrany zrzut ekranu', use_container_width=True)
            
            if st.button("Wyciągnij ID i generuj Regex z obrazka"):
                with st.spinner('Analizowanie obrazu (OCR)... To może chwilę potrwać.'):
                    try:
                        extracted_text = pytesseract.image_to_string(img, config='--psm 6')
                        found_ids = re.findall(id_pattern_ocr, extracted_text)
                        
                        if found_ids:
                            unique_ids = set(found_ids)
                            sorted_ids_img = sorted(unique_ids, key=int)
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
                            
                            with st.expander("Pokaż odczytany surowy tekst z obrazka (Debug)"):
                                st.text(extracted_text)
                        else:
                            st.warning("Nie znaleziono żadnych pasujących ID na tym obrazie.")
                            
                    except Exception as e:
                        st.error(f"Błąd podczas analizy pliku. Upewnij się, że Tesseract jest prawidłowo zainstalowany. Szczegóły: {e}")

    # ==========================================
    # ZAKŁADKA 3: Z wyszukiwarki (Linki)
    # ==========================================
    with tab3:
        st.header("Ekstrakcja linków z wyszukiwarki")
        
        search_url = st.text_input("Podaj link do wyników wyszukiwania:", placeholder="np. https://automatykab2b.pl/szukaj?q=Designer")
        
        odrzucane_input = st.text_area(
            "Czarna lista (wpisz fragmenty, których chcesz unikać, każdy w nowej linii):",
            value="szybkie-i-latwe-planowanie-systemow\n/logowanie\n/rejestracja\n/kontakt\n/regulamin\n/polityka-prywatnosci"
        )

        if st.button("Skanuj i pobierz linki", type="primary"):
            if not search_url:
                st.warning("Proszę podać link do przeskanowania.")
            else:
                # Przygotowanie listy odrzucanych fraz
                odrzucane_frazy = [fraza.strip() for fraza in odrzucane_input.split('\n') if fraza.strip()]
                
                with st.spinner("Pobieranie i analizowanie wyników..."):
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    try:
                        response = requests.get(search_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            domena_bazowa = urlparse(search_url).netloc
                            znalezione_linki = set()
                            
                            for a_tag in soup.find_all('a', href=True):
                                href = a_tag['href']
                                full_url = urljoin(search_url, href)
                                parsed = urlparse(full_url)
                                
                                # Sprawdzanie domeny i oczyszczanie URL
                                if parsed.netloc == domena_bazowa:
                                    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
                                    
                                    # Szukanie cyfry w samej ścieżce (np. ID artykułu)
                                    if re.search(r'\d+', parsed.path):
                                        # Sprawdzanie z czarną listą
                                        if not any(fraza in clean_url for fraza in odrzucane_frazy):
                                            znalezione_linki.add(clean_url)
                            
                            if znalezione_linki:
                                posortowane_linki = sorted(znalezione_linki)
                                st.success(f"Gotowe! Znaleziono {len(posortowane_linki)} pożądanych linków.")
                                
                                formatowane_linki = "\n".join(posortowane_linki)
                                st.code(formatowane_linki, language="text")
                                
                                st.download_button(
                                    label="Pobierz listę linków jako plik .txt",
                                    data=formatowane_linki,
                                    file_name="wyciagniete_linki.txt",
                                    mime="text/plain",
                                    key="download_links"
                                )
                            else:
                                st.warning("Nie znaleziono linków spełniających podane kryteria.")
                        else:
                            st.error(f"Błąd pobierania strony. Kod HTTP: {response.status_code}")
                            
                    except requests.exceptions.RequestException as e:
                        st.error(f"Wystąpił błąd sieciowy podczas łączenia: {e}")

if __name__ == "__main__":
    generate_regex()
