import {Component} from '@angular/core';
import {MessageService} from '../services/message.service';
import {OAuthManager} from '../services/oauth-manager.service';


@Component({
	selector: 'oauth-banner',
	host: {
		"[class]": "'authlink'"
	},
	template: `
		<ng-template [ngIf]="isAuthorizing">
			<div><img [src]="appInfo.image"
			          alt="{{ appInfo.name }} Logo"
			          height="72"></div>
			<div><img [src]="authLinkBadgrLogoSrc" height="72" alt="Logo"></div>
		</ng-template>
	`
})
export class OAuthBannerComponent {
	readonly authLinkBadgrLogoSrc = require("../../../breakdown/static/images/logo.svg");

	get authInfo() {
		return this.oAuthManager.currentAuthorization;
	}

	get appInfo() {
		return this.oAuthManager.currentAuthorization.application;
	}

	get isAuthorizing() {
		return this.oAuthManager.isAuthorizationInProgress;
	}

	constructor(
		private messageService: MessageService,
		public oAuthManager: OAuthManager,
	) { }
}
