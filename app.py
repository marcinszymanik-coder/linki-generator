import os
import re
import time
import socket
import ipaddress

import requests
import streamlit as st
import pytesseract
from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

st.set_page_config(page_title="Generator Regex & Ekstraktor Linków", page_icon="🔍", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
MAX_BYTES = 5 * 1024 * 1024  # limit 5 MB na stronę
URL_RE = re.compile(r'https?://[^\s,;"\'<>]+')


def is_safe_url(url: str) -> bool:
    """Blokuje adresy lokalne/prywatne (ochrona przed SSRF)."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast):
                return False
        return True
    except Exception:
        return False


@st.cache_resource
def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_soup(url: str):
    """Zwraca (soup, None) lub (None, komunikat_błędu)."""
    if not is_safe_url(url):
        return None, f"Niedozwolony lub nieosiągalny adres: {url}"
    try:
        r = get_session().get(url, timeout=10, stream=True)
        if r.status_code != 200:
            return None, f"Błąd HTTP {r.status_code} dla: {url}"
        content = r.raw.read(MAX_BYTES + 1, decode_content=True)
        if len(content) > MAX_BYTES:
            return None, f"Strona zbyt duża: {url}"
        return BeautifulSoup(content, 'html.parser'), None
    except requests.exceptions.RequestException as e:
        return None, f"Błąd sieciowy dla {url}: {e}"


def clean(parsed):
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))


def build_regex(ids):
    return f".*/({'|'.join(sorted(set(ids), key=int))})-.*"


def main():
    st.title("Narzędzia SEO & Regex")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Z pliku tekstowego (.txt)",
        "Ze zrzutu ekranu (OCR)",
        "Z wyszukiwarki",
        "Zbiorcze z podstron (IRBJ)",
        "Kategorie z profilu firmy",
    ])

    id_pattern_txt = re.compile(r'/(\d+)-')
    id_pattern_ocr = re.compile(r'/\s*(\d+)\s*-')

    # --- TAB 1 ---
    with tab1:
        st.header("Ekstrakcja ID z pliku .txt")
        f = st.file_uploader("Wgraj plik z linkami (np. linki.txt)", type=["txt"])
        if f is not None:
            content = f.getvalue().decode("utf-8-sig", errors="ignore")
            ids = set(id_pattern_txt.findall(content))
            if not ids:
                st.warning("Nie znaleziono żadnych ID w podanym pliku.")
            else:
                rx = build_regex(ids)
                st.success(f"Wygenerowano regex! Unikalne ID: {len(ids)}")
                st.code(rx, language="regex")
                st.download_button("Pobierz jako regex.txt", rx, "regex.txt",
                                   "text/plain", key="download_txt")

    # --- TAB 2 ---
    with tab2:
        st.header("Ekstrakcja ID ze zrzutu ekranu")
        if os.path.exists('/usr/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

        img_file = st.file_uploader("Wybierz plik ze zrzutem ekranu", type=['png', 'jpg', 'jpeg'])
        if img_file is not None:
            img = Image.open(img_file)
            st.image(img, caption='Wgrany zrzut ekranu', use_container_width=True)

            if st.button("Wyciągnij ID i generuj Regex z obrazka"):
                with st.spinner('Analizowanie obrazu (OCR)...'):
                    try:
                        text = pytesseract.image_to_string(img, config='--psm 6')
                        found = id_pattern_ocr.findall(text)
                        if found:
                            rx = build_regex(found)
                            st.success(f"Znaleziono {len(set(found))} unikalnych ID!")
                            st.caption("OCR bywa zawodny – sprawdź ID przed użyciem.")
                            st.code(rx, language='regex')
                            st.download_button("Pobierz jako regex_ocr.txt", rx,
                                               "regex_ocr.txt", "text/plain", key="download_ocr")
                            with st.expander("Surowy tekst z OCR (debug)"):
                                st.text(text)
                        else:
                            st.warning("Nie znaleziono żadnych pasujących ID na tym obrazie.")
                    except Exception as e:
                        st.error(f"Błąd OCR. Sprawdź instalację Tesseract. Szczegóły: {e}")

        # --- TAB 3 ---
    with tab3:
        st.header("Ekstrakcja linków z wyszukiwarki")
        search_urls_in = st.text_area(
            "Podaj link(i) do wyników wyszukiwania (każdy w nowej linii, np. kolejne strony paginacji):",
            placeholder=("https://automatykab2b.pl/szukaj?q=askom\n"
                         "https://automatykab2b.pl/szukaj?q=askom&start=20"),
            height=150)
        black = st.text_area(
            "Czarna lista (każda fraza w nowej linii):",
            value="szybkie-i-latwe-planowanie-systemow\n/logowanie\n/rejestracja\n/kontakt\n/regulamin\n/polityka-prywatnosci")

        if st.button("Skanuj z wyszukiwarki", type="primary", key="btn_wyszukiwarka"):
            search_urls = list(dict.fromkeys(URL_RE.findall(search_urls_in)))
            if not search_urls:
                st.warning("Proszę podać przynajmniej jeden link do przeskanowania.")
            else:
                phrases = [x.strip() for x in black.split('\n') if x.strip()]
                links = set()
                bar = st.progress(0)
                status = st.empty()
                for i, s_url in enumerate(search_urls):
                    status.text(f"Skanowanie ({i+1}/{len(search_urls)}): {s_url}")
                    soup, err = fetch_soup(s_url)
                    if err:
                        st.error(err)
                    else:
                        domain = urlparse(s_url).netloc
                        for a in soup.find_all('a', href=True):
                            p = urlparse(urljoin(s_url, a['href']))
                            if p.netloc == domain and re.search(r'\d+', p.path):
                                c = clean(p)
                                if not any(x in c for x in phrases):
                                    links.add(c)
                    bar.progress((i + 1) / len(search_urls))
                    time.sleep(0.3)
                status.text("Skanowanie zakończone!")

                if links:
                    out = "\n".join(sorted(links))
                    st.success(f"Gotowe! Znaleziono {len(links)} unikalnych linków z {len(search_urls)} stron.")
                    st.code(out, language="text")
                    st.download_button("Pobierz listę", out, "wyszukiwarka_linki.txt",
                                       "text/plain", key="down_wyszukiwarka")
                else:
                    st.warning("Nie znaleziono linków spełniających kryteria.")

    # --- TAB 4 ---
    with tab4:
        st.header("Wyciąganie linków z podstron z filtrem kategorii")
        st.markdown("Wklej grupę adresów URL (oddzielonych spacją, enterem lub tekstem). "
                    "Skrypt wyciągnie tylko linki z cyframi.")
        urls_in = st.text_area("Lista linków startowych:", height=150)
        phrases_in = st.text_area(
            "Szukane kategorie/frazy (każda w nowej linii, link musi zawierać min. jedną):",
            value="irbj/porady\nirbj/nowosci\nirbj/aktualnosci\nirbj/filmy\nirbj/promocje")

        if st.button("Skanuj podstrony", type="primary", key="btn_irbj"):
            start_urls = list(dict.fromkeys(URL_RE.findall(urls_in)))
            if not start_urls:
                st.warning("Nie znaleziono żadnych poprawnych linków startowych.")
            else:
                phrases = [x.strip() for x in phrases_in.split('\n') if x.strip()]
                found = set()
                bar = st.progress(0)
                status = st.empty()
                for i, url in enumerate(start_urls):
                    status.text(f"Skanowanie ({i+1}/{len(start_urls)}): {url}")
                    soup, err = fetch_soup(url)
                    if err:
                        st.error(err)
                    else:
                        for a in soup.find_all('a', href=True):
                            p = urlparse(urljoin(url, a['href']))
                            if p.scheme not in ("http", "https"):
                                continue
                            c = clean(p)
                            if any(x in c for x in phrases) and re.search(r'\d+', p.path):
                                found.add(c)
                    bar.progress((i + 1) / len(start_urls))
                    time.sleep(0.3)
                status.text("Skanowanie zakończone!")

                if found:
                    out = "\n".join(sorted(found))
                    st.success(f"Gotowe. Unikalnych linków: {len(found)}")
                    st.code(out, language="text")
                    st.download_button("Pobierz listę", out, "podstrony_linki.txt",
                                       "text/plain", key="down_irbj")
                else:
                    st.info("Nie znaleziono linków spełniających kryteria.")

    # --- TAB 5 ---
    with tab5:
        st.header("Wyciąganie fragmentów kategorii firm")
        st.markdown("Wklej link(i) do profilu firmy (np. `https://automatykab2b.pl/firmy/827-amtek`). "
                    "Zwracam fragment po `/firmy/` oddzielony znakiem `|`.")
        urls_in = st.text_area("Linki do profilu firm:",
                               placeholder="https://automatykab2b.pl/firmy/827-amtek\n...", height=100)

        if st.button("Wyciągnij kategorie", type="primary", key="btn_kategorie"):
            start_urls = list(dict.fromkeys(URL_RE.findall(urls_in)))
            if not start_urls:
                st.warning("Proszę podać przynajmniej jeden link.")
            else:
                frags = set()
                with st.spinner("Pobieranie i analizowanie stron..."):
                    for url in start_urls:
                        soup, err = fetch_soup(url)
                        if err:
                            st.error(err)
                            continue
                        domain = urlparse(url).netloc
                        for a in soup.find_all('a', href=True):
                            p = urlparse(urljoin(url, a['href']))
                            if p.netloc == domain and p.path.startswith('/firmy/'):
                                frag = p.path[len('/firmy/'):].strip('/')
                                if frag and frag != 'szukaj' and not re.match(r'^\d+-', frag):
                                    frags.add(frag)
                        time.sleep(0.3)

                if frags:
                    out = "|".join(sorted(frags))
                    st.success(f"Sukces! Wyciągnięto {len(frags)} unikalnych kategorii.")
                    st.code(out, language="text")
                    st.download_button("Pobierz fragmenty", out, "kategorie_firmy.txt",
                                       "text/plain", key="down_kat")
                else:
                    st.info("Nie znaleziono kategorii przypisanych do podanego profilu firmy.")


if __name__ == "__main__":
    main()
