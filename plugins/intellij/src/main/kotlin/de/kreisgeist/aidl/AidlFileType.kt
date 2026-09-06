package de.kreisgeist.aidl

import com.intellij.openapi.fileTypes.LanguageFileType
import javax.swing.Icon

class AidlFileType private constructor() : LanguageFileType(AidlLanguage) {
    override fun getName() = "AIDL"

    override fun getDescription() = "AIDL file"

    override fun getDefaultExtension() = "aidl"

    override fun getIcon(): Icon? = null

    companion object {
        @JvmField
        val INSTANCE = AidlFileType()
    }
}
