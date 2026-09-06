package de.kreisgeist.aidl.psi

import com.intellij.psi.tree.IElementType

object AidlTypes {
    val MODULE_DECLARATION: IElementType = AidlElementType("MODULE_DECLARATION")
    val IMPORT_DECLARATION: IElementType = AidlElementType("IMPORT_DECLARATION")
    val EXPORT_DECLARATION: IElementType = AidlElementType("EXPORT_DECLARATION")
    val DECLARATION: IElementType = AidlElementType("DECLARATION")
    val DECLARATION_NAME: IElementType = AidlElementType("DECLARATION_NAME")
    val MODULE_NAME: IElementType = AidlElementType("MODULE_NAME")
    val IMPORT_PATH: IElementType = AidlElementType("IMPORT_PATH")
    val ANNOTATION: IElementType = AidlElementType("ANNOTATION")

    val IDENTIFIER: IElementType = AidlTokenType("IDENTIFIER")
    val TYPE_NAME: IElementType = AidlTokenType("TYPE_NAME")
    val PROPERTY_NAME: IElementType = AidlTokenType("PROPERTY_NAME")
    val ANNOTATION_NAME: IElementType = AidlTokenType("ANNOTATION_NAME")
    val INTEGER: IElementType = AidlTokenType("INTEGER")
    val DECIMAL_LITERAL: IElementType = AidlTokenType("DECIMAL_LITERAL")
    val PERCENTAGE: IElementType = AidlTokenType("PERCENTAGE")
    val DURATION_LITERAL: IElementType = AidlTokenType("DURATION_LITERAL")
    val BYTE_LITERAL: IElementType = AidlTokenType("BYTE_LITERAL")
    val CPU_LITERAL: IElementType = AidlTokenType("CPU_LITERAL")
    val STRING: IElementType = AidlTokenType("STRING")
    val REGEX: IElementType = AidlTokenType("REGEX")
    val NEWLINE: IElementType = AidlTokenType("NEWLINE")
    val LINE_COMMENT: IElementType = AidlTokenType("LINE_COMMENT")
    val BLOCK_COMMENT_START: IElementType = AidlTokenType("BLOCK_COMMENT_START")
    val BLOCK_COMMENT_CONTENT: IElementType = AidlTokenType("BLOCK_COMMENT_CONTENT")
    val BLOCK_COMMENT_END: IElementType = AidlTokenType("BLOCK_COMMENT_END")

    val SPREAD: IElementType = AidlTokenType("SPREAD")
    val ARROW: IElementType = AidlTokenType("ARROW")
    val RANGE: IElementType = AidlTokenType("RANGE")
    val EQEQ: IElementType = AidlTokenType("EQEQ")
    val NEQ: IElementType = AidlTokenType("NEQ")
    val LTE: IElementType = AidlTokenType("LTE")
    val GTE: IElementType = AidlTokenType("GTE")
    val LPAREN: IElementType = AidlTokenType("LPAREN")
    val RPAREN: IElementType = AidlTokenType("RPAREN")
    val LBRACE: IElementType = AidlTokenType("LBRACE")
    val RBRACE: IElementType = AidlTokenType("RBRACE")
    val LBRACKET: IElementType = AidlTokenType("LBRACKET")
    val RBRACKET: IElementType = AidlTokenType("RBRACKET")
    val LT: IElementType = AidlTokenType("LT")
    val GT: IElementType = AidlTokenType("GT")
    val COMMA: IElementType = AidlTokenType("COMMA")
    val COLON: IElementType = AidlTokenType("COLON")
    val DOT: IElementType = AidlTokenType("DOT")
    val QUESTION: IElementType = AidlTokenType("QUESTION")
    val AT: IElementType = AidlTokenType("AT")
    val EQ: IElementType = AidlTokenType("EQ")
    val PLUS: IElementType = AidlTokenType("PLUS")
    val MINUS: IElementType = AidlTokenType("MINUS")
    val STAR: IElementType = AidlTokenType("STAR")
    val SLASH: IElementType = AidlTokenType("SLASH")
    val PERCENT: IElementType = AidlTokenType("PERCENT")
    val AMP: IElementType = AidlTokenType("AMP")

