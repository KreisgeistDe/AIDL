# VideoHub

> **M10.2 Support-Tier:** Die committed `.aidl`-Dateien dieses Referenzbeispiels sind bis zur M10.3-Migration als `legacy-readable-compatibility` klassifiziert. Die dargestellte Architektur ist keine pauschale Aussage, dass jede verwendete Deklaration oder Schreibweise bereits kanonisch oder produktiv zugelassen ist. Die maschinenlesbare Klassifikation steht in `spec/m10-2-language-surface-classification.json`; M10.3 migriert bzw. disponiert die beabsichtigte Referenzoberfläche.

VideoHub ist ein Architektur- und Konformitätsbeispiel für eine
YouTube-ähnliche Anwendung. Es demonstriert:

- getrennte Catalog-, Media-, Comment- und Search-Services,
- strikt getrennten Datenbesitz ohne serviceübergreifende ref-Felder,
- resumierbare Upload-Sitzungen und opake BlobHandles,
- Event/Outbox-getriebene Transcoding-Workflows,
- Worker-Queue und idempotente Verarbeitung,
- Renditions und CDN-Auslieferung,
- eventual konsistente Suchprojektion,
- Realtime-Kommentare mit Query-Fallback,
- View-Counter und Watch-Analytics-Stream,
- lokale und globale Deployments.

Der Transcoding-Algorithmus ist native, seine Eingaben, Ausgaben, Effects,
Capabilities, Ressourcen und Fehler bleiben jedoch Teil des AIDL-Vertrags.

VideoHub ist keine Behauptung, dass AIDL einen globalen Videodienst bereits
implementiert. Es zeigt, dass die architekturtragende Semantik erstklassig
darstellbar ist.
