package de.kreisgeist.aidl.compiler.ir

private const val IR_VERSION = "0.3.0"
private const val ZERO_HASH = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

class CanonicalIrDocumentSliceException(message: String) : IllegalArgumentException(message)

data class CanonicalIrDocumentSlice internal constructor(
    internal val document: Map<String, Any?>,
) {
    /** Schema-shaped JSON. Semantic hashes are placeholders because hash migration is out of scope. */
    fun canonicalJson(): String = deterministicJson(document)

    /** Full-document structural comparison surface excluding separately owned semantic hashes. */
    fun structuralJson(): String = deterministicJson(stripSemanticHashes(document))
}

/**
 * Second bounded M10.5-04 Canonical-IR slice.
 *
 * The existing domain projector remains the only Kotlin owner of enum/value/entity construction.
 * This projector composes that slice with the already-shared minimal app/service/system/deployment
 * envelope fixture so Kotlin can produce a complete schema-shaped document. Semantic hash
 * calculation remains Python-owned; zero hashes are carried only as schema-valid placeholders and
 * are deliberately excluded from the cross-implementation structural comparison surface.
 */
object CanonicalIrDocumentSliceProjector {
    fun project(
        domainSourceId: String,
        domainPath: String,
        domainSource: String,
        envelopeSourceId: String,
        envelopePath: String,
        envelopeSource: String,
    ): CanonicalIrDocumentSlice {
        val domain = CanonicalIrDomainSliceProjector.project(domainSourceId, domainPath, domainSource)
        val domainModule = Regex("(?m)^module\\s+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)\\s*$")
            .find(domainSource)?.groupValues?.get(1)
            ?: throw CanonicalIrDocumentSliceException("canonical IR document slice requires domain module")
        val envelope = parseEnvelope(envelopePath, envelopeSource, domainModule, domain)
        return CanonicalIrDocumentSlice(envelope)
    }

    private data class Block(val name: String, val body: String, val start: Int, val end: Int)

