# Domänentransparente Abfragen auf Robotikdatenbanken – Notebooks zur Bachelorarbeit

Dieses Repository enthält die Jupyter-Notebooks zur Bachelorarbeit
*Domänentransparente Abfragen auf Robotikdatenbanken: Erweiterung eines
EQL-zu-SQL-Übersetzers und Vergleich mit generiertem und handgeschriebenem SQL*.

Mit den Notebooks lassen sich die Ergebnisse der Evaluation (Kapitel 6 der Arbeit)
neu erzeugen. Außerdem kann man EQL auf der Datenbank eines aufgezeichneten
Roboterplans ausprobieren (Kapitel 7, Abschnitt „Notebooks zum Nachvollziehen der
Ergebnisse“).

## Hintergrund

Die Entity Query Language (EQL) ist eine Abfragesprache aus KRROOD, einem Framework
der Robotikarchitektur CRAM (Cognitive Robot Abstract Machine). Mit EQL lassen sich
Abfragen direkt über die Domänenklassen formulieren. Ein Übersetzer erzeugt daraus
SQL für die relationalen Datenbanken, in denen das Planungsframework coraplex
(früher pycram) Aktions-, Plan- und Weltdaten speichert.

- CRAM-Repository: [cram2/cognitive_robot_abstract_machine](https://github.com/cram2/cognitive_robot_abstract_machine)
- Stand des Übersetzers, auf den sich die Arbeit bezieht:
  [Commit d6458e2](https://github.com/zanto21/cognitive_robot_abstract_machine/tree/d6458e27beeed21a8a468950715f9b957e7c34da)
  im Branch `test_eql_to_sql`, später in das CRAM-Repository übernommen
- KRROOD-Paper: [arXiv:2601.14840](https://arxiv.org/abs/2601.14840)

## Im Browser starten (BinderHub)

[https://binder.intel4coro.de/v2/gh/zanto21/EQLshow/HEAD](https://binder.intel4coro.de/v2/gh/zanto21/EQLshow/HEAD)

Der erste Start baut das Image und kann einige Minuten dauern.

Das Image installiert krrood, coraplex und die übrigen benötigten Pakete aus dem
aktuellen `main`-Branch des CRAM-Repositorys. Die Ergebnisse der Arbeit wurden mit
dem oben verlinkten Stand erzeugt. Spätere Änderungen in CRAM können das generierte
SQL und damit einzelne Metrikwerte leicht verändern.

## Notebooks

Alle Notebooks liegen in `tutorials/`.

| Notebook | Inhalt |
|---|---|
| `metrics_evaluation.ipynb` | Übersetzt die sechs Abfragen der Evaluation, zeigt EQL, generiertes SQL (GenSQL) und handgeschriebenes SQL (HandSQL) nebeneinander und erzeugt alle Ergebnistabellen der Arbeit (Metriken, Übersetzer-Overhead, Skalierung, Feature-Tabelle). Jede HandSQL-Abfrage wird einmal gegen die Testdatenbank ausgeführt. |
| `metrics_data_setup.ipynb` | Baut die Testdatenbank und die Beispielwelten auf und wird von `metrics_evaluation.ipynb` per `%run` eingebunden. |
| `plan_db_create.ipynb` | Führt einen Roboterplan in der Simulation aus und speichert ihn als SQLite-Datenbank (`plan_result_rich.sqlite`). |
| `plan_db_queries.ipynb` | Stellt EQL-Abfragen an diese Plan-Datenbank und zeigt jeweils EQL, generiertes SQL und Ergebnis. Am Ende ist Platz für eigene Abfragen. |

`eql_metrics.py` enthält die Metrikfunktionen (Zeichenlänge, technischer Lärm,
Domänen-Transparenz, Verschachtelungstiefe, Halstead-Volumen,
Fremdschlüssel-Fehleranfälligkeit, extrinsische Last, kognitive Komplexität),
die EQL-Quelltexte und HandSQL-Abfragen der sechs Queries sowie die
Feature-Tabelle. Die Zählregeln sind im Anhang der Arbeit beschrieben.

**Reihenfolge:**

1. Evaluation: `metrics_evaluation.ipynb` ausführen. Das Notebook lädt `metrics_data_setup.ipynb` selbst.
2. Plan-Datenbank: erst `plan_db_create.ipynb`, dann `plan_db_queries.ipynb`.

`plan_db_queries.ipynb` braucht einen eigenen Kernel, also einen Kernel-Neustart
nach `metrics_evaluation.ipynb`. Die ORM-Klassen der Plan-Datenbank und die
Testklassen der Evaluation registrieren Tabellen in denselben
SQLAlchemy-Metadaten und lassen sich deshalb nicht im selben Kernel laden.

## Lokal starten (Docker)

```bash
docker compose up --build
```

Danach `http://localhost:8888` im Browser öffnen (kein Token nötig).

## Struktur

```
Dockerfile           Image auf Basis von intel4coro/jupyter-ros2 mit den CRAM-Paketen (coraplex, krrood, ...)
docker-compose.yml   Lokales Docker-Setup
entrypoint.sh        Lädt die ROS2- und Workspace-Umgebung beim Containerstart
scripts/             Hilfsskripte, die beim Bauen des Images Import-Probleme beheben
tutorials/           Notebooks und eql_metrics.py
```
