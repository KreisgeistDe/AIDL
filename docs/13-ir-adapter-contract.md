# 13. IR- und Adaptervertrag

## Zweck

Die konkrete DSL-Syntax wird nach Resolve, Type-, Effect-, Policy- und
Topologieprüfung in eine kanonische JSON-IR überführt. Generatoren und
Runtime-/Deployment-Adapter konsumieren ausschließlich diese IR, niemals
untypisierten Quelltext.

spec/ir.schema.json definiert den stabilen Exchange-Envelope. Detailobjekte
dürfen nur über versionierte Profil-Namespaces erweitert werden.

## Kanonische JSON-Serialisierung

M3-02 definiert die Serialisierungsgrenze für bereits semantisch aufgebaute und
schema-konforme IR-Strukturen. Sie erzeugt keine declarationIds/FQNs, keine
Defaults, keinen semanticHash, keinen Plan und keine Source-to-IR-Abbildung.

Der Text-/Byte-Vertrag ist:

- Objekt-Keys werden lexikographisch nach ihren Unicode-Strings sortiert.
- JSON wird kompakt ohne Einrückung und ohne Leerzeichen an `,` oder `:` ausgegeben.
- Nicht-ASCII-Zeichen bleiben als UTF-8 erhalten; es gibt kein BOM.
- Nicht-endliche Zahlen (`NaN`, `Infinity`) sind unzulässig.
- Das Dokument endet mit genau einem LF (`\n`).
- Die Bytes sind exakt die UTF-8-Codierung dieses Textes.

Nur nachweislich mengenartige Core-Collections werden vor der Ausgabe sortiert:
`profiles`, `app.apiIds`, `app.auth.roles`, `app.auth.scopes`, Operation-
`errorIds`, Topic-`eventIds`, Service-`owns`/`uses`/`exposes`/`runs`, Resource-
`transactionIsolation`, `system.topicIds`, `system.apiIds` und
Consumer-Group-`consumerIds`. Ihre Reihenfolge trägt keine Semantik; sortiert
wird nach der rekursiv kanonischen JSON-Darstellung des jeweiligen Elements.

Alle anderen Arrays bleiben positionsstabil. Insbesondere werden
Deklarationen, Felder, API-Operations, Read-/Transaction-/Workflow-Schritte,
Deployments/Regions/Bindings, Source-Map-Einträge und Profile-Extension-Einträge
nicht umgeordnet. Profile-Extensions dürfen keinen numerischen Elementindex
innerhalb einer oben als mengenartig definierten Collection als stabile
Identität behandeln; dafür ist der umgebende stabile Identifier zu verwenden.

Die compiler- und PSI-unabhängige Referenzboundary liegt in
`tools/ir_canonical_json.py`.

## Identität

Jede öffentliche oder generierte Deklaration besitzt:

- eine stabile declarationId aus voll qualifiziertem Namen und Major-Version,
- kind,
- ownerModule,
- optional ownerService,
- sourceSpan,
- semanticHash.

M3-03 definiert dafür eine compiler-/PSI-unabhängige Identitätsboundary in
`tools/ir_identity.py`. Sie konsumiert ausschließlich die bereits aufgelöste
Deklarationsprojektion: `fqn` kommt aus deren bestehendem `fully_qualified_name`,
`name` aus dem Deklarationsheader und `ownerModule` aus dem vorhandenen Modul.
Fehlt einer dieser Werte oder widerspricht das FQN der vorhandenen Modul-/Name-
Projektion, wird die Identität nicht synthetisiert.

`declarationId` ist exakt `<fqn>@<major>`. Der Major ist ein explizit vom
Aufrufer übergebener positiver Integer, weil das Source-Modell noch keine
autoritative Deklarations-Major-Version liefert. Daraus wird insbesondere keine
neue oder implizite AIDL-Sprachversion abgeleitet. Ein geändertes FQN oder ein
geänderter expliziter Major erzeugt eine andere declarationId. Doppelte FQNs
werden weder zusammengeführt noch künstlich disambiguiert und erhalten daher
für denselben Major dieselbe declarationId; die bestehende Symbol-/Diagnostik-
Schicht bleibt für Mehrdeutigkeiten verantwortlich.

Die M3-03-Boundary erzeugt keine Defaults, berechnet keinen semanticHash und
emittiert keine vollständige IR. Umbenennungen ohne evolves-/migration-Angabe
erzeugen eine neue Identität. Formatierung und Kommentare verändern
semanticHash nicht.

## TypeRef

Typen werden nicht als Strings übertragen. TypeRef unterscheidet:

- scalar für die Core-Skalare,
- named mit declarationId und konkreten typeArguments,
- list und set,
- map mit explizitem key- und value-TypeRef,
- nullable,
- ref mit Zielentität und lokalem Owner,
- record mit stabil benannten Feldern.

Alle Generics sind vor Generatorausgabe vollständig gebunden. Ein Adapter sieht
keine offenen Typparameter, außer er deklariert ausdrücklich
openGenericSupport.