    private fun parseEnvelope(
        path: String,
        source: String,
        domainModule: String,
        domain: CanonicalIrDomainSlice,
    ): Map<String, Any?> {
        val module = Regex("(?m)^module\\s+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)\\s*$")
            .find(source)?.groupValues?.get(1)
            ?: throw CanonicalIrDocumentSliceException("canonical IR envelope requires module")
        val imports = Regex("(?m)^import\\s+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)\\.\\*\\s*$")
            .findAll(source).map { it.groupValues[1] }.toList()
        if (imports != listOf(domainModule)) {
            throw CanonicalIrDocumentSliceException("canonical IR envelope requires exactly import $domainModule.*")
        }

        val appMatch = singleBlock(source, Regex("(?ms)^app\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\{(.*?)^\\}"), "app")
        val authMatch = singleBlock(source, Regex("(?ms)^auth\\s*\\{(.*?)^\\}"), "auth", nameGroup = null)
        val serviceMatches = blocks(source, Regex("(?ms)^export\\s+service\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\{(.*?)^\\}"))
        val systemMatch = singleBlock(source, Regex("(?ms)^export\\s+system\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\{(.*?)^\\}"), "system")
        val deploymentRegex = Regex("(?ms)^export\\s+deployment\\s+([A-Za-z_][A-Za-z0-9_]*)\\s+for\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\{(.*?)^\\}")
        val deployments = deploymentRegex.findAll(source).toList()
        if (deployments.size != 1) throw CanonicalIrDocumentSliceException("canonical IR envelope requires exactly one deployment")
        ensureOnlyOwnedEnvelopeSurface(source, appMatch, authMatch, serviceMatches, systemMatch, deployments.single())

        val profiles = Regex("(?m)^\\s*profile\\s+([a-z][a-z0-9-]*)\\s+version\\s+([1-9][0-9]*)\\s*$")
            .findAll(appMatch.body).map { mapOf("id" to it.groupValues[1], "major" to it.groupValues[2].toInt()) }.toList()
        if (profiles.isEmpty()) throw CanonicalIrDocumentSliceException("canonical IR envelope app requires profile")
        val appSystem = lineValue(appMatch.body, "system")
        val defaultDeployment = lineValue(appMatch.body, "defaultDeployment")
        val appId = identity(module, appMatch.name)

        val authProvider = lineValue(authMatch.body, "provider")
        val subject = lineValue(authMatch.body, "subject")
        val subjectClaim = Regex("^claim\\s+\"([^\"]+)\"$").matchEntire(subject)?.groupValues?.get(1)
            ?: throw CanonicalIrDocumentSliceException("canonical IR envelope owns only auth subject claim")
        val roles = bracketList(lineValue(authMatch.body, "roles"), "auth roles")
        val scopes = bracketList(lineValue(authMatch.body, "scopes"), "auth scopes")
        val serviceIdentities = lineValue(authMatch.body, "serviceIdentities")
        if (serviceIdentities !in setOf("required", "optional")) {
            throw CanonicalIrDocumentSliceException("unsupported serviceIdentities '$serviceIdentities'")
        }

        val domainEntities = domain.declarations.filter { it.kind == "entity" }.associateBy { it.fqn }
        val servicesByName = linkedMapOf<String, Map<String, Any?>>()
        for (service in serviceMatches) {
            val owns = bracketList(lineValue(service.body, "owns"), "service owns")
            val ownerIds = owns.map { ref ->
                domainEntities[ref]?.declarationId
                    ?: throw CanonicalIrDocumentSliceException("unsupported or unresolved owned entity '$ref'")
            }
            val uses = bracketList(lineValue(service.body, "uses"), "service uses")
            val exposes = bracketList(lineValue(service.body, "exposes"), "service exposes")
            val runs = bracketList(lineValue(service.body, "runs"), "service runs")
            if (uses.isNotEmpty() || exposes.isNotEmpty() || runs.isNotEmpty()) {
                throw CanonicalIrDocumentSliceException("service uses/exposes/runs are outside bounded document slice")
            }
            servicesByName[service.name] = identity(module, service.name) + mapOf(
                "owns" to ownerIds,
                "uses" to emptyList<String>(),
                "exposes" to emptyList<String>(),
                "runs" to emptyList<String>(),
            )
        }
        if (servicesByName.size != serviceMatches.size) {
            throw CanonicalIrDocumentSliceException("canonical IR envelope requires unique service names")
        }

        val systemServices = bracketList(lineValue(systemMatch.body, "services"), "system services")
        val systemServiceObjects = systemServices.map { name ->
            servicesByName[name] ?: throw CanonicalIrDocumentSliceException("unresolved system service '$name'")
        }
        val resources = bracketList(lineValue(systemMatch.body, "resources"), "system resources")
        val apis = bracketList(lineValue(systemMatch.body, "apis"), "system apis")
        if (resources.isNotEmpty() || apis.isNotEmpty()) {
            throw CanonicalIrDocumentSliceException("system resources/apis are outside bounded document slice")
        }
        if (appSystem != systemMatch.name) {
            throw CanonicalIrDocumentSliceException("app system '$appSystem' does not match '${systemMatch.name}'")
        }

        val deployment = deployments.single()
        val deploymentName = deployment.groupValues[1]
        val deploymentSystem = deployment.groupValues[2]
        val deploymentBody = deployment.groupValues[3]
        if (defaultDeployment != deploymentName || deploymentSystem != systemMatch.name) {
            throw CanonicalIrDocumentSliceException("deployment references do not match app/system")
        }
        val environment = lineValue(deploymentBody, "environment")
        val target = lineValue(deploymentBody, "target")
        if (!Regex("(?m)^\\s*colocate\\s+services\\s+all\\s*$").containsMatchIn(deploymentBody)) {
            throw CanonicalIrDocumentSliceException("bounded deployment requires 'colocate services all'")
        }
        val deploymentKnown = Regex("(?m)^\\s*(environment\\s+\\S+|target\\s+\\S+|colocate\\s+services\\s+all)\\s*$")
        val deploymentUnknown = deploymentBody.lines().filter { it.isNotBlank() && !deploymentKnown.matches(it) }
        if (deploymentUnknown.isNotEmpty()) {
            throw CanonicalIrDocumentSliceException("unsupported deployment fact '${deploymentUnknown.first().trim()}'")
        }

        val declarations = domain.declarations.map { declarationMap(it) }
        val app = appId + mapOf(
            "systemId" to declarationId(module, systemMatch.name),
            "apiIds" to emptyList<String>(),
            "defaultDeploymentId" to declarationId(module, deploymentName),
            "auth" to mapOf(
                "provider" to authProvider,
                "subjectClaim" to subjectClaim,
                "roles" to roles,
                "scopes" to scopes,
                "serviceIdentities" to serviceIdentities,
            ),
        )
        val system = identity(module, systemMatch.name) + mapOf(
            "services" to systemServiceObjects,
            "resources" to emptyList<Any?>(),
            "topicIds" to emptyList<String>(),
            "apiIds" to emptyList<String>(),
            "edges" to emptyList<Any?>(),
            "consumerGroups" to emptyList<Any?>(),
        )
        val deploymentObject = identity(module, deploymentName) + mapOf(
            "environment" to environment,
            "regions" to emptyList<String>(),
            "serviceBindings" to systemServices.map { name ->
                mapOf("serviceId" to declarationId(module, name), "adapter" to target)
            },
            "resourceBindings" to emptyList<Any?>(),
        )

        val sourceEntries = mutableListOf<Map<String, Any?>>()
        sourceEntries += sourceEntry("/app", appId.getValue("declarationId") as String, path, source, appMatch.start, appMatch.end)
        sourceEntries += domain.sourceEntries.map { entry -> sourceEntryMap(entry) }
        sourceEntries += sourceEntry(
            "/system",
            declarationId(module, systemMatch.name),
            path,
            source,
            kindStart(source, systemMatch.start, "system"),
            systemMatch.end,
        )
        serviceMatches.forEachIndexed { index, service ->
            sourceEntries += sourceEntry(
                "/system/services/$index",
                declarationId(module, service.name),
                path,
                source,
                kindStart(source, service.start, "service"),
                service.end,
            )
        }
        sourceEntries += sourceEntry(
            "/deployments/0",
            declarationId(module, deploymentName),
            path,
            source,
            kindStart(source, deployment.range.first, "deployment"),
            deployment.range.last + 1,
        )

        return linkedMapOf(
            "irVersion" to IR_VERSION,
            "semanticHash" to ZERO_HASH,
            "profiles" to profiles,
            "app" to app,
            "declarations" to declarations,
            "system" to system,
            "deployments" to listOf(deploymentObject),
            "sourceMap" to mapOf("entries" to sourceEntries),
            "profileExtensions" to emptyMap<String, Any?>(),
        )
    }

