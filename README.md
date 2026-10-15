# EQL in SQL übersetzen – Notebooks zur Bachelorarbeit

Dieses Repository enthält die Jupyter-Notebooks zur Bachelorarbeit
*EQL in SQL übersetzen*. Mit ihnen lassen sich die Ergebnisse der Evaluation
(Kapitel 6 der Arbeit) neu erzeugen, und EQL lässt sich auf der Datenbank eines
aufgezeichneten Roboterplans ausprobieren (Kapitel 7, Abschnitt „Notebooks zum
Nachvollziehen der Ergebnisse“).

Die Umgebung basiert auf `intel4coro/jupyter-ros2:jazzy-py3.12` und installiert
pycram sowie krrood (mit dem EQL-zu-SQL-Übersetzer) aus
[cognitive_robot_abstract_machine](https://github.com/cram2/cognitive_robot_abstract_machine).

## Im Browser starten (BinderHub)

[https://binder.intel4coro.de/v2/gh/zanto21/EQLshow/HEAD](https://binder.intel4coro.de/v2/gh/zanto21/EQLshow/HEAD)

Der erste Start baut das Image und kann einige Minuten dauern.

## Notebooks

Alle Notebooks liegen in `tutorials/`.

| Notebook | Inhalt |
|---|---|
| `metrics_evaluation.ipynb` | Übersetzt die sechs Abfragen der Evaluation, zeigt EQL, generiertes und handgeschriebenes SQL nebeneinander und erzeugt alle Ergebnistabellen der Arbeit (Metriken, Übersetzer-Overhead, Skalierung, Feature-Tabelle). Jede handgeschriebene Abfrage wird einmal gegen die Testdatenbank ausgeführt. |
| `metrics_data_setup.ipynb` | Baut die Testdatenbank und die Beispielwelten auf; wird von `metrics_evaluation.ipynb` per `%run` eingebunden. |
| `plan_db_create.ipynb` | Führt einen Roboterplan in der Simulation aus und speichert ihn als SQLite-Datenbank (`plan_result_rich.sqlite`). |
| `plan_db_queries.ipynb` | Stellt EQL-Abfragen an diese Plan-Datenbank und zeigt jeweils EQL, generiertes SQL und Ergebnis. Am Ende ist Platz für eigene Abfragen. |

`eql_metrics.py` enthält die Metrikfunktionen (Zeichenlänge, technischer Lärm,
Domänen-Transparenz, Verschachtelungstiefe, Halstead-Volumen,
Fremdschlüssel-Fehleranfälligkeit, extrinsische Last, kognitive Komplexität),
die EQL-Quelltexte und handgeschriebenen SQL-Abfragen der sechs Queries sowie
die Feature-Tabelle. Die Zählregeln sind im Anhang der Arbeit beschrieben.

**Reihenfolge:**

1. Evaluation: `metrics_evaluation.ipynb` ausführen (lädt `metrics_data_setup.ipynb` selbst).
2. Plan-Datenbank: erst `plan_db_create.ipynb`, dann `plan_db_queries.ipynb`.

`plan_db_queries.ipynb` braucht einen eigenen Kernel (bzw. einen Kernel-Neustart
nach `metrics_evaluation.ipynb`): Die ORM-Klassen der Plan-Datenbank und die
Testklassen der Evaluation registrieren Tabellen in denselben
SQLAlchemy-Metadaten und lassen sich nicht im selben Kernel laden.

## Lokal starten (Docker)

```bash
docker compose up --build
```

Danach `http://localhost:8888` im Browser öffnen (kein Token nötig).

## Struktur

```
Dockerfile           Image auf Basis von intel4coro/jupyter-ros2 mit pycram und krrood
docker-compose.yml   Lokales Docker-Setup
entrypoint.sh        Lädt die ROS2- und Workspace-Umgebung beim Containerstart
scripts/             Hilfsskripte, die beim Bauen des Images Import-Probleme beheben
tutorials/           Notebooks und eql_metrics.py
```
