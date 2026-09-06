package de.kreisgeist.aidl.psi

import com.intellij.psi.tree.TokenSet

object AidlTokenSets {
    val DECLARATION_KEYWORDS: TokenSet = TokenSet.create(
        AidlTypes.APP_KEYWORD,
        AidlTypes.AUTH_KEYWORD,
        AidlTypes.A11Y_KEYWORD,
        AidlTypes.PRIVACY_KEYWORD,
        AidlTypes.ENUM_KEYWORD,
        AidlTypes.ALIAS_KEYWORD,
        AidlTypes.OPAQUE_KEYWORD,
        AidlTypes.VALUE_KEYWORD,
        AidlTypes.UNION_KEYWORD,
        AidlTypes.ERROR_KEYWORD,
        AidlTypes.ENTITY_KEYWORD,
        AidlTypes.VIEW_KEYWORD,
        AidlTypes.API_KEYWORD,
        AidlTypes.POLICY_KEYWORD,
        AidlTypes.QUERY_KEYWORD,
        AidlTypes.MUTATION_KEYWORD,
        AidlTypes.EVENT_KEYWORD,
        AidlTypes.TOPIC_KEYWORD,
        AidlTypes.QUEUE_KEYWORD,
        AidlTypes.CONSUMER_KEYWORD,
        AidlTypes.PROJECTION_KEYWORD,
        AidlTypes.WORKFLOW_KEYWORD,
        AidlTypes.SAGA_KEYWORD,
        AidlTypes.TASK_KEYWORD,
        AidlTypes.SCHEDULE_KEYWORD,
        AidlTypes.SYSTEM_KEYWORD,
        AidlTypes.SERVICE_KEYWORD,
        AidlTypes.CLIENT_KEYWORD,
        AidlTypes.TENANT_KEYWORD,
        AidlTypes.CHANNEL_KEYWORD,
        AidlTypes.RESOURCE_KEYWORD,
        AidlTypes.MEDIA_KEYWORD,
        AidlTypes.RENDITION_KEYWORD,
        AidlTypes.SYNC_KEYWORD,
        AidlTypes.MIGRATION_KEYWORD,
        AidlTypes.DEPLOYMENT_KEYWORD,
        AidlTypes.FRONTEND_KEYWORD,
        AidlTypes.THEME_KEYWORD,
        AidlTypes.COMPONENT_KEYWORD,
        AidlTypes.PAGE_KEYWORD,
        AidlTypes.FORM_KEYWORD,
        AidlTypes.ACTION_KEYWORD,
        AidlTypes.SYNC_STATUS_KEYWORD,
        AidlTypes.SEO_KEYWORD,
        AidlTypes.NATIVE_KEYWORD,
        AidlTypes.FUNCTION_KEYWORD,
        AidlTypes.FIXTURE_KEYWORD,
        AidlTypes.TEST_KEYWORD,
        AidlTypes.SCENARIO_KEYWORD,
    )

    val SCALAR_TYPES: TokenSet = TokenSet.create(
        AidlTypes.STRING_TYPE_KEYWORD,
        AidlTypes.INT_KEYWORD,
        AidlTypes.DECIMAL_KEYWORD,
        AidlTypes.BOOL_KEYWORD,
        AidlTypes.UUID_KEYWORD,
        AidlTypes.DATE_KEYWORD,
        AidlTypes.DATETIME_KEYWORD,
        AidlTypes.DURATION_KEYWORD,
        AidlTypes.REVISION_KEYWORD,
        AidlTypes.EMAIL_KEYWORD,
        AidlTypes.URL_KEYWORD,
        AidlTypes.BYTES_KEYWORD,
    )

    val PROPERTY_NAMES: TokenSet = TokenSet.create(AidlTypes.PROPERTY_NAME)

    val KEYWORDS: TokenSet = TokenSet.create(
        *DECLARATION_KEYWORDS.types,
        *SCALAR_TYPES.types,
        *AidlTypes.GRAMMAR_KEYWORD_TOKENS.toTypedArray(),
        AidlTypes.MODULE_KEYWORD,
        AidlTypes.IMPORT_KEYWORD,
        AidlTypes.EXPORT_KEYWORD,
        AidlTypes.TRUE_KEYWORD,
        AidlTypes.FALSE_KEYWORD,
        AidlTypes.NULL_KEYWORD,
        AidlTypes.AND_KEYWORD,
        AidlTypes.OR_KEYWORD,
        AidlTypes.NOT_KEYWORD,
        AidlTypes.IN_KEYWORD,
        AidlTypes.REF_KEYWORD,
    )

    val COMMENTS: TokenSet = TokenSet.create(
        AidlTypes.LINE_COMMENT,
        AidlTypes.BLOCK_COMMENT_START,
        AidlTypes.BLOCK_COMMENT_CONTENT,
        AidlTypes.BLOCK_COMMENT_END,
    )

    val STRINGS: TokenSet = TokenSet.create(AidlTypes.STRING, AidlTypes.REGEX)

    val NUMBERS: TokenSet = TokenSet.create(
        AidlTypes.INTEGER,
        AidlTypes.DECIMAL_LITERAL,
        AidlTypes.PERCENTAGE,
        AidlTypes.DURATION_LITERAL,
        AidlTypes.BYTE_LITERAL,
        AidlTypes.CPU_LITERAL,
    )

    val OPERATORS: TokenSet = TokenSet.create(
        AidlTypes.SPREAD,
        AidlTypes.ARROW,
        AidlTypes.RANGE,
        AidlTypes.EQEQ,
        AidlTypes.NEQ,
        AidlTypes.LTE,
        AidlTypes.GTE,
        AidlTypes.EQ,
        AidlTypes.PLUS,
        AidlTypes.MINUS,
        AidlTypes.STAR,
        AidlTypes.SLASH,
        AidlTypes.PERCENT,
        AidlTypes.AMP,
        AidlTypes.DOT,
        AidlTypes.COLON,
        AidlTypes.COMMA,
        AidlTypes.QUESTION,
    )

    val BRACES: TokenSet = TokenSet.create(
        AidlTypes.LPAREN,
        AidlTypes.RPAREN,
        AidlTypes.LBRACE,
        AidlTypes.RBRACE,
        AidlTypes.LBRACKET,
        AidlTypes.RBRACKET,
        AidlTypes.LT,
        AidlTypes.GT,
    )
}