    private fun singleBlock(
        source: String,
        regex: Regex,
        label: String,
        nameGroup: Int? = 1,
    ): Block {
        val matches = regex.findAll(source).toList()
        if (matches.size != 1) throw CanonicalIrDocumentSliceException("canonical IR envelope requires exactly one $label block")
        val match = matches.single()
        val bodyGroup = if (nameGroup == null) 1 else 2
        val name = nameGroup?.let { match.groupValues[it] } ?: label
        return Block(name, match.groupValues[bodyGroup], match.range.first, match.range.last + 1)
    }

    private fun blocks(source: String, regex: Regex): List<Block> = regex.findAll(source).map { match ->
        Block(match.groupValues[1], match.groupValues[2], match.range.first, match.range.last + 1)
    }.toList().also {
        if (it.isEmpty()) throw CanonicalIrDocumentSliceException("canonical IR envelope requires at least one service")
    }

    private fun ensureOnlyOwnedEnvelopeSurface(
        source: String,
        app: Block,
        auth: Block,
        services: List<Block>,
        system: Block,
        deployment: MatchResult,
    ) {
        val owned = BooleanArray(source.length)
        fun mark(start: Int, end: Int) { for (index in start until end) owned[index] = true }
        Regex("(?m)^module\\s+[^\\n]+$").findAll(source).forEach { mark(it.range.first, it.range.last + 1) }
        Regex("(?m)^import\\s+[^\\n]+$").findAll(source).forEach { mark(it.range.first, it.range.last + 1) }
        mark(app.start, app.end); mark(auth.start, auth.end); services.forEach { mark(it.start, it.end) }
        mark(system.start, system.end); mark(deployment.range.first, deployment.range.last + 1)
        val unexpected = source.indices.firstOrNull { !owned[it] && !source[it].isWhitespace() }
        if (unexpected != null) {
            throw CanonicalIrDocumentSliceException("unsupported canonical IR envelope syntax at offset $unexpected")
        }
    }

