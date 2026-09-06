package de.kreisgeist.aidl.references

import com.intellij.psi.PsiElement

data class AidlDefinition(
    val name: String,
    val qualifiedName: String?,
    val element: PsiElement,
)
