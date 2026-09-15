package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedDocumentationStatus {
    INVALID,
    UNRESOLVED,
    AMBIGUOUS,
    RESOLVED,
}

data class ProjectedDeclarationDocumentation(
    val fullyQualifiedName: String,
    val kind: String,
    val sourceId: String,
    val line: Int,
    val column: Int,
    val offset: Int,
    val representation: String,
)

data class ProjectedDocumentationResult(
    val status: ProjectedDocumentationStatus,
    val declaration: ProjectedDeclarationDocumentation? = null,
)

/**
 * Bounded M10.5-04 documentation query over already-migrated source/resolution facts.
 *
 * This query owns no parser, resolver, symbol index, cache or workspace state of its own.
 * Reference extraction stays on [AidlSourceProjector], candidate semantics stay on
 * [ProjectNameResolver], and declaration locations/headers are projected from the same source
 * text that produced those facts. Unsupported or malformed contexts fail closed.
 */
class ProjectDocumentationQuery private constructor(
    private val resolver: ProjectNameResolver,
    private val sources: List<Pair<String, String>>,
    private val sourceById: Map<String, String>,
) {
    fun document(sourceId: String, offset: Int): ProjectedDocumentationResult {
        val source = sourceById[sourceId] ?: return invalidResult()
        if (offset !in source.indices) return invalidResult()
        val reference = try {
            AidlSourceProjector.referenceAt(source, offset)
        } catch (_: SourceProjectionException) {
            null
        } ?: return invalidResult()

        val resolution = resolver.resolve(sourceId, reference)
        return when (resolution.status) {
            ProjectedResolutionStatus.UNRESOLVED ->
                ProjectedDocumentationResult(ProjectedDocumentationStatus.UNRESOLVED)
            ProjectedResolutionStatus.AMBIGUOUS ->
                ProjectedDocumentationResult(ProjectedDocumentationStatus.AMBIGUOUS)
            ProjectedResolutionStatus.RESOLVED ->
                ProjectedDocumentationResult(
                    ProjectedDocumentationStatus.RESOLVED,
                    declarationFor(resolution.symbols.single()),
                )
        }
    }

    /** Query explicit unsaved text under an existing stable source identity. */
    fun document(sourceId: String, sourceText: String, offset: Int): ProjectedDocumentationResult {
        if (sourceId !in sourceById) return invalidResult()
        if (sourceById.getValue(sourceId) == sourceText) return document(sourceId, offset)
        val overriddenSources = sources.map { (candidateId, source) ->
            candidateId to if (candidateId == sourceId) sourceText else source
        }
        val overridden = try {
            fromSources(overriddenSources)
        } catch (_: SourceProjectionException) {
            return invalidResult()
        }
        return overridden.document(sourceId, offset)
    }

    private fun declarationFor(symbol: ProjectedSymbol): ProjectedDeclarationDocumentation {
        val document = resolver.documents.first { it.sourceId == symbol.sourceId }
        val declaration = document.projection.declarations[symbol.declarationIndex]
        val source = sourceById.getValue(symbol.sourceId)
        val offset = declaration.nameOffset
        val prefix = source.substring(0, offset)
        val line = prefix.count { it == '\n' } + 1
        val lineStart = prefix.lastIndexOf('\n') + 1
        val column = offset - lineStart + 1
        val headerEnd = listOf(
            source.indexOf('{', declaration.offset).takeIf { it >= 0 } ?: declaration.endOffset,
            source.indexOf('\n', declaration.offset).takeIf { it >= 0 } ?: declaration.endOffset,
            source.indexOf('\r', declaration.offset).takeIf { it >= 0 } ?: declaration.endOffset,
            declaration.endOffset,
        ).filter { it >= declaration.offset }.minOrNull() ?: declaration.endOffset
        val representation = source.substring(declaration.offset, headerEnd)
            .trim()
            .split(Regex("\\s+"))
            .joinToString(" ")
        return ProjectedDeclarationDocumentation(
            fullyQualifiedName = symbol.fullyQualifiedName!!,
            kind = symbol.kind,
            sourceId = symbol.sourceId,
            line = line,
            column = column,
            offset = offset,
            representation = representation,
        )
    }

    private fun invalidResult() = ProjectedDocumentationResult(ProjectedDocumentationStatus.INVALID)

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectDocumentationQuery {
            val stableSources = sources.toList()
            return ProjectDocumentationQuery(
                resolver = ProjectNameResolver.fromSources(stableSources),
                sources = stableSources,
                sourceById = stableSources.toMap(),
            )
        }
    }
}
