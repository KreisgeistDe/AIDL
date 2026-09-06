# 8. Offline- und Multi-Writer-Synchronisation

## Betriebsmodelle

| Modell | Client darf offline schreiben | Finale Autorität |
|---|---|---|
| serverAuthoritative | nein | Server |
| queuedCommands | Operationen ja, bestätigter State nein | Server |
| replicated | ja | deklarierter Merge plus Servervalidierung |

Das Modell wird pro Aggregate oder Sync-Scope gewählt, nicht global für die
gesamte Anwendung.

## Replizierbare Entität

~~~dsl
entity CalendarEvent {
  id: uuid primary clientGenerated immutable
  revision: revision generated concurrencyToken
  ownerId: SubjectId required immutable
  title: string(1..200) required mutable
  description: string(0..4000) default "" mutable
  startsAt: datetime required mutable
  endsAt: datetime required mutable
  attendees: set<email> default [] mutable
  deletedAt: datetime? generated mutable

  invariant validRange: endsAt > startsAt
}
~~~

Offline erstellbare Entitäten benötigen global eindeutige clientGenerated IDs.
revision wird ausschließlich vom bestätigenden Server beziehungsweise
Konvergenzlog vergeben.

## Sync-Vertrag

~~~dsl
sync CalendarEventSync for CalendarEvent {
  mode replicated
  authority serverValidated
  scope: entity.ownerId == principal.subjectId
  localStore CalendarLocal
  serverStore CalendarDb

  operationLog {
    id operationId
    baseRevision baseRevision
    ordering causal
    retain confirmed 7d
  }

  push batch max 100 retry exponential(maxDelay: 5m)
  pull cursor serverRevision page 500
  changes to CalendarChanges via outbox
  delete tombstone retain 180d

  conflict {
    field title merge lww(clock: serverHlc)
    field description merge lww(clock: serverHlc)
    field attendees merge addWinsSet
    group schedule fields [startsAt, endsAt] merge manual
  }

  rejected retainLocal mark rejected
  schemaMigration required
}
~~~

## Operationslog

Jede lokale Operation enthält:

- operationId,
- deviceId und Actor/Subject,
- Entity-ID,
- Baserevision oder Kausalitätskontext,
- typisierten Patch beziehungsweise Command,
- lokale Reihenfolge,
- Client-Schema-Version,
- optional referenzierte Blob-Uploads.

Der Server dedupliziert operationId innerhalb des deklarierten Scopes. Eine
bestätigte Operation erhält eine Serverrevision und einen kanonischen State.

serverStore ist die atomare Commit-Grenze. changes to ... via outbox verlangt,
dass bestätigter State, neue Revision, Deduplizierungsstatus und Change-Feed-
Eintrag gemeinsam committen. Der Pull-Stream bleibt at-least-once; Cursor und
Entity-ID deduplizieren die lokale Anwendung.

## Uhren und Kausalität

Geräteuhren dürfen niemals allein konfliktentscheidend sein. Zulässige Clocks:

- serverSequence,
- serverHlc als vom Server normalisierte Hybrid Logical Clock,
- vector für begrenzte Replikagruppen.

deviceTime darf als Nutzerinformation gespeichert werden, ist aber keine
autoritative LWW-Uhr.

## Konfliktstrategien

| Strategie | Zulässige Daten |
|---|---|
| reject | sicherheitskritische oder nicht mergefähige Änderung |
| serverWins | serverautoritatives Feld |
| lww(serverSequence/serverHlc) | unabhängiges Register |
| max/min | monotone Zahlen oder Zeiten |
| addWinsSet/removeWinsSet | Mengen mit definierter Löschsemantik |
| counter | kommutativer Zähler |
| manual | fachliche Entscheidung durch Nutzer |
| custom deterministic | geprüfte reine Merge-Funktion |

Zusammenhängende Invarianten werden als conflict group atomar gemergt. Im
Kalender dürfen startsAt und endsAt nicht unabhängig per LWW zusammengeführt
werden, weil sonst ein ungültiges Intervall entstehen kann.

Custom Merge:

~~~dsl
native function calendar.mergeRecurrence {
  input: MergeInput<RecurrenceRule>
  output: MergeDecision<RecurrenceRule>
  effects: []
  deterministic: true
  capabilities: []
}
~~~

Nichtdeterministische oder I/O-ausführende Merge-Funktionen sind verboten.

## Tombstones und Löschung

Ein physisches Löschen vor Ablauf der Tombstone-Retention kann gelöschte
Objekte durch alte Clients wiederbeleben. Die Retention muss mindestens
maxOfflineDuration plus maximale Sync-Verzögerung abdecken.

Nach Ablauf benötigt jeder Client entweder:

- einen Full-Resync,
- einen Server-Snapshot nach der Lösch-Watermark,
- oder eine verifizierte minimale Revision.

## Autorisierung

Offline angenommene Änderungen sind vorläufig. Beim Push prüft der Server
aktuelle Identität, Berechtigung, Tenant, Quota und Invarianten erneut.

Entzogene Berechtigungen führen zu rejected, niemals zu stiller Annahme.
Sensitive lokale Daten verlangen Encryption-at-rest und deklarierte Löschung
bei Sign-out oder Device-Revocation.

## Abgelehnte Operationen

rejected besitzt:

- stabilen Fehlercode,
- kanonischen Serverzustand,
- betroffene lokale Operation,
- mögliche Aktionen discard, editAndRetry oder requestAccess.

Die UI muss jeden im Sync-Vertrag möglichen Ausgang behandeln. Automatisches
Verwerfen lokaler Nutzerdaten ist verboten.

## Anhänge und Medien

Operationen referenzieren lokale Blob-Tickets, nicht rohe Bytes. Upload erfolgt
resumierbar vor oder parallel zum State-Push. Eine Operation wird erst
bestätigt, wenn alle required Blob-Tickets serverseitig gebunden sind.

Verwaiste Uploads besitzen eine TTL und Cleanup-Policy.

## Lokale Schemamigration

Jede Änderung an replizierten Typen klassifiziert:

- serverBackwardCompatible,
- oldClientReadable,
- operationUpcastRequired,
- fullResyncRequired.

Ein alter Client darf keine Operation hochladen, deren Bedeutung der Server
nicht mehr eindeutig interpretieren kann.

## Peer-to-Peer-Grenze

Die Kernfunktion unterstützt Server-koordinierte Multi-Writer-Replikation.
Beliebige serverlose Peer-to-Peer-Topologien, Byzantine Fault Tolerance und
anwendungsspezifische Konsensusprotokolle sind keine Kernfunktion und benötigen
ein versioniertes Profil oder native Integration.
