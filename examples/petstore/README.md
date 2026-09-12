# Petstore

> **M10.2 Support-Tier:** Die committed `.aidl`-Dateien dieses Referenzbeispiels sind bis zur M10.3-Migration als `legacy-readable-compatibility` klassifiziert. Parser-Lesbarkeit, vorhandene Tooling-/Runtime-Slices und die Produktgeschichte sind keine pauschale Production-Admission-Aussage für jede darin verwendete Deklaration oder Schreibweise. Die maschinenlesbare Klassifikation steht in `spec/m10-2-language-surface-classification.json`; M10.3 migriert bzw. disponiert die beabsichtigte Referenzoberfläche.

Das Beispiel ist ein modularer, horizontal replizierbarer Petstore mit einer
lokalen SQL-Transaktionsgrenze.

Es demonstriert:

- OIDC-Identität ohne inkonsistente lokale User-Doppelung,
- explizite mutable/immutable-Felder und Revisionen,
- Compare-and-set gegen parallele Adoptionsanfragen,
- vollständige Idempotenz- und Fehlerverträge,
- atomare Outbox-Publikation,
- idempotenten Consumer als Workflow-Trigger,
- explizite Rückgabewerte,
- Web-UI mit stabiler Operation-ID und Conflict Handling,
- lokale und produktive Deployment-Profile,
- Concurrency-, Duplicate-Delivery- und Crashpoint-Tests.

PetstoreService besitzt alle fachlichen Entitäten. Das ist bewusst ein
modularer Monolith: Die Adoption aktualisiert Pet und AdoptionRequest in einer
einzigen lokalen Transaktion. Eine künstliche Trennung in Microservices würde
eine Saga erfordern und für dieses Beispiel keinen fachlichen Nutzen bringen.

## Struktur

~~~text
app.aidl
domain/
contracts/
operations/
policies/
system/
deployments/
ui/
tests/
aidl.lock
~~~

## Prüfen

~~~bash
aidl check . --format json
aidl compatibility .
aidl plan . --deployment production
aidl test . --suite all
python3 ../../tools/spec_lint.py ../..
~~~
