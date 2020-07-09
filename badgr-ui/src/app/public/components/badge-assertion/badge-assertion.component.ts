import { Component, Injector, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { preloadImageURL } from '../../../common/util/file-util';
import { PublicApiService } from '../../services/public-api.service';
import { LoadedRouteParam } from '../../../common/util/loaded-route-param';
import {
	PublicApiBadgeAssertionWithBadgeClass,
	PublicApiBadgeClass,
	PublicApiIssuer
} from '../../models/public-api.model';
import { EmbedService } from '../../../common/services/embed.service';
import { routerLinkForUrl } from '../public/public.component';
import { QueryParametersService } from '../../../common/services/query-parameters.service';
import { MessageService } from '../../../common/services/message.service';
import { AppConfigService } from '../../../common/app-config.service';
import { saveAs } from 'file-saver';
import { Title } from '@angular/platform-browser';
import { VerifyBadgeDialog } from '../verify-badge-dialog/verify-badge-dialog.component';


@Component({
	templateUrl: './badge-assertion.component.html'
})
export class PublicBadgeAssertionComponent {

	constructor(
		private injector: Injector,
		public embedService: EmbedService,
		public messageService: MessageService,
		public configService: AppConfigService,
		public queryParametersService: QueryParametersService,
		private title: Title

	) {
		title.setTitle(`Assertion - ${this.configService.theme['serviceName'] || "Badgr"}`);
		this.assertionIdParam = this.createLoadedRouteParam();
	}

	readonly issuerImagePlacholderUrl = preloadImageURL(require('../../../../breakdown/static/images/placeholderavatar-issuer.svg') as string);

	readonly badgeLoadingImageUrl = require('../../../../breakdown/static/images/badge-loading.svg') as string;

	readonly badgeFailedImageUrl = require('../../../../breakdown/static/images/badge-failed.svg') as string;

	@ViewChild('verifyBadgeDialog')
	verifyBadgeDialog: VerifyBadgeDialog;

	assertionIdParam: LoadedRouteParam<PublicApiBadgeAssertionWithBadgeClass>;

	assertionId: string;

	awardedToDisplayName: string;

	routerLinkForUrl = routerLinkForUrl;

	tense = {
		'expires': {
			'=1' : 'Expired',
			'=0' : 'Expires',
		},
	};

	get showDownload() {
		return this.queryParametersService.queryStringValue("action") === "download";
	}

	get assertion(): PublicApiBadgeAssertionWithBadgeClass {
		return this.assertionIdParam.value;
	}

	get badgeClass(): PublicApiBadgeClass {
		return this.assertion.badge;
	}

	get issuer(): PublicApiIssuer {
		return this.assertion.badge.issuer;
	}

	get isExpired(): boolean {
		return !this.assertion.expires || new Date(this.assertion.expires) < new Date();
	}

	private get rawUrl() {
		return `${this.configService.apiConfig.baseUrl}/public/assertions/${this.assertionId}`;
	}

	private get rawJsonUrl() {
		return `${this.rawUrl}.json`;
	}

	get rawBakedUrl() {
		return `${this.rawUrl}/baked`;
	}

	get verifyUrl() {
		let url = `${this.configService.assertionVerifyUrl}?url=${this.rawJsonUrl}`;

		for (const IDENTITY_TYPE of ['identity__email', 'identity__url', 'identity__telephone']) {
			const identity = this.queryParametersService.queryStringValue(IDENTITY_TYPE);
			if (identity) {
				url = `${url}&${IDENTITY_TYPE}=${identity}`;
			}
		}
		return url;
	}

	onVerifiedBadgeAssertion(ba){
		this.assertionIdParam = this.createLoadedRouteParam();
	}

	verifyBadge() {
		this.verifyBadgeDialog.openDialog(this.assertion);
	}

	generateFileName(assertion, fileExtension): string {
		return `${assertion.badge.name} - ${assertion.recipient.identity}${fileExtension}`;
	}

	openSaveDialog(assertion): void {
		const xhr = new XMLHttpRequest();
		xhr.open("GET", assertion.image, true);
		xhr.responseType = "blob";
		xhr.onload = (e) => {
			if (xhr.status === 200) {
				const fileExtension = this.mimeToExtension(xhr.response.type);
				const name = this.generateFileName(assertion, fileExtension);
				saveAs(xhr.response, name);
			}
		};
		xhr.send();
	}

	mimeToExtension(mimeType: string): string {
		if (mimeType.indexOf('svg') !== -1) return ".svg";
		if (mimeType.indexOf('png') !== -1) return ".png";
		return "";
	}

	private createLoadedRouteParam() {
		return new LoadedRouteParam(
			this.injector.get(ActivatedRoute),
			"assertionId",
			paramValue => {
				this.assertionId = paramValue;
				const service: PublicApiService = this.injector.get(PublicApiService);
				return service.getBadgeAssertion(paramValue).then(assertion => {
					if (assertion.revoked) {
						if (assertion.revocationReason) {
							this.messageService.reportFatalError("Assertion has been revoked:", assertion.revocationReason);
						} else {
							this.messageService.reportFatalError("Assertion has been revoked.", "");
						}
					} else if (this.showDownload) {
						this.openSaveDialog(assertion);
					}
					if (assertion["extensions:recipientProfile"] && assertion["extensions:recipientProfile"].name) {
						this.awardedToDisplayName = assertion["extensions:recipientProfile"].name;
					}
					return assertion;
				});
			}
		);
	}

}
