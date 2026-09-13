package de.kreisgeist.aidl.compiler.jvm

import de.kreisgeist.aidl.compiler.contract.CommonCompilerBoundary

object JvmCompilerAdapter {
    fun contractSnapshotJson(): String = CommonCompilerBoundary.deterministicContractSnapshot()
}
