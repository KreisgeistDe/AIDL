package de.kreisgeist.aidl.references

import com.intellij.patterns.PlatformPatterns.psiElement
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiReference
import com.intellij.psi.PsiReferenceContributor
import com.intellij.psi.PsiReferenceProvider
import com.intellij.psi.PsiReferenceRegistrar
import com.intellij.util.ProcessingContext
import de.kreisgeist.aidl.AidlLanguage
import de.kreisgeist.aidl.psi.AidlTokenSets
import de.kreisgeist.aidl.psi.AidlTypes

class AidlReferenceContributor : PsiReferenceContributor() {
    override fun registerReferenceProviders(registrar: PsiReferenceRegistrar) {
        registrar.registerReferenceProvider(
            psiElement().withLanguage(AidlLanguage),
            object : PsiReferenceProvider() {
                override fun getReferencesByElement(element: PsiElement, context: ProcessingContext): Array<PsiReference> {
                    if (!AidlPsiUtil.isNameToken(element)) {
                        return PsiReference.EMPTY_ARRAY
                    }
                    if (AidlPsiUtil.isDeclarationName(element)) {
                        return PsiReference.EMPTY_ARRAY
                    }
                    if (
                        element.node?.elementType in AidlTokenSets.KEYWORDS &&
                        !AidlPsiUtil.isImportPath(element) &&
                        !AidlPsiUtil.isModuleName(element)
                    ) {
                        return PsiReference.EMPTY_ARRAY
                    }
                    if (element.node?.elementType == AidlTypes.PROPERTY_NAME && !AidlPsiUtil.isImportPath(element)) {
                        return PsiReference.EMPTY_ARRAY
                    }
                    return arrayOf(AidlReference(element))
                }
            },
        )
    }
}
