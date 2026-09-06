package de.kreisgeist.aidl.lexer;

import com.intellij.lexer.FlexLexer;
import com.intellij.psi.TokenType;
import com.intellij.psi.tree.IElementType;

import static de.kreisgeist.aidl.psi.AidlTypes.*;
%%

%{
  public _AidlLexer() {
    this((java.io.Reader)null);
  }
%}

%class _AidlLexer
%implements FlexLexer
%unicode
%function advance
%type IElementType
%state BLOCK_COMMENT
%eof{ return;
%eof}

/* --------------------------------------------------------- */
/* Basic character classes                                   */
/* --------------------------------------------------------- */

LETTER       = [A-Za-z_]
UPPER        = [A-Z]
DIGIT        = [0-9]

IDENTIFIER   = {LETTER}({LETTER}|{DIGIT})*
TYPE_NAME    = {UPPER}({LETTER}|{DIGIT})*

HWS          = [ \t\f]+
NEWLINE      = \r\n|\r|\n


/* --------------------------------------------------------- */
/* Numeric literals                                          */
/* --------------------------------------------------------- */

INTEGER      = -?{DIGIT}+
DECIMAL      = -?{DIGIT}+\.{DIGIT}+

NUMBER       = ({INTEGER}|{DECIMAL})

PERCENTAGE   = {DIGIT}+"%"

DURATION     = {NUMBER}(ms|s|m|h|d)
BYTE_LITERAL = {NUMBER}(B|KB|MB|GB|TB)
CPU_LITERAL  = {NUMBER}(mCPU|core|cores)


/* --------------------------------------------------------- */
/* String / regex helpers                                    */
/* --------------------------------------------------------- */

ESCAPE       = \\.
STRING_CHAR  = [^\"\\\r\n]
REGEX_CHAR   = [^\/\\\r\n]

STRING       = \"({STRING_CHAR}|{ESCAPE})*\"
REGEX        = \/({REGEX_CHAR}|{ESCAPE})*\/


/* --------------------------------------------------------- */
/* Comments                                                  */
/* --------------------------------------------------------- */

LINE_COMMENT = "//"[^\r\n]*


%%

<YYINITIAL> {

    /* ----------------------------------------------------- */
    /* Whitespace                                            */
    /* ----------------------------------------------------- */

    {HWS} {
        return TokenType.WHITE_SPACE;
    }

    {NEWLINE} {
        return NEWLINE;
    }


    /* ----------------------------------------------------- */
    /* Comments                                              */
    /* ----------------------------------------------------- */

    {LINE_COMMENT} {
        return LINE_COMMENT;
    }

    "/*" {
        yybegin(BLOCK_COMMENT);
        return BLOCK_COMMENT_START;
    }


    /* ----------------------------------------------------- */
    /* Multi-character operators                            */
    /* ----------------------------------------------------- */

    "..." {
        return SPREAD;
    }

    "->" {
        return ARROW;
    }

    ".." {
        return RANGE;
    }

    "==" {
        return EQEQ;
    }

    "!=" {
        return NEQ;
    }

    "<=" {
        return LTE;
    }

    ">=" {
        return GTE;
    }


    /* ----------------------------------------------------- */
    /* Single-character operators / punctuation             */
    /* ----------------------------------------------------- */

    "(" {
        return LPAREN;
    }

    ")" {
        return RPAREN;
    }

    "{" {
        return LBRACE;
    }

    "}" {
        return RBRACE;
    }

    "[" {
        return LBRACKET;
    }

    "]" {
        return RBRACKET;
    }

    "<" {
        return LT;
    }

    ">" {
        return GT;
    }

    "," {
        return COMMA;
    }

    ":" {
        return COLON;
    }

    "." {
        return DOT;
    }

    "?" {
        return QUESTION;
    }

    "@" {
        return AT;
    }

    "=" {
        return EQ;
    }

    "+" {
        return PLUS;
    }

    "-" {
        return MINUS;
    }

    "*" {
        return STAR;
    }

    "/" {
        return SLASH;
    }

    "%" {
        return PERCENT;
    }

    "&" {
        return AMP;
    }


    /* ----------------------------------------------------- */
    /* Literals                                              */
    /* ----------------------------------------------------- */

    {DURATION} {
        return DURATION_LITERAL;
    }

    {BYTE_LITERAL} {
        return BYTE_LITERAL;
    }

    {CPU_LITERAL} {
        return CPU_LITERAL;
    }

    {PERCENTAGE} {
        return PERCENTAGE;
    }

    {DECIMAL} {
        return DECIMAL_LITERAL;
    }

    {INTEGER} {
        return INTEGER;
    }

    {STRING} {
        return STRING;
    }

    {REGEX} {
        return REGEX;
    }


    /* ----------------------------------------------------- */
    /* Identifiers                                           */
    /* ----------------------------------------------------- */

    {TYPE_NAME} {
        return TYPE_NAME;
    }

    {IDENTIFIER} {
        return IDENTIFIER;
    }


    /* ----------------------------------------------------- */
    /* Invalid input                                         */
    /* ----------------------------------------------------- */

    [^] {
        return TokenType.BAD_CHARACTER;
    }
}


/* --------------------------------------------------------- */
/* Block comments                                            */
/* --------------------------------------------------------- */

<BLOCK_COMMENT> {

    "*/" {
        yybegin(YYINITIAL);
        return BLOCK_COMMENT_END;
    }

    [^] {
        return BLOCK_COMMENT_CONTENT;
    }
}