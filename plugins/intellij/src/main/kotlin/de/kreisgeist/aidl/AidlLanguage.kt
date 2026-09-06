package de.kreisgeist.aidl

import com.intellij.lang.Language

object AidlLanguage : Language("AIDL") {
    private fun readResolve(): Any = AidlLanguage
}