    val MODULE_KEYWORD = keywordToken("module")
    val IMPORT_KEYWORD = keywordToken("import")
    val EXPORT_KEYWORD = keywordToken("export")
    val APP_KEYWORD = keywordToken("app")
    val AUTH_KEYWORD = keywordToken("auth")
    val A11Y_KEYWORD = keywordToken("a11y")
    val PRIVACY_KEYWORD = keywordToken("privacy")
    val ENUM_KEYWORD = keywordToken("enum")
    val ALIAS_KEYWORD = keywordToken("alias")
    val OPAQUE_KEYWORD = keywordToken("opaque")
    val VALUE_KEYWORD = keywordToken("value")
    val UNION_KEYWORD = keywordToken("union")
    val ERROR_KEYWORD = keywordToken("error")
    val ENTITY_KEYWORD = keywordToken("entity")
    val VIEW_KEYWORD = keywordToken("view")
    val API_KEYWORD = keywordToken("api")
    val POLICY_KEYWORD = keywordToken("policy")
    val QUERY_KEYWORD = keywordToken("query")
    val MUTATION_KEYWORD = keywordToken("mutation")
    val EVENT_KEYWORD = keywordToken("event")
    val TOPIC_KEYWORD = keywordToken("topic")
    val QUEUE_KEYWORD = keywordToken("queue")
    val CONSUMER_KEYWORD = keywordToken("consumer")
    val PROJECTION_KEYWORD = keywordToken("projection")
    val WORKFLOW_KEYWORD = keywordToken("workflow")
    val SAGA_KEYWORD = keywordToken("saga")
    val TASK_KEYWORD = keywordToken("task")
    val SCHEDULE_KEYWORD = keywordToken("schedule")
    val SYSTEM_KEYWORD = keywordToken("system")
    val SERVICE_KEYWORD = keywordToken("service")
    val CLIENT_KEYWORD = keywordToken("client")
    val TENANT_KEYWORD = keywordToken("tenant")
    val CHANNEL_KEYWORD = keywordToken("channel")
    val RESOURCE_KEYWORD = keywordToken("resource")
    val MEDIA_KEYWORD = keywordToken("media")
    val RENDITION_KEYWORD = keywordToken("rendition")
    val SYNC_KEYWORD = keywordToken("sync")
    val MIGRATION_KEYWORD = keywordToken("migration")
    val DEPLOYMENT_KEYWORD = keywordToken("deployment")
    val FRONTEND_KEYWORD = keywordToken("frontend")
    val THEME_KEYWORD = keywordToken("theme")
    val COMPONENT_KEYWORD = keywordToken("component")
    val PAGE_KEYWORD = keywordToken("page")
    val FORM_KEYWORD = keywordToken("form")
    val ACTION_KEYWORD = keywordToken("action")
    val SYNC_STATUS_KEYWORD = keywordToken("syncStatus")
    val SEO_KEYWORD = keywordToken("seo")
    val NATIVE_KEYWORD = keywordToken("native")
    val FUNCTION_KEYWORD = keywordToken("function")
    val FIXTURE_KEYWORD = keywordToken("fixture")
    val TEST_KEYWORD = keywordToken("test")
    val SCENARIO_KEYWORD = keywordToken("scenario")

    val STRING_TYPE_KEYWORD = keywordToken("string")
    val INT_KEYWORD = keywordToken("int")
    val DECIMAL_KEYWORD = keywordToken("decimal")
    val BOOL_KEYWORD = keywordToken("bool")
    val UUID_KEYWORD = keywordToken("uuid")
    val DATE_KEYWORD = keywordToken("date")
    val DATETIME_KEYWORD = keywordToken("datetime")
    val DURATION_KEYWORD = keywordToken("duration")
    val REVISION_KEYWORD = keywordToken("revision")
    val EMAIL_KEYWORD = keywordToken("email")
    val URL_KEYWORD = keywordToken("url")
    val BYTES_KEYWORD = keywordToken("bytes")

