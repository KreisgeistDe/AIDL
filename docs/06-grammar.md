# 6. Normative Grammatik

## Geltungsbereich

Diese EBNF ist für die konkrete AIDL-Syntax normativ. Profilkapitel
definieren zusätzlich die erlaubten Property-Namen, Reihenfolgen und
semantischen Constraints. Ein syntaktisch gültiger unbekannter Profil-Key ist
deshalb weiterhin ein AIDL-E101-Fehler.

Alle in Anführungszeichen stehenden Terminals sind reservierte Schlüsselwörter
im jeweiligen Kontext.

## Lexikalische Regeln

~~~ebnf
letter          = "A".."Z" | "a".."z" | "_" ;
digit           = "0".."9" ;
identifier      = letter { letter | digit } ;
typeName        = upperLetter { letter | digit } ;
upperLetter     = "A".."Z" ;
qualifiedName   = identifier { "." identifier }
                | typeName { "." identifier | "." typeName } ;

integer         = [ "-" ] digit { digit } ;
decimalLiteral  = [ "-" ] digit { digit } "." digit { digit } ;
percentage      = digit { digit } "%" ;
durationLiteral = number ( "ms" | "s" | "m" | "h" | "d" ) ;
byteLiteral     = number ( "B" | "KB" | "MB" | "GB" | "TB" ) ;
cpuLiteral      = number ( "mCPU" | "core" | "cores" ) ;
number          = integer | decimalLiteral ;

string          = '"' { escapedChar | nonQuoteChar } '"' ;
regex           = "/" { escapedChar | nonSlashChar } "/" ;
comment         = "//" { nonNewlineChar }
                | "/*" { anyChar } "*/" ;
annotation      = "@" identifier [ "(" [ arguments ] ")" ] ;
newline         = ? logical line ending ? ;
~~~

Kommentare und Whitespace sind außerhalb von Strings nicht signifikant, mit
einer Ausnahme: Ein logical newline beendet Feld- und Leaf-Klauseln. Eine
physische Zeile wird fortgesetzt, wenn Klammern offen sind, der Parser nach
einem Operator oder Doppelpunkt einen Ausdruck erwartet oder die nächste Zeile
mit einem Punkt beginnt. Semikolons sind ungültig.

## Programme und Module

~~~ebnf
program         = { moduleDecl | importDecl | exportDecl | declaration } ;

moduleDecl      = "module" qualifiedName newline ;
importDecl      = "import" qualifiedName [ "." "*" ] newline ;
exportDecl      = "export" declaration ;

declaration     = appDecl
                | authDecl
                | a11yDecl
                | privacyDecl
                | enumDecl
                | aliasDecl
                | valueDecl
                | unionDecl
                | errorDecl
                | entityDecl
                | viewDecl
                | apiDecl
                | policyDecl
                | queryDecl
                | mutationDecl
                | eventDecl
                | topicDecl
                | queueDecl
                | consumerDecl
                | projectionDecl
                | workflowDecl
                | sagaDecl
                | taskDecl
                | scheduleDecl
                | systemDecl
                | serviceDecl
                | clientDecl
                | tenantDecl
                | channelDecl
                | resourceDecl
                | mediaDecl
                | renditionDecl
                | syncDecl
                | migrationDecl
                | deploymentDecl
                | frontendDecl
                | themeDecl
                | componentDecl
                | pageDecl
                | formDecl
                | actionDecl
                | syncStatusDecl
                | seoDecl
                | nativeFunctionDecl
                | nativeComponentDecl
                | fixtureDecl
                | testDecl
                | scenarioDecl ;
~~~

Eine Datei darf höchstens eine module-Deklaration besitzen; sie muss vor
Imports und Deklarationen stehen.

## App und Profile

~~~ebnf
appDecl         = { annotation }
                  "app" typeName
                  "{" { appClause } "}" ;

appClause       = "profile" identifier "version" integer newline
                | "system" typeName newline
                | "frontend" typeName newline
                | "api" typeName newline
                | "defaultDeployment" identifier newline
                | "compatibility" identifier newline ;

