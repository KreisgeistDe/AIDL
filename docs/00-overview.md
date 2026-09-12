# 0. Überblick

> **M10.2 Support-Tier-Hinweis:** Dieses Kapitel beschreibt die spezifizierte Produkt-/Architekturvision und ist als `illustrative-aspirational` klassifiziert, sofern eine Fähigkeit nicht zusätzlich durch die eingefrorene M10.1-Revision 4 und Production-Normalization-Evidenz als produktiv zugelassen ist. Parser-Lesbarkeit, kanonische Zielsprache und aktuelle Produktionszulassung sind getrennte Aussagen. Die normative Zielgrammatik steht in `docs/06-grammar.md`; die Repository-Klassifikation in `spec/m10-2-language-surface-classification.json`.

## Ziel

AIDL minimiert den Lösungsraum für Coding-Agenten, ohne wesentliche
Systemsemantik in generiertem Code zu verstecken. Für jede Standardaufgabe gibt
es einen kanonischen Mechanismus. Die Textsprache ist die menschenlesbare
Projektion einer versionierten Intermediate Representation.

~~~text
Anforderung
  -> AIDL / AST
  -> Namens-, Typ-, Policy- und Topologieprüfung
  -> versionierte IR
  -> Plan für Schema, Verträge, Sync und Deployment
  -> Generatoren und Runtime
~~~

## Abdeckung statt bloßer Erweiterbarkeit

Eine Anwendungsfähigkeit ist erstklassig abgedeckt, wenn:

1. ihre Semantik in der IR repräsentiert ist,
2. ungültige Kombinationen statisch diagnostiziert werden,
3. Generatoren einen deterministischen Umsetzungsplan erhalten,
4. Fehler-, Wiederholungs- und Evolutionsverhalten testbar sind.

Eine native Implementierung kann jede fehlende Funktion anbinden. Sie erweitert
aber nicht automatisch den analysierbaren Sprachumfang.

## Architekturebenen

### Application Model

Beschreibt Domänentypen, Invarianten, Operationen, Policies, Workflows,
Benutzeroberflächen und Qualitätsanforderungen.

### System Model

Beschreibt Services, Datenbesitz, erlaubte Abhängigkeiten, Topics, Consumer,
Projektionen, Konsistenzgrenzen und Replikationsmodelle.

### Deployment Model

Beschreibt Umgebungen, Platzierung, Replicas, Skalierung, Rollout, Failover,
Ressourcenbindungen, Datenresidenz und SLOs. Provider-spezifische Namen liegen
in versionierten Adaptern oder Binding-Dateien, nicht in der Fachdomäne.

## Designprinzipien

| Prinzip | Konsequenz |
|---|---|
| Ein offensichtlicher Weg | Keine konkurrierenden Standardpatterns |
| Explizite Autorität | Schreib-, Merge- und Validierungsautorität stehen im Modell |
| Ownership vor Kopplung | Jede persistierte Entität besitzt genau einen Service |
| Fehler sind Verträge | Fehlercode, Retry-Klasse und öffentliche Daten sind typisiert |
| At-least-once als Default | Deduplizierung wird erzwungen; exactly-once wird nicht behauptet |
| Lokal atomar, verteilt kompensierbar | Keine versteckten verteilten Transaktionen |
| Portable Ressourcen | Fachmodelle nennen Fähigkeiten, keine Provider-SKUs |
| Deterministische Ausgabe | AIDL, Lockfile, Adapter und Toolchain bestimmen das Ergebnis |
| Sichere Defaults | Schreibzugriffe deny-by-default; Secrets werden nur referenziert |
| Kontrollierte Escape Hatches | Native Logik bleibt typisiert, budgetiert und capability-beschränkt |

## Sprachschichten

| Schicht | Deklarationen |
|---|---|
| Typen | enum, value, union, error, alias |
| Domäne | entity, view, invariant, index |
| Verhalten | api, policy, query, mutation, event, workflow, task |
| Verteilung | system, service, topic, consumer, projection, channel |
| Synchronisation | sync, conflict, tombstone, replica |
| Ressourcen | resource, media, deployment, binding |
| Frontend | frontend, route, page, component, form, theme |
| Qualität | test, fixture, scenario, a11y, budget, slo |
| Erweiterung | native function, native component |

## Unterstützte Architekturklassen

Die folgende Tabelle beschreibt die **Zielvision**, nicht automatisch die aktuelle Production-Semantic-Envelope-Zulassung einzelner Deklarationsfamilien.

| Klasse | Status |
|---|---|
| Modularer Monolith | erstklassig |
| Horizontale, zustandslose API-Replikation | erstklassig |
| Message-getriebene Microservices | erstklassig |
| CQRS und materialisierte Projektionen | erstklassig |
| Langlebige Workflows und Sagas | erstklassig |
| Offline Command Queue | erstklassig |
| Feldweiser Multi-Writer-Merge | erstklassig mit begrenzten Strategien |
| Medien-Upload und Verarbeitungspipeline | erstklassiges Profil |
| Realtime-Kanäle | erstklassiges Profil |
| Beliebige Peer-to-Peer-Protokolle | native Integration |
| Hard-Realtime und Kernel/Systemsoftware | Nicht-Ziel |

## Normative Begriffe

- MUSS / DARF NICHT: zwingend innerhalb der jeweils ausdrücklich als normativ markierten und aktuell zugelassenen Oberfläche.
- SOLL / SOLL NICHT: Standard innerhalb dieser Oberfläche; Abweichung benötigt eine Annotation mit Grund.
- DARF: optionale Fähigkeit innerhalb deklarierter Grenzen.
- kanonisch: Form der eingefrorenen Zielsprache; dies allein ist keine Production-Admission-Aussage.
- Owner: einziger Service, der eine Entität direkt persistieren darf.
- Authority: Instanz, die einen Wert validiert oder final bestätigt.

## Nicht-Ziele

- universelle Systemprogrammiersprache
- automatische Zerlegung beliebiger Module in Microservices
- Provider-IaC als Bestandteil des fachlichen Kerns
- beliebige DOM-Manipulation oder freie CSS-/JavaScript-Skripte
- unbeschränkte Laufzeitreflexion, Makros oder höherkindige Typen
- exakt-einmalige Ausführung über unabhängige Systeme hinweg
- Verbergen von Sicherheits-, Kosten-, Konsistenz- oder Infrastrukturgrenzen
