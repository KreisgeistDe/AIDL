package de.kreisgeist.aidl.compiler.jvm

import de.kreisgeist.aidl.compiler.contract.CommonCompilerBoundary
import de.kreisgeist.aidl.compiler.contract.ParityContract

object JvmCompilerAdapter {
    fun contractSnapshotJson(): String = CommonCompilerBoundary.deterministicContractSnapshot(ParityContract)
}
