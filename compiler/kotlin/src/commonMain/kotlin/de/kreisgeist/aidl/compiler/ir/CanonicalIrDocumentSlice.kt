package de.kreisgeist.aidl.compiler.ir

private const val IR_VERSION = "0.3.0"
private const val ZERO_HASH = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

class CanonicalIrDocumentSliceException(message: String) : IllegalArgumentException(message)

class CanonicalIrDocumentSlice internal constructor(
    internal val document: Map<String, Any?>,
) {
    fun canonicalJson(): String = deterministicJson(document)
    fun structuralJson(): String = deterministicJson(stripSemanticHashes(document))
}

/**
 * Bounded M10.5-04 full-document projector for the already-integrated enum/value/entity corpus.
 *
 * The envelope grammar is intentionally closed to the shared one-app/one-service/one-system/
 * one-deployment parity fixture. This is not a second general AIDL parser: the real bounded domain
 * declarations still flow through [CanonicalIrDomainSliceProjector], while any envelope shape not
 * explicitly owned by this slice is rejected as a whole. Semantic hash calculation stays outside
 * this migration package; zero hashes are schema-valid placeholders only.
 */
object CanonicalIrDocumentSliceProjector {
    private val envelopePattern = Regex(
        """(?ms)\A\s*module\s+([A-Za-z_][A-Za-z0-9_.]*)\s+
            |import\s+([A-Za-z_][A-Za-z0-9_.]*)\.\*\s+
            |app\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*
            |profile\s+([a-z][a-z0-9-]*)\s+version\s+([1-9][0-9]*)\s*
            |system\s+([A-Za-z_][A-Za-z0-9_]*)\s*
            |defaultDeployment\s+([A-Za-z_][A-Za-z0-9_]*)\s*\}\s*
            |auth\s*\{\s*
            |provider\s+([A-Za-z_][A-Za-z0-9_-]*)\s*
            |subject\s+claim\s+"([^"]+)"\s*
            |roles\s+\[([^\]]*)]\s*
            |scopes\s+\[([^\]]*)]\s*
            |serviceIdentities\s+(required|optional)\s*\}\s*
            |export\s+service\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*
            |owns\s+\[([^\]]*)]\s*
            |uses\s+\[\s*]\s*
            |exposes\s+\[\s*]\s*
            |runs\s+\[\s*]\s*\}\s*
            |export\s+system\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*
            |services\s+\[([^\]]*)]\s*
            |resources\s+\[\s*]\s*
            |apis\s+\[\s*]\s*\}\s*
            |export\s+deployment\s+([A-Za-z_][A-Za-z0-9_]*)\s+for\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*
            |environment\s+([A-Za-z_][A-Za-z0-9_-]*)\s*
            |target\s+([A-Za-z_][A-Za-z0-9_-]*)\s*
            |colocate\s+services\s+all\s*\}\s*\z""".trimMargin(),
    )

