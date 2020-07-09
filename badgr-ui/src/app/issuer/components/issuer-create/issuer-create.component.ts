import {Component, OnInit} from '@angular/core';
import {FormBuilder, Validators} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {MessageService} from '../../../common/services/message.service';
import {IssuerManager} from '../../services/issuer-manager.service';
import {BaseAuthenticatedRoutableComponent} from '../../../common/pages/base-authenticated-routable.component';
import {UrlValidator} from '../../../common/validators/url.validator';
import {Title} from '@angular/platform-browser';
import {ApiIssuerForCreation} from '../../models/issuer-api.model';
import {SessionService} from '../../../common/services/session.service';
import {preloadImageURL} from '../../../common/util/file-util';
import {UserProfileManager} from '../../../common/services/user-profile-manager.service';
import {UserProfileEmail} from '../../../common/model/user-profile.model';
import {FormFieldSelectOption} from '../../../common/components/formfield-select';
import {AppConfigService} from '../../../common/app-config.service';
import {typedFormGroup} from '../../../common/util/typed-forms';

@Component({
	selector: 'issuer-create',
	templateUrl: './issuer-create.component.html'
})
export class IssuerCreateComponent extends BaseAuthenticatedRoutableComponent implements OnInit {
	readonly issuerImagePlacholderUrl = preloadImageURL(
		require('../../../../breakdown/static/images/placeholderavatar-issuer.svg') as string
	);

	issuerForm = typedFormGroup()
		.addControl('issuer_name', '', [
			Validators.required,
			Validators.maxLength(1024)
		])
		.addControl('issuer_description', '', [
			Validators.required,
			Validators.maxLength(1024)
		])
		.addControl('issuer_email', '', [
			Validators.required,
			/*Validators.maxLength(75),
                EmailValidator.validEmail*/
		])
		.addControl('issuer_url', '', [
			Validators.required,
			UrlValidator.validUrl
		])
		.addControl('issuer_image', '');

	emails: UserProfileEmail[];
	emailsOptions: FormFieldSelectOption[];
	addIssuerFinished: Promise<unknown>;
	emailsLoaded: Promise<unknown>;

	constructor(
		loginService: SessionService,
		router: Router,
		route: ActivatedRoute,
		protected configService: AppConfigService,
		protected profileManager: UserProfileManager,
		protected formBuilder: FormBuilder,
		protected title: Title,
		protected messageService: MessageService,
		protected issuerManager: IssuerManager
	) {
		super(router, route, loginService);
		title.setTitle(`Create Issuer - ${this.configService.theme['serviceName'] || 'Badgr'}`);

		if(this.configService.theme.dataProcessorTermsLink) {
			this.issuerForm.addControl('agreedTerms', '', Validators.requiredTrue);
		}

		this.emailsLoaded = this.profileManager.userProfilePromise
			.then(profile => profile.emails.loadedPromise)
			.then(emails => {
				this.emails = emails.entities.filter(e => e.verified);
				this.emailsOptions = this.emails.map((e) => {
					return {
						label: e.email,
						value: e.email,
					};
				});
			});
	}

	ngOnInit() {
		super.ngOnInit();
	}

	onSubmit() {
		if (!this.issuerForm.markTreeDirtyAndValidate()) {
			return;
		}

		const formState = this.issuerForm.value;

		const issuer: ApiIssuerForCreation = {
			'name': formState.issuer_name,
			'description': formState.issuer_description,
			'email': formState.issuer_email,
			'url': formState.issuer_url,
		};

		if (formState.issuer_image && String(formState.issuer_image).length > 0) {
			issuer.image = formState.issuer_image;
		}

		this.addIssuerFinished = this.issuerManager.createIssuer(issuer)
			.then((newIssuer) => {
				this.router.navigate(['issuer/issuers', newIssuer.slug]);
				this.messageService.setMessage('Issuer created successfully.', 'success');
			}, error => {
				this.messageService.setMessage('Unable to create issuer: ' + error, 'error');
			}).then(() => this.addIssuerFinished = null);
	}

	get dataProcessorUrl() {
		return this.configService.theme.dataProcessorTermsLink;
	}
}
