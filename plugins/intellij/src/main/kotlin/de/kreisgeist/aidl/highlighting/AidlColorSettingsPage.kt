package de.kreisgeist.aidl.highlighting

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import javax.swing.Icon

class AidlColorSettingsPage : ColorSettingsPage {
    override fun getIcon(): Icon? = null

    override fun getHighlighter(): SyntaxHighlighter = AidlSyntaxHighlighter()

    override fun getDemoText(): String = """
        module examples.petstore
        import examples.petstore.domain.*

        app Petstore {
          profile core version 1
          profile web version 1
          profile distributed version 1
          profile cloud version 1
          system PetstoreSystem
          frontend PetstoreWeb
          api PetstoreApi
          defaultDeployment local
        }

        @ownedBy("pets")
        entity Pet {
          id: uuid primary generated
          name: string required
          weight: decimal(0.1..200.0)
          adopted: bool default false
          invariant hasName: name != ""
        }

        query findPets(status: string?) -> [Pet] {
          auth: public
          read: Pets.filter(p => p.status == status)
          cache: public ttl 30s
        }
    """.trimIndent()

    override fun getAdditionalHighlightingTagToDescriptorMap(): Map<String, TextAttributesKey>? = null

    override fun getAttributeDescriptors(): Array<AttributesDescriptor> = DESCRIPTORS

    override fun getColorDescriptors(): Array<ColorDescriptor> = ColorDescriptor.EMPTY_ARRAY

    override fun getDisplayName() = "AIDL"

    companion object {
        private val DESCRIPTORS = arrayOf(
            AttributesDescriptor("Keyword", AidlSyntaxHighlighter.KEYWORD),
            AttributesDescriptor("Declaration keyword", AidlSyntaxHighlighter.DECLARATION_KEYWORD),
            AttributesDescriptor("Scalar type", AidlSyntaxHighlighter.SCALAR_TYPE),
            AttributesDescriptor("Property name", AidlSyntaxHighlighter.PROPERTY_NAME),
            AttributesDescriptor("Identifier", AidlSyntaxHighlighter.IDENTIFIER),
            AttributesDescriptor("Type name", AidlSyntaxHighlighter.TYPE_NAME),
            AttributesDescriptor("String", AidlSyntaxHighlighter.STRING),
            AttributesDescriptor("Number", AidlSyntaxHighlighter.NUMBER),
            AttributesDescriptor("Comment", AidlSyntaxHighlighter.COMMENT),
            AttributesDescriptor("Annotation", AidlSyntaxHighlighter.ANNOTATION),
            AttributesDescriptor("Operator", AidlSyntaxHighlighter.OPERATOR),
            AttributesDescriptor("Braces and brackets", AidlSyntaxHighlighter.BRACES),
            AttributesDescriptor("Bad character", AidlSyntaxHighlighter.BAD_CHARACTER),
        )
    }
}
