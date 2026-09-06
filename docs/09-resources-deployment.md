# 9. Ressourcen und Deployment

## Portable Ressourcen

Ressourcen beschreiben benötigte Semantik. Ein Deployment-Adapter bindet sie an
lokale oder verwaltete Produkte.

### SQL

~~~dsl
resource PetstoreDb sql {
  consistency strong
  transactions [readCommitted, repeatableRead, serializable]
  migrations expandBackfillContract
  backup rpo 15m rto 1h
  encryption required
}
~~~

### Blob und CDN

~~~dsl
resource VideoObjects blob<VideoObject> {
  upload resumable multipart
  maxObjectSize 20GB
  checksum sha256
  versioning enabled
  encryption required
  lifecycle {
    incompleteUploads expire 24h
    originals transition archive after 365d
  }
}

resource VideoDelivery cdn {
  origin VideoObjects
  access signed
  cache immutableByHash
  purge bySurrogateKey
}
~~~

### Cache, Queue, Stream und Suche

~~~dsl
resource CatalogCache cache {
  consistency cacheAside
  maxEntry 1MB
  encryption required
}

resource WatchEvents stream<WatchEvent> {
  partition by videoId
  retention 7d
  replay enabled
}

resource VideoSearch search<VideoSearchDocument> {
  consistency eventual
  rebuild from VideoEvents
}
~~~

Ressourcentypen:

- sql, document, keyValue und timeSeries,
- blob und cdn,
- cache,
- queue, topic und stream,
- search,
- counter,
- secretRef und configRef,
- localStore.

Mehrere Stores sind erlaubt. Eine Operation nennt jeden verwendeten Store
explizit; eine lokale transaction darf genau einen transaktionalen Owner
umfassen.

## Medienprofil

BlobHandle<S> ist ein opaker, serialisierbarer Verweis mit Store-ID,
Objektschlüssel, Version, Hash, Größe und Media Type. Er enthält niemals
Provider-Credentials.

~~~dsl
media VideoObject {
  types ["video/mp4", "video/webm", "video/quicktime"]
  maxSize 20GB
  inspect antivirus required
  metadata [duration, width, height, codec]
}

rendition Hd1080 from VideoObject {
  container "mp4"
  videoCodec "h264"
  maxResolution 1920x1080
  audioCodec "aac"
}
~~~

UploadSession<S>, BlobHandle<S> und RenditionSet<S> sind Standardtypen.

## Deployment-Profil

~~~dsl
deployment production for PetstoreSystem {
  environment production
  target containers
  region primary "eu-central"
  dataResidency ["EU"]

  service PetstoreService {
    replicas 2..20
    availability zones minimum 2
    autoscale cpu target 65%
    resources cpu 500mCPU..2cores, memory 512MB..2GB
    health {
      readiness "/health/ready"
      liveness "/health/live"
    }
    rollout rolling(maxUnavailable: 0, maxSurge: 1)
    shutdown grace 30s
  }

  bind PetstoreDb from secret("DATABASE_URL")
  bind AdoptionEvents managed

  observability {
    telemetry otel
    traces sample 10%
    sensitiveFields redact
  }

  slo apiAvailability 99.9% window 30d
  slo apiLatency p95 < 300ms window 30d
}
~~~

Replicas geben einen Bereich an. Der Adapter muss nachweisen, dass Health,
Autoscaling und Rollout die Untergrenze nicht verletzen.

## Lokale und produktive Topologien

~~~dsl
deployment local for VideoHubSystem {
  environment development
  target process
  colocate services all
  bind MetadataDb container "postgres:17"
  bind VideoObjects filesystem "./.local/blobs"
  bind VideoEvents memory
}
~~~

colocate ändert nur die physische Platzierung. Serviceidentitäten,
Ownership-Grenzen und Verträge bleiben wirksam, damit lokales Verhalten die
Produktion nicht semantisch verfälscht.

## Regionen und Failover

~~~dsl
deployment global for VideoHubSystem {
  regions ["eu-central", "us-east", "ap-southeast"]
  routing latencyAware
  service CatalogService activeActive
  resource MetadataDb primary "eu-central" replicas readOnly
  failover {
    rpo 5m
    rto 30m
    promote manual
  }
}
~~~

activeActive ist nur zulässig, wenn alle Writes des Services eine kompatible
Concurrency-/Replikationssemantik besitzen. Der Compiler darf aus mehreren
Replicas keine Multi-Region-Write-Sicherheit ableiten.

## Serverless und Worker

target functions erfordert:

- keine lokale persistente Session,
- endliche Laufzeit innerhalb des Provider-unabhängigen Budgets,
- idempotente Event-Verarbeitung,
- deklarierte Cold-Start- und Concurrency-Grenzen.

Langlebige Workflows werden nicht im Funktionsprozess gehalten, sondern von
einem Durable-Workflow-Adapter persistiert.

## Secrets und Konfiguration

Secret-Werte sind niemals DSL-Literale. secret("NAME") ist eine Referenz.
Compiler und Generatoren dürfen Secrets weder in Plan, Logs, Client-Bundles
noch Manifest-Hashes aufnehmen.

Config ist typisiert und kann öffentliche nicht-sensitive Werte enthalten.
Änderungen deklarieren restart, reload oder immutable.

config("NAME") und secret("NAME") sind ausschließlich Referenzen. Ein OIDC-
Issuer ist gewöhnlich config; Client-Secrets, Datenbankpasswörter und
Signaturschlüssel sind secret.

## Observability

Jede Request-, Workflow-, Operation- und Message-ID wird als Correlation
Context propagiert. Telemetrie deklariert:

- Logs, Metrics und Traces,
- Sampling,
- PII-/Secret-Redaction,
- Retention,
- SLO-basierte Alerts,
- Kostenbudget.

## Provider-Bindings

Provider-Adapter besitzen eigene Versionen und Capability-Matrizen. Ein Build
scheitert, wenn ein Adapter Isolation, Retention, Ordering, Region oder
Backupvertrag nicht erfüllen kann. Silent Downgrade ist verboten.
