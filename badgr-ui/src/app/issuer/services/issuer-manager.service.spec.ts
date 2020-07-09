import {inject, TestBed} from '@angular/core/testing';
import {AppConfigService} from '../../common/app-config.service';
import {MockBackend, MockConnection} from '@angular/http/testing';
import {BaseRequestOptions, Http, RequestMethod} from '@angular/http';
import {CommonEntityManager} from '../../entity-manager/services/common-entity-manager.service';
import {expectRequest, expectRequestAndRespondWith, setupMockResponseReporting} from '../../common/util/mock-response-util.spec';
import {IssuerApiService} from './issuer-api.service';
import {IssuerManager} from './issuer-manager.service';
import {ApiIssuer, ApiIssuerStaff, ApiIssuerStaffOperation} from '../models/issuer-api.model';
import {apiIssuer1, apiIssuer2, apiIssuer3} from '../models/issuer.model.spec';
import {verifyEntitySetWhenLoaded, verifyManagedEntitySet} from '../../common/model/managed-entity-set.spec';
import {BadgeClassApiService} from './badgeclass-api.service';
import {BadgeClassManager} from './badgeclass-manager.service';
import {MessageService} from '../../common/services/message.service';
import {SessionService} from '../../common/services/session.service';
import {first} from 'rxjs/operators';

