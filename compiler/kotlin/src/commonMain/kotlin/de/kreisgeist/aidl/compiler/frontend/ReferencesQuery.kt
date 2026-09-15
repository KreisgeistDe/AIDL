package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedReferencesStatus {
    INVALID,
    UNRESOLVED,
    AMBIGUOUS,
    RESOLVED,
}

data class ProjectedReferenceOccurrence(
    val fullyQualifiedName: String,
    val sourceId: String,
    val line: Int,
    val column: Int,
    val offset: Int,
    val length: Int,
)

data class ProjectedReferencesResult(
    val status: ProjectedReferencesStatus,
    val reference: String? = null,
    val target: ProjectedDefinitionTarget? = null,
    val occurrences: List<ProjectedReferenceOccurrence> = emptyList(),
)

/**
 * Bounded M10.5-04 references query over the existing source projection and resolver.
 *
 * This owns no workspace, cache, reverse-reference index, or alternate resolver. Candidate
 * terminals come from [AidlSourceProjector] and are retained only when [ProjectNameResolver]
 * resolves them to the exact same semantic declaration as the query target.
 */
class ProjectReferencesQuery private constructor(
    private val resolver: ProjectNameResolver,
    private val sources: List<Pair<String, String>>,
    private val sourceById: Map<String, String>,
) {
    fun references(sourceId: String, offset: Int): ProjectedReferencesResult {
        val source = sourceById[sourceId]
            ?: return ProjectedReferencesResult(ProjectedReferencesStatus.INVALID)
        val reference = try {
            AidlSourceProjector.referenceAt(source, offset)
        } catch (_: SourceProjectionException) {
            null
        } ?: return ProjectedReferencesResult(ProjectedReferencesStatus.INVALID)

        val resolution = resolver.resolve(sourceId, reference)
        return when (resolution.status) {
            ProjectedResolutionStatus.UNRESOLVED ->
                ProjectedReferencesResult(ProjectedReferencesStatus.UNRESOLVED, reference)
            ProjectedResolutionStatus.AMBIGUOUS ->
                ProjectedReferencesResult(ProjectedReferencesStatus.AMBIGUOUS, reference)
            ProjectedResolutionStatus.RESOLVED -> resolved(reference, resolution.symbols.single())
        }
    }

    fun references(sourceId: String, sourceText: String, offset: Int): ProjectedReferencesResult {
        if (sourceId !in sourceById) return ProjectedReferencesResult(ProjectedReferencesStatus.INVALID)
        if (sourceById.getValue(sourceId) == sourceText) return references(sourceId, offset)
        val overriddenSources = sources.map { (candidateId, source) ->
            candidateId to if (candidateId == sourceId) sourceText else source
        }
        val overridden = try {
            fromSources(overriddenSources)
        } catch (_: SourceProjectionException) {
            return ProjectedReferencesResult(ProjectedReferencesStatus.INVALID)
        }
        return overridden.references(sourceId, offset)
    }

    private fun resolved(reference: String, targetSymbol: ProjectedSymbol): ProjectedReferencesResult {
        val target = targetFor(targetSymbol)
        val occurrences = mutableListOf<ProjectedReferenceOccurrence>()
        try {
            for ((candidateSourceId, source) in sources) {
                for (token in AidlSourceProjector.terminalReferences(source)) {
                    if (candidateSourceId == target.sourceId && token.offset == target.offset) continue
                    val candidate = resolver.resolve(candidateSourceId, token.reference)
                    if (candidate.status != ProjectedResolutionStatus.RESOLVED) continue
                    val symbol = candidate.symbols.single()
                    if (symbol.stableIdentity != targetSymbol.stableIdentity) continue
                    val prefix = source.substring(0, token.offset)
                    val line = prefix.count { it == '\n' } + 1
                    val lineStart = prefix.lastIndexOf('\n') + 1
                    occurrences += ProjectedReferenceOccurrence(
                        fullyQualifiedName = target.fullyQualifiedName,
                        sourceId = candidateSourceId,
                        line = line,
                        column = token.offset - lineStart + 1,
                        offset = token.offset,
                        length = token.length,
                    )
                }
            }
        } catch (_: SourceProjectionException) {
            return ProjectedReferencesResult(ProjectedReferencesStatus.INVALID, reference)
        }
        return ProjectedReferencesResult(
            status = ProjectedReferencesStatus.RESOLVED,
            reference = reference,
            target = target,
            occurrences = occurrences
                .distinctBy { it.sourceId to it.offset }
                .sortedWith(compareBy<ProjectedReferenceOccurrence>({ it.sourceId }, { it.offset })),
        )
    }

    private fun targetFor(symbol: ProjectedSymbol): ProjectedDefinitionTarget {
        val document = resolver.documents.first { it.sourceId == symbol.sourceId }
        val declaration = document.projection.declarations[symbol.declarationIndex]
        val source = sourceById.getValue(symbol.sourceId)
        val offset = declaration.nameOffset
        val prefix = source.substring(0, offset)
        val line = prefix.count { it == '\n' } + 1
        val lineStart = prefix.lastIndexOf('\n') + 1
        return ProjectedDefinitionTarget(
            fullyQualifiedName = symbol.fullyQualifiedName!!,
            kind = symbol.kind,
            sourceId = symbol.sourceId,
            line = line,
            column = offset - lineStart + 1,
            offset = offset,
        )
    }

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectReferencesQuery {
            val stableSources = sources.toList()
            return ProjectReferencesQuery(
                resolver = ProjectNameResolver.fromSources(stableSources),
                sources = stableSources,
                sourceById = stableSources.toMap(),
            )
        }
    }
}