## Effects und Garantien

OperationIR enthält:

- Auth-/Allow-/Authorize-Plan,
- öffentliche Fehler,
- Read-/Write-/Publish-/External-Effects,
- Root-Effect,
- Isolation und Concurrency,
- Idempotenz-Scope und Retention,
- Timeout-/Retry-Budget,
- Source Map.

Ein Generator darf keine stärkere Garantie ausgeben als die IR. Insbesondere
darf atLeastOnce nicht als exactlyOnce dokumentiert werden.

## Topologie

SystemIR enthält:

- Services und ihre Entity-Ownership,
- verwendete Ressourcen,
- synchrone Dependencies,
- Event-/Queue-/Channel-Kanten,
- Consumer Groups,
- Projektionen,
- Sync-Surfaces.

Der aufgelöste Graph ist Teil des Build-Manifests. Ein Adapter darf Services
physisch zusammenlegen, aber keine logische Kante oder Policy entfernen.

## Deployment-Adapter

Ein Adapter veröffentlicht ein signiertes Capability Manifest:

~~~json
{
  "adapter": "example.container-platform",
  "version": "3.1.0",
  "supports": {
    "sql.isolation": ["readCommitted", "serializable"],
    "topic.delivery": ["atLeastOnce"],
    "topic.ordering": ["perPartition"],
    "blob.resumable": true,
    "deployment.multiRegion": true
  }
}
~~~

Der Compiler gleicht jede Resource- und Deployment-Anforderung gegen dieses
Manifest ab. Unbekannte oder schwächere Fähigkeiten sind Buildfehler. Ein
Adapter darf nur mit explicitAdapterOverride und begründetem, im Plan sichtbarem
Downgrade abweichen; Sicherheits-, Auth-, Secret- und Datenverlustgarantien sind
nicht überschreibbar.

## Generatorvertrag

Jeder Generator deklariert:

- akzeptierte irVersion und Profile,
- erzeugte Artefaktarten,
- deterministische Eingabeparameter,
- benötigte Adapter-Capabilities,
- eigene Version und Hash,
- unterstützte Evolutionspfade.

Output-Manifest:

~~~json
{
  "irVersion": "0.3.0",
  "semanticHash": "sha256:...",
  "lockHash": "sha256:...",
  "generator": {
    "id": "aidl.reference.typescript",
    "version": "0.3.0"
  },
  "artifacts": [
    {
      "path": "generated/api/openapi.json",
      "sha256": "..."
    }
  ]
}
~~~

## Profilregistry

spec/profile-registry.json ist die maschinenlesbare Liste der Profile,
Deklarationen und verpflichtenden Validatoren. Aktivierte Profilversionen
werden im Lockfile fixiert.

Ein neues Profil benötigt:

1. eindeutige Profil-ID und Major-Version,
2. konkrete Syntax- und IR-Erweiterung,
3. geschlossene Property-Schemas,
4. Diagnosen und allowedFixes,
5. Conformance Tests,
6. mindestens einen lokalen Adapter oder eine explizite contractOnly-Markierung.

## Source Map und Diagnosen

Jeder IR-Knoten verweist auf Quellspanne und ursprüngliche declarationId.
Generatorfehler werden deshalb auf DSL-Quellen zurückgeführt. Pfade in
generierten Dateien sind keine primären Reparaturziele.

## Forward Compatibility

Unbekannte IR-Felder werden nicht still ignoriert. Consumer akzeptieren nur:

- dieselbe IR-Major-Version,
- bekannte Profil-Majors,
- additive Minor-Felder, die ihr Capability Manifest ausdrücklich toleriert.

Andernfalls endet der Build vor irgendeiner Ausgabe.


## M3-04 — Explizite semantische Defaults

`tools/ir_defaults.py` definiert die compiler-/PSI-unabhängige Grenze zwischen
bereits semantisch aufgebauten IR-Strukturen und kanonischer Serialisierung.
Sie materialisiert ausschließlich Core-Defaults, deren Weglassen keine eigene
Semantik trägt:

- `field.primary = false`,
- `field.concurrencyToken = false`,
- `field.onDelete = "none"`,
- `workflow|saga|task.retry = {"kind":"none"}`.

Ein explizit angegebener Default und sein semantisch gleichwertiges Weglassen
ergeben danach dieselbe Struktur und dieselben kanonischen JSON-Bytes. Die
Funktion ist deterministisch, idempotent und verändert ihre Eingabe nicht.
Optionale Werte, bei denen Abwesenheit selbst Bedeutung trägt oder kein
unzweideutiger Core-Default spezifiziert ist (beispielsweise Timeout,
Idempotency, Compensation, Rate-Limit oder Provider-Bindings), bleiben
absichtlich abwesend. Die Grenze erzeugt weder Identitäten noch semanticHash,
vollständige Source-to-IR-Ausgabe, CLI- oder Plan-Verhalten.


