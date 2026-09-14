package de.kreisgeist.aidl.compiler.ir

import de.kreisgeist.aidl.compiler.frontend.AidlSourceProjector
import de.kreisgeist.aidl.compiler.frontend.ProjectedDeclaration
import de.kreisgeist.aidl.compiler.frontend.SourceProjection

class CanonicalIrDomainSliceException(message: String) : IllegalArgumentException(message)

data class CanonicalIrSourceSpan(
    val file: String,
    val startLine: Int,
    val startColumn: Int,
    val endLine: Int,
    val endColumn: Int,
) {
    fun stableSignature(): String = "$file:$startLine:$startColumn-$endLine:$endColumn"
}

sealed interface CanonicalIrTypeRef {
    fun stableSignature(): String
}

data class CanonicalIrScalarType(val name: String) : CanonicalIrTypeRef {
    override fun stableSignature(): String = "scalar:$name"
}

data class CanonicalIrNamedType(
    val declarationId: String,
    val fqn: String,
    val typeArguments: List<CanonicalIrTypeRef> = emptyList(),
) : CanonicalIrTypeRef {
    override fun stableSignature(): String = buildString {
        append("named:").append(declarationId).append(':').append(fqn)
        if (typeArguments.isNotEmpty()) {
            append('<').append(typeArguments.joinToString(",") { it.stableSignature() }).append('>')
        }
    }
}

data class CanonicalIrListType(val element: CanonicalIrTypeRef) : CanonicalIrTypeRef {
    override fun stableSignature(): String = "list<${element.stableSignature()}>"
}

data class CanonicalIrNullableType(val element: CanonicalIrTypeRef) : CanonicalIrTypeRef {
    override fun stableSignature(): String = "nullable<${element.stableSignature()}>"
}

data class CanonicalIrField(
    val name: String,
    val type: CanonicalIrTypeRef,
    val required: Boolean,
    val mutable: Boolean,
    val sensitive: Boolean,
    val generated: Boolean,
    val primary: Boolean,
    val concurrencyToken: Boolean,
    val onDelete: String,
) {
    fun stableSignature(): String = buildString {
        append(name).append('=').append(type.stableSignature())
        append("|required=").append(required)
        append("|mutable=").append(mutable)
        append("|sensitive=").append(sensitive)
        append("|generated=").append(generated)
        append("|primary=").append(primary)
        append("|concurrencyToken=").append(concurrencyToken)
        append("|onDelete=").append(onDelete)
    }
}

data class CanonicalIrDomainDeclaration(
    val kind: String,
    val declarationId: String,
    val fqn: String,
    val name: String,
    val ownerModule: String,
    val values: List<String> = emptyList(),
    val fields: List<CanonicalIrField> = emptyList(),
    val identityFields: List<String> = emptyList(),
) {
    fun stableSignature(): String = buildString {
        append(kind).append('|').append(declarationId).append('|').append(fqn)
        append('|').append(name).append('|').append(ownerModule)
        when (kind) {
            "enum" -> append("|values=").append(values.joinToString(","))
            "value" -> append("|fields=").append(fields.joinToString(";") { it.stableSignature() })
            "entity" -> {
                append("|fields=").append(fields.joinToString(";") { it.stableSignature() })
                append("|identityFields=").append(identityFields.joinToString(","))
            }
        }
    }
}

data class CanonicalIrSourceEntry(
    val nodePath: String,
    val originalDeclarationId: String,
    val span: CanonicalIrSourceSpan,
) {
    fun stableSignature(): String = "$nodePath|$originalDeclarationId|${span.stableSignature()}"
}

data class CanonicalIrDomainSlice(
    val declarations: List<CanonicalIrDomainDeclaration>,
    val sourceEntries: List<CanonicalIrSourceEntry>,
) {
    fun stableSignature(): String = buildString {
        declarations.forEachIndexed { index, declaration ->
            if (isNotEmpty()) append('\n')
            append("declaration|").append(index).append('|').append(declaration.stableSignature())
        }
        sourceEntries.forEach { entry ->
            if (isNotEmpty()) append('\n')
            append("sourceMap|").append(entry.stableSignature())
        }
    }
}

/**
 * First bounded M10.5-04 Canonical-IR construction slice.
 *
 * This projector owns only the schema-facing enum/value/entity declaration fragments and their
 * declaration source-map entries for the already Gate-03-covered SourceProjection surface.
 * Root IR envelope fields, semantic hashes, app/system/deployment declarations and semantic
 * queries remain Python reference/conformance-owned until separately migrated.
 */
