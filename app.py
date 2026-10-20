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

    # Tworzenie zakładek dla 4 metod
    tab1, tab2, tab3, tab4 = st.tabs([
        "Z pliku tekstowego (.txt)", 
        "Ze zrzutu ekranu (OCR)", 
        "Z wyszukiwarki", 
        "Zbiorcze z podstron (IRBJ)"
    ])

    id_pattern_txt = re.compile(r'/(\d+)-')
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

        if st.button("Skanuj z wyszukiwarki", type="primary", key="btn_wyszukiwarka"):
            if not search_url:
                st.warning("Proszę podać link do przeskanowania.")
            else:
                odrzucane_frazy = [fraza.strip() for fraza in odrzucane_input.split('\n') if fraza.strip()]
                
                with st.spinner("Pobieranie i analizowanie wyników..."):
                    headers = {'User-Agent': 'Mozilla/5.0'}
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
                                
                                if parsed.netloc == domena_bazowa:
                                    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
                                    
                                    if re.search(r'\d+', parsed.path):
                                        if not any(fraza in clean_url for fraza in odrzucane_frazy):
                                            znalezione_linki.add(clean_url)
                            
                            if znalezione_linki:
                                posortowane_linki = sorted(znalezione_linki)
                                st.success(f"Gotowe! Znaleziono {len(posortowane_linki)} pożądanych linków.")
                                formatowane_linki = "\n".join(posortowane_linki)
                                st.code(formatowane_linki, language="text")
                                st.download_button("Pobierz listę", formatowane_linki, "wyszukiwarka_linki.txt", "text/plain", key="down_wyszukiwarka")
                            else:
                                st.warning("Nie znaleziono linków spełniających podane kryteria.")
                        else:
                            st.error(f"Błąd pobierania strony. Kod HTTP: {response.status_code}")
                            
                    except requests.exceptions.RequestException as e:
                        st.error(f"Wystąpił błąd sieciowy podczas łączenia: {e}")

    # ==========================================
    # ZAKŁADKA 4: Zbiorcze z podstron (IRBJ)
    # ==========================================
    with tab4:
        st.header("Wyciąganie linków z podstron z filtrem kategorii")
        
        st.markdown("Wklej całą grupę adresów URL (mogą być oddzielone spacją, enterem lub innym tekstem). Skrypt wyciągnie tylko linki z cyframi (np. artykuły).")
        urls_input_irbj = st.text_area("Lista linków startowych do przeskanowania:", height=150)
        
        phrases_input_irbj = st.text_area(
            "Szukane kategorie/frazy (każda w nowej linii, link musi zawierać minimum jedną):",
            value="irbj/porady\nirbj/nowosci\nirbj/aktualnosci\nirbj/filmy\nirbj/promocje"
        )
        
        if st.button("Skanuj podstrony", type="primary", key="btn_irbj"):
            start_urls = list(set(re.findall(r'https?://[^\s,;\"\'<>]+', urls_input_irbj)))
            
            if not start_urls:
                st.warning("Nie znaleziono żadnych poprawnych linków startowych w podanym tekście.")
            else:
                szukane_frazy = [fraza.strip() for fraza in phrases_input_irbj.split('\n') if fraza.strip()]
                headers = {'User-Agent': 'Mozilla/5.0'}
                znalezione_linki_irbj = set()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_urls = len(start_urls)
                
                for i, url in enumerate(start_urls):
                    status_text.text(f"Skanowanie ({i+1}/{total_urls}): {url}")
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            for a_tag in soup.find_all('a', href=True):
                                href = a_tag['href']
                                if any(fraza in href for fraza in szukane_frazy):
                                    if re.search(r'\d+', href):
                                        full_url = urljoin(url, href)
                                        parsed = urlparse(full_url)
                                        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
                                        znalezione_linki_irbj.add(clean_url)
                    except Exception as e:
                        st.toast(f"Wystąpił błąd podczas łączenia z {url}: {e}")
                    
                    progress_bar.progress((i + 1) / total_urls)
                
                status_text.text("Skanowanie zakończone!")
                
                if znalezione_linki_irbj:
                    posortowane_linki = sorted(znalezione_linki_irbj)
                    st.success(f"Gotowe. Znaleziono łącznie unikalnych linków: {len(posortowane_linki)}")
                    formatowane_linki = "\n".join(posortowane_linki)
                    st.code(formatowane_linki, language="text")
                    st.download_button("Pobierz listę", formatowane_linki, "podstrony_linki.txt", "text/plain", key="down_irbj")
                else:
                    st.info("Nie znaleziono linków spełniających podane kryteria.")

if __name__ == "__main__":
    generate_regex()