    fun project(
        domainSourceId: String,
        domainPath: String,
        domainSource: String,
        envelopeSourceId: String,
        envelopePath: String,
        envelopeSource: String,
    ): CanonicalIrDocumentSlice {
        val domain = CanonicalIrDomainSliceProjector.project(domainSourceId, domainPath, domainSource)
        val domainModule = domain.declarations.firstOrNull()?.ownerModule
            ?: throw CanonicalIrDocumentSliceException("bounded Canonical IR document requires domain declarations")
        val match = envelopePattern.matchEntire(envelopeSource)
            ?: throw CanonicalIrDocumentSliceException("unsupported Canonical IR envelope shape")
        val g = match.groupValues
        val module = g[1]
        val importedModule = g[2]
        val appName = g[3]
        val profileId = g[4]
        val profileMajor = g[5].toInt()
        val appSystem = g[6]
        val defaultDeployment = g[7]
        val provider = g[8]
        val subjectClaim = g[9]
        val roles = commaList(g[10])
        val scopes = commaList(g[11])
        val serviceIdentities = g[12]
        val serviceName = g[13]
        val ownedEntityRefs = commaList(g[14])
        val systemName = g[15]
        val systemServices = commaList(g[16])
        val deploymentName = g[17]
        val deploymentSystem = g[18]
        val environment = g[19]
        val target = g[20]

        if (importedModule != domainModule) {
            throw CanonicalIrDocumentSliceException("envelope import does not match bounded domain module")
        }
        if (appSystem != systemName || defaultDeployment != deploymentName || deploymentSystem != systemName) {
            throw CanonicalIrDocumentSliceException("envelope app/system/deployment references are inconsistent")
        }
        if (systemServices != listOf(serviceName)) {
            throw CanonicalIrDocumentSliceException("bounded system must contain exactly its projected service")
        }

        val entities = domain.declarations.filter { it.kind == "entity" }.associateBy { it.fqn }
        val ownedEntityIds = ownedEntityRefs.map { ref ->
            entities[ref]?.declarationId
                ?: throw CanonicalIrDocumentSliceException("unresolved bounded owned entity '$ref'")
        }

        val appId = identity(module, appName)
        val service = identity(module, serviceName) + mapOf(
            "owns" to ownedEntityIds,
            "uses" to emptyList<String>(),
            "exposes" to emptyList<String>(),
            "runs" to emptyList<String>(),
        )
        val app = appId + mapOf(
            "systemId" to declarationId(module, systemName),
            "apiIds" to emptyList<String>(),
            "defaultDeploymentId" to declarationId(module, deploymentName),
            "auth" to mapOf(
                "provider" to provider,
                "subjectClaim" to subjectClaim,
                "roles" to roles,
                "scopes" to scopes,
                "serviceIdentities" to serviceIdentities,
            ),
        )
        val system = identity(module, systemName) + mapOf(
            "services" to listOf(service),
            "resources" to emptyList<Any?>(),
            "topicIds" to emptyList<String>(),
            "apiIds" to emptyList<String>(),
            "edges" to emptyList<Any?>(),
            "consumerGroups" to emptyList<Any?>(),
        )
        val deployment = identity(module, deploymentName) + mapOf(
            "environment" to environment,
            "regions" to emptyList<String>(),
            "serviceBindings" to listOf(
                mapOf("serviceId" to declarationId(module, serviceName), "adapter" to target),
            ),
            "resourceBindings" to emptyList<Any?>(),
        )

        val sourceEntries = mutableListOf<Map<String, Any?>>()
        sourceEntries += envelopeEntry(
            "/app",
            declarationId(module, appName),
            envelopePath,
            envelopeSource,
            "app $appName",
            "app $appName",
        )
        sourceEntries += domain.sourceEntries.map(::sourceEntryMap)
        sourceEntries += envelopeEntry(
            "/system",
            declarationId(module, systemName),
            envelopePath,
            envelopeSource,
            "export system $systemName",
            "system $systemName",
        )
        sourceEntries += envelopeEntry(
            "/system/services/0",
            declarationId(module, serviceName),
            envelopePath,
            envelopeSource,
            "export service $serviceName",
            "service $serviceName",
        )
        sourceEntries += envelopeEntry(
            "/deployments/0",
            declarationId(module, deploymentName),
            envelopePath,
            envelopeSource,
            "export deployment $deploymentName",
            "deployment $deploymentName",
        )

        return CanonicalIrDocumentSlice(
            linkedMapOf(
                "irVersion" to IR_VERSION,
                "semanticHash" to ZERO_HASH,
                "profiles" to listOf(mapOf("id" to profileId, "major" to profileMajor)),
                "app" to app,
                "declarations" to domain.declarations.map(::declarationMap),
                "system" to system,
                "deployments" to listOf(deployment),
                "sourceMap" to mapOf("entries" to sourceEntries),
                "profileExtensions" to emptyMap<String, Any?>(),
            ),
        )
    }

    private fun commaList(raw: String): List<String> = raw.trim().let { value ->
        if (value.isEmpty()) emptyList() else value.split(',').map(String::trim)
    }

    private fun declarationMap(value: CanonicalIrDomainDeclaration): Map<String, Any?> {
        val result = linkedMapOf<String, Any?>(
            "kind" to value.kind,
            "declarationId" to value.declarationId,
            "fqn" to value.fqn,
            "name" to value.name,
            "ownerModule" to value.ownerModule,
            "semanticHash" to ZERO_HASH,
        )
        when (value.kind) {
            "enum" -> result["values"] = value.values
            "value" -> result["fields"] = value.fields.map(::fieldMap)
            "entity" -> {
                result["fields"] = value.fields.map(::fieldMap)
                result["identityFields"] = value.identityFields
            }
        }
        return result
    }

