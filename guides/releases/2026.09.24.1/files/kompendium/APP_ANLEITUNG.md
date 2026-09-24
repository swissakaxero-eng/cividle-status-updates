# CivIdle-Status-App: kurze Anleitung

Dokumentstand: 23. September 2026. Zielversion 2026.09.23.3 / Build 2026092303; native Abnahme und tatsächliche neue Serveranbindung noch ausstehend.

## Auf welchem Gerät?

Die Status-App gehört auf deinen Windows-PC oder Laptop. CivIdle und der eigentliche Spielbot laufen auf dem Server. Mit der Status-App liest du den gespeicherten Arbeitsstand und bereitest Dateien für die Fortsetzung vor.

Entpacke das gesamte Downloadpaket in einen eigenen Ordner. Starte darin `CivIdle_Starten.bat`. Die Startdatei öffnet die EXE zusammen mit dem beigefügten `PROJEKTSTAND_AKTUELL.json`. Lass diese Dateien zusammen im Ordner. Für die fertige EXE brauchst du kein eigenes Python.

## Die wichtigsten Tasten

| Taste | Verwendung |
| --- | --- |
| JSON auswählen | Einen gespeicherten Projektstand öffnen. Die App lädt spätere Änderungen an dieser Datei automatisch. |
| GitHub verbinden | Neue Projektbelege und veröffentlichte Servermeldungen automatisch aus dem privaten Repository lesen. Dafür ist ein GitHub-Token mit Leserecht nötig. |
| Trennen | Die aktuelle Quelle trennen und die automatische Aktualisierung beenden. |
| Details anzeigen | Aufgaben, Prüfbelege, Messwerte und Quellen im eigenen Fenster ansehen. Ein Doppelklick auf eine Zeile öffnet den gesamten Eintrag. |
| Snapshot speichern | Den gerade geladenen, geprüften Stand als JSON-Datei unter Dokumente → CivIdle → Sicherungen speichern. |
| Neuen Chat vorbereiten | Eine ZIP unter Dokumente → CivIdle → Chat-Uebergaben erstellen und auf Windows für das Einfügen als Datei bereitstellen. |
| Bibliothek | Mitgelieferte Anleitungen und Kompendien sowie die eigenen Chat-Übergaben und Sicherungen finden. |
| App-Update / Update verfügbar | Nach einer neuen Appfassung sehen und ein verfügbares Update nach Bestätigung installieren. |

Lass die Maus kurz über einer Taste stehen: Nach ungefähr einer halben Sekunde erscheint ihre Erklärung. Auch eine derzeit graue Taste kann erklären, was noch fehlt. Der Hinweis verschwindet, wenn du die Taste verlässt, klickst oder Escape drückst.

Ein GitHub-Token bleibt nur während der Sitzung im Arbeitsspeicher. Ohne GitHub-Verbindung kannst du weiterhin lokale JSON-Dateien verwenden. Ein vorhandenes Zugriffsrecht in ChatGPT ist keine Anmeldung der Windows-App.

## Was die Anzeige bedeutet

Die vier Bereiche **Spielbot**, **Ohne Grafik**, **OpenCV** und **Server-Agent (beim Bot)** beschreiben getrennte Rollen. Eine vorhandene Meldung aus einem Chat steht zusätzlich unter **Chat-Arbeit**. Ein bestandener früherer Test beweist nicht, dass der zugehörige Teil gerade läuft. Wenn frische Laufbelege fehlen, bleibt der aktuelle Zustand unbekannt.

Der Server-Agent ist der bestehende Steuerworker auf dem Server. Er ist kein Nachweis dafür, dass ein Sprachmodell selbstständig den Bot weiterentwickelt. Eine Lebensmeldung kann den Worker als erreichbar ausweisen; Entwicklung, Tests oder Spielbetrieb brauchen jeweils eine ausdrückliche passende Meldung. Chat-Arbeit an der PC-App wird getrennt angezeigt und ist kein Serverlauf.

**Quelle zuletzt geprüft** bezeichnet den Abruf der Quelle. Der **Quellenstand** und das **Datenalter** sagen, wie alt ihr Inhalt ist. Eine eben geladene Datei kann einen älteren Arbeitsstand enthalten. Unter Details findest du die zugehörigen Belege.

Gespeicherte Änderungen und Tests sind ein Fortschritt in der Entwicklung. Eine schnellere Rebirth-Zeit ist erst belegt, wenn passende echte Läufe gemessen und verglichen wurden. Die Status-App startet durch das Lesen eines Projektstands keinen Spielbot.

### Gemeldete Tätigkeit

**Entwickeln**, **Testen** oder **Leerlauf** werden aus ausdrücklichen Statusmeldungen angezeigt. Dazu gehören der betroffene Bereich, die Quelle, der Zeitpunkt und eine begrenzte Gültigkeit. Für neue veröffentlichte Servermeldungen wähle auf deinem PC **GitHub verbinden**. Die mitgelieferte JSON enthält einen gespeicherten Stand und meldet die App nicht automatisch bei GitHub an.

