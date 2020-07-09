import {Component, EventEmitter, Input, Output} from '@angular/core';

declare function require(path: string): string;

@Component({
	selector: 'bg-badgecard',
	host: {'class': 'badgecard'},
	template: `
		<div class="badgecard-x-status badgestatus badgestatus-{{mostRelevantStatus}}" *ngIf="mostRelevantStatus">
			{{mostRelevantStatus}}
		</div>

		<div class="badgecard-x-body">
			<div class="badgecard-x-image">
				<img class="badgeimage badgeimage-{{mostRelevantStatus}}"
					[loaded-src]="badgeImage"
					[loading-src]="badgeLoadingImageUrl"
					[error-src]="badgeFailedImageUrl"
					width="80" />
			</div>
			<a *ngIf="badgeSlug" class="badgecard-x-title u-text-breakword" [routerLink]="['../earned-badge', badgeSlug]">{{ badgeTitle }}</a>
			<a *ngIf="publicUrl" class="badgecard-x-title" [href]="publicUrl">{{ badgeTitle }}</a>
			<div class="badgecard-x-issuer">{{ issuerTitle }}</div>
			<p class="badgecard-x-desc" [truncatedText]="badgeDescription" [maxLength]="100"></p>
		</div>
		<div class="badgecard-x-footer">
			<div class="badgecard-x-date">
				<time [date]="badgeIssueDate" format="mediumDate"></time>
			</div>

			<!-- Show Verify or Share Button unless public -->
			<button class="badgecard-x-sharelink" *ngIf="!verifyUrl && !public && (mostRelevantStatus !== 'pending')"
					(click)="shareClicked.emit($event)">
				Share
			</button>
			<a class="badgecard-x-sharelink" *ngIf="verifyUrl" [href]="verifyUrl">
				Verify
			</a>
		</div>
	`
})
export class BgBadgecard {
	readonly badgeLoadingImageUrl = require('../../../breakdown/static/images/badge-loading.svg');
	readonly badgeFailedImageUrl = require('../../../breakdown/static/images/badge-failed.svg');
	@Input() badgeSlug: string;
	@Input() publicUrl: string;
	@Input() badgeImage: string;
	@Input() badgeTitle: string;
	@Input() badgeDescription: string;
	@Input() badgeIssueDate: string;
	@Input() issuerTitle: string;
	@Input() mostRelevantStatus: "expired" | "new" | "pending" | undefined;
	@Input() verifyUrl: string;
	@Input() public = false;
	@Output() shareClicked = new EventEmitter<MouseEvent>();
}
