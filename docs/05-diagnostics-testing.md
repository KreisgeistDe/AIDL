# 5. Diagnostik und Tests

> **M10.2 Support-Tier-Hinweis:** Dieses Kapitel ist als `illustrative-aspirational` klassifiziert. Diagnose- und Testszenarien beschreiben die spezifizierte Zieloberfläche; nur repository-eigene implementierte Diagnose-/Testpfade und M10.1-zertifizierte Production-Semantic-Envelope-Fakten sind aktuelle Support-Aussagen. Die unten gezeigten `test`-Deklarationen und weitere nicht produktiv zugelassene Familien sind keine implizite Production Admission. Negative Fixtures bleiben explizite Rejection-Evidenz; M10.3 disponiert beabsichtigte Referenzbeispiele.

## Compilerphasen

| Phase | Prüfung | Ergebnis |
|---|---|---|
| parse | Tokens und Grammatik | AST oder Syntaxfehler |
| resolve | Namen, Imports und Zyklen | Symbolgraph |
| type | Generics, Constraints und Nullbarkeit | typisierte IR |
| effect | Reinheit, Capabilities und Seiteneffekte | Effect Graph |
| policy | Auth, Ownership und Datenklassifikation | Sicherheitsdiagnosen |
| transaction | Isolation, Revisionen und Outbox | Commit-Plan |
| topology | Services, Verträge und verbotene Store-Zugriffe | Runtime-Graph |
| delivery | Topics, Consumer, Ordering und Deduplizierung | Delivery-Plan |
| sync | Autorität, Delta, Tombstones und Konflikte | Sync-Plan |
| ui | Bindings, Zustände, A11y und Tokens | UI-Diagnosen |
| compatibility | API-, Event-, Store- und Client-Evolution | Rollout-Plan |
| deployment | Ressourcen, Regionen, SLO und Kapazität | Deployment-IR |
| emit | Generatorvertrag und Hashes | Artefakte |

## Diagnoseformat

~~~json
{
  "severity": "error",
  "code": "AIDL-DIST411",
  "message": "Consumer 'StartReview' besitzt keinen Idempotenzvertrag.",
  "location": {
    "file": "operations/adoptions.aidl",
    "line": 83,
    "column": 1
  },
  "subject": {
    "kind": "consumer",
    "name": "StartReview"
  },
  "expected": "idempotency clause or proven pure body",
  "allowedFixes": [
    {
      "kind": "insertClause",
      "text": "idempotency: event.eventId retain 30d"
    }
  ],
  "docs": "aidl://diagnostics/AIDL-DIST411"
}
~~~

## Kernfehlercodes

| Code | Bedeutung |
|---|---|
| AIDL-E101 | unbekanntes Schlüsselwort |
| AIDL-E121 | unaufgelöste Referenz |
| AIDL-T140 | ungültige Generic-Instanziierung |
| AIDL-T162 | nicht serialisierbarer öffentlicher Typ |
| AIDL-E203 | fehlende Autorisierung |
| AIDL-E241 | nicht deklarierte Capability |
| AIDL-E260 | nicht deklarierter öffentlicher Fehler |
| AIDL-TX301 | Cross-Owner-Transaktion |
| AIDL-TX312 | unsicherer konkurrierender Write |
| AIDL-TX321 | Event in Transaktion ohne Outbox |
| AIDL-MIG310 | möglicher Datenverlust |
| AIDL-COMP340 | inkompatible Contract-Änderung |
| AIDL-DIST401 | direkter Zugriff auf fremde Entität |
| AIDL-DIST411 | nicht idempotenter Consumer |
| AIDL-DIST421 | Ordering ohne passende Partition |
| AIDL-DIST431 | Projektion ohne Rebuild-Strategie |
| AIDL-DIST432 | Retention reicht nicht für vollständigen Rebuild |
| AIDL-SYNC501 | replizierte Entität ohne Tombstone-Regel |
| AIDL-SYNC511 | mehrdeutige Konfliktstrategie |
| AIDL-SYNC521 | Client-Uhr als autoritativer LWW-Clock |
| AIDL-DEP601 | SLO nicht mit Deployment erfüllbar |
| AIDL-DEP611 | Secret als Literal |
| AIDL-UI204 | fehlender Async-Zustand |
| AIDL-UI231 | unzugängliche Interaktion |
| AIDL-UI252 | freier Designwert |
| AIDL-UI271 | Sync-Konflikt in UI unbehandelt |

