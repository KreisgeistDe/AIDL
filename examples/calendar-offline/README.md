# Offline-Kalender

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

