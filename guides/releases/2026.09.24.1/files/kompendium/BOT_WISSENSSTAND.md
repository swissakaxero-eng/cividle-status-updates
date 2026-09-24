# CivIdle-Bot: dokumentierter Wissensstand

Bezugsstand: Rebirth-Kandidat vom 23. September 2026. Dieser Text beschreibt den gespeicherten Entwicklungsstand. Neuere geprüfte Projektbelege können ihn ergänzen oder ersetzen.

## Rollen

**Spielbot:** Führt die vorgesehenen Spielaktionen aus. **OpenCV:** Prüft Bildschirmzustände und bekannte Bildmerkmale. **Ohne Grafik:** Bezeichnet gesonderte Arbeit ohne sichtbares Grafikfenster, beispielsweise die Auswertung gespeicherter Bilder. **Server-Agent (beim Bot):** Der bestehende Steuerworker auf dem Server. **Chat-Arbeit:** Getrennte Analyse und Entwicklung im Chat, beispielsweise an der PC-Status-App. Die Tätigkeit eines Teils belegt nicht automatisch die Tätigkeit der anderen Teile.

Die Rollenbezeichnungen entsprechen dem vorbereiteten Appstand V3. Ein erreichbarer Server-Steuerworker belegt keine autonome Botentwicklung durch ein Sprachmodell. Die neue Serveranbindung und ihre native Abnahme sind zu diesem Dokumentstand noch ausstehend. Der folgende Rebirth-Abschnitt bleibt der unveränderte historische Kandidatenstand.

Die Status-App zeigt gespeicherte Belege dieser Bereiche auf dem eigenen PC. Neue veröffentlichte Servermeldungen benötigen dort eine GitHub-Verbindung; ein geöffnetes lokales JSON ersetzt sie nicht. Berichte gelten höchstens fünf Minuten ab ihrem Meldezeitpunkt. Fehlen passende frische Ereignisse, bleibt der aktuelle Zustand unbekannt; daraus folgt kein bewiesener Stopp. Ein offener Chat oder eine grüne Entwicklungsanzeige ersetzt keine solche Prozessbeobachtung.

## Gesicherte Rebirth-Verbesserung

Der Kandidat `rebirth-deadline-20260923` verwendet ein gemeinsames Zeitbudget über die beteiligten Rebirth-Funktionen. Beim Wechsel zwischen ihnen startet das Gesamtbudget nicht erneut.

Nach einer verspäteten Bildschirmaufnahme oder Erkennung blockiert der nächste Kontrollpunkt weitere Aktionen. Ein manueller Stopp hat bei der Prüfung Vorrang. Kurze Pausen und lokale Warteabschnitte halten das noch verfügbare Budget ein.

Die Änderung besteht aus drei zusammengehörigen Python-Modulen. Sie wurde als separater Änderungsvorschlag [PR #623](https://github.com/swissakaxero-eng/cividle-bot-private/pull/623) gesichert. Dieser gespeicherte Verweis ist kein Hinweis darauf, dass die Änderung bereits im Serverbot installiert wurde.

## Nachgewiesener Prüfumfang

- 54 von 54 Kandidatentests bestanden, mit 154 parametrisierten Teilfällen.
- Vier Fehler des ursprünglichen Ablaufs wurden in separaten Charakterisierungstests nachgewiesen.
- Die getesteten Kontrollflüsse verwenden kontrollierte Zeit-, Bild- und Eingabequellen.
- Ein unabhängiger Quellreview und die Bindung der verwendeten Dateien sind dokumentiert.

Diese Tests belegen die geprüften Abläufe. Sie messen keine neue Rebirth-Geschwindigkeit im echten Spiel und keine verbesserte Bild-Erkennungsquote. Ein schon gestarteter synchroner Aufruf wird nicht hart unterbrochen; sein verspätetes Ergebnis wird nach der Rückkehr am nächsten Kontrollpunkt abgefangen.

## Was für den Betrieb noch zu prüfen ist

Die drei Module müssen gemeinsam in einen vollständigen neuen Botkandidaten integriert werden. Danach sind die regulären Abhängigkeiten und Prüfungen des gesamten Laufzeitpakets nötig. Der hier beschriebene Stand enthält keinen Nachweis eines anschliessenden echten Spiellaufs.

Die festgehaltene Vergleichsregel bleibt: zunächst genau drei erfolgreiche Screening-Läufe mit besserem Median der vollständigen Zykluszeit `full_cycle_sec`; anschliessend 20 von 20 stabile Läufe für den Sieger. Nur vergleichbare, tatsächlich gemessene Läufe können eine Geschwindigkeitsverbesserung belegen.

F9 beziehungsweise Manual Stop und bereits verbrauchte Versuchskandidaten bleiben Teil des bestehenden Projektvertrags. Zuständigkeiten anderer Chats werden durch eine neue Status-App oder eine gespeicherte Anleitung nicht verändert.

## Quellen dieses Kurztexts

Der Inhalt ist eine kurze Zusammenfassung des gespeicherten Kandidaten-README, seines Vertrags und seiner Prüfergebnisse. Originalpfade, Bezugsstand und Prüfsummen sind in `catalog.json` festgehalten. Die vollständigen Botquellen und Berichte gehören zur Bot-Übergabe; diese Anleitung ersetzt sie nicht.
