package de.kreisgeist.aidl.compiler.frontend

data class ProjectedDocument(
    val sourceId: String,
    val projection: SourceProjection,
)

data class ProjectedSymbol(
    val sourceId: String,
    val declarationIndex: Int,
    val module: String?,
    val kind: String,
    val name: String,
    val exported: Boolean,
    val fullyQualifiedName: String?,
) {
    val stableIdentity: String?
        get() = fullyQualifiedName?.let { "$it@$sourceId#$declarationIndex" }
}

data class ProjectedImportResolution(
    val sourceId: String,
    val importName: String,
    val symbols: List<ProjectedSymbol>,
)

enum class ProjectedResolutionStatus {
    RESOLVED,
    UNRESOLVED,
    AMBIGUOUS,
}

data class ProjectedNameResolution(
    val status: ProjectedResolutionStatus,
    val reference: String,
    val symbols: List<ProjectedSymbol>,
)

/**
 * Second bounded M10.5-03 front-end slice.
 *
 * This mirrors only Python compiler_project/compiler_resolution name projection over the
 * already-bounded SourceProjection surface: module-qualified declaration identities,
 * explicit/wildcard exported imports, local-module lookup, imported short-name lookup,
 * qualified FQN lookup, stable project order, and ambiguity preservation.
 */
class ProjectNameResolver private constructor(
    val documents: List<ProjectedDocument>,
    val symbols: List<ProjectedSymbol>,
    val importResolutions: List<ProjectedImportResolution>,
) {
    private val documentBySourceId = documents.associateBy { it.sourceId }
    private val symbolsByFqn = symbols
        .filter { it.fullyQualifiedName != null }
        .groupBy { it.fullyQualifiedName!! }

    fun lookupFullyQualified(fullyQualifiedName: String): List<ProjectedSymbol> =
        symbolsByFqn[fullyQualifiedName].orEmpty()

    fun resolve(sourceId: String, reference: String): ProjectedNameResolution {
        val document = requireNotNull(documentBySourceId[sourceId]) { "unknown sourceId '$sourceId'" }
        require(reference.isNotBlank()) { "reference must not be blank" }

        val candidates = if ('.' in reference) {
            lookupFullyQualified(reference)
        } else {
            buildList {
                val module = document.projection.module
                if (module != null) {
                    addAll(lookupFullyQualified("$module.$reference"))
                }
                for (resolution in importResolutions) {
                    if (resolution.sourceId != sourceId) continue
                    addAll(resolution.symbols.filter { it.name == reference })
                }
            }.distinctBy { it.sourceId to it.declarationIndex }
        }

        val status = when (candidates.size) {
            0 -> ProjectedResolutionStatus.UNRESOLVED
            1 -> ProjectedResolutionStatus.RESOLVED
            else -> ProjectedResolutionStatus.AMBIGUOUS
        }
        return ProjectedNameResolution(status, reference, candidates)
    }

    companion object {
        fun fromSources(sources: List<Pair<String, String>>): ProjectNameResolver {
            require(sources.map { it.first }.distinct().size == sources.size) {
                "sourceId values must be unique"
            }
            require(sources.all { it.first.isNotBlank() }) { "sourceId must not be blank" }

            val documents = sources.map { (sourceId, source) ->
                ProjectedDocument(sourceId, AidlSourceProjector.project(source))
            }
            val symbols = buildList {
                for (document in documents) {
                    val module = document.projection.module
                    document.projection.declarations.forEachIndexed { index, declaration ->
                        add(
                            ProjectedSymbol(
                                sourceId = document.sourceId,
                                declarationIndex = index,
                                module = module,
                                kind = declaration.kind,
                                name = declaration.name,
                                exported = declaration.exported,
                                fullyQualifiedName = module?.let { "$it.${declaration.name}" },
                            ),
                        )
                    }
                }
            }

            val exportedByFqn = symbols
                .filter { it.exported && it.fullyQualifiedName != null }
                .groupBy { it.fullyQualifiedName!! }
            val exportedByModule = symbols
                .filter { it.exported && it.module != null && it.fullyQualifiedName != null }
                .groupBy { it.module!! }

            val importResolutions = buildList {
                for (document in documents) {
                    for (importName in document.projection.imports) {
                        val resolved = if (importName.endsWith(".*")) {
                            exportedByModule[importName.removeSuffix(".*")].orEmpty()
                        } else {
                            exportedByFqn[importName].orEmpty()
                        }
                        add(ProjectedImportResolution(document.sourceId, importName, resolved))
                    }
                }
            }
            return ProjectNameResolver(documents, symbols, importResolutions)
        }
    }
}
