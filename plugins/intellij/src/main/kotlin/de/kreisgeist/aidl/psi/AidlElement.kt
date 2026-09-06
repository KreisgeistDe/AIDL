package de.kreisgeist.aidl.psi

import com.intellij.extapi.psi.ASTWrapperPsiElement
import com.intellij.lang.ASTNode

open class AidlElement(node: ASTNode) : ASTWrapperPsiElement(node)
