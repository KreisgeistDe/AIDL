package de.kreisgeist.aidl.compiler.jvm

import de.kreisgeist.aidl.compiler.contract.DeterministicJson
import de.kreisgeist.aidl.compiler.contract.ParityContract

object JvmCompilerAdapter {
    fun contractSnapshotJson(): String = DeterministicJson.objectOf(ParityContract.contractSnapshot())
}
