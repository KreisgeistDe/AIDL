package de.kreisgeist.aidl.compiler.frontend

enum class ProjectedMaterializationStatus {
    MATERIALIZABLE,
    REJECTED,
    UNRESOLVED,
    AMBIGUOUS,
    OUTSIDE_SLICE,
}

data class ProjectedSourceLocation(
    val line: Int,
    val column: Int,
    val offset: Int,
)

data class ProjectedMaterializationCheck(
    val status: ProjectedMaterializationStatus,
    val diagnosticCode: String? = null,
    val sourcePath: String? = null,
    val location: ProjectedSourceLocation? = null,
)

internal data class ProjectedFieldMaterializationCheck(
    val fieldName: String,
    val typeSource: String,
    val check: ProjectedMaterializationCheck,
)

/**
 * Bounded M10.5-03 materialization-boundary parity over the integrated type/resolution surface.
 *
 * Direct Core remains semantic authority and Python remains compatibility/conformance evidence.
 * This slice mirrors the current Python Core-materialization observable that admits only the
 * currently materialized declaration kinds, rejects other resolved named declarations with
 * AIDL-T005, and preserves known one-argument Core standard generics. Direct-Core-valid generic
 * forms that the historical projector cannot materialize remain OUTSIDE_SLICE rather than
 * becoming language errors.
 */
object ProjectedMaterializationChecker {
    private val standardTypes = setOf(
        "Page", "PageInput", "Cursor", "OperationId", "PrincipalId", "SubjectId",
        "FieldError", "FieldErrors", "ProblemDetails", "Unit",
    )
    private val materializedKinds = setOf("alias", "opaque", "enum", "value", "entity", "view")
    private val genericHead = Regex("([A-Za-z_][A-Za-z0-9_.]*)\\s*<(.*)>")

