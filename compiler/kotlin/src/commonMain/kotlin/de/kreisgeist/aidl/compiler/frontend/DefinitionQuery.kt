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
            ProjectedResolutionStatus.RESOLVED -> {
                val target = resolution.symbols.singleOrNull()?.let(::targetFor)
                    ?: return ProjectedDefinitionResult(ProjectedDefinitionStatus.INVALID, reference)
                ProjectedDefinitionResult(ProjectedDefinitionStatus.RESOLVED, reference, target)
            }
        }
    }

    private fun targetFor(symbol: ProjectedSymbol): ProjectedDefinitionTarget? {
        val document = resolver.documents.firstOrNull { it.sourceId == symbol.sourceId } ?: return null
        val declaration = document.projection.declarations.getOrNull(symbol.declarationIndex) ?: return null
        val source = sourceById[symbol.sourceId] ?: return null
        val offset = declaration.nameOffset
        if (
            offset < 0 ||
            offset + declaration.name.length > source.length ||
            source.substring(offset, offset + declaration.name.length) != declaration.name
        ) {
            return null
        }
        val prefix = source.substring(0, offset)
        val line = prefix.count { it == '\n' } + 1
        val lineStart = prefix.lastIndexOf('\n') + 1
        val column = offset - lineStart + 1
        val fullyQualifiedName = symbol.fullyQualifiedName ?: return null
        return ProjectedDefinitionTarget(
            fullyQualifiedName = fullyQualifiedName,
            kind = symbol.kind,
            sourceId = symbol.sourceId,
            line = line,
            column = column,
            offset = offset,
        )
    }

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectDefinitionQuery {
            require(sources.map { it.first }.distinct().size == sources.size) {
                "sourceId values must be unique"
            }
            require(sources.all { it.first.isNotBlank() }) { "sourceId must not be blank" }
            val documents = sources.map { (sourceId, source) ->
                ProjectedDocument(
                    sourceId,
                    AidlSourceProjector.project(sourceId, "$sourceId.source", source),
                )
            }
            return ProjectDefinitionQuery(
                resolver = ProjectNameResolver.fromProjectedDocuments(documents),
                sourceById = sources.toMap(),
            )
        }
    }
}
