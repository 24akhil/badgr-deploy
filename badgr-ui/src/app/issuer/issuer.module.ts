import {NgModule} from '@angular/core';
// import { CommonModule } from '@angular/common';
import {RouterModule} from '@angular/router';

import {BadgrCommonModule, COMMON_IMPORTS} from '../common/badgr-common.module';
import {IssuerListComponent} from './components/issuer-list/issuer-list.component';
import {IssuerCreateComponent} from './components/issuer-create/issuer-create.component';
import {IssuerDetailComponent} from './components/issuer-detail/issuer-detail.component';
import {IssuerEditComponent} from './components/issuer-edit/issuer-edit.component';
import {BadgeClassCreateComponent} from './components/badgeclass-create/badgeclass-create.component';
import {BadgeClassEditComponent} from './components/badgeclass-edit/badgeclass-edit.component';
import {BadgeClassDetailComponent} from './components/badgeclass-detail/badgeclass-detail.component';
import {BadgeClassIssueComponent} from './components/badgeclass-issue/badgeclass-issue.component';
import {BadgeClassIssueBulkAwardComponent} from './components/badgeclass-issue-bulk-award/badgeclass-issue-bulk-award.component';
import {BadgeClassIssueBulkAwardPreviewComponent} from './components/badgeclass-issue-bulk-award-preview/badgeclass-issue-bulk-award-preview.component';
import {BadgeclassIssueBulkAwardConformation} from './components/badgeclass-issue-bulk-award-confirmation/badgeclass-issue-bulk-award-confirmation.component';
import {BadgeclassIssueBulkAwardError} from './components/badgeclass-issue-bulk-award-error/badgeclass-issue-bulk-award-error.component';
import {BadgeInstanceManager} from './services/badgeinstance-manager.service';
import {BadgeInstanceApiService} from './services/badgeinstance-api.service';
import {BadgeClassManager} from './services/badgeclass-manager.service';
import {BadgeClassApiService} from './services/badgeclass-api.service';
import {IssuerManager} from './services/issuer-manager.service';
import {IssuerApiService} from './services/issuer-api.service';
import {BadgeSelectionDialog} from './components/badge-selection-dialog/badge-selection-dialog.component';
import {BadgeStudioComponent} from './components/badge-studio/badge-studio.component';
import {BadgeClassIssueBulkAwardImportComponent} from './components/badgeclass-issue-bulk-award-import/badgeclass-issue-bulk-award-import.component';
import {CommonEntityManagerModule} from '../entity-manager/entity-manager.module';
import {IssuerStaffComponent} from './components/issuer-staff/issuer-staff.component';
import {BadgeClassEditFormComponent} from './components/badgeclass-edit-form/badgeclass-edit-form.component';
import {IssuerStaffCreateDialogComponent} from './components/issuer-staff-create-dialog/issuer-staff-create-dialog.component';

const routes = [
	/* Issuer */
	{
		path: "",
		component: IssuerListComponent
	},
	{
		path: "create",
		component: IssuerCreateComponent
	},
	{
		path: "issuers/:issuerSlug",
		component: IssuerDetailComponent
	},
	{
		path: "issuers/:issuerSlug/edit",
		component: IssuerEditComponent
	},
	{
		path: "issuers/:issuerSlug/staff",
		component: IssuerStaffComponent
	},
	{
		path: "issuers/:issuerSlug/badges/create",
		component: BadgeClassCreateComponent
	},
	{
		path: "issuers/:issuerSlug/badges/:badgeSlug",
		component: BadgeClassDetailComponent
	},
	{
		path: "issuers/:issuerSlug/badges/:badgeSlug/edit",
		component: BadgeClassEditComponent
	},
	{
		path: "issuers/:issuerSlug/badges/:badgeSlug/issue",
		component: BadgeClassIssueComponent
	},
	{
		path: "issuers/:issuerSlug/badges/:badgeSlug/bulk-import",
		component: BadgeClassIssueBulkAwardComponent
	},
	{
		path: "**",
		component: IssuerListComponent
	},
];

@NgModule({
	imports: [
		...COMMON_IMPORTS,
		BadgrCommonModule,
		CommonEntityManagerModule,
		RouterModule.forChild(routes)
	],
	declarations: [
		BadgeClassCreateComponent,
		BadgeClassEditComponent,
		BadgeClassEditFormComponent,
		BadgeClassDetailComponent,
		BadgeClassIssueComponent,

		BadgeClassIssueBulkAwardComponent,
		BadgeClassIssueBulkAwardImportComponent,
		BadgeClassIssueBulkAwardPreviewComponent,
		BadgeclassIssueBulkAwardError,
		BadgeclassIssueBulkAwardConformation,

		BadgeClassDetailComponent,
		BadgeClassIssueComponent,
		BadgeSelectionDialog,
		BadgeStudioComponent,

		IssuerCreateComponent,
		IssuerDetailComponent,
		IssuerEditComponent,
		IssuerStaffComponent,
		IssuerListComponent,

		IssuerStaffCreateDialogComponent,
	],
	exports: [],
	providers: [
		BadgeClassApiService,
		BadgeClassManager,
		BadgeInstanceApiService,
		BadgeInstanceManager,
		IssuerApiService,
		IssuerManager,
	]
})
export class IssuerModule {}
