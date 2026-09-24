# CivIdle-Kompendium: Bestand und offene Kapitel

Dokumentstand: 23. September 2026. Gemeint ist **CivIdle**, nicht Civilization.

## Was dieser Bereich enthält

Hier werden vorhandene Anleitungen und Projektunterlagen zugänglich gemacht. Die Status-App-Anleitung erklärt die Bedienung der EXE. Dieser Text hält fest, welche Spielthemen noch vollständig und überprüfbar ausgearbeitet werden sollen.

Die neue Übersicht ist noch kein vollständig recherchiertes Spielhandbuch. Drei frühere Kompendium- und Guide-Dateien sind als unveränderte Originale beigefügt. Ihre Prüfsummen stimmen mit dem dokumentierten historischen Bestand überein. Diese Übereinstimmung belegt die Dateiidentität; die Inhalte wurden hier nicht erneut gegen den aktuell installierten Steam-Build geprüft.

## Gewünschter Umfang des Spielkompendiums

| Thema | Noch auszuarbeiten bzw. gegen den Spielbuild zu prüfen |
| --- | --- |
| Gebäude | Freischaltungen, Baukosten, Bauzeiten, Produktions- und Upgradeeffekte |
| Produktion | Ressourcen je Gebäude und Stufe, Multiplikatoren sowie Verbrauch und Nettoproduktion |
| Transport und Lager | Wege, Durchsatz, Lagerkapazität, Engpässe und Auswirkungen auf die Produktion |
| Forschung | Forschungsbaum, Kosten, Freischaltungen und Boni |
| Grosse Persönlichkeiten / GP | Auswahl, Fähigkeiten, Levelkosten und Auswirkungen auf Rebirth-Routen |
| Zeitalter | Geeignete Abläufe für die gewünschten GP- und Rebirth-Ziele |
| Karten | Karteneigenschaften, Unterschiede bei der Bedienung und sinnvolle Bauabläufe |
| Praxis | Einstellungen, Tasten, Startzustand, verständliche Beispiele und bebilderte Abläufe |
| Botvergleich | Vollständige Rebirth-Zeit, erfolgreiche Läufe und Stabilität anhand benannter Messungen |

Für Leveltabellen ist **Level 100 ausreichend**, wie im bisherigen Auftrag festgelegt. Tabellen bis Level 500 gehören nicht zum bestätigten Bedarf.

## Wie verlässliche Tabellen entstehen sollen

Jede Spieltabelle benötigt eine benannte Spielversion oder einen gebundenen Originalquellstand. Werte aus unterschiedlichen Builds dürfen nicht stillschweigend zusammengeführt werden. Formeln und Rundung sollten nachvollziehbar bleiben; besondere Boni und Voraussetzungen gehören zur Zeile oder Tabelle.

Für Beispiele aus dem Spiel sollen passende Originalbilder oder gespeicherte Zustände verwendet werden. Eine fehlende Quelle wird als offen festgehalten. Leere Zahlenfelder werden nicht durch vermutete Baukosten, GP-Kosten oder Produktionswerte ersetzt.

## Verbindung zum Botprojekt

Das Projekt soll bestehende geprüfte Botbestandteile weiter verbessern. OpenCV kann gespeicherte Bildschirmbilder auswerten; ein früherer Bildtest belegt keinen gerade laufenden Serverprozess und kein selbstlernendes Modell. Ein Ablauf ohne sichtbares Grafikfenster und ein laufendes grafisches Spiel sind getrennt zu dokumentieren.

Der gespeicherte Rebirth-Kandidat vom 23.09.2026 verbessert die Behandlung des Gesamtzeitlimits. Er ist offline geprüft. Seine Integration in den vollständigen Serverbot und echte Laufmessungen waren in dieser Übergabe noch offen. Einzelheiten stehen in `BOT_WISSENSSTAND.md`.

## Historische Dokumente

Im früheren Projektbestand sind diese Dateien nachgewiesen:

- `CivIdle_Ultimatives_Kompendium_Build968_2026-09-06.pdf`
- `CivIdle_Kompendium_2026-09-05.zip`
- `CivIdle_Erkenntnisse_und_Guide_2026-09-21.zip`

Die Originaldateien liegen im Unterordner `originals/` und sind im Katalog einzeln auswählbar. Der Buildbezug im ersten Dateinamen wird als historische Angabe erhalten; daraus folgt keine Prüfung des heute installierten Spiels.

Das ZIP vom 05.09.2026 enthält laut seinem Dateiverzeichnis unter anderem Forschungs- und GP-Tabellen, generische Upgrade-Skalierung, Gebäude-Basiswerte, Upgrade-Beispiele bis Level 50 und einen Guide. Damit sind echte frühere Materialien vorhanden. Ob sie alle gewünschten Themen bis Level 100 korrekt und vollständig abdecken, ist in dieser App-Ergänzung nicht neu geprüft worden.

Das ZIP vom 21.09.2026 enthält laut Dateiverzeichnis einen Einrichtungsguide, Werkzeugvergleich, Texte zu Headless-Arbeit und echtem Bot, Messregeln, Auftragsvorlagen und eine Roadmap. Es ist eine historische Projektsammlung.

Das ebenfalls vorhandene `CIVIDLE_SETUP_750_CHF.md` beschreibt ein recherchiertes Infrastrukturkonzept vom 22./23.09.2026. Es ist kein Gebäude- oder Forschungshandbuch und keine bestätigte Bestellung. Anbieterpreise und Verfügbarkeit darin sind an den damaligen Recherchezeitpunkt gebunden.

## Nächster inhaltlicher Schritt

Als Nächstes den Inhalt der beigefügten historischen Originaldokumente gegen den aktuellen Spielbuild prüfen, Lücken nach Themen ordnen und die Tabellen bis Level 100 anhand passender Quellen vervollständigen. Die offenen Aufgaben und bereits getroffenen Entscheidungen bleiben dabei erhalten.

Grundlagen und Bestandsbelege: `catalog.json`, Abschnitt `provenance`.
