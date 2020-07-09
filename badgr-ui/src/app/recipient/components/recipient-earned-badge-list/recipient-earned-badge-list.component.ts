import {Component, OnInit, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {Title} from '@angular/platform-browser';

import {CommonDialogsService} from '../../../common/services/common-dialogs.service';
import {StringMatchingUtil} from '../../../common/util/string-matching-util';
import {BaseAuthenticatedRoutableComponent} from '../../../common/pages/base-authenticated-routable.component';
import {groupIntoArray, groupIntoObject} from '../../../common/util/array-reducers';
import {MessageService} from '../../../common/services/message.service';
import {SessionService} from '../../../common/services/session.service';

import {AddBadgeDialogComponent} from '../add-badge-dialog/add-badge-dialog.component';
import {RecipientBadgeManager} from '../../services/recipient-badge-manager.service';
import {ApiRecipientBadgeIssuer} from '../../models/recipient-badge-api.model';
import {RecipientBadgeInstance} from '../../models/recipient-badge.model';
import {badgeShareDialogOptionsFor} from '../recipient-earned-badge-detail/recipient-earned-badge-detail.component';
import {UserProfileManager} from '../../../common/services/user-profile-manager.service';
import {AppConfigService} from '../../../common/app-config.service';
import { ImportLauncherDirective } from "../../../mozz-transition/directives/import-launcher/import-launcher.directive";
import { LinkEntry } from "../../../common/components/bg-breadcrumbs/bg-breadcrumbs.component";

type BadgeDispay = "grid" | "list" ;

@Component({
	selector: 'recipient-earned-badge-list',
	templateUrl: './recipient-earned-badge-list.component.html'
})

export class RecipientEarnedBadgeListComponent extends BaseAuthenticatedRoutableComponent implements OnInit {
	readonly noBadgesImageUrl = require('@concentricsky/badgr-style/dist/images/image-empty-backpack.svg');
	readonly badgeLoadingImageUrl = require('../../../../breakdown/static/images/badge-loading.svg');
	readonly badgeFailedImageUrl = require('../../../../breakdown/static/images/badge-failed.svg');

	@ViewChild("addBadgeDialog")
	addBadgeDialog: AddBadgeDialogComponent;

	@ViewChild(ImportLauncherDirective) importLauncherDirective:ImportLauncherDirective;

	allBadges: RecipientBadgeInstance[] = [];
	badgesLoaded: Promise<unknown>;
	allIssuers: ApiRecipientBadgeIssuer[] = [];

	badgeResults: BadgeResult[] = [];
	issuerResults: MatchingIssuerBadges[] = [];
	badgeClassesByIssuerId: { [issuerUrl: string]: RecipientBadgeInstance[] };

	mozillaTransitionOver = true;
	mozillaFeatureEnabled = this.configService.featuresConfig[
		"enableComingFromMozilla"
	];
	maxDisplayedResults = 100;

	crumbs: LinkEntry[] = [{title: 'Backpack', routerLink: ['/recipient/badges']},];

	private _badgesDisplay: BadgeDispay = "grid";
	get badgesDisplay() {return this._badgesDisplay;}
	set badgesDisplay(val: BadgeDispay) {
		this._badgesDisplay = val;
		// this.updateResults();
		this.saveDisplayState();
	}

	private _groupByIssuer = false;
	get groupByIssuer() {return this._groupByIssuer;}
	set groupByIssuer(val: boolean) {
		this._groupByIssuer = val;
		this.saveDisplayState();
		this.updateResults();
	}

	private _searchQuery = "";
	get searchQuery() { return this._searchQuery; }
	set searchQuery(query) {
		this._searchQuery = query;
		this.saveDisplayState();
		this.updateResults();
	}

	constructor(
		router: Router,
		route: ActivatedRoute,
		sessionService: SessionService,

		private title: Title,
		private dialogService: CommonDialogsService,
		private messageService: MessageService,
		private recipientBadgeManager: RecipientBadgeManager,
		public configService: AppConfigService,
		private profileManager: UserProfileManager
	) {
		super(router, route, sessionService);

		title.setTitle(`Backpack - ${this.configService.theme['serviceName'] || "Badgr"}`);

		this.badgesLoaded = this.recipientBadgeManager.recipientBadgeList.loadedPromise
			.catch(e => this.messageService.reportAndThrowError("Failed to load your badges", e));

		this.recipientBadgeManager.recipientBadgeList.changed$.subscribe(
			badges => this.updateBadges(badges.entities)
		);

		if (sessionService.isLoggedIn) {
			// force a refresh of the userProfileSet now that we are authenticated
			profileManager.userProfileSet.updateList().then(p => {
				if (profileManager.userProfile.agreedTermsVersion !== profileManager.userProfile.latestTermsVersion) {
					dialogService.newTermsDialog.openDialog();
				}
			});
		}

		this.mozillaTransitionOver = !!localStorage.getItem('mozillaTransitionOver') || false;

		this.restoreDisplayState();
	}

	// NOTE: Mozz import functionality
	launchImport = ($event: Event) => {
		$event.preventDefault();
		this.importLauncherDirective.insert();
	};
	hideMozz = ($event: Event) => {
		$event.preventDefault();
		this.mozillaTransitionOver = true;
		localStorage.setItem('mozillaTransitionOver', 'true');
	};

	restoreDisplayState() {
		try {
			const state: object = JSON.parse(window.localStorage["recipient-earned-badge-list-viewstate"]);

			this.groupByIssuer = state["groupByIssuer"];
			this.searchQuery = state["searchQuery"];
			this.badgesDisplay = state["badgesDisplay"];
		} catch (e) {
			// Bad serialization
		}
	}

	saveDisplayState() {
		try {
			window.localStorage["recipient-earned-badge-list-viewstate"] = JSON.stringify({
				groupByIssuer: this.groupByIssuer,
				searchQuery: this.searchQuery,
				badgesDisplay: this.badgesDisplay
			});
		} catch (e) {
			// We can't always save to local storage
		}
	}

	ngOnInit() {
		super.ngOnInit();
		if(this.route.snapshot.routeConfig.path === "badges/import") this.launchImport(new Event('click'));
	}

	addBadge() {
		this.addBadgeDialog.openDialog({})
			.then(
				() => {},
				() => {}
			);
	}

	shareBadge(badge: RecipientBadgeInstance) {
		badge.markAccepted();

		this.dialogService.shareSocialDialog.openDialog(badgeShareDialogOptionsFor(badge));
	}

	deleteBadge(badge: RecipientBadgeInstance) {
		this.dialogService.confirmDialog.openResolveRejectDialog({
			dialogTitle: "Confirm Remove",
			dialogBody: `Are you sure you want to remove ${badge.badgeClass.name} from your badges?`,
			rejectButtonLabel: "Cancel",
			resolveButtonLabel: "Remove Badge"
		}).then(
			() => this.recipientBadgeManager.deleteRecipientBadge(badge),
			() => {}
		);
	}

	private updateBadges(allBadges: RecipientBadgeInstance[]) {
		this.badgeClassesByIssuerId = allBadges
			.reduce(groupIntoObject<RecipientBadgeInstance>(b => b.issuerId), {});

		this.allIssuers = allBadges
			.reduce(groupIntoArray<RecipientBadgeInstance, string>(b => b.issuerId), [])
			.map(g => g.values[0].badgeClass.issuer);

		this.allBadges = allBadges;

		this.updateResults();
	}

	private updateResults() {
		// Clear Results
		this.badgeResults.length = 0;
		this.issuerResults.length = 0;

		const issuerResultsByIssuer: {[issuerUrl: string]: MatchingIssuerBadges} = {};

		const addBadgeToResults = (badge: RecipientBadgeInstance) => {
			// Restrict Length
			if (this.badgeResults.length > this.maxDisplayedResults) {
				return false;
			}

			let issuerResults = issuerResultsByIssuer[ badge.issuerId ];

			if (!issuerResults) {
				issuerResults = issuerResultsByIssuer[ badge.issuerId ] = new MatchingIssuerBadges(
					badge.issuerId,
					badge.badgeClass.issuer
				);

				// append result to the issuerResults array bound to the view template.
				this.issuerResults.push(issuerResults);
			}

			issuerResults.addBadge(badge);

			if (!this.badgeResults.find(r => r.badge === badge)) {
				// appending the results to the badgeResults array bound to the view template.
				this.badgeResults.push(new BadgeResult(badge, issuerResults.issuer));
			}

			return true;
		};

		const addIssuerToResults = (issuer: ApiRecipientBadgeIssuer) => {
			(this.badgeClassesByIssuerId[ issuer.id ] || []).forEach(addBadgeToResults);
		};

		this.allIssuers
			.filter(MatchingAlgorithm.issuerMatcher(this.searchQuery))
			.forEach(addIssuerToResults);

		this.allBadges
			.filter(MatchingAlgorithm.badgeMatcher(this._searchQuery))
			.forEach(addBadgeToResults);

		this.badgeResults.sort((a, b) => b.badge.issueDate.getTime() - a.badge.issueDate.getTime());
		this.issuerResults.forEach(r => r.badges.sort((a, b) => b.issueDate.getTime() - a.issueDate.getTime()));
	}
}

class BadgeResult {
	constructor(public badge: RecipientBadgeInstance, public issuer: ApiRecipientBadgeIssuer) {}
}

class MatchingIssuerBadges {
	constructor(
		public issuerId: string,
		public issuer: ApiRecipientBadgeIssuer,
		public badges: RecipientBadgeInstance[] = []
	) {}

	addBadge(badge: RecipientBadgeInstance) {
		if (badge.issuerId === this.issuerId) {
			if (this.badges.indexOf(badge) < 0) {
				this.badges.push(badge);
			}
		}
	}
}

class MatchingAlgorithm {
	static issuerMatcher(inputPattern: string): (issuer: ApiRecipientBadgeIssuer) => boolean {
		const patternStr = StringMatchingUtil.normalizeString(inputPattern);
		const patternExp = StringMatchingUtil.tryRegExp(patternStr);

		return issuer => (
			StringMatchingUtil.stringMatches(issuer.name, patternStr, patternExp)
		);
	}

	static badgeMatcher(inputPattern: string): (badge: RecipientBadgeInstance) => boolean {
		const patternStr = StringMatchingUtil.normalizeString(inputPattern);
		const patternExp = StringMatchingUtil.tryRegExp(patternStr);

		return badge => (
			StringMatchingUtil.stringMatches(badge.badgeClass.name, patternStr, patternExp)
		);
	}
}
