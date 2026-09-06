package de.kreisgeist.aidl

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.psi.FileViewProvider

class AidlFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, AidlLanguage) {
    override fun getFileType() = AidlFileType.INSTANCE

    override fun toString() = "AIDL file"
}