authDecl        = "auth" "{" { profileProperty } "}" ;
a11yDecl        = "a11y" "{" { profileProperty } "}" ;
privacyDecl     = "privacy" "{" { profileProperty } "}" ;
~~~

## Typen

~~~ebnf
type            = primaryType [ "?" ] ;

primaryType     = scalarType
                | namedType
                | constrainedType
                | genericType
                | listType
                | refType
                | recordType
                | inlineEnumType ;

scalarType      = "string" | "int" | "decimal" | "bool" | "uuid"
                | "date" | "datetime" | "duration" | "revision"
                | "email" | "url" | "bytes" ;

namedType       = qualifiedName ;
constrainedType = ( scalarType | qualifiedName ) constraintArguments ;
genericType     = qualifiedName typeArguments ;
listType        = "[" type "]" ;
refType         = "ref" qualifiedName ;
recordType      = "{" [ recordField { "," recordField } ] "}" ;
recordField     = identifier ":" type ;
inlineEnumType  = "enum" "(" string { "," string } ")" ;

typeArguments   = "<" type { "," type } ">" ;
typeParameters  = "<" typeParameter { "," typeParameter } ">" ;
typeParameter   = typeName [ ":" typeBound { "&" typeBound } ] ;
typeBound       = "serializable" | "scalar" | "value" | "entityView"
                | "ErrorValue" | "comparable" | "hashable" ;

constraintArguments
                = "(" [ constraintArgument { "," constraintArgument } ] ")" ;
constraintArgument
                = identifier ":" literal
                | range
                | literal ;
range           = literal ".." literal ;
~~~

## Ausdrücke

~~~ebnf
expression      = orExpression ;
orExpression    = andExpression { "or" andExpression } ;
andExpression   = equalityExpression { "and" equalityExpression } ;
equalityExpression
                = relationalExpression
                  { ( "==" | "!=" | "in" | "not" "in" )
                    relationalExpression } ;
relationalExpression
                = additiveExpression
                  { ( "<" | "<=" | ">" | ">=" )
                    additiveExpression } ;
additiveExpression
                = multiplicativeExpression
                  { ( "+" | "-" ) multiplicativeExpression } ;
multiplicativeExpression
                = unaryExpression { ( "*" | "/" | "%" ) unaryExpression } ;
unaryExpression = [ "not" | "-" ] postfixExpression ;
postfixExpression
                = primaryExpression { memberAccess | callSuffix | indexSuffix } ;
memberAccess    = "." identifier ;
callSuffix      = "(" [ arguments ] ")" ;
indexSuffix     = "[" expression "]" ;

primaryExpression
                = literal
                | qualifiedName
                | capabilityLiteral
                | listLiteral
                | objectLiteral
                | "(" expression ")" ;

arguments       = argument { "," argument } ;
argument        = [ identifier ":" ] expression | spread ;
spread          = "..." expression ;
listLiteral     = "[" [ expression { "," expression } ] "]" ;
objectLiteral   = "{" [ objectMember { "," objectMember } ] "}" ;
objectMember    = identifier ":" expression | spread ;
capabilityLiteral
                = identifier ":" qualifiedName ;

literal         = string | integer | decimalLiteral | percentage
                | durationLiteral | byteLiteral | cpuLiteral
                | "true" | "false" | "null" ;
~~~

## Typdeklarationen

~~~ebnf
enumDecl        = { annotation } "enum" typeName
                  "{" enumCase { "," enumCase } "}" ;
enumCase        = identifier [ "=" string ] ;

aliasDecl       = { annotation } ( "alias" | "opaque" )
                  typeName [ typeParameters ] "=" type newline ;

valueDecl       = { annotation } "value" typeName [ typeParameters ]
                  "{" { fieldDecl | invariantDecl } "}" ;

unionDecl       = { annotation } "union" typeName [ typeParameters ]
                  "{" { unionVariant } "}" ;
unionVariant    = identifier [ "(" [ parameters ] ")" ] newline ;

