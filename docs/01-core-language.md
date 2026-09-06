# 1. Kernsprache

## Projekt, Module und Profile

~~~aidl
module petstore.domain.pets

import aidl.std.Page
import petstore.common.Money

export entity Pet { ... }
~~~

- Dateien enden auf .aidl und verwenden UTF-8.
- Dateinamen sind lowercase-kebab-case.
- Typen und Komponenten sind PascalCase; Operationen und Felder camelCase.
- Importe verwenden Projekt-Namespaces, niemals relative Dateipfade.
- Zyklische Modulabhängigkeiten sind ungültig.
- Import ist eine Compile-Zeit-Abhängigkeit und niemals implizit ein Remote-Call.
- generated/ darf von Coding-Agenten nicht geändert werden.

Ein Projekt aktiviert Profile im app-Block. Jede Profilversion wird im Lockfile
fixiert.

~~~aidl
app Petstore {
  profile core version 1
  profile web version 1
  profile distributed version 1
  profile cloud version 1
  system PetstoreSystem
  frontend PetstoreWeb
}
~~~

## Skalare Typen

| Typ | Bedeutung |
|---|---|
| string | Unicode-Text mit optionalen Längen-/Pattern-Constraints |
| int | vorzeichenbehaftete 64-Bit-Ganzzahl |
| decimal | exakte Dezimalzahl |
| bool | Wahrheitswert |
| uuid | UUID |
| date | ISO-Kalenderdatum |
| datetime | UTC-Zeitpunkt |
| duration | Dauer |
| revision | monotoner, opaker Concurrency-Token |
| email, url | semantisch validierte Zeichenfolge |
| bytes | kleine Inline-Binärdaten; nicht für große Dateien |
| json<S> | JSON entsprechend dem serialisierbaren Schema S |

Große Dateien verwenden BlobHandle\<S> aus dem media-Profil. T? ist nullable,
[T] eine geordnete Liste, set<T> eine eindeutige ungeordnete Menge und
map<K,V> eine Map mit scalar- oder value-Schlüssel.

Implizite Typkonvertierungen sind verboten, außer verlustfreiem int nach
decimal. Nullbarkeit, Abwesenheit und leere Collection sind verschiedene Werte.

## Generics

Generische Parameter sind für value, union, view, component und native function
zulässig. Persistierte entity- und error-Deklarationen dürfen nicht
generisch sein.

~~~aidl
export value Slice<T: serializable> {
  items: [T]
  nextCursor: Cursor?
}

export union Outcome<T: serializable, E: ErrorValue> {
  success(value: T)
  failure(error: E)
}
~~~

Erlaubte Bounds sind serializable, scalar, value, entityView, ErrorValue,
comparable und hashable. Mehrere Bounds werden mit & verbunden.

Generics sind:

- invariant,
- vollständig zur Compile-Zeit aufgelöst,
- ohne Runtime-Reflection,
- ohne Higher-Kinded, Conditional oder Mapped Types,
- für Schemaausgabe stabil benannt und monomorphisiert.

Der Compiler meldet unbenutzte Typparameter, rekursive Expansion ohne Grenze
und nicht serialisierbare öffentliche Instanziierungen als Fehler.

## Enums, Value Objects und Aliase

~~~aidl
enum PetStatus { available, pending, adopted }

value Money {
  amount: decimal(precision: 12, scale: 2, min: 0)
  currency: enum("EUR", "USD", "CHF")
}

alias PetId = uuid
opaque SubjectReference = string(1..200)
~~~

alias erzeugt keinen neuen Typ. opaque erzeugt einen nominal verschiedenen Typ
mit expliziten Konvertierungen an einer Adaptergrenze.

## Diskriminierte Unions

~~~aidl
union UploadState {
  pending(uploadId: uuid)
  processing(progress: decimal(min: 0, max: 1))
  ready(asset: BlobHandle<VideoObject>)
  failed(errorCode: string)
}
~~~

Jede Variante besitzt einen stabilen Tag. Öffentliche Unions deklarieren ihre
Wire-Repräsentation über die Standardbibliothek; Default ist
{ kind: "<variant>", ...fields }.

