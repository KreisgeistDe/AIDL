# M16.5 E1 Production Traceability Inventory — Structural-B

Status: **non-normative E1 design evidence**. `docs/06-grammar.md` remains normative. Reference positions are construction metadata only; resolution and target-kind truth remain Semantic-owned. `syntax-default-token` means the production contains the source keyword `default`, not that Structural Schema owns semantic defaulting.

Base: `KreisgeistDe/AIDL@36403b0df688ea46205c0ce015f826dd113c51d9`.

| ID | Source section | Production | Owner | Cardinality | Order | Default relevance | Reference relevance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PF-135 | Events, Messaging und Verarbeitung | `namedRetryArg` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-136 | Events, Messaging und Verarbeitung | `projectionDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-137 | Events, Messaging und Verarbeitung | `projectionClause` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-138 | Workflows, Sagas, Tasks und Scheduler | `workflowDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-139 | Workflows, Sagas, Tasks und Scheduler | `workflowStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-140 | Workflows, Sagas, Tasks und Scheduler | `budgetClause` | `structural-schema` | repeat | preserve | none | none |
| PF-141 | Workflows, Sagas, Tasks und Scheduler | `workflowStep` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-142 | Workflows, Sagas, Tasks und Scheduler | `workflowInnerStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-143 | Workflows, Sagas, Tasks und Scheduler | `invocationStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-144 | Workflows, Sagas, Tasks und Scheduler | `approvalStep` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-145 | Workflows, Sagas, Tasks und Scheduler | `approvalClause` | `structural-schema` | single/choice | semantic/preserve | none | reference-position |
| PF-146 | Workflows, Sagas, Tasks und Scheduler | `sagaDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-147 | Workflows, Sagas, Tasks und Scheduler | `sagaStatement` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-148 | Workflows, Sagas, Tasks und Scheduler | `taskDecl` | `structural-schema` | repeat | preserve | none | none |
| PF-149 | Workflows, Sagas, Tasks und Scheduler | `taskClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-150 | Workflows, Sagas, Tasks und Scheduler | `scheduleDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-151 | Workflows, Sagas, Tasks und Scheduler | `scheduleClause` | `structural-schema` | single/choice | preserve | none | none |
| PF-152 | Systeme und Services | `systemDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-153 | Systeme und Services | `systemClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-154 | Systeme und Services | `serviceDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-155 | Systeme und Services | `serviceClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-156 | Systeme und Services | `exposedItem` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-157 | Systeme und Services | `runnableItem` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-158 | Systeme und Services | `clientDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-159 | Systeme und Services | `clientCall` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-160 | Systeme und Services | `tenantDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-161 | Systeme und Services | `channelDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-162 | Ressourcen und Medien | `resourceDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-163 | Ressourcen und Medien | `resourceKind` | `structural-schema` | single/choice | preserve | none | none |
| PF-164 | Ressourcen und Medien | `mediaDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-165 | Ressourcen und Medien | `renditionDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-166 | Ressourcen und Medien | `profileProperty` | `structural-schema` | optional + repeats | preserve | none | none |
| PF-167 | Ressourcen und Medien | `propertyPath` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-168 | Ressourcen und Medien | `profilePropertyValue` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-169 | Offline-Synchronisation | `syncDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-170 | Offline-Synchronisation | `syncClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-171 | Offline-Synchronisation | `syncMode` | `structural-schema` | single/choice | preserve | none | none |
| PF-172 | Offline-Synchronisation | `syncAuthority` | `structural-schema` | single/choice | preserve | none | none |
| PF-173 | Offline-Synchronisation | `operationLogBlock` | `structural-schema` | repeat | preserve | none | none |
| PF-174 | Offline-Synchronisation | `conflictBlock` | `structural-schema` | repeat | preserve | none | none |
| PF-175 | Offline-Synchronisation | `conflictRule` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-176 | Offline-Synchronisation | `mergeStrategy` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-177 | Migration und Deployment | `migrationDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-178 | Migration und Deployment | `migrationStep` | `structural-schema` | repeat | semantic/preserve | none | none |
| PF-179 | Migration und Deployment | `migrationPhase` | `structural-schema` | single/choice | preserve | none | none |
| PF-180 | Migration und Deployment | `deploymentDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-181 | Migration und Deployment | `deploymentClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-182 | Frontend | `frontendDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-183 | Frontend | `frontendClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-184 | Frontend | `routeDecl` | `structural-schema` | optional | preserve | none | reference-position |
| PF-185 | Frontend | `themeDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-186 | Frontend | `componentDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-187 | Frontend | `pageDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-188 | Frontend | `pageClause` | `structural-schema` | optional + repeats | preserve | none | none |
| PF-189 | Frontend | `stateDecl` | `structural-schema` | optional + repeats | preserve | syntax-default-token | reference-position |
| PF-190 | Frontend | `stateKind` | `structural-schema` | single/choice | preserve | none | none |
| PF-191 | Frontend | `dataDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-192 | Frontend | `dataSource` | `structural-schema` | single/choice | preserve | none | none |
| PF-193 | Frontend | `dataModifier` | `structural-schema` | single/choice | preserve | none | reference-position |
| PF-194 | Frontend | `asyncStateClause` | `structural-schema` | optional | preserve | none | none |
| PF-195 | Frontend | `formDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-196 | Frontend | `formClause` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-197 | Frontend | `submitOutcome` | `structural-schema` | optional | semantic/preserve | none | reference-position |
| PF-198 | Frontend | `actionDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-199 | Frontend | `actionStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-200 | Frontend | `syncStatusDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-201 | Frontend | `seoDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-202 | Frontend | `uiStatement` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-203 | Frontend | `uiAtom` | `structural-schema` | single/choice | preserve | none | none |
| PF-204 | Native Deklarationen | `nativeFunctionDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-205 | Native Deklarationen | `nativeComponentDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-206 | Tests und Fixtures | `fixtureDecl` | `structural-schema` | optional + repeats | preserve | none | reference-position |
| PF-207 | Tests und Fixtures | `scenarioDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-208 | Tests und Fixtures | `testDecl` | `structural-schema` | repeat | preserve | none | reference-position |
| PF-209 | Tests und Fixtures | `testStatement` | `structural-schema` | single/choice | semantic/preserve | none | none |
| PF-210 | Tests und Fixtures | `testLeaf` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
| PF-211 | Tests und Fixtures | `testBlock` | `structural-schema` | repeat | semantic/preserve | none | reference-position |