## M3-05 — Projektion auf semantische IR

`tools/ir_semantic_projection.py` definiert die compiler-/PSI-unabhängige
Projektion von bereits aufgelösten semantischen Strukturen auf die kanonische
IR. Vor der M3-04-Defaultmaterialisierung entfernt sie ausschließlich die
geschlossene Menge präsentationsbezogener Source-Metadaten `sourceText`,
`rawText`, `tokens`, `comments`, `whitespace`, `punctuation`,
`clauseOrder` und `syntaxForm`.

Andere unbekannte Felder bleiben erhalten, damit das geschlossene IR-Schema sie
weiterhin abweist statt mögliche Semantik still zu verlieren. `sourceMap` ist
der explizite Traceability-Vertrag der IR und bleibt vollständig erhalten;
versionierte `profileExtensions`-Payloads gehören ihrem Profilschema und werden
nicht durchsucht oder verändert. Ebenso bleiben semantische Werte und die
Reihenfolge positionaler Arrays unverändert. Damit ergeben reine
Formatierungs-, Kommentar-, Token- oder Klauselreihenfolgevarianten dieselbe
kanonische IR, während semantisch verschiedene Eingaben unterscheidbar bleiben.
Die Projektion ist deterministisch, idempotent und input-immutable; sie erzeugt
weder semanticHash noch Source-to-IR-, CLI-, Plan- oder M3-06+-Verhalten.


## M3-06 — IR-Version und Consumer-Kompatibilität

Die kanonische IR trägt weiterhin verpflichtend `irVersion: "0.3.0"`; dies ist
eine eigenständige Version des IR-Austauschvertrags und ausdrücklich keine
AIDL-Sprachversion. `tools/ir_version.py` definiert die compiler-/PSI-unabhängige
Consumer-Grenze mit strikt numerischem `major.minor.patch`-Format ohne Präfix,
Suffix oder führende Nullen.

Kompatibilität gilt deterministisch wie folgt:

- Producer und Consumer müssen denselben IR-Major besitzen.
- Ältere Producer-Minors sowie Patch-Unterschiede innerhalb derselben
  Major/Minor-Linie werden akzeptiert.
- Ein neuerer Producer-Minor wird nur akzeptiert, wenn jedes tatsächlich
  verwendete additive Feld als JSON-Pointer sowohl von der Producer-Projektion
  gemeldet als auch im Consumer-Capability-Manifest explizit toleriert wird.
- Jedes verwendete Profil wird unabhängig von der IR-Version als exakte
  `(profileId, major)`-Capability geprüft; unbekannte Profil-Majors werden
  deterministisch abgewiesen.
- Fehlende, falsch formatierte oder Major-inkompatible Versionen sowie ungültige
  Capability-Manifeste beenden die Verarbeitung vor Adapter-Ausgabe.

Die Prüfung verändert das Dokument nicht und implementiert weder semanticHash,
Source-to-IR, CLI, Plan noch M3-07+-Verhalten.


## M3-07 — Deterministischer semanticHash

`tools/ir_semantic_hash.py` füllt die bereits im M3-01-Schema verpflichtenden
`semanticHash`-Felder für das Gesamtdokument und jede Core-Deklaration. Die
Boundary konsumiert die bereits semantisch projizierte M3-05/M3-06-IR, verändert
die Eingabe nicht und verwendet ausschließlich SHA-256 über die von M3-02
definierten kanonischen JSON-Bytes. Der Wert ist immer
`sha256:<64 lowercase hex>`.

Für eine Deklaration besteht die Hash-Preimage aus genau ihrem Core-
Deklarationsobjekt ohne dessen eigenes `semanticHash`. Zur Wiederverwendung der
M3-02-Normalisierung wird dieses Objekt intern als einziges Element unter
`declarations` kanonisiert; der statische Envelope wird nicht ausgegeben.
Dadurch bleiben insbesondere mengenartige `errorIds`/`eventIds` unabhängig von
ihrer Eingabereihenfolge, während positionssemantische Arrays unterscheidbar
bleiben.

Die Dokument-Preimage enthält die vollständige kanonische IR einschließlich
`irVersion`, aktiver Profile, App/System/Deployments, Deklarationen und
`profileExtensions`, jedoch ohne das Root-`semanticHash`, ohne die
Deklarations-`semanticHash`-Felder und ohne `sourceMap`. Die Hashfelder werden
ausgeschlossen, um Selbstreferenz zu vermeiden. `sourceMap` bleibt unverändert
im ausgegebenen Dokument erhalten, ist aber Traceability statt Semantik; reine
Datei-/Zeilen-/Spaltenänderungen dürfen den Fingerprint daher nicht ändern.
Profil-Extension-Werte bleiben dagegen Teil des Dokument-Fingerprints.

M3-07 erzeugt keine Source-to-IR-Pipeline und implementiert weder CLI, Plan noch
M3-08+-Verhalten.
