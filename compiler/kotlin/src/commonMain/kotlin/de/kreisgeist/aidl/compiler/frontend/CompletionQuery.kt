package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedCompletionStatus {
    INVALID,
    RESOLVED,
}

data class ProjectedCompletionCandidate(
    val insertText: String,
    val displayText: String,
    val fullyQualifiedName: String,
    val kind: String,
    val origin: String,
    val sourceId: String,
    val sourceOffset: Int,
)

data class ProjectedCompletionResult(
    val status: ProjectedCompletionStatus,
    val prefix: String?,
    val qualifier: String?,
    val candidates: List<ProjectedCompletionCandidate>,
)

private data class ProjectedCompletionContext(
    val prefix: String,
    val qualifier: String?,
)

/**
 * Bounded M10.5-04 completion query over the already-migrated Gate-03 source/resolution facts.
 *
 * This class owns no resolver, index, cache or workspace state. It uses the bounded source
 * projector to establish an accepted source/declaration shape, derives a conservative
 * parser-backed reference-value context inside that projection, and projects candidates through
 * [ProjectNameResolver]. Ambiguous simple names are omitted instead of guessed.
 */
class ProjectCompletionQuery private constructor(
    private val resolver: ProjectNameResolver,
    private val sources: List<Pair<String, String>>,
    private val sourceById: Map<String, String>,
) {
    fun complete(sourceId: String, offset: Int): ProjectedCompletionResult {
        val source = sourceById[sourceId] ?: return invalidResult()
        val projection = try {
            AidlSourceProjector.project(source)
        } catch (_: SourceProjectionException) {
            return invalidResult()
        }
        val context = completionContext(projection, source, offset) ?: return invalidResult()
        val candidates = if (context.qualifier != null) {
            qualifiedCandidates(context.qualifier, context.prefix)
        } else {
            visibleUnqualifiedCandidates(sourceId, context.prefix)
        }
        return ProjectedCompletionResult(
            status = ProjectedCompletionStatus.RESOLVED,
            prefix = context.prefix,
            qualifier = context.qualifier,
            candidates = candidates,
        )
    }

    /** Query an explicit in-memory text for an existing projected source identity. */
    fun complete(sourceId: String, sourceText: String, offset: Int): ProjectedCompletionResult {
        if (sourceId !in sourceById) return invalidResult()
        if (sourceById.getValue(sourceId) == sourceText) return complete(sourceId, offset)
        val overriddenSources = sources.map { (candidateId, source) ->
            candidateId to if (candidateId == sourceId) sourceText else source
        }
        val overridden = try {
            fromSources(overriddenSources)
        } catch (_: SourceProjectionException) {
            return invalidResult()
        }
        return overridden.complete(sourceId, offset)
    }

    private fun visibleUnqualifiedCandidates(
        sourceId: String,
        prefix: String,
    ): List<ProjectedCompletionCandidate> {
        val document = resolver.documents.first { it.sourceId == sourceId }
        val visible = linkedMapOf<String, MutableList<Pair<ProjectedSymbol, String>>>()
        val module = document.projection.module
        if (module != null) {
            for (symbol in resolver.symbols) {
                if (symbol.module != module) continue
                if (!symbol.name.startsWith(prefix)) continue
                visible.getOrPut(symbol.name) { mutableListOf() }
                    .add(symbol to "local:$module")
            }
        }
        for (resolution in resolver.importResolutions) {
            if (resolution.sourceId != sourceId) continue
            val origin = if (resolution.importName.endsWith(".*")) {
                "wildcardImport:${resolution.importName}"
            } else {
                "exactImport:${resolution.importName}"
            }
            for (symbol in resolution.symbols) {
                if (!symbol.name.startsWith(prefix)) continue
                visible.getOrPut(symbol.name) { mutableListOf() }.add(symbol to origin)
            }
        }

        return buildList {
            for (name in visible.keys.sorted()) {
                val unique = visible.getValue(name)
                    .distinctBy { (symbol, _) -> symbol.sourceId to symbol.declarationIndex }
                if (unique.size != 1) continue
                val (symbol, origin) = unique.single()
                add(candidateFor(symbol, name, origin))
            }
        }
    }

    private fun qualifiedCandidates(
        qualifier: String,
        prefix: String,
    ): List<ProjectedCompletionCandidate> {
        val fqnPrefix = "$qualifier."
        return buildList {
            val fqns = resolver.symbols
                .mapNotNull { it.fullyQualifiedName }
                .distinct()
                .sorted()
            for (fullyQualifiedName in fqns) {
                if (!fullyQualifiedName.startsWith(fqnPrefix)) continue
                val remainder = fullyQualifiedName.removePrefix(fqnPrefix)
                if ('.' in remainder || !remainder.startsWith(prefix)) continue
                val matches = resolver.lookupFullyQualified(fullyQualifiedName)
                if (matches.size != 1) continue
                add(candidateFor(matches.single(), remainder, "qualified:$qualifier"))
            }
        }
    }

    private fun candidateFor(
        symbol: ProjectedSymbol,
        insertText: String,
        origin: String,
    ): ProjectedCompletionCandidate {
        val document = resolver.documents.first { it.sourceId == symbol.sourceId }
        val declaration = document.projection.declarations[symbol.declarationIndex]
        return ProjectedCompletionCandidate(
            insertText = insertText,
            displayText = "$insertText (${symbol.kind})",
            fullyQualifiedName = symbol.fullyQualifiedName!!,
            kind = symbol.kind,
            origin = origin,
            sourceId = symbol.sourceId,
            sourceOffset = declaration.nameOffset,
        )
    }

    private fun completionContext(
        projection: SourceProjection,
        source: String,
        offset: Int,
    ): ProjectedCompletionContext? {
        if (offset !in 0..source.length) return null

        val wordIndex = when {
            offset < source.length && source[offset].isCompletionWordPart() -> offset
            offset > 0 && source[offset - 1].isCompletionWordPart() -> offset - 1
            else -> -1
        }
        if (wordIndex >= 0) {
            val lexicalReference = AidlSourceProjector.referenceAt(source, wordIndex)
                ?.takeUnless { it.startsWith("@") }
                ?: return null
            var start = wordIndex
            while (start > 0 && source[start - 1].isCompletionWordPart()) start -= 1
            var end = wordIndex + 1
            while (end < source.length && source[end].isCompletionWordPart()) end += 1
            if (!lexicalReference.contains(source.substring(start, end))) return null
            if (!isParserBackedReferenceValue(projection, source, start)) return null
            val prefixEnd = offset.coerceIn(start, end)
            return ProjectedCompletionContext(
                prefix = source.substring(start, prefixEnd),
                qualifier = qualifierBefore(source, start),
            )
        }

        if (offset > 0 && source[offset - 1] == '.') {
            val dotOffset = offset - 1
            if (!isParserBackedReferenceValue(projection, source, dotOffset)) return null
            val qualifier = AidlSourceProjector.referenceAt(source, dotOffset - 1)
                ?.takeUnless { it.startsWith("@") }
                ?: return null
            return ProjectedCompletionContext("", qualifier)
        }
        return null
    }

    private fun isParserBackedReferenceValue(
        projection: SourceProjection,
        source: String,
        anchor: Int,
    ): Boolean {
        val declaration = projection.declarations.firstOrNull {
            anchor in it.offset..it.endOffset
        } ?: return false
        val before = anchor - 1
        val boundary = maxOf(
            source.lastIndexOf('\n', before),
            source.lastIndexOf('{', before),
            source.lastIndexOf('}', before),
            declaration.offset - 1,
        )
        return source.lastIndexOf(':', before) > boundary
    }

    private fun qualifierBefore(source: String, wordStart: Int): String? {
        if (wordStart <= 0 || source[wordStart - 1] != '.') return null
        return qualifiedNameEndingAt(source, wordStart - 2)
    }

    private fun qualifiedNameEndingAt(source: String, endInclusive: Int): String? {
        if (endInclusive < 0 || !source[endInclusive].isCompletionWordPart()) return null
        var start = endInclusive
        while (start > 0) {
            val previous = source[start - 1]
            if (!previous.isCompletionWordPart() && previous != '.') break
            start -= 1
        }
        val value = source.substring(start, endInclusive + 1)
        return value.takeIf { candidate -> candidate.split('.').all { it.isNotEmpty() } }
    }

    private fun Char.isCompletionWordPart(): Boolean = this == '_' || isLetterOrDigit()

    private fun invalidResult(): ProjectedCompletionResult = ProjectedCompletionResult(
        status = ProjectedCompletionStatus.INVALID,
        prefix = null,
        qualifier = null,
        candidates = emptyList(),
    )

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectCompletionQuery {
            val stableSources = sources.toList()
            return ProjectCompletionQuery(
                resolver = ProjectNameResolver.fromSources(stableSources),
                sources = stableSources,
                sourceById = stableSources.toMap(),
            )
        }
    }
}
