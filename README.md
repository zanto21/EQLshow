# EQL in SQL Übersetzen — Interaktive Demo

Dieses Repository enthält eine interaktive Jupyter-Notebook-Demo zur Bachelorarbeit
*EQL in SQL Übersetzen*. Die Umgebung basiert auf `intel4coro/jupyter-ros2:jazzy-py3.12`
und bringt ROS2 Jazzy sowie pycram bereits vorinstalliert mit.

## Was zeigt die Demo?

- Live-Übersetzung von EQL-Ausdrücken in SQL, inklusive der Beispiele aus der
  Bachelorarbeit (einfacher Filter, transitiver Attributzugriff, Multi-Variable-Join,
  Sortierung und Limit)
- Verifikation, dass EQL-Auswertung und SQL-Auswertung dasselbe Ergebnis liefern
  (analog zur Teststrategie aus Abschnitt 5.9 der Arbeit)
- Ein interaktives Dropdown-Menü, mit dem verschiedene EQL-Beispiele ausgewählt
  werden können, jeweils mit live berechnetem SQL und den zugehörigen Metriken
- Ein zusammenfassendes Diagramm, das die Kognitive Komplexität (Campbell, 2018)
  und weitere Metriken aus Kapitel 6 der Arbeit live aus den generierten
  Übersetzungen berechnet und visualisiert
- Ein abschließendes Fazit, das die Ergebnisse mit der Bachelorarbeit verknüpft

## Struktur

```
Dockerfile               # Erweitert intel4coro/jupyter-ros2 um pycram + krrood
docker-compose.yml       # Lokales Docker-Compose-Setup
entrypoint.sh            # Sourced ROS2- und Workspace-Umgebung beim Containerstart
notebooks/
  eql_demo.ipynb           # Die interaktive Demo
  eql_metrics.py            # Reine Metrikfunktionen aus test_eql_readability.py,
                             # ohne pytest-Abhängigkeiten, direkt importierbar
```

## Auf BinderHub starten

Diese Demo läuft auf der Cloud-based Robotics Platform der Universität Bremen:
[https://binder.intel4coro.de/](https://binder.intel4coro.de/)

Repository-URL beim Start angeben:
```
https://github.com/zanto21/EQLshow
```

## Lokal starten (mit Docker)

```bash
docker compose up --build
```

Danach im Browser `http://localhost:8888` öffnen (kein Token/Passwort nötig).

## Hinweis zu eql_metrics.py

`eql_metrics.py` ist ein bewusst schlanker Auszug aus
`test/krrood_test/test_ormatic/test_eql_readability.py`. Die dortigen `test_*`-Funktionen
benötigen pytest-Fixtures (insbesondere `session` aus `conftest.py`) und sind daher nicht
direkt in einem Notebook lauffähig. `eql_metrics.py` enthält nur die neun reinen
Metrikfunktionen (Zeichenlänge, technischer Lärm, Domänen-Transparenz, Verschachtelungstiefe,
Halstead-Volumen, Abstraktionsverhältnis, Fremdschlüssel-Fehleranfälligkeit, extrinsische
kognitive Last, kognitive Komplexität) sowie die `analyze()`-Hilfsfunktion.

## Hintergrund

Der EQL-zu-SQL-Übersetzer stammt aus dem Projekt
[cognitive_robot_abstract_machine](https://github.com/cram2/cognitive_robot_abstract_machine)
(krrood). Die vollständige wissenschaftliche Auswertung und Methodik ist in der
zugehörigen Bachelorarbeit beschrieben (siehe `main.pdf` im Repository-Root).
