import {Component, OnInit, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';

import {BaseAuthenticatedRoutableComponent} from '../../../common/pages/base-authenticated-routable.component';

import {SessionService} from '../../../common/services/session.service';
import {MessageService} from '../../../common/services/message.service';
import {IssuerManager} from '../../services/issuer-manager.service';
import {Title} from '@angular/platform-browser';
import {Issuer, IssuerStaffMember, issuerStaffRoles} from '../../models/issuer.model';
import {preloadImageURL} from '../../../common/util/file-util';
import {FormFieldSelectOption} from '../../../common/components/formfield-select';
import {BadgrApiFailure} from '../../../common/services/api-failure';
import {CommonDialogsService} from '../../../common/services/common-dialogs.service';
import {UserProfileManager} from '../../../common/services/user-profile-manager.service';
import {UserProfileEmail} from '../../../common/model/user-profile.model';
import {IssuerStaffRoleSlug} from '../../models/issuer-api.model';
import {AppConfigService} from '../../../common/app-config.service';
import {LinkEntry} from '../../../common/components/bg-breadcrumbs/bg-breadcrumbs.component';
import {IssuerStaffCreateDialogComponent} from '../issuer-staff-create-dialog/issuer-staff-create-dialog.component';


@Component({
	templateUrl: './issuer-staff.component.html'
})
export class IssuerStaffComponent extends BaseAuthenticatedRoutableComponent implements OnInit {
	get issuerStaffRoleOptions() {
		return this._issuerStaffRoleOptions || (this._issuerStaffRoleOptions = issuerStaffRoles.map(r => ({
			label: r.label,
			value: r.slug
		})));
	}

	get isCurrentUserIssuerOwner() {
		return this.issuer && this.issuer.currentUserStaffMember && this.issuer.currentUserStaffMember.isOwner;
	}

	readonly issuerImagePlaceHolderUrl = preloadImageURL(require(
		'../../../../breakdown/static/images/placeholderavatar-issuer.svg') as string
	);

	issuer: Issuer;
	issuerSlug: string;
	issuerLoaded: Promise<Issuer>;
	profileEmailsLoaded: Promise<UserProfileEmail[]>;
	profileEmails: UserProfileEmail[] = [];

	@ViewChild("issuerStaffCreateDialog")
	issuerStaffCreateDialog: IssuerStaffCreateDialogComponent;

	breadcrumbLinkEntries: LinkEntry[] = [];

	private _issuerStaffRoleOptions: FormFieldSelectOption[];

	constructor(
		loginService: SessionService,
		router: Router,
		route: ActivatedRoute,
		protected title: Title,
		protected messageService: MessageService,
		protected issuerManager: IssuerManager,
		protected profileManager: UserProfileManager,
		protected configService: AppConfigService,
		protected dialogService: CommonDialogsService,
	) {
		super(router, route, loginService);
		title.setTitle(`Manage Issuer Staff - ${this.configService.theme['serviceName'] || "Badgr"}`);

		this.issuerSlug = this.route.snapshot.params['issuerSlug'];
		this.issuerLoaded = this.issuerManager.issuerBySlug(this.issuerSlug)
			.then(issuer => {
				this.issuer = issuer;
				this.breadcrumbLinkEntries = [
					{title: 'Issuers', routerLink: ['/issuer']},
					{title: issuer.name, routerLink: ['/issuer/issuers', this.issuerSlug]},
					{title: this.isCurrentUserIssuerOwner ? 'Manage Staff' : 'View Staff'}
				];
				return issuer;
			});

		this.profileEmailsLoaded = this.profileManager.userProfilePromise
			.then(profile => profile.emails.loadedPromise)
			.then(emails => this.profileEmails = emails.entities);

	}

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	// Staff Editing

	changeMemberRole(
		member: IssuerStaffMember,
		roleSlug: IssuerStaffRoleSlug
	) {
		member.roleSlug = roleSlug;

		member.save().then(
			() => {
				this.messageService.reportMajorSuccess(`${member.nameLabel}'s role has been changed to ${member.roleInfo.label}`);
			},
			error => this.messageService.reportHandledError(`Failed to edit member: ${BadgrApiFailure.from(error).firstMessage}`)
		);
	}

	memberId(member){
		return member.email || member.url || member.telephone;
	}

	async removeMember(member: IssuerStaffMember) {
		if (!await this.dialogService.confirmDialog.openTrueFalseDialog({
			dialogTitle: `Remove ${member.nameLabel}?`,
			dialogBody: `${member.nameLabel} is ${member.roleInfo.indefiniteLabel} of ${this.issuer.name}. Are you sure you want to remove them from this role?`,
			resolveButtonLabel: `Remove ${member.nameLabel}`,
			rejectButtonLabel: "Cancel",
		})) {
			return;
		}

		return member.remove().then(
			() => this.messageService.reportMinorSuccess(`Removed ${member.nameLabel} from ${this.issuer.name}`),
			error => this.messageService.reportHandledError(`Failed to add member: ${BadgrApiFailure.from(error).firstMessage}`)
		);
	}

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	// Staff Creation

	addStaff() {
		this.issuerStaffCreateDialog.openDialog();
		// this.issuerStaffCreateDialog._issuerStaffRoleOptions = this._issuerStaffRoleOptions;
		this.issuerStaffCreateDialog.issuer = this.issuer;
	}

}
