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
    private val sourceById: Map<String, String>,
) {
    fun definition(sourceId: String, offset: Int): ProjectedDefinitionResult {
        val source = sourceById[sourceId]
            ?: return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)
        return definition(sourceId, source, offset)
    }

    /**
     * Query an explicit in-memory text for an existing projected source identity.
     *
     * This bounded override is intended for offset/reference changes that leave the already
     * projected module/import/declaration graph unchanged. It does not create workspace state.
     */
    fun definition(sourceId: String, sourceText: String, offset: Int): ProjectedDefinitionResult {
        if (sourceId !in sourceById) {
            return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID)
        }
        val reference = try {
            AidlSourceProjector.referenceAt(sourceText, offset)
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
        fun fromSources(sources: List<Pair<String, String>>): ProjectDefinitionQuery =
            ProjectDefinitionQuery(
                resolver = ProjectNameResolver.fromSources(sources),
                sourceById = sources.toMap(),
            )
    }
}
