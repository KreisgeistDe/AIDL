package de.kreisgeist.aidl.compiler.frontend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class MaterializationLocationParityTest {
    private val consumerSource = """
        module demo.consumer
        import demo.shared.*
        query myQuery(id: string) -> string {}
        alias QueryTarget = myQuery
        alias MissingTarget = Missing
        alias AmbiguousTarget = Duplicate
        alias BindingCoreGenericTarget = Page<myQuery>
        alias AcceptedTarget = PublicEntity
    """.trimIndent() + "\n"

    private fun resolver(): ProjectNameResolver {
        val consumerProjection = AidlSourceProjector.project(
            """
                module demo.consumer
                import demo.shared.*
                entity Holder {}
            """.trimIndent(),
        )
        val consumer = ProjectedDocument(
            "consumer.aidl",
            consumerProjection.copy(
                declarations = consumerProjection.declarations +
                    ProjectedDeclaration("query", "myQuery", false, emptyList()),
            ),
        )
        val providerA = ProjectedDocument(
            "provider-a.aidl",
            AidlSourceProjector.project(
                """
                    module demo.shared
                    export enum PublicEnum {}
                    export entity PublicEntity {}
                    export entity Duplicate {}
                """.trimIndent(),
            ),
        )
        val providerB = ProjectedDocument(
            "provider-b.aidl",
            AidlSourceProjector.project(
                """
                    module demo.shared
                    export enum Duplicate {}
                """.trimIndent(),
            ),
        )
        return ProjectNameResolver.fromProjectedDocuments(listOf(consumer, providerA, providerB))
    }

    private fun anchored(typeSource: String): ProjectedMaterializationCheck =
        ProjectedMaterializationChecker.checkAt(
            sourceId = "consumer.aidl",
            sourceText = consumerSource,
            diagnosticOffset = consumerSource.indexOf("alias QueryTarget"),
            typeSource = typeSource,
            resolver = resolver(),
        )

    private fun render(label: String, check: ProjectedMaterializationCheck): String {
        val location = check.location
        return listOf(
            label,
            check.status.toString(),
            check.diagnosticCode.orEmpty(),
            check.sourcePath.orEmpty(),
            location?.line?.toString().orEmpty(),
            location?.column?.toString().orEmpty(),
            location?.offset?.toString().orEmpty(),
        ).joinToString("|")
    }

    private fun signature(): String = listOf(
        render("query", anchored("myQuery")),
        render("missing", anchored("Missing")),
        render("ambiguous", anchored("Duplicate")),
        render("binding-core-generic", anchored("Page<myQuery>")),
        render("accepted", anchored("PublicEntity")),
    ).joinToString("\n")

    @Test
    fun materializationDiagnosticLocationsMatchPinnedPresenceAndAbsenceDeterministically() {
        val expected = """
            query|REJECTED|AIDL-T005|consumer.aidl|4|1|81
            missing|UNRESOLVED|AIDL-T001||||
            ambiguous|AMBIGUOUS|CORE-S023||||
            binding-core-generic|OUTSIDE_SLICE|||||
            accepted|MATERIALIZABLE|||||
        """.trimIndent()
        assertEquals(expected, signature())
        assertEquals(signature(), signature())
    }

    @Test
    fun materializationOwnsOnlyAidlT005LocationProjection() {
        val query = anchored("myQuery")
        assertEquals("consumer.aidl", query.sourcePath)
        assertEquals(ProjectedSourceLocation(line = 4, column = 1, offset = 81), query.location)

        for (type in listOf("Missing", "Duplicate", "Page<myQuery>", "PublicEntity")) {
            val check = anchored(type)
            assertEquals(null, check.sourcePath)
            assertEquals(null, check.location)
        }
    }

    @Test
    fun diagnosticOffsetMustBelongToSourceText() {
        assertFailsWith<IllegalArgumentException> {
            ProjectedMaterializationChecker.checkAt(
                sourceId = "consumer.aidl",
                sourceText = consumerSource,
                diagnosticOffset = consumerSource.length + 1,
                typeSource = "myQuery",
                resolver = resolver(),
            )
        }
    }
}