object CanonicalIrDomainSliceProjector {
    private val scalarTypes = setOf(
        "string", "int", "decimal", "bool", "uuid", "date", "datetime", "duration",
        "revision", "email", "url", "bytes",
    )
    private val fieldModifiers = setOf(
        "required", "mutable", "sensitive", "generated", "primary", "concurrencyToken",
        "immutable", "default", "onDelete",
    )

    fun project(sourceId: String, path: String, source: String): CanonicalIrDomainSlice =
        project(AidlSourceProjector.project(sourceId, path, source), source)

    internal fun project(projection: SourceProjection, source: String): CanonicalIrDomainSlice {
        val module = projection.module
            ?: throw CanonicalIrDomainSliceException("canonical IR domain slice requires module")
        if (projection.imports.isNotEmpty()) {
            throw CanonicalIrDomainSliceException(
                "canonical IR domain slice does not own imported type resolution yet",
            )
        }
        val declarationByName = projection.declarations.associateBy { it.name }
        if (declarationByName.size != projection.declarations.size) {
            throw CanonicalIrDomainSliceException(
                "canonical IR domain slice requires unique local declaration names",
            )
        }

        val declarations = projection.declarations.map { declaration ->
            canonicalDeclaration(module, declaration, declarationByName)
        }
        val sourceEntries = projection.declarations.mapIndexed { index, declaration ->
            val id = declarationId(module, declaration.name)
            CanonicalIrSourceEntry(
                nodePath = "/declarations/$index",
                originalDeclarationId = id,
                span = CanonicalIrSourceSpan(
                    file = projection.path,
                    startLine = position(source, declaration.offset).first,
                    startColumn = position(source, declaration.offset).second,
                    endLine = position(source, declaration.endOffset).first,
                    endColumn = position(source, declaration.endOffset).second,
                ),
            )
        }
        return CanonicalIrDomainSlice(declarations, sourceEntries)
    }

    private fun canonicalDeclaration(
        module: String,
        declaration: ProjectedDeclaration,
        declarationByName: Map<String, ProjectedDeclaration>,
    ): CanonicalIrDomainDeclaration {
        val fqn = "$module.${declaration.name}"
        val id = declarationId(module, declaration.name)
        return when (declaration.kind) {
            "enum" -> CanonicalIrDomainDeclaration(
                kind = "enum",
                declarationId = id,
                fqn = fqn,
                name = declaration.name,
                ownerModule = module,
                values = enumValues(declaration.bodyTokens),
            )
            "value" -> CanonicalIrDomainDeclaration(
                kind = "value",
                declarationId = id,
                fqn = fqn,
                name = declaration.name,
                ownerModule = module,
                fields = fields(module, declaration.bodyTokens, declarationByName),
            )
            "entity" -> {
                val fields = fields(module, declaration.bodyTokens, declarationByName)
                val identities = fields.filter { it.primary }.map { it.name }
                    .ifEmpty { fields.filter { it.name == "id" }.map { it.name } }
                if (identities.isEmpty()) {
                    throw CanonicalIrDomainSliceException(
                        "entity '${declaration.name}' has no identity field",
                    )
                }
                CanonicalIrDomainDeclaration(
                    kind = "entity",
                    declarationId = id,
                    fqn = fqn,
                    name = declaration.name,
                    ownerModule = module,
                    fields = fields,
                    identityFields = identities,
                )
            }
            else -> throw CanonicalIrDomainSliceException(
                "unsupported canonical IR domain declaration '${declaration.kind}'",
            )
        }
    }

    private fun enumValues(tokens: List<String>): List<String> {
        val values = mutableListOf<String>()
        var expectValue = true
        for (token in tokens) {
            if (expectValue) {
                if (token == ",") {
                    throw CanonicalIrDomainSliceException("empty enum value")
                }
                values += token
                expectValue = false
            } else {
                if (token != ",") {
                    throw CanonicalIrDomainSliceException("unsupported enum value syntax")
                }
                expectValue = true
            }
        }
        if (values.isEmpty() || expectValue) {
            throw CanonicalIrDomainSliceException("enum requires non-empty simple values")
        }
        return values
    }