    private fun lineValue(body: String, key: String): String =
        Regex("(?m)^\\s*${Regex.escape(key)}\\s+(.+?)\\s*$").find(body)?.groupValues?.get(1)
            ?: throw CanonicalIrDocumentSliceException("canonical IR envelope requires '$key'")

    private fun bracketList(raw: String, label: String): List<String> {
        val trimmed = raw.trim()
        if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) {
            throw CanonicalIrDocumentSliceException("$label must be a bracketed list")
        }
        val inner = trimmed.substring(1, trimmed.length - 1).trim()
        return if (inner.isEmpty()) emptyList() else inner.split(',').map { it.trim() }.also { values ->
            if (values.any { it.isEmpty() }) throw CanonicalIrDocumentSliceException("$label contains empty item")
        }
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
            "value" -> result["fields"] = value.fields.map { fieldMap(it) }
            "entity" -> {
                result["fields"] = value.fields.map { fieldMap(it) }
                result["identityFields"] = value.identityFields
            }
            else -> throw CanonicalIrDocumentSliceException("unsupported document declaration '${value.kind}'")
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
            "typeArguments" to value.typeArguments.map { typeMap(it) },
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

    private fun sourceEntry(
        nodePath: String,
        id: String,
        path: String,
        source: String,
        start: Int,
        end: Int,
    ): Map<String, Any?> {
        val startPosition = position(source, start)
        val endPosition = position(source, end)
        return mapOf(
            "nodePath" to nodePath,
            "originalDeclarationId" to id,
            "span" to mapOf(
                "file" to path,
                "startLine" to startPosition.first,
                "startColumn" to startPosition.second,
                "endLine" to endPosition.first,
                "endColumn" to endPosition.second,
            ),
        )
    }

    private fun kindStart(source: String, blockStart: Int, kind: String): Int {
        val found = source.indexOf(kind, blockStart)
        if (found < blockStart) throw CanonicalIrDocumentSliceException("cannot locate $kind source span")
        return found
    }

    private fun identity(module: String, name: String): Map<String, Any?> = linkedMapOf(
        "declarationId" to declarationId(module, name),
        "fqn" to "$module.$name",
        "name" to name,
        "ownerModule" to module,
        "semanticHash" to ZERO_HASH,
    )

    private fun declarationId(module: String, name: String): String = "$module.$name@1"

    private fun position(source: String, offset: Int): Pair<Int, Int> {
        if (offset !in 0..source.length) throw CanonicalIrDocumentSliceException("invalid source offset $offset")
        var line = 1
        var column = 1
        for (index in 0 until offset) {
            if (source[index] == '\n') { line += 1; column = 1 } else column += 1
        }
        return line to column
    }
}

private fun stripSemanticHashes(value: Any?): Any? = when (value) {
    is Map<*, *> -> value.entries
        .filter { it.key != "semanticHash" }
        .associate { it.key as String to stripSemanticHashes(it.value) }
    is List<*> -> value.map { stripSemanticHashes(it) }
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
