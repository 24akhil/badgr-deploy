import {inject, TestBed} from '@angular/core/testing';
import {AppConfigService} from '../app-config.service';
import {CommonEntityManager} from '../../entity-manager/services/common-entity-manager.service';
import {expectRequestAndRespondWith, setupMockResponseReporting} from '../util/mock-response-util.spec';
import {verifyEntitySetWhenLoaded} from '../../common/model/managed-entity-set.spec';

import {MessageService} from '../../common/services/message.service';
import {SessionService} from '../../common/services/session.service';
import {UserProfileManager} from './user-profile-manager.service';
import {UserProfileApiService} from './user-profile-api.service';
import {ApiUserProfile, ApiUserProfileEmail, ApiUserProfileSocialAccount} from '../model/user-profile-api.model';
import {apiProfileEmails, apiSocialAccounts, apiUserProfile, verifyUserProfile} from '../model/user-profile.model.spec';
import {UserProfile} from '../model/user-profile.model';
import {EventsService} from './events.service';
import {HttpClientTestingModule} from '@angular/common/http/testing';
import {MockBackend} from '@angular/http/testing';
import {RequestMethod} from '@angular/http';
import { RouterTestingModule } from "@angular/router/testing";
import { CommonModule } from "@angular/common";
import { BadgrCommonModule, COMMON_IMPORTS } from "../badgr-common.module";
import { COMMON_MOCKS_PROVIDERS_WITH_SUBS } from "../../mocks/mocks.module.spec";

xdescribe('UserProfileManager', () => {
	beforeEach(() => TestBed.configureTestingModule({
		declarations: [  ],
		imports: [
			RouterTestingModule,
			CommonModule,
			BadgrCommonModule,
			...COMMON_IMPORTS,
		],
		providers: [
			...COMMON_MOCKS_PROVIDERS_WITH_SUBS,
		],
	}));

	setupMockResponseReporting();

	beforeEach(inject([ SessionService ], (loginService: SessionService) => {
		loginService.storeToken({ access_token: "MOCKTOKEN" });
	}));

	it('should retrieve user profile',
		inject(
			[ UserProfileManager, SessionService, MockBackend ],
			(userProfileManager: UserProfileManager, loginService: SessionService, mockBackend: MockBackend) => {
				return Promise.all([
					expectUserProfileRequest(mockBackend),
					verifyEntitySetWhenLoaded(
						userProfileManager.userProfileSet,
						[apiUserProfile],
						(e: UserProfile, ae: ApiUserProfile) => verifyUserProfile(e, ae, null, null)
					)
				]);
			}
		)
	);

	it('should retrieve emails',
		inject(
			[ UserProfileManager, SessionService, MockBackend ],
			(userProfileManager: UserProfileManager, loginService: SessionService, mockBackend: MockBackend) => {
				return Promise.all([
					expectUserProfileRequest(mockBackend),
					expectProfileEmailsRequest(mockBackend),
					userProfileManager.userProfilePromise
						.then(p => p.emails.loadedPromise)
						.then(p => verifyEntitySetWhenLoaded(
							userProfileManager.userProfileSet,
							[apiUserProfile],
							(e: UserProfile, ae: ApiUserProfile) => verifyUserProfile(e, ae, apiProfileEmails, null)
						))
				]);
			}
		)
	);

	it('should retrieve social accounts',
		inject(
			[ UserProfileManager, SessionService, MockBackend ],
			(userProfileManager: UserProfileManager, loginService: SessionService, mockBackend: MockBackend) => {
				return Promise.all([
					expectUserProfileRequest(mockBackend),
					expectProfileSocialAccountsRequest(mockBackend),
					userProfileManager.userProfilePromise
						.then(p => p.socialAccounts.loadedPromise)
						.then(p => verifyEntitySetWhenLoaded(
							userProfileManager.userProfileSet,
							[apiUserProfile],
							(e: UserProfile, ae: ApiUserProfile) => verifyUserProfile(e, ae, null, apiSocialAccounts)
						))
				]);
			}
		)
	);
});

function expectUserProfileRequest(
	mockBackend: MockBackend,
	apiProfile: ApiUserProfile = apiUserProfile
) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Get,
		`/v1/user/profile`,
		apiProfile
	);
}

function expectProfileEmailsRequest(
	mockBackend: MockBackend,
	emails: ApiUserProfileEmail[] = apiProfileEmails
) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Get,
		`/v1/user/emails`,
		emails
	);
}

function expectProfileSocialAccountsRequest(
	mockBackend: MockBackend,
	socialAccounts: ApiUserProfileSocialAccount[] = apiSocialAccounts
) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Get,
		`/v1/user/socialaccounts`,
		socialAccounts
	);
}