    val VERSION_KEYWORD = keywordToken("version")
    val LANGUAGE_KEYWORD = keywordToken("language")
    val PROFILE_KEYWORD = keywordToken("profile")
    val DEFAULT_DEPLOYMENT_KEYWORD = keywordToken("defaultDeployment")
    val COMPATIBILITY_KEYWORD = keywordToken("compatibility")
    val REQUIRED_KEYWORD = keywordToken("required")
    val PRIMARY_KEYWORD = keywordToken("primary")
    val GENERATED_KEYWORD = keywordToken("generated")
    val CLIENT_GENERATED_KEYWORD = keywordToken("clientGenerated")
    val IMMUTABLE_KEYWORD = keywordToken("immutable")
    val MUTABLE_KEYWORD = keywordToken("mutable")
    val SENSITIVE_KEYWORD = keywordToken("sensitive")
    val UNIQUE_KEYWORD = keywordToken("unique")
    val CONCURRENCY_TOKEN_KEYWORD = keywordToken("concurrencyToken")
    val DEFAULT_KEYWORD = keywordToken("default")
    val ON_DELETE_KEYWORD = keywordToken("onDelete")
    val RESTRICT_KEYWORD = keywordToken("restrict")
    val CASCADE_KEYWORD = keywordToken("cascade")
    val NULLIFY_KEYWORD = keywordToken("nullify")
    val INVARIANT_KEYWORD = keywordToken("invariant")
    val INDEX_KEYWORD = keywordToken("index")
    val FROM_KEYWORD = keywordToken("from")
    val FOR_KEYWORD = keywordToken("for")
    val TARGET_KEYWORD = keywordToken("target")
    val TRANSPORT_KEYWORD = keywordToken("transport")
    val REST_KEYWORD = keywordToken("rest")
    val RPC_KEYWORD = keywordToken("rpc")
    val GRAPHQL_KEYWORD = keywordToken("graphql")
    val OPERATIONS_KEYWORD = keywordToken("operations")
    val ERRORS_KEYWORD = keywordToken("errors")
    val RATE_LIMIT_KEYWORD = keywordToken("rateLimit")
    val ALLOW_KEYWORD = keywordToken("allow")
    val AUTHENTICATED_KEYWORD = keywordToken("authenticated")
    val PUBLIC_KEYWORD = keywordToken("public")
    val READ_KEYWORD = keywordToken("read")
    val CONSISTENCY_KEYWORD = keywordToken("consistency")
    val CACHE_KEYWORD = keywordToken("cache")
    val TIMEOUT_KEYWORD = keywordToken("timeout")
    val AUTHORIZE_KEYWORD = keywordToken("authorize")
    val REMOTE_KEYWORD = keywordToken("remote")
    val ELSE_KEYWORD = keywordToken("else")
    val IDEMPOTENCY_KEYWORD = keywordToken("idempotency")
    val TRANSACTION_KEYWORD = keywordToken("transaction")
    val ISOLATION_KEYWORD = keywordToken("isolation")
    val REQUIRE_KEYWORD = keywordToken("require")
    val WRITE_KEYWORD = keywordToken("write")
    val EXPECT_KEYWORD = keywordToken("expect")
    val EMIT_KEYWORD = keywordToken("emit")
    val TO_KEYWORD = keywordToken("to")
    val VIA_KEYWORD = keywordToken("via")
    val OUTBOX_KEYWORD = keywordToken("outbox")
    val WHEN_KEYWORD = keywordToken("when")
    val RETURN_KEYWORD = keywordToken("return")
    val RETRY_KEYWORD = keywordToken("retry")
    val RETAIN_KEYWORD = keywordToken("retain")
    val STEP_KEYWORD = keywordToken("step")
    val APPROVAL_KEYWORD = keywordToken("approval")
    val BUDGET_KEYWORD = keywordToken("budget")
    val CALL_KEYWORD = keywordToken("call")
    val START_KEYWORD = keywordToken("start")
    val DELIVERY_KEYWORD = keywordToken("delivery")
    val PARTITION_KEYWORD = keywordToken("partition")
    val ORDERING_KEYWORD = keywordToken("ordering")
    val DEAD_LETTER_KEYWORD = keywordToken("deadLetter")
    val MESSAGE_KEYWORD = keywordToken("message")
    val MESSAGES_KEYWORD = keywordToken("messages")
    val EVENTS_KEYWORD = keywordToken("events")
    val MODE_KEYWORD = keywordToken("mode")
    val AUTHORITY_KEYWORD = keywordToken("authority")
    val SCOPE_KEYWORD = keywordToken("scope")
    val LOCAL_STORE_KEYWORD = keywordToken("localStore")
    val SERVER_STORE_KEYWORD = keywordToken("serverStore")
    val OPERATION_LOG_KEYWORD = keywordToken("operationLog")
    val PUSH_KEYWORD = keywordToken("push")
    val PULL_KEYWORD = keywordToken("pull")
    val CHANGES_KEYWORD = keywordToken("changes")
    val DELETE_KEYWORD = keywordToken("delete")
    val TOMBSTONE_KEYWORD = keywordToken("tombstone")
    val CONFLICT_KEYWORD = keywordToken("conflict")
    val MERGE_KEYWORD = keywordToken("merge")
    val FIELD_KEYWORD = keywordToken("field")
    val GROUP_KEYWORD = keywordToken("group")
    val FIELDS_KEYWORD = keywordToken("fields")
    val ROUTE_KEYWORD = keywordToken("route")
    val RENDERING_KEYWORD = keywordToken("rendering")
    val LOCALE_KEYWORD = keywordToken("locale")
    val FALLBACK_KEYWORD = keywordToken("fallback")
    val NAVIGATION_KEYWORD = keywordToken("navigation")
    val TITLE_KEYWORD = keywordToken("title")
    val MAIN_KEYWORD = keywordToken("main")
    val DATA_KEYWORD = keywordToken("data")
    val STATE_KEYWORD = keywordToken("state")
    val URL_STATE_KEYWORD = keywordToken("urlState")
    val SESSION_STATE_KEYWORD = keywordToken("sessionState")
    val LOCAL_STATE_KEYWORD = keywordToken("localState")
    val REPLICATED_STATE_KEYWORD = keywordToken("replicatedState")
    val LOADING_KEYWORD = keywordToken("loading")
    val EMPTY_KEYWORD = keywordToken("empty")
    val STALE_KEYWORD = keywordToken("stale")
    val REFRESHING_KEYWORD = keywordToken("refreshing")
    val SUBMIT_KEYWORD = keywordToken("submit")
    val PENDING_KEYWORD = keywordToken("pending")
    val SUCCESS_KEYWORD = keywordToken("success")
    val FAILURE_KEYWORD = keywordToken("failure")
    val ENQUEUE_KEYWORD = keywordToken("enqueue")
    val OPTIMISTIC_KEYWORD = keywordToken("optimistic")
    val ROLLBACK_KEYWORD = keywordToken("rollback")
    val REJECTED_KEYWORD = keywordToken("rejected")
    val TRUE_KEYWORD = keywordToken("true")
    val FALSE_KEYWORD = keywordToken("false")
    val NULL_KEYWORD = keywordToken("null")
    val AND_KEYWORD = keywordToken("and")
    val OR_KEYWORD = keywordToken("or")
    val NOT_KEYWORD = keywordToken("not")
    val IN_KEYWORD = keywordToken("in")
    val REF_KEYWORD = keywordToken("ref")

