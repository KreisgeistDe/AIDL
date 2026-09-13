package de.kreisgeist.aidl.compiler.native

import de.kreisgeist.aidl.compiler.contract.CommonCompilerBoundary
import de.kreisgeist.aidl.compiler.contract.ParityContract

fun main() {
    println(CommonCompilerBoundary.deterministicContractSnapshot(ParityContract))
}
