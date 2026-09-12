# Offline-Kalender

> **M10.2 Support-Tier:** Die committed `.aidl`-Dateien dieses Referenzbeispiels sind bis zur M10.3-Migration als `legacy-readable-compatibility` klassifiziert. Parser-Lesbarkeit und die beschriebene Produktgeschichte sind keine pauschale Aussage, dass jede verwendete Deklaration oder Schreibweise bereits kanonisch oder produktiv zugelassen ist. Die maschinenlesbare Klassifikation steht in `spec/m10-2-language-surface-classification.json`; M10.3 entscheidet die ausführbare Migration bzw. explizite Nicht-Produktions-Disposition.

Dieses Beispiel prüft Server-koordinierte Multi-Writer-Synchronisation:

- Events können mit clientgenerierter ID offline entstehen.
- Änderungen werden als typisierte Operationen protokolliert.
- Titel und Beschreibung verwenden servernormalisierte LWW-Metadaten.
- Teilnehmer verwenden ein Add-wins-Set.
- Start und Ende werden als atomare Konfliktgruppe manuell aufgelöst.
- Löschungen bleiben als Tombstone erhalten.
- aktuelle Serverberechtigungen werden bei jedem Push erneut geprüft.

Das Beispiel behauptet kein beliebiges Peer-to-Peer-CRDT. Der Server validiert
Invarianten und vergibt die kanonische Revision.