    val GRAMMAR_KEYWORD_TOKENS: Collection<IElementType>
        get() = grammarKeywords.values

    fun keyword(text: String, declarationKeywordPosition: Boolean): IElementType? =
        expressionKeywords[text]
            ?: scalarKeywords[text]
            ?: forcedKeywords[text]
            ?: (if (declarationKeywordPosition) declarationKeywords[text] else null)
            ?: grammarKeywords[text]

    fun isPropertyName(text: String): Boolean = text in propertyNames

    private fun keywordToken(text: String): IElementType = AidlTokenType(text)

    private val declarationKeywords = mapOf(
        "module" to MODULE_KEYWORD,
        "import" to IMPORT_KEYWORD,
        "export" to EXPORT_KEYWORD,
        "app" to APP_KEYWORD,
        "auth" to AUTH_KEYWORD,
        "a11y" to A11Y_KEYWORD,
        "privacy" to PRIVACY_KEYWORD,
        "enum" to ENUM_KEYWORD,
        "alias" to ALIAS_KEYWORD,
        "opaque" to OPAQUE_KEYWORD,
        "value" to VALUE_KEYWORD,
        "union" to UNION_KEYWORD,
        "error" to ERROR_KEYWORD,
        "entity" to ENTITY_KEYWORD,
        "view" to VIEW_KEYWORD,
        "api" to API_KEYWORD,
        "policy" to POLICY_KEYWORD,
        "query" to QUERY_KEYWORD,
        "mutation" to MUTATION_KEYWORD,
        "event" to EVENT_KEYWORD,
        "topic" to TOPIC_KEYWORD,
        "queue" to QUEUE_KEYWORD,
        "consumer" to CONSUMER_KEYWORD,
        "projection" to PROJECTION_KEYWORD,
        "workflow" to WORKFLOW_KEYWORD,
        "saga" to SAGA_KEYWORD,
        "task" to TASK_KEYWORD,
        "schedule" to SCHEDULE_KEYWORD,
        "system" to SYSTEM_KEYWORD,
        "service" to SERVICE_KEYWORD,
        "client" to CLIENT_KEYWORD,
        "tenant" to TENANT_KEYWORD,
        "channel" to CHANNEL_KEYWORD,
        "resource" to RESOURCE_KEYWORD,
        "media" to MEDIA_KEYWORD,
        "rendition" to RENDITION_KEYWORD,
        "sync" to SYNC_KEYWORD,
        "migration" to MIGRATION_KEYWORD,
        "deployment" to DEPLOYMENT_KEYWORD,
        "frontend" to FRONTEND_KEYWORD,
        "theme" to THEME_KEYWORD,
        "component" to COMPONENT_KEYWORD,
        "page" to PAGE_KEYWORD,
        "form" to FORM_KEYWORD,
        "action" to ACTION_KEYWORD,
        "syncStatus" to SYNC_STATUS_KEYWORD,
        "seo" to SEO_KEYWORD,
        "native" to NATIVE_KEYWORD,
        "fixture" to FIXTURE_KEYWORD,
        "test" to TEST_KEYWORD,
        "scenario" to SCENARIO_KEYWORD,
    )

