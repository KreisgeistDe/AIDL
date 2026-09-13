package de.kreisgeist.aidl.compiler.contract

object DeterministicJson {
    fun objectOf(values: Map<String, String>): String = values
        .toSortedMap()
        .entries
        .joinToString(prefix = "{", postfix = "}", separator = ",") { (key, value) ->
            "${quote(key)}:${quote(value)}"
        }

    private fun quote(value: String): String = buildString {
        append('"')
        value.forEach { ch ->
            when {
                ch == '"' -> append("\\\"")
                ch == '\\' -> append("\\\\")
                ch.code < 0x20 -> append("\\u" + ch.code.toString(16).padStart(4, '0'))
                else -> append(ch)
            }
        }
        append('"')
    }
}
