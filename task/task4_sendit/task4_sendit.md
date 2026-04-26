Przygotuj kompletną deklarację przewozową.

**Kroki do wykonania:**
1.  **Pobierz i zrozum dokumentację** (`fetch_doc_and_links` z ${HUB_DANE_BASE_URL}/doc/index.md).
    *   Znajdź **wzór deklaracji**.
    *   Znajdź **tabelę opłat** w regulaminie SPK i zasady finansowania.
    *   Znajdź informacje o **wyłączonych trasach**.
    *   Znajdź znaczenie skrótów (np. WDP, PNR itp.).
    *   Zbadaj oznaczenia kategorii.
    *   Znajdź tabelę opłat.
    *   Znajdź które załadunki mogą przejechać jako darmowe.
    *   **ZASADY ZAŁADUNKU**: Sprawdź ograniczenia co do minimalnej wagi/liczby wagonów.

2.  **Ustal PRAWIDŁOWY KOD TRASY**.
    *   Znajdź połączenie z **Gdańska** do **Żarnowca**.
    *   Sprawdź, czy trasa nie prowadzi przez odcinki wyłączone. Jeśli tak, znajdź objazd.

3.  **Ustal opłatę** i **liczbę wagonów** (przesyłka: "kasety z paliwem do reaktora", 2.8t).

4.  **Wypełnij deklarację**:
    *   Dane: Nadawca: 450202122, Punkt nadawczy: Gdańsk, Punkt docelowy: Żarnowiec, Waga: 2,8 tony (2800 kg), Zawartość: kasety z paliwem do reaktora.
    *   **Data**: Użyj formatu YYYY-MM-DD.

**Wynik**:
Zwróć wynik jako zwykły TEKST oraz w formacie JSON: { "declaration": "TRESC" }.