    private val scalarKeywords = mapOf(
        "string" to STRING_TYPE_KEYWORD,
        "int" to INT_KEYWORD,
        "decimal" to DECIMAL_KEYWORD,
        "bool" to BOOL_KEYWORD,
        "uuid" to UUID_KEYWORD,
        "date" to DATE_KEYWORD,
        "datetime" to DATETIME_KEYWORD,
        "duration" to DURATION_KEYWORD,
        "revision" to REVISION_KEYWORD,
        "email" to EMAIL_KEYWORD,
        "url" to URL_KEYWORD,
        "bytes" to BYTES_KEYWORD,
    )

    private val expressionKeywords = mapOf(
        "true" to TRUE_KEYWORD,
        "false" to FALSE_KEYWORD,
        "null" to NULL_KEYWORD,
        "and" to AND_KEYWORD,
        "or" to OR_KEYWORD,
        "not" to NOT_KEYWORD,
        "in" to IN_KEYWORD,
        "ref" to REF_KEYWORD,
    )

    private val forcedKeywords = mapOf(
        "version" to VERSION_KEYWORD,
    )

    private val grammarKeywords = setOf(
        "a11y",
        "action",
        "addWinsSet",
        "after",
        "alias",
        "all",
        "allow",
        "api",
        "apis",
        "app",
        "approval",
        "asc",
        "atLeastOnce",
        "atMostOnce",
        "attempts",
        "audit",
        "auth",
        "authenticated",
        "authority",
        "authorize",
        "backfill",
        "backoff",
        "backward",
        "basePath",
        "bind",
        "blob",
        "boundedStaleness",
        "budget",
        "by",
        "cache",
        "call",
        "cascade",
        "catchUp",
        "cdn",
        "changes",
        "channel",
        "channels",
        "checkpoint",
        "client",
        "clientGenerated",
        "clock",
        "code",
        "colocate",
        "comparable",
        "compatibility",
        "compensate",
        "component",
        "concurrencyToken",
        "configRef",
        "conflict",
        "consistency",
        "consumer",
        "contract",
        "counter",
        "cron",
        "custom",
        "data",
        "deadLetter",
        "default",
        "defaultDeployment",
        "defaults",
        "delete",
        "delivery",
        "dependsOn",
        "deployReaders",
        "deployment",
        "desc",
        "document",
        "else",
        "emit",
        "empty",
        "enqueue",
        "entity",
        "entityView",
        "enum",
        "error",
        "errors",
        "event",
        "events",
        "eventual",
        "evolves",
        "execution",
        "expand",
        "expect",
        "exponential",
        "export",
        "exposes",
        "fail",
        "failure",
        "fallback",
        "field",
        "fields",
        "fixture",
        "for",
        "form",
        "forward",
        "from",
        "frontend",
        "full",
        "function",
        "generated",
        "global",
        "graphql",
        "group",
        "hashable",
        "httpStatus",
        "idempotency",
        "immediate",
        "immutable",
        "import",
        "index",
        "into",
        "invariant",
        "isolation",
        "key",
        "keyValue",
        "language",
        "latest",
        "lease",
        "loading",
        "localState",
        "localStore",
        "locale",
        "localizationKey",
        "lock",
        "lww",
        "main",
        "manual",
        "map",
        "max",
        "maxLag",
        "media",
        "merge",
        "messages",
        "migration",
        "min",
        "mode",
        "model",
        "module",
        "mutable",
        "mutation",
        "native",
        "navigation",
        "never",
        "none",
        "nullify",
        "offline",
        "on",
        "onDelete",
        "onFailure",
        "onTimeout",
        "opaque",
        "operationLog",
        "operations",
        "optimistic",
        "ordering",
        "outbox",
        "owns",
        "page",
        "partition",
        "pending",
        "perPartition",
        "policy",
        "primary",
        "privacy",
        "private",
        "profile",
        "projection",
        "public",
        "pull",
        "push",
        "query",
        "queue",
        "queuedCommands",
        "rateLimit",
        "read",
        "readCommitted",
        "rebuild",
        "reconnect",
        "refresh",
        "refreshing",
        "reject",
        "rejected",
        "reliability",
        "remote",
        "removeWinsSet",
        "rendering",
        "rendition",
        "repeatableRead",
        "replay",
        "replicated",
        "replicatedState",
        "require",
        "required",
        "resource",
        "resources",
        "rest",
        "restrict",
        "resume",
        "retain",
        "retention",
        "retry",
        "return",
        "rollback",
        "route",
        "rpc",
        "runs",
        "safeMessage",
        "saga",
        "scalar",
        "scenario",
        "schedule",
        "schemaMigration",
        "scope",
        "search",
        "secretRef",
        "sensitive",
        "seo",
        "serializable",
        "server",
        "serverAuthoritative",
        "serverStore",
        "serverValidated",
        "serverWins",
        "service",
        "services",
        "session",
        "sessionState",
        "singleton",
        "slo",
        "snapshot",
        "sql",
        "stale",
        "staleAfter",
        "start",
        "state",
        "step",
        "stream",
        "strong",
        "submit",
        "subscribe",
        "success",
        "switchWrites",
        "sync",
        "syncStatus",
        "system",
        "target",
        "task",
        "telemetry",
        "tenant",
        "test",
        "theme",
        "timeSeries",
        "timeout",
        "timezone",
        "title",
        "to",
        "tombstone",
        "topic",
        "transaction",
        "transport",
        "ttl",
        "union",
        "unique",
        "update",
        "urlState",
        "uses",
        "validate",
        "value",
        "vary",
        "verify",
        "via",
        "view",
        "visibilityTimeout",
        "when",
        "workflow",
        "write",
    ).associateWith(::keywordToken)