xdescribe('IssuerManager', () => {
	beforeEach(() => TestBed.configureTestingModule({
		declarations: [  ],
		providers: [
			AppConfigService,
			MockBackend,
			BaseRequestOptions,
			MessageService,
			{ provide: 'config', useValue: { api: { baseUrl: '' }, features: {} } },
			{
				provide: Http,
				useFactory: (backend, options) => new Http(backend, options),
				deps: [ MockBackend, BaseRequestOptions ]
			},

			SessionService,
			CommonEntityManager,
			IssuerApiService,
			IssuerManager,

		  BadgeClassApiService,
		  BadgeClassManager,

		  MessageService
		],
		imports: [ ]
	}));

	setupMockResponseReporting();

	beforeEach(inject([ SessionService ], (loginService: SessionService) => {
		loginService.storeToken({ access_token: "MOCKTOKEN" });
	}));

	it('should retrieve all issuers',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				return Promise.all([
					expectAllIssuersRequest(mockBackend),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, allApiIssuers)
				]);
			}
		)
	);

	it('should not cause dependent entity managers to make API calls when requesting entity counts',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				// Ensure the dependent entity APIs aren't called
				mockBackend.connections.subscribe((connection: MockConnection) => {
					if (connection.request.url !== '/v1/issuer/issuers') {
						fail("Only issuer list calls are allowed. No other API calls should occur when counting issuer entities.");
					}
				});

				return Promise.all([
					expectAllIssuersRequest(mockBackend),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, allApiIssuers)
						.then(list => {
							/*list.entities.forEach(issuer => {
								issuer.badgeClassCount;
							});*/
						})
				]);
			}
		)
	);

	it('should retrieve issuers on subscription of allIssuers$',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				return Promise.all([
					expectAllIssuersRequest(mockBackend),
					issuerManager.allIssuers$.pipe(first()).toPromise().then(() => {
						verifyManagedEntitySet(issuerManager.issuersList, allApiIssuers);
					})
				]);
			}
		)
	);

	it('should add a new issuer',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				const existingIssuer = apiIssuer1;
				const newIssuer = apiIssuer2;
				const newIssuerForCreation = {
					name: apiIssuer2.name,
					description: apiIssuer2.description,
					image: apiIssuer2.image,
					email: apiIssuer2.json.email,
					url: apiIssuer2.json.url,
				};

				return Promise.all([
					expectAllIssuersRequest(mockBackend, [ existingIssuer ]),
					expectRequestAndRespondWith(
						mockBackend,
						RequestMethod.Post,
						`/v1/issuer/issuers`,
						newIssuer,
						201
					),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, [ existingIssuer ])
						.then(issuersList => issuerManager.createIssuer(newIssuerForCreation))
						.then(() => verifyManagedEntitySet(issuerManager.issuersList, [ newIssuer, existingIssuer ]))
				]);
			}
		)
	);

	it('should handle adding staff members',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				const existingIssuer = apiIssuer1;
				const newStaffMember: ApiIssuerStaff = {
					role: "staff",
					user: {
						email: "new@user.com",
						first_name: "New",
						last_name: "User",
					}
				};
				const existingIssuerWithNewUser = {
					... existingIssuer,
					staff: [
						... existingIssuer.staff,
						newStaffMember
					]
				};

				return Promise.all([
					expectAllIssuersRequest(mockBackend, [ existingIssuer ]),
					expectRequest(
						mockBackend,
						RequestMethod.Post,
						`/v1/issuer/issuers/${existingIssuer.slug}/staff`
					).then(c => {
						expect(c.requestJson()).toEqual({
							action: "add",
							email: "new@user.com",
							role: "staff",
						} as ApiIssuerStaffOperation);

						return c.respondWithJson({ message: "Success" }, 200);
					}),
					expectRequestAndRespondWith(
						mockBackend,
						RequestMethod.Get,
						`/v1/issuer/issuers/${existingIssuer.slug}`,
						existingIssuerWithNewUser,
						201
					),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, [ existingIssuer ])
						.then(issuersList => issuersList.entities[0].addStaffMember("staff", "new@user.com"))
						.then(issuer => {
							expect(issuer.staff.entityForApiEntity(newStaffMember).apiModel).toEqual(newStaffMember);
						})
				]);
			}
		)
	);

	it('should handle modifying staff members',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				const existingIssuer = apiIssuer1;
				const modifiedStaffMember: ApiIssuerStaff = {
					... existingIssuer.staff.find(s => s.role === "staff"),
					role: "editor"
				};
				const existingIssuerWithModifiedStaff = {
					... existingIssuer,
					staff: [
						... existingIssuer.staff.filter(s => s.role !== "staff"),
						modifiedStaffMember
					]
				};

				return Promise.all([
					expectAllIssuersRequest(mockBackend, [ existingIssuer ]),
					expectRequest(
						mockBackend,
						RequestMethod.Post,
						`/v1/issuer/issuers/${existingIssuer.slug}/staff`
					).then(c => {
						expect(c.requestJson()).toEqual({
							action: "modify",
							email: modifiedStaffMember.user.email,
							role: "editor",
						} as ApiIssuerStaffOperation);

						return c.respondWithJson({ message: "Success" }, 200);
					}),
					expectRequestAndRespondWith(
						mockBackend,
						RequestMethod.Get,
						`/v1/issuer/issuers/${existingIssuer.slug}`,
						existingIssuerWithModifiedStaff,
						201
					),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, [ existingIssuer ])
						.then(issuersList => {
							const member = issuersList.entities[0].staff.entityForApiEntity(modifiedStaffMember);
							member.roleSlug = modifiedStaffMember.role;
							return member.save();
						})
						.then(member => {
							expect(member.apiModel).toEqual(modifiedStaffMember);
						})
				]);
			}
		)
	);

	it('should handle deleting staff members',
		inject(
			[ IssuerManager, SessionService, MockBackend ],
			(issuerManager: IssuerManager, loginService: SessionService, mockBackend: MockBackend) => {
				const existingIssuer = apiIssuer1;
				const staffMemberToRemove: ApiIssuerStaff = existingIssuer.staff.find(s => s.role === "staff");
				const existingIssuerWithoutMember = {
					... existingIssuer,
					staff: [
						... existingIssuer.staff.filter(s => s.role !== "staff")
					]
				};

				return Promise.all([
					expectAllIssuersRequest(mockBackend, [ existingIssuer ]),
					expectRequest(
						mockBackend,
						RequestMethod.Post,
						`/v1/issuer/issuers/${existingIssuer.slug}/staff`
					).then(c => {
						expect(c.requestJson()).toEqual({
							action: "remove",
							email: staffMemberToRemove.user.email
						} as ApiIssuerStaffOperation);

						return c.respondWithJson({ message: "Success" }, 200);
					}),
					expectRequestAndRespondWith(
						mockBackend,
						RequestMethod.Get,
						`/v1/issuer/issuers/${existingIssuer.slug}`,
						existingIssuerWithoutMember,
						201
					),
					verifyEntitySetWhenLoaded(issuerManager.issuersList, [ existingIssuer ])
						.then(issuersList => issuersList.entities[0].staff.entityForApiEntity(staffMemberToRemove).remove())
						.then(issuer => {
							expect(issuer.staff.entities.map(s => s.apiModel)).not.toContain(staffMemberToRemove);
						})
				]);
			}
		)
	);
});

const allApiIssuers = [ apiIssuer1, apiIssuer2, apiIssuer3 ];

function expectAllIssuersRequest(mockBackend: MockBackend, issuers: ApiIssuer[] = allApiIssuers) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Get,
		`/v1/issuer/issuers`,
		issuers
	);
}

export function testIssuerRefForSlug(issuerSlug: string) {
	return {
		"@id": `http://localhost:8000/public/issuers/${issuerSlug}`,
		"slug": issuerSlug
	};
}
