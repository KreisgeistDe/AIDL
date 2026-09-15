package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedDefinitionStatus {
    INVALID,
    UNRESOLVED,
    AMBIGUOUS,
    RESOLVED,
}

data class ProjectedDefinitionTarget(
    val fullyQualifiedName: String,
    val kind: String,
    val sourceId: String,
    val line: Int,
    val column: Int,
    val offset: Int,
)

data class ProjectedDefinitionResult(
    val status: ProjectedDefinitionStatus,
    val reference: String? = null,
    val target: ProjectedDefinitionTarget? = null,
)

/**
 * Bounded M10.5-04 definition query over the already-migrated Gate-03 source/resolution facts.
 *
 * This class owns no symbol index of its own. It extracts the lexical reference at file+offset
 * through [AidlSourceProjector] and delegates all candidate semantics to [ProjectNameResolver].
 */
class ProjectDefinitionQuery private constructor(
    private val resolver: ProjectNameResolver,
    private val sources: List<Pair<String, String>>,
    private val sourceById: Map<String, String>,
) {
    fun definition(sourceId: String, offset: Int): ProjectedDefinitionResult {
        val source = sourceById[sourceId]
            ?: return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)
        val reference = try {
            AidlSourceProjector.referenceAt(source, offset)
        } catch (_: SourceProjectionException) {
            null
        } ?: return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)

        val resolution = resolver.resolve(sourceId, reference)
        return when (resolution.status) {
            ProjectedResolutionStatus.UNRESOLVED ->
                ProjectedDefinitionResult(ProjectedDefinitionStatus.UNRESOLVED, reference)
            ProjectedResolutionStatus.AMBIGUOUS ->
                ProjectedDefinitionResult(ProjectedDefinitionStatus.AMBIGUOUS, reference)
            ProjectedResolutionStatus.RESOLVED ->
                ProjectedDefinitionResult(
                    ProjectedDefinitionStatus.RESOLVED,
                    reference,
                    targetFor(resolution.symbols.single()),
                )
        }
    }

    /**
     * Query an explicit in-memory text for an existing projected source identity.
     *
     * The override is projected for this call so reference extraction, resolution facts and
     * target locations all come from the same snapshot text. No workspace or cached state is
     * retained between calls.
     */
    fun definition(sourceId: String, sourceText: String, offset: Int): ProjectedDefinitionResult {
        if (sourceId !in sourceById) {
            return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)
        }
        if (sourceById.getValue(sourceId) == sourceText) {
            return definition(sourceId, offset)
        }
        val overriddenSources = sources.map { (candidateId, source) ->
            candidateId to if (candidateId == sourceId) sourceText else source
        }
        val overridden = try {
            fromSources(overriddenSources)
        } catch (_: SourceProjectionException) {
            return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)
        }
        return overridden.definition(sourceId, offset)
    }

    private fun targetFor(symbol: ProjectedSymbol): ProjectedDefinitionTarget {
        val document = resolver.documents.first { it.sourceId == symbol.sourceId }
        val declaration = document.projection.declarations[symbol.declarationIndex]
        val source = sourceById.getValue(symbol.sourceId)
        val offset = declaration.nameOffset
        val prefix = source.substring(0, offset)
        val line = prefix.count { it == '\n' } + 1
        val lineStart = prefix.lastIndexOf('\n') + 1
        val column = offset - lineStart + 1
        return ProjectedDefinitionTarget(
            fullyQualifiedName = symbol.fullyQualifiedName!!,
            kind = symbol.kind,
            sourceId = symbol.sourceId,
            line = line,
            column = column,
            offset = offset,
        )
    }

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectDefinitionQuery {
            val stableSources = sources.toList()
            return ProjectDefinitionQuery(
                resolver = ProjectNameResolver.fromSources(stableSources),
                sources = stableSources,
                sourceById = stableSources.toMap(),
            )
        }
    }
}
