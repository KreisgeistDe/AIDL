package de.kreisgeist.aidl.compiler.jvm

import kotlin.test.Test
import kotlin.test.assertEquals
import de.kreisgeist.aidl.compiler.contract.DeterministicJson
import de.kreisgeist.aidl.compiler.contract.ParityContract

class JvmCompilerAdapterTest {
    @Test
    fun delegatesToCommonContractWithoutAdapterSemantics() {
        assertEquals(
            DeterministicJson.objectOf(ParityContract.contractSnapshot()),
            JvmCompilerAdapter.contractSnapshotJson(),
        )
    }
}