    fun check(
        sourceId: String,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = typeSource.trim()
        if ('<' in text || '>' in text) {
            val shape = genericShape(text)
                ?: return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            if (shape.first in standardTypes) {
                val nested = materializationOnly(sourceId, shape.second, resolver)
                if (nested.status == ProjectedMaterializationStatus.REJECTED) return nested
                if (nested.status == ProjectedMaterializationStatus.MATERIALIZABLE) return nested
                if (nested.status == ProjectedMaterializationStatus.UNRESOLVED) return nested
                if (nested.status == ProjectedMaterializationStatus.AMBIGUOUS) return nested
                return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
            val resolution = resolver.resolve(sourceId, shape.first)
            return when (resolution.status) {
                ProjectedResolutionStatus.AMBIGUOUS ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
                ProjectedResolutionStatus.UNRESOLVED ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
                ProjectedResolutionStatus.RESOLVED ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            }
        }

        val typeCheck = ProjectedTypeConstructor.check(sourceId, typeSource, resolver)
        return when (typeCheck.status) {
            ProjectedTypeResolutionStatus.AMBIGUOUS ->
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
            ProjectedTypeResolutionStatus.UNRESOLVED ->
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
            ProjectedTypeResolutionStatus.RESOLVED -> if (
                typeCheck.symbols.any { it.kind !in materializedKinds }
            ) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.MATERIALIZABLE)
            }
        }
    }

    /**
     * Internal diagnostic projection for callers that already own an authoritative source anchor.
     *
     * The materialization layer owns source anchoring only for its AIDL-T005 rejection. Resolver
     * classifications remain location-less here because their source-location contract belongs to
     * the resolver slice. OUTSIDE_SLICE and accepted results likewise carry no invented location.
     */
    internal fun checkAt(
        sourceId: String,
        sourceText: String,
        diagnosticOffset: Int,
        typeSource: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        require(diagnosticOffset in 0..sourceText.length) { "diagnostic offset is outside source text" }
        val check = check(sourceId, typeSource, resolver)
        if (
            check.status != ProjectedMaterializationStatus.REJECTED ||
            check.diagnosticCode != "AIDL-T005"
        ) {
            return check
        }
        return check.copy(
            sourcePath = sourceId,
            location = sourceLocation(sourceText, diagnosticOffset),
        )
    }

    /**
     * Bounded value/entity field traversal over the already-projected declaration body.
     *
     * SourceProjection owns lexical declaration boundaries; this layer only extracts ordered
     * `field name: TypeRef` facts from its deterministic body token stream and delegates every
     * TypeRef to the existing materialization/type/resolution boundary. It does not add parser or
     * language authority. The source anchor is the field keyword, matching the Python field span.
     */
    internal fun checkProjectedFields(
        sourceId: String,
        sourceText: String,
        declaration: ProjectedDeclaration,
        resolver: ProjectNameResolver,
    ): List<ProjectedFieldMaterializationCheck> {
        require(declaration.kind == "value" || declaration.kind == "entity") {
            "field materialization traversal is bounded to value/entity declarations"
        }
        val fields = projectedFields(declaration.bodyTokens)
        var searchFrom = 0
        return fields.map { (fieldName, typeSource) ->
            val marker = "field $fieldName"
            val offset = sourceText.indexOf(marker, startIndex = searchFrom)
            require(offset >= 0) { "projected field '$fieldName' is missing from source text" }
            searchFrom = offset + marker.length
            ProjectedFieldMaterializationCheck(
                fieldName = fieldName,
                typeSource = typeSource,
                check = checkAt(sourceId, sourceText, offset, typeSource, resolver),
            )
        }
    }

    private fun projectedFields(tokens: List<String>): List<Pair<String, String>> {
        val result = mutableListOf<Pair<String, String>>()
        var index = 0
        while (index < tokens.size) {
            if (tokens[index] != "field") {
                index += 1
                continue
            }
            require(index + 3 < tokens.size && tokens[index + 2] == ":") {
                "projected field tokens are malformed"
            }
            val name = tokens[index + 1]
            index += 3
            val typeTokens = mutableListOf<String>()
            while (index < tokens.size && tokens[index] != "field") {
                typeTokens += tokens[index]
                index += 1
            }
            require(typeTokens.isNotEmpty()) { "projected field '$name' has no type" }
            result += name to typeTokens.joinToString("")
        }
        return result
    }

    private fun sourceLocation(source: String, offset: Int): ProjectedSourceLocation {
        var line = 1
        var column = 1
        for (index in 0 until offset) {
            if (source[index] == '\n') {
                line += 1
                column = 1
            } else {
                column += 1
            }
        }
        return ProjectedSourceLocation(line = line, column = column, offset = offset)
    }

    private fun materializationOnly(
        sourceId: String,
        source: String,
        resolver: ProjectNameResolver,
    ): ProjectedMaterializationCheck {
        val text = source.trim()
        if ('<' in text || '>' in text) {
            val shape = genericShape(text)
                ?: return ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            if (shape.first in standardTypes) {
                return materializationOnly(sourceId, shape.second, resolver)
            }
            return if (resolver.resolve(sourceId, shape.first).status == ProjectedResolutionStatus.RESOLVED) {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.REJECTED, "AIDL-T005")
            } else {
                ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
            }
        }
        return try {
            val check = ProjectedTypeConstructor.check(sourceId, text, resolver)
            when (check.status) {
                ProjectedTypeResolutionStatus.AMBIGUOUS ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.AMBIGUOUS, "CORE-S023")
                ProjectedTypeResolutionStatus.UNRESOLVED ->
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.UNRESOLVED, "AIDL-T001")
                ProjectedTypeResolutionStatus.RESOLVED -> if (
                    check.symbols.any { it.kind !in materializedKinds }
                ) {
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
                } else {
                    ProjectedMaterializationCheck(ProjectedMaterializationStatus.MATERIALIZABLE)
                }
            }
        } catch (_: ProjectedTypeException) {
            ProjectedMaterializationCheck(ProjectedMaterializationStatus.OUTSIDE_SLICE)
        }
    }

    private fun genericShape(text: String): Pair<String, String>? {
        val match = genericHead.matchEntire(text) ?: return null
        val argument = match.groupValues[2].trim()
        if (argument.isEmpty() || ',' in argument) return null
        return match.groupValues[1] to argument
    }
}