errorDecl       = { annotation } "error" typeName
                  "{" { errorClause | fieldDecl } "}" ;
errorClause     = "code" string newline
                | "httpStatus" integer newline
                | "retry" retryClass newline
                | "safeMessage" string newline
                | "localizationKey" string newline ;
retryClass      = "never" | "immediate" | "backoff"
                | "after" durationLiteral ;

entityDecl      = { annotation } "entity" typeName
                  "{" { fieldDecl | indexDecl | invariantDecl } "}" ;
fieldDecl       = { annotation } identifier ":" type
                  { fieldModifier } newline ;
fieldModifier   = "required" | "primary" | "generated"
                | "clientGenerated" | "immutable" | "mutable"
                | "sensitive" | "unique" | "concurrencyToken"
                | "default" expression
                | "onDelete" deleteAction
                | "via" identifier ;
deleteAction    = "restrict" | "cascade" | "nullify" ;

indexDecl       = "index" identifier "(" indexField
                  { "," indexField } ")" newline ;
indexField      = identifier [ "asc" | "desc" ] ;
invariantDecl   = "invariant" identifier ":" expression newline ;

viewDecl        = { annotation } "view" typeName [ typeParameters ]
                  [ "from" type ] "{" { viewMember } "}" ;
viewMember      = identifier [ "{" viewSelection "}" ] [ "," ] newline
                | identifier ":" expression newline ;
viewSelection   = viewInlineMember { "," viewInlineMember }
                | { viewMember } ;
viewInlineMember
                = identifier [ "{" viewSelection "}" ] ;

parameters      = parameter { "," parameter } ;
parameter       = identifier ":" type [ "default" expression ] ;
~~~

## Operationen

~~~ebnf
apiDecl         = { annotation } "api" typeName
                  "{" { apiClause } "}" ;
apiClause       = "transport" ( "rest" | "rpc" | "graphql" ) newline
                | "version" integer newline
                | "basePath" string newline
                | "operations" "[" exposedItem
                  { "," exposedItem } "]" newline
                | "auth" identifier newline
                | "errors" identifier newline
                | "compatibility" compatibilityMode newline
                | "rateLimit" profilePropertyValue
                  { profilePropertyValue } newline ;

operationSignature
                = identifier [ typeParameters ]
                  "(" [ parameters ] ")" "->" type ;

policyDecl      = { annotation } "policy" operationSignature
                  "{" { policyStatement } "}" ;
queryDecl       = { annotation } "query" operationSignature
                  "{" { queryClause } "}" ;
mutationDecl    = { annotation } "mutation" operationSignature
                  "{" { mutationClause } "}" ;

policyStatement = requireStatement | bindingStatement | returnStatement ;

queryClause     = authClause
                | allowClause
                | "read" ":" expression newline
                | "consistency" ":" consistency newline
                | cacheClause
                | errorsClause
                | timeoutClause ;

mutationClause  = authClause
                | allowClause
                | errorsClause
                | authorizeClause
                | idempotencyClause
                | transactionBlock
                | callClause
                | auditClause
                | timeoutClause ;

authClause      = "auth" ":" authMode newline ;
authMode        = "public" | "authenticated" | "service"
                | qualifiedName ;
allowClause     = "allow" ":" expression newline ;
authorizeClause = "authorize" ":" "remote" "query" expression
                  [ "else" typeName ] newline ;
errorsClause    = "errors" ":" "[" type { "," type } "]" newline ;
timeoutClause   = "timeout" ":" durationLiteral newline ;
auditClause     = "audit" ":" ( "required" | "none" ) newline ;
callClause      = "call" ":" expression newline ;

consistency     = "strong" | "session" | "eventual"
                | "boundedStaleness" "(" "max" ":" durationLiteral ")" ;

cacheClause     = "cache" ":" cacheVisibility "ttl" durationLiteral
                  [ "vary" "[" identifier { "," identifier } "]" ] newline ;
cacheVisibility = "none" | "private" | "public" ;

idempotencyClause
                = "idempotency" ":" idempotencyInline newline
                | "idempotency" ":" newline
                  "{" { idempotencyProperty } "}" ;
