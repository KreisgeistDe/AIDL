# Grammar

## Lexical Model

AIDL uses contextual keywords. Quoted EBNF terminals are reserved only in their context.

Important lexer behavior for IntelliJ:

- Top-level declaration starters are keywords only outside braces.
- `module`, `import`, and `export` are declaration-level keywords.
- Scalar types and expression literals/operators such as `string`, `int`, `true`, `false`, `null`, `and`, `or`, `not`, `in`, and `ref` are keywords.
- Forced syntax words such as declaration-level `version` clauses are keywords where the grammar requires them.
- Profile/clause names inside blocks are `PROPERTY_NAME`.
- Any identifier after `.` remains identifier/type name, including words that are keywords elsewhere.

Whitespace and comments are insignificant outside strings, except a logical newline ends field and leaf clauses. A physical line continues when brackets are open, an expression is expected after an operator/colon, or the next line starts with `.`. Semicolons are invalid.

## Program

```ebnf
program    = { moduleDecl | importDecl | exportDecl | declaration } ;
moduleDecl = "module" qualifiedName newline ;
importDecl = "import" qualifiedName [ "." "*" ] newline ;
exportDecl = "export" declaration ;
```

A file has at most one `module`, before imports and declarations.

Declaration starters include `app`, `auth`, `a11y`, `privacy`, `enum`, `alias`, `opaque`, `value`, `union`, `error`, `entity`, `view`, `api`, `policy`, `query`, `mutation`, `event`, `topic`, `queue`, `consumer`, `projection`, `workflow`, `saga`, `task`, `schedule`, `system`, `service`, `client`, `tenant`, `channel`, `resource`, `media`, `rendition`, `sync`, `migration`, `deployment`, `frontend`, `theme`, `component`, `page`, `form`, `action`, `syncStatus`, `seo`, `native function`, `native component`, `fixture`, `test`, and `scenario`.

## Types

```ebnf
type        = primaryType [ "?" ] ;
primaryType = scalarType | namedType | constrainedType | genericType
            | listType | refType | recordType | inlineEnumType ;
listType    = "[" type "]" ;
refType     = "ref" qualifiedName ;
recordType  = "{" [ recordField { "," recordField } ] "}" ;
```

Scalar types: `string`, `int`, `decimal`, `bool`, `uuid`, `date`, `datetime`, `duration`, `revision`, `email`, `url`, `bytes`.

Type parameters use `<T: bound & bound>`. Constraint arguments use ranges, literals, or named literal arguments.

## Expressions

Precedence, high to low:

1. member access, call, index
2. unary `not`, `-`
3. `*`, `/`, `%`
4. `+`, `-`
5. `<`, `<=`, `>`, `>=`
6. `==`, `!=`, `in`, `not in`
7. `and`
8. `or`

Primary expressions are literals, qualified names, capability literals, list literals, object literals, and parenthesized expressions.

Literals include strings, integers, decimals, percentages, duration, byte and CPU literals, `true`, `false`, and `null`.

## Core Declarations

Fields:

```ebnf
fieldDecl = { annotation } identifier ":" type { fieldModifier } newline ;
fieldModifier = "required" | "primary" | "generated" | "clientGenerated"
              | "immutable" | "mutable" | "sensitive" | "unique"
              | "concurrencyToken" | "default" expression
              | "onDelete" deleteAction | "via" identifier ;
```

Views select fields or expression aliases. Operation signatures are `name(params) -> type`.

## Operations

Canonical operation clause order:

1. `auth`
2. `allow`
3. `errors`
4. `authorize`
5. `consistency` or `idempotency`
6. `read`, `transaction`, or `call`
7. `cache`
8. `audit`
9. `timeout`

Transactions contain bindings, `require`, `write`, `emit`, `when`, and `return`. `emit` inside transaction needs `via outbox`.

## Messaging and Processing

Topics declare `events`, `delivery`, `partition by`, `ordering`, `retention`, `compatibility`, and `deadLetter`. Queues declare `messages`, `delivery`, `visibilityTimeout`, and `deadLetter`.

Consumers use `on Event from Topic` and may declare service, idempotency, retry, start/call, or transaction.

Workflows have budget, idempotency, steps, approvals, and return. Sagas have steps with optional compensation. Tasks declare execution, queue, retry, idempotency, resources, call, errors, and timeout.

## Systems and Resources

Systems list services, resources, APIs, and channels. Services list `owns`, `uses`, `exposes`, `runs`, optional `dependsOn`, `reliability`, and telemetry.

Resources use `resource Name kind [typeArguments] { profileProperty }`; valid kinds are listed in `resources-deployment.md`.

Profile properties are syntactically generic but semantically closed by the profile schema. Unknown profile keys are `AIDL-E101`.

## Frontend and Tests

Frontend route syntax: `route "/path/:id" -> Page auth authenticated`. Pages contain title, state, data, async states, auth, and UI statements. Forms use `for Type`, fields, validation, and submit outcomes.

Test profile words such as `arrange`, `assert`, `parallel`, `clients`, `disconnect`, `connect`, `crashpoint`, `restart`, `deliver`, `duplicate`, and `sync` are profile-typed. Unknown test verbs are errors.