    private fun fields(
        module: String,
        tokens: List<String>,
        declarationByName: Map<String, ProjectedDeclaration>,
    ): List<CanonicalIrField> {
        val result = mutableListOf<CanonicalIrField>()
        var index = 0
        while (index < tokens.size) {
            if (tokens[index] == "field") index += 1
            if (index >= tokens.size) break
            val name = tokens[index++]
            if (tokens.getOrNull(index) != ":") {
                throw CanonicalIrDomainSliceException("field '$name' is missing ':'")
            }
            index += 1

            val typeTokens = mutableListOf<String>()
            var nesting = 0
            while (index < tokens.size) {
                val token = tokens[index]
                val startsNextField = nesting == 0 && (
                    token == "field" || tokens.getOrNull(index + 1) == ":"
                )
                if (nesting == 0 && (token in fieldModifiers || startsNextField)) break
                typeTokens += token
                if (token in setOf("[", "<", "(")) nesting += 1
                if (token in setOf("]", ">", ")")) nesting -= 1
                if (nesting < 0) {
                    throw CanonicalIrDomainSliceException("field '$name' has unbalanced type")
                }
                index += 1
            }
            if (typeTokens.isEmpty() || nesting != 0) {
                throw CanonicalIrDomainSliceException("field '$name' has invalid type")
            }

            var mutable = false
            var sensitive = false
            var generated = false
            var primary = false
            var concurrencyToken = false
            var onDelete = "none"
            while (index < tokens.size) {
                val token = tokens[index]
                val startsNextField = token == "field" || tokens.getOrNull(index + 1) == ":"
                if (startsNextField) break
                when (token) {
                    "required", "immutable" -> index += 1
                    "default" -> index = consumeDefaultValue(tokens, index + 1, name)
                    "mutable" -> { mutable = true; index += 1 }
                    "sensitive" -> { sensitive = true; index += 1 }
                    "generated" -> { generated = true; index += 1 }
                    "primary" -> { primary = true; index += 1 }
                    "concurrencyToken" -> { concurrencyToken = true; index += 1 }
                    "onDelete" -> {
                        onDelete = tokens.getOrNull(index + 1)
                            ?: throw CanonicalIrDomainSliceException("field '$name' lacks onDelete value")
                        if (onDelete !in setOf("restrict", "cascade", "setNull", "none")) {
                            throw CanonicalIrDomainSliceException(
                                "field '$name' has unsupported onDelete '$onDelete'",
                            )
                        }
                        index += 2
                    }
                    else -> throw CanonicalIrDomainSliceException(
                        "field '$name' has unsupported modifier '$token'",
                    )
                }
            }

            val rawType = typeTokens.joinToString("")
            result += CanonicalIrField(
                name = name,
                type = typeRef(module, rawType, declarationByName),
                required = !rawType.endsWith("?"),
                mutable = mutable,
                sensitive = sensitive,
                generated = generated,
                primary = primary,
                concurrencyToken = concurrencyToken,
                onDelete = onDelete,
            )
        }
        return result
    }

    private fun consumeDefaultValue(tokens: List<String>, start: Int, fieldName: String): Int {
        if (start >= tokens.size) {
            throw CanonicalIrDomainSliceException("field '$fieldName' lacks default value")
        }
        val token = tokens[start]
        val startsNextField = token == "field" || tokens.getOrNull(start + 1) == ":"
        if (token in fieldModifiers || startsNextField) {
            throw CanonicalIrDomainSliceException("field '$fieldName' lacks default value")
        }
        val closing = when (token) {
            "[" -> "]"
            "(" -> ")"
            "{" -> "}"
            else -> null
        }
        if (closing == null) return start + 1

        var depth = 0
        var index = start
        while (index < tokens.size) {
            when (tokens[index]) {
                token -> depth += 1
                closing -> depth -= 1
            }
            index += 1
            if (depth == 0) return index
            if (depth < 0) break
        }
        throw CanonicalIrDomainSliceException("field '$fieldName' has unbalanced default value")
    }

    private fun typeRef(
        module: String,
        raw: String,
        declarationByName: Map<String, ProjectedDeclaration>,
    ): CanonicalIrTypeRef {
        if (raw.endsWith("?")) {
            return CanonicalIrNullableType(typeRef(module, raw.dropLast(1), declarationByName))
        }
        if (raw.startsWith("[") && raw.endsWith("]")) {
            return CanonicalIrListType(typeRef(module, raw.substring(1, raw.length - 1), declarationByName))
        }
        if (raw in scalarTypes) return CanonicalIrScalarType(raw)
        if (!raw.matches(Regex("[A-Za-z_][A-Za-z0-9_]*"))) {
            throw CanonicalIrDomainSliceException("unsupported bounded type '$raw'")
        }
        val target = declarationByName[raw]
            ?: throw CanonicalIrDomainSliceException("unresolved local bounded type '$raw'")
        if (target.kind !in setOf("enum", "value", "entity")) {
            throw CanonicalIrDomainSliceException("unsupported bounded type target '$raw'")
        }
        val fqn = "$module.$raw"
        return CanonicalIrNamedType(
            declarationId = "$fqn@1",
            fqn = fqn,
        )
    }

    private fun declarationId(module: String, name: String): String = "$module.$name@1"

    private fun position(source: String, offset: Int): Pair<Int, Int> {
        if (offset !in 0..source.length) {
            throw CanonicalIrDomainSliceException("invalid source offset $offset")
        }
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
        return line to column
    }
}