    private fun fieldMap(value: CanonicalIrField): Map<String, Any?> = linkedMapOf(
        "name" to value.name,
        "type" to typeMap(value.type),
        "required" to value.required,
        "mutable" to value.mutable,
        "sensitive" to value.sensitive,
        "generated" to value.generated,
        "primary" to value.primary,
        "concurrencyToken" to value.concurrencyToken,
        "onDelete" to value.onDelete,
    )

    private fun typeMap(value: CanonicalIrTypeRef): Map<String, Any?> = when (value) {
        is CanonicalIrScalarType -> mapOf("kind" to "scalar", "name" to value.name)
        is CanonicalIrNamedType -> mapOf(
            "kind" to "named",
            "declarationId" to value.declarationId,
            "fqn" to value.fqn,
            "typeArguments" to value.typeArguments.map(::typeMap),
        )
        is CanonicalIrListType -> mapOf("kind" to "list", "element" to typeMap(value.element))
        is CanonicalIrNullableType -> mapOf("kind" to "nullable", "element" to typeMap(value.element))
    }

    private fun sourceEntryMap(value: CanonicalIrSourceEntry): Map<String, Any?> = mapOf(
        "nodePath" to value.nodePath,
        "originalDeclarationId" to value.originalDeclarationId,
        "span" to mapOf(
            "file" to value.span.file,
            "startLine" to value.span.startLine,
            "startColumn" to value.span.startColumn,
            "endLine" to value.span.endLine,
            "endColumn" to value.span.endColumn,
        ),
    )

    private fun envelopeEntry(
        nodePath: String,
        declarationId: String,
        path: String,
        source: String,
        searchHeader: String,
        spanHeader: String,
    ): Map<String, Any?> {
        val searchOffset = source.indexOf(searchHeader)
        val headerOffset = searchOffset + searchHeader.indexOf(spanHeader)
        val closeOffset = source.indexOf('}', searchOffset) + 1
        val start = position(source, headerOffset)
        val end = position(source, closeOffset)
        return mapOf(
            "nodePath" to nodePath,
            "originalDeclarationId" to declarationId,
            "span" to mapOf(
                "file" to path,
                "startLine" to start.first,
                "startColumn" to start.second,
                "endLine" to end.first,
                "endColumn" to end.second,
            ),
        )
    }

    private fun position(source: String, offset: Int): Pair<Int, Int> {
        val before = source.substring(0, offset)
        val line = before.count { it == '\n' } + 1
        val column = offset - before.lastIndexOf('\n')
        return line to column
    }

    private fun identity(module: String, name: String): Map<String, Any?> = linkedMapOf(
        "declarationId" to declarationId(module, name),
        "fqn" to "$module.$name",
        "name" to name,
        "ownerModule" to module,
        "semanticHash" to ZERO_HASH,
    )

    private fun declarationId(module: String, name: String): String = "$module.$name@1"
}

private fun stripSemanticHashes(value: Any?): Any? = when (value) {
    is Map<*, *> -> value.entries
        .filter { it.key != "semanticHash" }
        .associate { it.key as String to stripSemanticHashes(it.value) }
    is List<*> -> value.map(::stripSemanticHashes)
    else -> value
}

private fun deterministicJson(value: Any?): String = when (value) {
    null -> "null"
    is String -> quoteJson(value)
    is Boolean, is Int, is Long, is Double, is Float -> value.toString()
    is List<*> -> value.joinToString(prefix = "[", postfix = "]", separator = ",") { deterministicJson(it) }
    is Map<*, *> -> value.entries
        .map { (key, item) -> key as String to item }
        .sortedBy { it.first }
        .joinToString(prefix = "{", postfix = "}", separator = ",") { (key, item) ->
            "${quoteJson(key)}:${deterministicJson(item)}"
        }
    else -> throw CanonicalIrDocumentSliceException("unsupported deterministic JSON value ${value::class}")
}

private fun quoteJson(value: String): String = buildString {
    append('"')
    value.forEach { ch ->
        when {
            ch == '"' -> append("\\\"")
            ch == '\\' -> append("\\\\")
            ch == '\b' -> append("\\b")
            ch == '\u000C' -> append("\\f")
            ch == '\n' -> append("\\n")
            ch == '\r' -> append("\\r")
            ch == '\t' -> append("\\t")
            ch.code < 0x20 -> append("\\u" + ch.code.toString(16).padStart(4, '0'))
            else -> append(ch)
        }
    }
    append('"')
}
