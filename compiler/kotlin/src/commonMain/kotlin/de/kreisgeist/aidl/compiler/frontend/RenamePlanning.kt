package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedRenameStatus {
    INVALID,
    INVALID_NAME,
    UNRESOLVED,
    AMBIGUOUS,
    COLLISION,
    READY,
}

data class ProjectedRenameTextEdit(
    val sourceId: String,
    val offset: Int,
    val length: Int,
    val replacement: String,
)

data class ProjectedRenameResult(
    val status: ProjectedRenameStatus,
    val target: ProjectedDefinitionTarget? = null,
    val newFullyQualifiedName: String? = null,
    val edits: List<ProjectedRenameTextEdit> = emptyList(),
    val message: String? = null,
)

/**
 * Bounded M10.5-04 compiler-owned rename planning over one exact source snapshot.
 *
 * The planner is deliberately non-applying. It reuses [ProjectReferencesQuery] and
 * [ProjectNameResolver], owns no filesystem mutation/index/cache semantics, and fails closed
 * when the bounded source snapshot cannot be projected. Python remains the migration oracle.
 */
class ProjectRenamePlanner private constructor(
    private val sources: List<Pair<String, String>>,
    private val sourceById: Map<String, String>,
    private val resolver: ProjectNameResolver?,
    private val referencesQuery: ProjectReferencesQuery?,
) {
    fun plan(sourceId: String, offset: Int, newName: String): ProjectedRenameResult {
        if (resolver == null || referencesQuery == null) {
            return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "snapshot has compiler errors before rename")
        }
        if (!validIdentifier(newName)) {
            return ProjectedRenameResult(ProjectedRenameStatus.INVALID_NAME, message = "new name must be a non-keyword AIDL identifier")
        }
        val source = sourceById[sourceId]
            ?: return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "rename target is not uniquely resolved")
        if (offset < 0 || offset >= source.length) {
            return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "rename target is not uniquely resolved")
        }

        val references = referencesQuery.references(sourceId, offset)
        val target = references.target
        when (references.status) {
            ProjectedReferencesStatus.INVALID ->
                return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "rename target is not uniquely resolved")
            ProjectedReferencesStatus.UNRESOLVED ->
                return ProjectedRenameResult(ProjectedRenameStatus.UNRESOLVED, message = "rename target is not uniquely resolved")
            ProjectedReferencesStatus.AMBIGUOUS ->
                return ProjectedRenameResult(ProjectedRenameStatus.AMBIGUOUS, message = "rename target is not uniquely resolved")
            ProjectedReferencesStatus.RESOLVED -> Unit
        }
        if (target == null) {
            return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "rename target is not uniquely resolved")
        }

        val oldName = target.fullyQualifiedName.substringAfterLast('.')
        if (newName == oldName) {
            return ProjectedRenameResult(
                ProjectedRenameStatus.INVALID_NAME,
                target = target,
                message = "new name must differ from current name",
            )
        }
        val moduleName = target.fullyQualifiedName.substringBeforeLast('.', missingDelimiterValue = "")
        val newFqn = if (moduleName.isEmpty()) newName else "$moduleName.$newName"
        if (resolver.lookupFullyQualified(newFqn).isNotEmpty()) {
            return ProjectedRenameResult(
                ProjectedRenameStatus.COLLISION,
                target = target,
                newFullyQualifiedName = newFqn,
                message = "new fully qualified name already exists",
            )
        }

        val edits = buildList {
            add(ProjectedRenameTextEdit(target.sourceId, target.offset, oldName.length, newName))
            addAll(references.occurrences.map {
                ProjectedRenameTextEdit(it.sourceId, it.offset, it.length, newName)
            })
        }.distinctBy { it.sourceId to it.offset }
            .sortedWith(compareBy<ProjectedRenameTextEdit>({ it.sourceId }, { it.offset }))

        for (edit in edits) {
            val text = sourceById[edit.sourceId]
                ?: return ProjectedRenameResult(ProjectedRenameStatus.INVALID, target = target, message = "rename edit is outside snapshot text")
            if (edit.offset < 0 || edit.offset + edit.length > text.length) {
                return ProjectedRenameResult(ProjectedRenameStatus.INVALID, target = target, message = "rename edit is outside snapshot text")
            }
            if (text.substring(edit.offset, edit.offset + edit.length) != oldName) {
                return ProjectedRenameResult(ProjectedRenameStatus.INVALID, target = target, message = "snapshot text changed while planning rename")
            }
        }
        return ProjectedRenameResult(ProjectedRenameStatus.READY, target, newFqn, edits)
    }

    fun plan(sourceId: String, sourceText: String, offset: Int, newName: String): ProjectedRenameResult {
        if (sourceId !in sourceById) {
            return ProjectedRenameResult(ProjectedRenameStatus.INVALID, message = "rename target is not uniquely resolved")
        }
        if (sourceById.getValue(sourceId) == sourceText) return plan(sourceId, offset, newName)
        val overridden = sources.map { (candidateId, source) ->
            candidateId to if (candidateId == sourceId) sourceText else source
        }
        return fromSources(overridden).plan(sourceId, offset, newName)
    }

    companion object {
        private val reservedWords = setOf(
            "a11y", "action", "alias", "and", "api", "app", "as", "auth", "boundedStaleness",
            "cache", "call", "channel", "client", "component", "config", "consumer", "deployment",
            "else", "emit", "entity", "enum", "error", "event", "export", "false", "fixture", "for",
            "form", "from", "frontend", "if", "import", "in", "isolation", "migration", "module",
            "mutation", "native", "not", "null", "on", "opaque", "or", "page", "policy", "privacy",
            "projection", "query", "queue", "ref", "rendition", "resource", "return", "saga", "scenario",
            "schedule", "secret", "seo", "service", "sync", "syncStatus", "system", "task", "tenant",
            "test", "theme", "to", "transaction", "true", "union", "value", "version", "view", "workflow",
        )

        private fun validIdentifier(name: String): Boolean {
            if (name.isEmpty() || name in reservedWords) return false
            if (!(name.first() == '_' || name.first().isLetter())) return false
            return name.drop(1).all { it == '_' || it.isLetterOrDigit() }
        }

        fun fromSources(sources: List<Pair<String, String>>): ProjectRenamePlanner {
            val stableSources = sources.toList()
            val sourceById = stableSources.toMap()
            if (stableSources.any { it.first.isBlank() } || sourceById.size != stableSources.size) {
                return ProjectRenamePlanner(stableSources, sourceById, null, null)
            }
            return try {
                ProjectRenamePlanner(
                    stableSources,
                    sourceById,
                    ProjectNameResolver.fromSources(stableSources),
                    ProjectReferencesQuery.fromSources(stableSources),
                )
            } catch (_: IllegalArgumentException) {
                ProjectRenamePlanner(stableSources, sourceById, null, null)
            }
        }
    }
}