    private val propertyNames = setOf(
        "language",
        "profile",
        "version",
        "auth",
        "system",
        "frontend",
        "api",
        "defaultDeployment",
        "compatibility",
        "provider",
        "subject",
        "roles",
        "serviceIdentities",
        "standard",
        "keyboard",
        "focus",
        "reducedMotion",
        "sensitiveFields",
        "localData",
        "deviceRevocation",
        "code",
        "httpStatus",
        "retry",
        "safeMessage",
        "localizationKey",
        "index",
        "invariant",
        "transport",
        "basePath",
        "operations",
        "errors",
        "rateLimit",
        "allow",
        "read",
        "consistency",
        "cache",
        "timeout",
        "authorize",
        "idempotency",
        "key",
        "scope",
        "retain",
        "transaction",
        "require",
        "write",
        "emit",
        "return",
        "events",
        "delivery",
        "partition",
        "ordering",
        "retention",
        "deadLetter",
        "messages",
        "visibilityTimeout",
        "service",
        "start",
        "call",
        "checkpoint",
        "rebuild",
        "maxLag",
        "budget",
        "step",
        "approval",
        "execution",
        "queue",
        "resources",
        "cron",
        "timezone",
        "singleton",
        "catchUp",
        "services",
        "apis",
        "channels",
        "owns",
        "uses",
        "exposes",
        "runs",
        "dependsOn",
        "reliability",
        "telemetry",
        "target",
        "rendering",
        "theme",
        "locale",
        "route",
        "fallback",
        "navigation",
        "seo",
        "title",
        "main",
        "state",
        "urlState",
        "sessionState",
        "localState",
        "replicatedState",
        "data",
        "loading",
        "empty",
        "stale",
        "refreshing",
        "field",
        "validate",
        "submit",
        "pending",
        "success",
        "failure",
        "enqueue",
        "optimistic",
        "rollback",
        "conflict",
        "rejected",
        "mode",
        "authority",
        "localStore",
        "serverStore",
        "operationLog",
        "push",
        "pull",
        "changes",
        "delete",
        "schemaMigration",
        "color",
        "spacing",
        "contrast",
    )
}