Die Tabelle ist Spezifikations-/Dokumentationsmaterial. Ob ein konkreter Code heute erzeugt wird, ergibt sich aus aktuellem Compiler-Code und Tests, nicht allein aus dieser Liste.

## Testarten

Die folgenden AIDL-Blöcke sind illustrative Zielbeispiele; sie sind nicht automatisch parser- oder production-admitted, nur weil sie hier dokumentiert sind.

### Fachlicher Full-Stack-Test

~~~aidl
test "user requests adoption" target fullstack {
  arrange {
    pet = fixture Pet(status: available)
    user = fixture Principal()
  }
  as user visit AdoptionPage(petId: pet.id)
  fill AdoptionForm with fixture AdoptionRequestInput()
  submit AdoptionForm
  assert navigated AdoptionConfirmation
  assert stored AdoptionRequest where applicantId == user.subjectId
  assert emitted AdoptionRequested exactly 1 logical
}
~~~

logical bedeutet ein fachliches Event; physische Zustellungsversuche dürfen
mehrfach auftreten.

### Concurrency-Test

~~~aidl
test "only one concurrent request reserves a pet" target concurrency {
  arrange pet = fixture Pet(status: available)
  parallel {
    a = call requestAdoption(fixture AdoptionRequestInput(
      petId: pet.id,
      expectedPetRevision: pet.revision
    ))
    b = call requestAdoption(fixture AdoptionRequestInput(
      petId: pet.id,
      expectedPetRevision: pet.revision
    ))
  }
  assert exactlyOne [a, b] is success
  assert exactlyOne [a, b] is error in [ConcurrentChange, PetUnavailable]
  assert count AdoptionRequest where petId == pet.id equals 1
}
~~~

### Delivery- und Crash-Test

~~~aidl
test "outbox survives crash after commit" target failure {
  crashpoint afterDatabaseCommit beforeTopicPublish
  call requestAdoption(fixture AdoptionRequestInput())
  restart service PetstoreService
  deliver pending
  duplicate lastDelivery times 2
  assert workflow ReviewAdoption started exactly 1 logical
}
~~~

### Offline- und Konflikttest

~~~aidl
test "offline calendar edits converge" target sync {
  clients [phone, laptop]
  disconnect phone
  on phone edit event.title to "Privat"
  on laptop edit event.attendees add "a@example.test"
  connect phone
  sync all
  assert converged CalendarEvent
  assert event.title == "Privat"
  assert event.attendees contains "a@example.test"
}
~~~

### Kompatibilitäts- und Migrationstest

~~~aidl
test "old client reads expanded schema" target compatibility {
  clientVersion "0.2"
  serverVersion "0.3"
  deploy phase expand
  assert contract backwardCompatible
  run fixture OldClientRequest()
  assert succeeds
}
~~~

## Deterministische Failure-Simulation

simulate kontrolliert:

- Clock und Zufall,
- Message-Duplikate, Verzögerung und Reordering innerhalb erlaubter Grenzen,
- Prozessabstürze an Commit-/Publish-Grenzen,
- Netzwerkpartitionen,
- Store-Failover,
- Offline-Dauer und Sync-Reihenfolge,
- alte Client- und Event-Versionen.

Ein Test darf keine stärkere Garantie annehmen als der deklarierte Vertrag.

## Abschlusskriterium

Für tatsächlich implementierte/zugelassene Oberflächen müssen `check`, `plan`, `compatibility`, `build` und die jeweils repository-eigenen Tests fehlerfrei laufen. Illustrative Zielsyntax erzeugt keine Support-Garantie. Neue Warnungen im unterstützten Pfad sind behoben oder mit einer überprüfbaren Annotation begründet.