idempotencyInline
                = expression "retain" durationLiteral ;
idempotencyProperty
                = "key" expression newline
                | "scope" expression newline
                | "retain" durationLiteral newline ;

transactionBlock
                = "transaction" "on" typeName
                  "isolation" isolation
                  "{" { transactionStatement } "}" ;
isolation       = "readCommitted" | "repeatableRead" | "serializable" ;

transactionStatement
                = bindingStatement
                | requireStatement
                | writeStatement
                | emitStatement
                | whenStatement
                | returnStatement ;

bindingStatement
                = identifier "=" expression
                  [ "else" typeName ]
                  [ "lock" "update" "timeout" durationLiteral ] newline ;
requireStatement
                = "require" expression [ "else" typeName ] newline ;
writeStatement  = "write" ":" expression
                  [ "expect" "revision" expression ]
                  [ "else" typeName ] newline ;
emitStatement   = "emit" ":" expression "to" typeName
                  [ "via" "outbox" ] newline ;
whenStatement   = "when" expression
                  "{" { transactionStatement } "}"
                  [ "else" "{" { transactionStatement } "}" ] ;
returnStatement = "return" expression newline ;
~~~

## Events, Messaging und Verarbeitung

~~~ebnf
eventDecl       = { annotation } "event" typeName
                  "version" integer
                  [ "evolves" typeName "version" integer ]
                  "{" { fieldDecl } "}" ;

topicDecl       = { annotation } "topic" typeName
                  "{" { topicClause } "}" ;
topicClause     = "events" "[" typeName { "," typeName } "]" newline
                | "delivery" delivery newline
                | "partition" "by" expression newline
                | "ordering" ordering newline
                | "retention" durationLiteral newline
                | "compatibility" compatibilityMode newline
                | "deadLetter" "after" integer "attempts" newline ;

queueDecl       = { annotation } "queue" typeName
                  "{" { queueClause } "}" ;
queueClause     = "messages" "[" typeName { "," typeName } "]" newline
                | "delivery" delivery newline
                | "visibilityTimeout" durationLiteral newline
                | "deadLetter" "after" integer "attempts" newline ;

delivery        = "atLeastOnce" | "atMostOnce" ;
ordering        = "none" | "perPartition" | "global" ;
compatibilityMode
                = "none" | "backward" | "forward" | "full" ;

consumerDecl    = { annotation } "consumer" typeName
                  "on" typeName "from" typeName
                  "{" { consumerClause } "}" ;
consumerClause  = "service" typeName newline
                | idempotencyClause
                | "retry" ":" retryPolicy newline
                | "start" ":" invocationKind expression newline
                | "call" ":" invocationKind expression newline
                | "transaction" "on" typeName
                  "{" { transactionStatement } "}" ;
invocationKind  = "workflow" | "task" | "mutation" ;

retryPolicy     = "none"
                | "immediate" "(" "max" ":" integer ")"
                | "exponential" "(" [ namedRetryArgs ] ")" ;
namedRetryArgs  = namedRetryArg { "," namedRetryArg } ;
namedRetryArg   = identifier ":" literal ;

projectionDecl  = { annotation } "projection" typeName
                  "from" "[" typeName { "," typeName } "]"
                  "into" typeName
                  "{" { projectionClause } "}" ;
projectionClause
                = "key" expression newline
                | "map" expression newline
                | "checkpoint" identifier newline
                | "rebuild"
                  ( "replay" | "snapshot" | "from" typeName ) newline
                | "maxLag" durationLiteral newline ;
~~~

## Workflows, Sagas, Tasks und Scheduler

~~~ebnf
workflowDecl    = { annotation } "workflow" operationSignature
                  "{" { workflowStatement } "}" ;
workflowStatement
                = budgetClause
                | idempotencyClause
                | workflowStep
                | approvalStep
                | returnStatement ;

budgetClause    = "budget" ":" profilePropertyValue
                  { "," profilePropertyValue } newline ;