## Fehlerverträge

~~~aidl
error PetUnavailable {
  code "PET_UNAVAILABLE"
  httpStatus 409
  retry never
  safeMessage "Das Tier ist nicht mehr verfügbar."
}
~~~

Fehler sind nominale, serialisierbare Verträge. Sie deklarieren:

- einen innerhalb der Anwendung eindeutigen stabilen Code,
- Transportabbildung,
- Retry-Klasse never, immediate, backoff oder after,
- ausschließlich öffentlich erlaubte Felder,
- eine sichere Standardnachricht oder einen Lokalisierungsschlüssel.

Unbekannte interne Fehler werden an öffentlichen Grenzen in InternalFailure
überführt. Stacktraces, Secrets und nicht klassifizierte Felder dürfen eine
Servicegrenze nicht passieren.

## Entitäten

~~~aidl
entity Pet {
  id: uuid primary generated immutable
  revision: revision generated concurrencyToken
  name: string(1..80) required mutable
  status: PetStatus default available mutable
  shelter: ref Shelter required immutable onDelete restrict
  createdAt: datetime generated immutable

  index byStatus(status, createdAt desc)
  invariant adoptedTimestamp:
    status != adopted or adoptedAt != null
}
~~~

Regeln:

- Jede Entität besitzt genau einen primary-Schlüssel.
- Änderbare Entitäten mit konkurrierenden Schreibern SOLLEN einen
  concurrencyToken besitzen.
- generated-, primary- und immutable-Felder fehlen in automatisch erzeugten
  Patch-Typen.
- ref ist nur zwischen Entitäten desselben Service-Owners zulässig.
- Serviceübergreifend werden nominale IDs, Snapshots oder API-Verträge genutzt.
- Invarianten werden bei jedem Commit innerhalb der lokalen Transaktion geprüft.
- Ein Service darf nur eigene Entitäten direkt lesen oder schreiben.

## Views

~~~aidl
view PetSummary from Pet {
  id
  revision
  name
  status
  shelter { id, name, city }
}
~~~

Views sind unveränderliche, serialisierbare Projektionen. Eine View darf nur
lokal navigierbare ref-Beziehungen verwenden. Serviceübergreifende Read Models
werden als projection deklariert.

Generische Views dürfen ausschließlich andere Views oder Values komponieren:

~~~aidl
view Selection<T: entityView> {
  item: T
  selected: bool
}
~~~

## Feldpräsenz und Mutabilität

- required bedeutet: Beim Erzeugen muss ein Wert vorhanden sein.
- T? bedeutet: Der gespeicherte oder übertragene Wert darf null sein.
- immutable bedeutet: Nach Erzeugung unveränderlich.
- mutable bedeutet: Durch explizit erlaubte Mutationen änderbar.
- sensitive markiert personenbezogene oder geheime Daten und erzwingt
  Redaction-, Audit- und Storage-Regeln.
- generated bedeutet: Runtime oder Store weist den Wert zu.

## Ausdrücke und Effects

Ausdrücke sind rein. Seiteneffekte existieren nur in deklarierten
Effect-Kontexten:

| Effect | Erlaubter Kontext |
|---|---|
| read | query, policy, mutation, workflow step, consumer |
| write | mutation, consumer über Mutation, workflow über Mutation |
| publish | lokale Transaktion via Outbox oder expliziter Consumer |
| external | native function mit Capability |
| clock | Operation mit nondeterministic clock-Effect |
| random | Operation mit nondeterministic random-Effect |

now() und uuid() sind keine versteckten reinen Funktionen. Compiler injiziert
Clock beziehungsweise RandomSource und zeichnet deren Werte für deterministische
Tests auf.

## Eindeutigkeitsregeln

- keine Überladung,
- keine benutzerdefinierten Operatoren,
- keine impliziten Semikolons,
- keine ungebundenen dynamic- oder any-Typen,
- keine unsichtbaren Netzwerk- oder Datenbankzugriffe,
- jede Deklaration hat genau einen kanonischen Definitionsort,
- jede öffentliche Deklaration besitzt eine stabile vollständig qualifizierte ID.
