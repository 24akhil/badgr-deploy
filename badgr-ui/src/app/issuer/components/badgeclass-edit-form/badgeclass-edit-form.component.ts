import {Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {AbstractControl, FormBuilder, Validators} from '@angular/forms';
import {Title} from '@angular/platform-browser';

import {BaseAuthenticatedRoutableComponent} from '../../../common/pages/base-authenticated-routable.component';

import {SessionService} from '../../../common/services/session.service';
import {MessageService} from '../../../common/services/message.service';

import {ApiBadgeClassForCreation, BadgeClassExpiresDuration} from '../../models/badgeclass-api.model';
import {BadgeClassManager} from '../../services/badgeclass-manager.service';
import {IssuerManager} from '../../services/issuer-manager.service';
import {BadgeStudioComponent} from '../badge-studio/badge-studio.component';
import {BgFormFieldImageComponent} from '../../../common/components/formfield-image';
import {UrlValidator} from '../../../common/validators/url.validator';
import {CommonDialogsService} from '../../../common/services/common-dialogs.service';
import {BadgeClass} from '../../models/badgeclass.model';
import {AppConfigService} from '../../../common/app-config.service';
import {typedFormGroup} from '../../../common/util/typed-forms';

@Component({
	selector: 'badgeclass-edit-form',
	templateUrl: './badgeclass-edit-form.component.html'
})
export class BadgeClassEditFormComponent extends BaseAuthenticatedRoutableComponent implements OnInit {

	@Input()
	set badgeClass(badgeClass: BadgeClass) {
		if (this.existingBadgeClass !== badgeClass) {
			this.existingBadgeClass = badgeClass;
			this.initFormFromExisting();
		}
	}

	get badgeClass() {
		return this.existingBadgeClass;
	}

	get alignmentFieldDirty() {
		return this.badgeClassForm.controls.badge_criteria_text.dirty || this.badgeClassForm.controls.badge_criteria_url.dirty;
	}

	readonly badgeClassPlaceholderImageUrl = require('../../../../breakdown/static/images/placeholderavatar.svg');

	savePromise: Promise<BadgeClass> | null = null;
	badgeClassForm = typedFormGroup(this.criteriaRequired.bind(this))
		.addControl('badge_name', '', [Validators.required, Validators.maxLength(255)])
		.addControl('badge_image', '', Validators.required)
		.addControl('badge_description', '', Validators.required)
		.addControl('badge_criteria_url', '')
		.addControl('badge_criteria_text', '')
		.addArray(
			'alignments',
			typedFormGroup()
				.addControl('target_name', '', Validators.required)
				.addControl('target_url', '', [Validators.required, UrlValidator.validUrl])
				.addControl('target_description', '')
				.addControl('target_framework', '')
				.addControl('target_code', '')
		);

	@ViewChild('badgeStudio')
	badgeStudio: BadgeStudioComponent;

	@ViewChild('imageField')
	imageField: BgFormFieldImageComponent;

	@ViewChild('newTagInput')
	newTagInput: ElementRef<HTMLInputElement>;

	@ViewChild('formElem')
	formElem: ElementRef<HTMLFormElement>;

	existingBadgeClass: BadgeClass | null = null;

	@Output()
	save = new EventEmitter<Promise<BadgeClass>>();

	@Output()
	cancel = new EventEmitter<void>();

	@Input()
	issuerSlug: string;

	@Input()
	submitText: string;

	@Input()
	submittingText: string;

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	// Tags
	tagsEnabled = false;
	tags = new Set<string>();

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	// Expiration
	expirationEnabled = false;
	expirationForm = typedFormGroup()
		.addControl('expires_amount', '', [Validators.required, this.positiveInteger, Validators.max(1000)])
		.addControl('expires_duration', '', Validators.required);

	durationOptions: { [key in BadgeClassExpiresDuration]: string } = {
		days: 'Days',
		weeks: 'Weeks',
		months: 'Months',
		years: 'Years'
	};

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	// Alignments
	alignmentsEnabled = false;
	showAdvanced: boolean[] = [false];

	constructor(
		sessionService: SessionService,
		router: Router,
		route: ActivatedRoute,
		protected fb: FormBuilder,
		protected title: Title,
		protected messageService: MessageService,
		protected issuerManager: IssuerManager,
		private configService: AppConfigService,
		protected badgeClassManager: BadgeClassManager,
		protected dialogService: CommonDialogsService,
		protected componentElem: ElementRef<HTMLElement>
	) {
		super(router, route, sessionService);
		title.setTitle(`Create Badge - ${this.configService.theme['serviceName'] || 'Badgr'}`);
	}

	initFormFromExisting() {
		const badgeClass = this.existingBadgeClass;

		if (badgeClass) {
			this.badgeClassForm.setValue(
				{
					badge_name: badgeClass.name,
					badge_image: badgeClass.image,
					badge_description: badgeClass.description,
					badge_criteria_url: badgeClass.criteria_url,
					badge_criteria_text: badgeClass.criteria_text,
					alignments: this.badgeClass.alignments.map(alignment => ({
						target_name: alignment.target_name,
						target_url: alignment.target_url,
						target_description: alignment.target_description,
						target_framework: alignment.target_framework,
						target_code: alignment.target_code,
					}))
				}
			);

			this.tags = new Set();
			this.badgeClass.tags.forEach(t => this.tags.add(t));

			this.tagsEnabled = this.tags.size > 0;
			this.alignmentsEnabled = this.badgeClass.alignments.length > 0;
			if (badgeClass.expiresAmount && badgeClass.expiresDuration) {
				this.enableExpiration();
			}
		}
	}

	ngOnInit() {
		super.ngOnInit();
	}

	enableTags() {
		this.tagsEnabled = true;
	}

	disableTags() {
		this.tagsEnabled = false;
	}

	addTag() {
		const newTag = ((this.newTagInput.nativeElement as HTMLInputElement).value || '').trim().toLowerCase();

		if (newTag.length > 0) {
			this.tags.add(newTag);
			(this.newTagInput.nativeElement as HTMLInputElement).value = '';
		}
	}

	handleTagInputKeyPress(event: KeyboardEvent) {
		if (event.keyCode === 13 /* Enter */) {
			this.addTag();
			this.newTagInput.nativeElement.focus();
			event.preventDefault();
		}
	}

	removeTag(tag: string) {
		this.tags.delete(tag);
	}

	enableExpiration() {
		const initialAmount = this.badgeClass ? this.badgeClass.expiresAmount : '';
		const initialDuration = this.badgeClass ? this.badgeClass.expiresDuration || '' : '';

		this.expirationEnabled = true;

		this.expirationForm.setValue({
			expires_amount: initialAmount.toString(),
			expires_duration: initialDuration.toString(),
		});
	}

	disableExpiration() {
		this.expirationEnabled = false;
		this.expirationForm.reset();
	}

	enableAlignments() {
		this.alignmentsEnabled = true;
		if (this.badgeClassForm.controls.alignments.length === 0) {
			this.addAlignment();
		}
	}

	addAlignment() {
		this.badgeClassForm.controls.alignments.addFromTemplate();
	}

	async disableAlignments() {
		const isPlural = this.badgeClassForm.value.alignments.length > 1;
		if (!await this.dialogService.confirmDialog.openTrueFalseDialog({
			dialogTitle: `Remove Alignment${isPlural ? 's' : ''}?`,
			dialogBody: `Are you sure you want to remove ${isPlural ? "these alignments?" : "this alignment?"} This action cannot be undone.`,
			resolveButtonLabel: 'Remove',
			rejectButtonLabel: 'Cancel'
		})) return;
		this.alignmentsEnabled = false;
		this.badgeClassForm.setValue(
				{...this.badgeClassForm.value, alignments: []});
	}

	async removeAlignment(alignment: this['badgeClassForm']['controls']['alignments']['controls'][0]) {
		const value = alignment.value;

		if ((value.target_name || '').trim().length > 0
			|| (value.target_url || '').trim().length > 0
			|| (value.target_description || '').trim().length > 0
			|| (value.target_framework || '').trim().length > 0
			|| (value.target_code || '').trim().length > 0
		) {
			if (!await this.dialogService.confirmDialog.openTrueFalseDialog({
				dialogTitle: 'Remove Alignment?',
				dialogBody: 'Are you sure you want to remove this alignment? This action cannot be undone.',
				resolveButtonLabel: 'Remove Alignment',
				rejectButtonLabel: 'Cancel'
			})) return;
		}

		this.badgeClassForm.controls.alignments.removeAt(this.badgeClassForm.controls.alignments.controls.indexOf(alignment));
	}

	//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

	criteriaRequired(): { [id: string]: boolean } | null {
		if (!this.badgeClassForm) return null;

		const value = this.badgeClassForm.value;

		const criteriaUrl = (value.badge_criteria_url || '').trim();
		const criteriaText = (value.badge_criteria_text || '').trim();

		if (!criteriaUrl.length && !criteriaText.length) {
			return {'criteriaRequired': true};
		} else {
			return null;
		}
	}

	async onSubmit() {
		this.badgeClassForm.markTreeDirty();
		if (this.expirationEnabled) {
			this.expirationForm.markTreeDirty();
		}

		if (!this.badgeClassForm.valid || (this.expirationEnabled && !this.expirationForm.valid)) {
			const firstInvalidInput = this.formElem.nativeElement.querySelector('.ng-invalid,.dropzone-is-error,.u-text-error');
			if (firstInvalidInput) {
				if (typeof firstInvalidInput['focus'] === 'function') {
					firstInvalidInput['focus']();
				}

				firstInvalidInput.scrollIntoView({behavior: 'smooth'});
			}
			return;
		}

		const formState = this.badgeClassForm.value;
		const expirationState = this.expirationEnabled ? this.expirationForm.value : undefined;

		if (this.existingBadgeClass) {
			this.existingBadgeClass.name = formState.badge_name;
			this.existingBadgeClass.description = formState.badge_description;
			this.existingBadgeClass.image = formState.badge_image;
			this.existingBadgeClass.criteria_text = formState.badge_criteria_text;
			this.existingBadgeClass.criteria_url = formState.badge_criteria_url;
			this.existingBadgeClass.alignments = this.alignmentsEnabled ? formState.alignments : [];
			this.existingBadgeClass.tags = this.tagsEnabled ? Array.from(this.tags) : [];
			if (this.expirationEnabled) {
				this.existingBadgeClass.expiresDuration = expirationState.expires_duration as BadgeClassExpiresDuration;
				this.existingBadgeClass.expiresAmount = parseInt(expirationState.expires_amount, 10);
			} else {
				this.existingBadgeClass.clearExpires();
			}

			this.savePromise = this.existingBadgeClass.save();
		} else {
			const badgeClassData = {
				name: formState.badge_name,
				description: formState.badge_description,
				image: formState.badge_image,
				criteria_text: formState.badge_criteria_text,
				criteria_url: formState.badge_criteria_url,
				tags: this.tagsEnabled ? Array.from(this.tags) : [],
				alignment: this.alignmentsEnabled ? formState.alignments : [],
			} as ApiBadgeClassForCreation;
			if (this.expirationEnabled) {
				badgeClassData.expires = {
					duration: expirationState.expires_duration as BadgeClassExpiresDuration,
					amount: parseInt(expirationState.expires_amount, 10)
				};
			}


			this.savePromise = this.badgeClassManager.createBadgeClass(this.issuerSlug, badgeClassData);
		}

		this.save.emit(this.savePromise);
	}

	cancelClicked() {
		this.cancel.emit();
	}

	generateRandomImage() {
		this.badgeStudio.generateRandom().then(imageUrl => this.imageField.useDataUrl(imageUrl, 'Auto-generated image'));
	}

	positiveInteger(control: AbstractControl) {
		const val = parseInt(control.value, 10);
		if (isNaN(val) || val < 1) {
			return {'expires_amount': 'Must be a positive integer'};
		}
	}
}