workflowStep    = "step" identifier "retry" retryPolicy
                  "{" { workflowInnerStatement } "}" ;
workflowInnerStatement
                = bindingStatement | requireStatement | returnStatement
                | invocationStatement ;
invocationStatement
                = [ identifier "=" ]
                  ( "query" | "mutation" | "task" | "workflow" )
                  expression newline ;

approvalStep    = "approval" identifier
                  "{" { approvalClause } "}" ;
approvalClause  = "timeout" ":" durationLiteral newline
                | "onTimeout" ":"
                  ( "fail" typeName
                  | invocationKind expression
                  | "return" expression ) newline ;

sagaDecl        = { annotation } "saga" operationSignature
                  "{" { sagaStatement } "}" ;
sagaStatement   = "step" identifier "=" invocationKind expression
                  [ "compensate" invocationKind expression ] newline
                | returnStatement
                | budgetClause
                | idempotencyClause ;

taskDecl        = { annotation } "task" operationSignature
                  "{" { taskClause } "}" ;
taskClause      = "execution" identifier newline
                | "queue" ":" typeName newline
                | "retry" ":" retryPolicy newline
                | idempotencyClause
                | "resources" ":" profilePropertyValue
                  { "," profilePropertyValue } newline
                | "call" ":" expression newline
                | errorsClause
                | timeoutClause ;

scheduleDecl    = { annotation } "schedule" typeName
                  "{" { scheduleClause } "}" ;
scheduleClause  = "cron" string newline
                | "timezone" string newline
                | "singleton" "lease" durationLiteral newline
                | "catchUp" ( "none" | "latest"
                  | "all" "(" "max" ":" integer ")" ) newline
                | "start" ":" invocationKind expression newline ;
~~~

## Systeme und Services

~~~ebnf
systemDecl      = { annotation } "system" typeName
                  "{" { systemClause } "}" ;
systemClause    = "services" "[" typeName { "," typeName } "]" newline
                | "resources" "[" typeName { "," typeName } "]" newline
                | "apis" "[" typeName { "," typeName } "]" newline
                | "channels" "[" typeName { "," typeName } "]" newline ;

serviceDecl     = { annotation } "service" typeName
                  "{" { serviceClause } "}" ;
serviceClause   = "owns" "[" typeName { "," typeName } "]" newline
                | "uses" "[" typeName { "," typeName } "]" newline
                | "exposes" "[" exposedItem { "," exposedItem } "]" newline
                | "runs" "[" runnableItem { "," runnableItem } "]" newline
                | "dependsOn" "[" typeName { "," typeName } "]" newline
                | "reliability" "{" { profileProperty } "}"
                | "telemetry" identifier newline ;
exposedItem     = ( "query" | "mutation" | "channel" | "sync" )
                  qualifiedName ;
runnableItem    = ( "consumer" | "workflow" | "task" | "schedule"
                  | "projection" | "sync" | "channel" )
                  qualifiedName ;

clientDecl      = { annotation } "client" typeName "for" typeName
                  "{" { clientCall } "}" ;
clientCall      = "call" identifier
                  "{" { profileProperty } "}" ;

tenantDecl      = { annotation } "tenant" "model" typeName
                  "{" { profileProperty } "}" ;

channelDecl     = { annotation } "channel" typeName [ typeParameters ]
                  "{" { profileProperty } "}" ;
~~~

## Ressourcen und Medien

~~~ebnf
resourceDecl    = { annotation } "resource" typeName resourceKind
                  [ typeArguments ] "{" { profileProperty } "}" ;
resourceKind    = "sql" | "document" | "keyValue" | "timeSeries"
                | "blob" | "cdn" | "cache" | "stream" | "search"
                | "counter" | "secretRef" | "configRef" | "localStore" ;

mediaDecl       = { annotation } "media" typeName
                  "{" { profileProperty } "}" ;
renditionDecl   = { annotation } "rendition" typeName "from" typeName
                  "{" { profileProperty } "}" ;

profileProperty = propertyPath [ ":" ] profilePropertyValue newline
                | propertyPath "{" { profileProperty } "}" ;