Eine Meldung gilt höchstens **fünf Minuten ab ihrem eigenen Meldezeitpunkt**. Die Anzeige prüft das jede Sekunde. Ein neuer Abruf verlängert diese Gültigkeit nicht. Fehlt eine aktuelle Meldung oder ist sie abgelaufen, lautet die Anzeige **Status unbekannt**; das bedeutet weder gestoppt noch untätig. Die App erkennt fremde Chats nicht automatisch. Ob die neue Serveranbindung tatsächlich funktioniert, wird im Abschlussbericht von Version 3 separat nachgewiesen und ist zu diesem Dokumentstand noch offen.

## In einem neuen Chat weiterarbeiten

1. Lade den Projektstand, den du übergeben möchtest.
2. Wähle **Neuen Chat vorbereiten**. Die ZIP wird im zugehörigen CivIdle-Ordner gespeichert.
3. Öffne selbst einen neuen Chat im bestehenden CivIdle-Projekt.
4. Hänge die ZIP an und bitte den neuen Chat, `START_HIER.txt` und die darin genannte Lesereihenfolge zu beachten.

Ein JSON-Snapshot speichert den Status. Die Übergabe-ZIP ist für die Fortsetzung mit Aufgaben, Quellen und vorhandenen Arbeitsdateien gedacht. Die ZIP enthält gespeicherte Unterlagen; ungespeicherte Nachrichten aus einem offenen Browserchat sind darin nicht automatisch enthalten.

Wenn die App bestätigt, dass die ZIP in der Zwischenablage liegt, kannst du im neuen Chat **Strg+V** versuchen. Ob der Browser die Datei dabei als Anhang übernimmt, hängt von dessen Unterstützung ab. Die ZIP bleibt zusätzlich im Ordner **Chat-Uebergaben** gespeichert und kann über die Anhangfunktion ausgewählt werden.

## Bibliothek und lokale Dateien

**Bibliothek** bündelt die Bereiche **Kompendium/Guide**, **Chat-Uebergaben** und **Sicherungen**. Die Standardablage liegt unter **Dokumente → CivIdle**. Der Dokumentbereich enthält die mitgelieferten Texte und historischen Originaldateien. Datums- und Umfangsangaben helfen, ihren Stand einzuordnen.

Die Kompendium-/Guide-Sammlung lässt sich als eigenes ZIP speichern. Ein historisches Kompendium wird dabei als Original erhalten. Seine Aufnahme in die App bestätigt keine neuen Spielwerte und keine aktuelle Prüfung gegen den installierten Steam-Build.

## Die App aktualisieren

**App-Update** prüft mit bestehender GitHub-Verbindung auf ein verfügbares Update. Bei einer gefundenen neuen Fassung zeigt die Taste **Update verfügbar**. Die App lädt und prüft das angebotene Paket nach deiner Bestätigung und startet die neue Fassung.

Ohne GitHub-Verbindung kannst du ein vorhandenes App-Updatepaket über **Update-ZIP öffnen** auswählen. Es muss dafür nicht von Hand entpackt oder in den Appordner kopiert werden. Nach dem Neustart musst du einen GitHub-Token erneut eingeben, wenn du GitHub weiter verwenden möchtest; der Token wird nicht dauerhaft gespeichert.

Die Statusdaten und das Appprogramm sind getrennte Dinge: Eine neue JSON aktualisiert den angezeigten Projektstand. Eine neue EXE kann die Bedienung oder Funktionen der App ändern.

## Wenn etwas unklar ist

Bei „Noch kein geprüfter Stand geladen“ verwende **JSON auswählen** und öffne die mitgelieferte Projektstanddatei. Bei einer GitHub-Meldung prüfe die Verbindung und das Leserecht des Tokens. Mit einer lokalen JSON kannst du den gespeicherten Stand auch ohne erfolgreiche GitHub-Abfrage ansehen.

Bei vermeintlich alten Daten vergleiche zuerst Quellenstand und Abrufzeit. Ein häufigerer Abruf macht den Inhalt der Quelle nicht neuer.

Diese Anleitung gehört zum mitgelieferten Appstand. Die Dokumente und ihre Datumsangaben findest du im begleitenden Katalog. Neue Appfassungen können zusätzliche Bedienmöglichkeiten enthalten.

## Grundlage

Die Anleitung wurde aus dem vorhandenen Appverhalten, der Startdatei und den dokumentierten Übergaberegeln zusammengestellt. Die Quellenbezüge stehen im begleitenden `catalog.json`. Prüfberichte zur tatsächlichen Ausführung gehören zum jeweiligen Apppaket.
