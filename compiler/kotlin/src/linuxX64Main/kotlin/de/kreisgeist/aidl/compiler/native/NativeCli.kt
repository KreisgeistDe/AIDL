package de.kreisgeist.aidl.compiler.native

import de.kreisgeist.aidl.compiler.contract.DeterministicJson
import de.kreisgeist.aidl.compiler.contract.ParityContract

fun main() {
    println(DeterministicJson.objectOf(ParityContract.contractSnapshot()))
}