propertyPath    = identifier { identifier } ;
profilePropertyValue
                = expression
                | expression ".." expression
                | qualifiedName { profilePropertyValue } ;
~~~

Die zulässigen profileProperty-Pfade und Werttypen sind je Deklarationsart im
Profil-Schema geschlossen definiert. Diese generische Produktion ist kein
offenes Key/Value-Erweiterungssystem.

## Offline-Synchronisation

~~~ebnf
syncDecl        = { annotation } "sync" typeName "for" type
                  "{" { syncClause } "}" ;
syncClause      = "mode" syncMode newline
                | "authority" syncAuthority newline
                | "scope" ":" expression newline
                | "localStore" typeName newline
                | "serverStore" typeName newline
                | operationLogBlock
                | "push" profilePropertyValue
                  { profilePropertyValue } newline
                | "pull" profilePropertyValue
                  { profilePropertyValue } newline
                | "changes" "to" typeName "via" "outbox" newline
                | "delete" "tombstone" "retain" durationLiteral newline
                | conflictBlock
                | "rejected" profilePropertyValue
                  { profilePropertyValue } newline
                | "schemaMigration" "required" newline ;
syncMode        = "serverAuthoritative" | "queuedCommands" | "replicated" ;
syncAuthority   = "server" | "serverValidated" | "merge" ;

operationLogBlock
                = "operationLog" "{" { profileProperty } "}" ;
conflictBlock   = "conflict" "{" { conflictRule } "}" ;
conflictRule    = "field" identifier "merge" mergeStrategy newline
                | "group" identifier "fields"
                  "[" identifier { "," identifier } "]"
                  "merge" mergeStrategy newline ;
mergeStrategy   = "reject" | "serverWins"
                | "lww" "(" "clock" ":" identifier ")"
                | "max" | "min" | "addWinsSet" | "removeWinsSet"
                | "counter" | "manual"
                | "custom" qualifiedName ;
~~~

## Migration und Deployment

~~~ebnf
migrationDecl   = { annotation } "migration" typeName
                  "from" string "to" string
                  "{" { migrationStep } "}" ;
migrationStep   = migrationPhase profilePropertyValue
                  { profilePropertyValue } newline ;
migrationPhase  = "expand" | "backfill" | "deployReaders"
                | "switchWrites" | "verify" | "contract" | "rollback" ;

deploymentDecl  = { annotation } "deployment" identifier "for" typeName
                  "{" { deploymentClause } "}" ;
deploymentClause
                = "service" typeName "{" { profileProperty } "}"
                | "resource" typeName "{" { profileProperty } "}"
                | "bind" typeName profilePropertyValue
                  { profilePropertyValue } newline
                | "colocate" "services"
                  ( "all" | "[" typeName { "," typeName } "]" ) newline
                | "slo" identifier profilePropertyValue
                  { profilePropertyValue } newline
                | profileProperty ;
~~~

## Frontend

~~~ebnf
frontendDecl    = { annotation } "frontend" typeName
                  "{" { frontendClause } "}" ;
frontendClause  = "target" identifier newline
                | "rendering" identifier newline
                | "theme" typeName newline
                | "locale" profilePropertyValue
                  { profilePropertyValue } newline
                | routeDecl
                | "fallback" "->" typeName newline
                | "navigation" identifier
                  "{" { uiStatement } "}"
                | "seo" "defaults"
                  "{" { profileProperty } "}" ;

routeDecl       = "route" string "->" typeName
                  [ "auth" authMode ] newline ;

themeDecl       = { annotation } "theme" typeName
                  "{" { profileProperty } "}" ;

componentDecl   = { annotation } "component" typeName [ typeParameters ]
                  "(" [ parameters ] ")"
                  "{" { uiStatement } "}" ;

pageDecl        = { annotation } "page" typeName
                  [ "(" [ parameters ] ")" ]
                  "{" { pageClause | uiStatement } "}" ;

