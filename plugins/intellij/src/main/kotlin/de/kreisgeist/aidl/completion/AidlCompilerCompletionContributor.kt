package de.kreisgeist.aidl.completion

import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionProvider
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.CompletionType
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.patterns.PlatformPatterns
import com.intellij.util.ProcessingContext
import de.kreisgeist.aidl.AidlLanguage
import java.nio.file.Path

class AidlCompilerCompletionContributor : CompletionContributor() {
    init {
        extend(
            CompletionType.BASIC,
            PlatformPatterns.psiElement().withLanguage(AidlLanguage),
            object : CompletionProvider<CompletionParameters>() {
                override fun addCompletions(
                    parameters: CompletionParameters,
                    context: ProcessingContext,
                    result: CompletionResultSet,
                ) {
                    val projectPath = parameters.position.project.basePath?.let(Path::of) ?: return
                    val sourcePath = parameters.originalFile.virtualFile?.path?.let(Path::of) ?: return
                    val completion = AidlCompilerCompletionAdapter().complete(
                        projectPath = projectPath,
                        sourcePath = sourcePath,
                        offset = parameters.offset,
                    ) as? AidlCompletionResult.Resolved ?: return

                    val target = if (completion.prefix.isEmpty()) result else result.withPrefixMatcher(completion.prefix)
                    completion.candidates.forEach { candidate ->
                        target.addElement(
                            LookupElementBuilder.create(candidate.insertText)
                                .withPresentableText(candidate.displayText)
                                .withTypeText("${candidate.kind} · ${candidate.origin}", true)
                                .withTailText(" — ${candidate.fullyQualifiedName}", true),
                        )
                    }
                }
            },
        )
    }
}