pageClause      = "title" expression newline
                | stateDecl
                | dataDecl
                | asyncStateClause
                | "main" "{" { uiStatement } "}"
                | "auth" authMode
                  [ "onFailure" uiStatement ] newline ;

stateDecl       = stateKind identifier ":" type
                  [ "default" expression ]
                  [ "retain" profilePropertyValue
                    { profilePropertyValue } ] newline ;
stateKind       = "urlState" | "state" | "sessionState"
                | "localState" | "replicatedState" ;

dataDecl        = "data" identifier "=" dataSource
                  { dataModifier } newline ;
dataSource      = "query" expression | "subscribe" expression ;
dataModifier    = "consistency" consistency
                | "refresh" "on" listLiteral
                | "staleAfter" durationLiteral
                | "offline" typeName
                | "resume" profilePropertyValue
                | "reconnect" profilePropertyValue
                | "fallback" "query" expression ;

asyncStateClause
                = ( "loading" | "empty" | "stale" | "refreshing" )
                  ":" expression newline
                | "error" [ "retry" ] ":" expression newline ;

formDecl        = { annotation } "form" typeName
                  [ "(" [ parameters ] ")" ]
                  "for" type
                  "{" { formClause | stateDecl | uiStatement } "}" ;
formClause      = "field" identifier { profilePropertyValue } newline
                | "validate" profilePropertyValue
                  { profilePropertyValue } newline
                | "submit" "call" expression
                  "{" { submitOutcome } "}" ;
submitOutcome   = "pending" uiStatement
                | "success" uiStatement
                | "failure" [ typeName ] uiStatement ;

actionDecl      = { annotation } "action" identifier
                  "(" [ parameters ] ")"
                  "{" { actionStatement } "}" ;
actionStatement = "call" expression newline
                | "enqueue" expression newline
                | "optimistic" uiStatement
                | "rollback" uiStatement
                | "pending" uiStatement
                | "conflict" uiStatement
                | "rejected" uiStatement
                | uiStatement ;

syncStatusDecl  = "syncStatus" typeName
                  "{" { profileProperty } "}" ;
seoDecl         = "seo" typeName "{" { profileProperty } "}" ;

uiStatement     = identifier { uiAtom } [ "{" { uiStatement } "}" ] newline ;
uiAtom          = expression | propertyPath | ":" ;
~~~

UI-Schlüsselwörter wie heading, grid, semantic und button sind im
web-Profil-Schema geschlossen. uiStatement erlaubt deren kompakte
domänenspezifische Schreibweise, ohne unbekannte Wörter semantisch zuzulassen.

## Native Deklarationen

~~~ebnf
nativeFunctionDecl
                = { annotation } "native" "function" qualifiedName
                  [ typeParameters ]
                  "{" { profileProperty } "}" ;
nativeComponentDecl
                = { annotation } "native" "component" typeName
                  [ typeParameters ]
                  "{" { profileProperty } "}" ;
~~~

## Tests und Fixtures

~~~ebnf
fixtureDecl     = "fixture" typeName [ "(" [ parameters ] ")" ]
                  "{" { testStatement } "}" ;
scenarioDecl    = "scenario" typeName "{" { testStatement } "}" ;

testDecl        = { annotation } "test" string "target" identifier
                  "{" { testStatement } "}" ;
testStatement   = testLeaf
                | testBlock ;
testLeaf        = identifier { expression | qualifiedName
                  | profilePropertyValue } newline ;
testBlock       = identifier { expression | qualifiedName }
                  "{" { testStatement } "}" ;
~~~

Testwörter wie arrange, act, assert, parallel, clients, disconnect, connect,
crashpoint, restart, deliver, duplicate und sync werden durch das Testprofil
typisiert. Unbekannte Testverben sind Fehler.

## Kanonische Reihenfolge

Innerhalb von Operationen gilt:

1. auth
2. allow
3. errors
4. authorize
5. consistency oder idempotency
6. read, transaction oder call
7. cache
8. audit
9. timeout

Formatter dürfen Kommentare erhalten, ändern aber niemals die semantische
Reihenfolge von Writes, Emits, Workflow- oder Saga-Schritten.
