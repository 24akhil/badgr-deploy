import {inject, TestBed} from '@angular/core/testing';
import {AppConfigService} from '../../common/app-config.service';
import {MockBackend} from '@angular/http/testing';
import {BaseRequestOptions, Http, RequestMethod} from '@angular/http';
import {CommonEntityManager} from '../../entity-manager/services/common-entity-manager.service';
import {expectRequestAndRespondWith} from '../../common/util/mock-response-util.spec';
import {verifyEntitySetWhenLoaded, verifyManagedEntitySet} from '../../common/model/managed-entity-set.spec';
import {RecipientBadgeCollectionApiService} from './recipient-badge-collection-api.service';
import {RecipientBadgeCollectionManager} from './recipient-badge-collection-manager.service';
import {buildTestRecipientBadgeCollections} from '../models/recipient-badge-collection.model.spec';
import {ApiRecipientBadgeCollection} from '../models/recipient-badge-collection-api.model';
import {RecipientBadgeApiService} from './recipient-badges-api.service';
import {RecipientBadgeManager} from './recipient-badge-manager.service';
import {MessageService} from '../../common/services/message.service';
import {EventsService} from '../../common/services/events.service';
import {SessionService} from '../../common/services/session.service';

xdescribe('RecipientBadgeCollectionManger', () => {
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
			RecipientBadgeCollectionApiService,
			RecipientBadgeCollectionManager,

			EventsService,

		  RecipientBadgeApiService,
		  RecipientBadgeManager
		],
		imports: [ ]
	}));

	beforeEach(inject([ SessionService ], (loginService: SessionService) => {
		loginService.storeToken({ access_token: "MOCKTOKEN" });
	}));

	it('should retrieve all recipient badge collections',
		inject(
			[ RecipientBadgeCollectionManager, MockBackend ],
			(recipientBadgeCollectionManager: RecipientBadgeCollectionManager, mockBackend: MockBackend) => {
				const testData = buildTestRecipientBadgeCollections();

				return Promise.all([
					expectAllCollectionsRequest(mockBackend, testData.apiCollections),
					verifyEntitySetWhenLoaded(recipientBadgeCollectionManager.recipientBadgeCollectionList, testData.apiCollections)
				]);
			}
		)
	);

	it('should retrieve collections on subscription',
		inject(
			[ RecipientBadgeCollectionManager, MockBackend ],
			(recipientBadgeCollectionManager: RecipientBadgeCollectionManager, mockBackend: MockBackend) => {
				const testData = buildTestRecipientBadgeCollections();

				return Promise.all([
					expectAllCollectionsRequest(mockBackend, testData.apiCollections),
					recipientBadgeCollectionManager.recipientBadgeCollectionList.loadedPromise.then(() => {
						verifyManagedEntitySet(recipientBadgeCollectionManager.recipientBadgeCollectionList, testData.apiCollections);
					})
				]);
			}
		)
	);

	it('should add a new collections successfully',
		inject(
			[ RecipientBadgeCollectionManager, MockBackend ],
			(recipientBadgeCollectionManager: RecipientBadgeCollectionManager, mockBackend: MockBackend) => {
				const testData = buildTestRecipientBadgeCollections();

				const existingRecipientBadgeCollection = testData.apiCollection1;
				const newRecipientBadgeCollection = testData.apiCollection2;

				return Promise.all([
					expectAllCollectionsRequest(mockBackend, [ existingRecipientBadgeCollection ]),
					expectCollectionPost(mockBackend, newRecipientBadgeCollection),
					verifyEntitySetWhenLoaded(recipientBadgeCollectionManager.recipientBadgeCollectionList, [ existingRecipientBadgeCollection ])
						.then(recipientBadgeCollectionsList => recipientBadgeCollectionManager.createRecipientBadgeCollection(newRecipientBadgeCollection))
						.then(() => verifyManagedEntitySet(recipientBadgeCollectionManager.recipientBadgeCollectionList, [ newRecipientBadgeCollection, existingRecipientBadgeCollection ]))
				]);
			}
		)
	);

	// TODO: Tests for modifying and saving recipient badge collection

	it('should delete a collection',
		inject(
			[ RecipientBadgeCollectionManager, MockBackend ],
			(recipientBadgeCollectionManager: RecipientBadgeCollectionManager, mockBackend: MockBackend) => {
				const testData = buildTestRecipientBadgeCollections();

				const startingCollections = [ testData.apiCollection1, testData.apiCollection2 ];
				const toDelete = testData.apiCollection2;
				const endingCollections = [ testData.apiCollection1 ];

				return Promise.all([
					expectAllCollectionsRequest(mockBackend, startingCollections),
					expectRequestAndRespondWith(
						mockBackend,
						RequestMethod.Delete,
						`/v1/earner/collections/${toDelete.slug}`,
						{},
						201
					),
					verifyEntitySetWhenLoaded(recipientBadgeCollectionManager.recipientBadgeCollectionList, startingCollections)
						.then(recipientBadgeCollectionsList => recipientBadgeCollectionManager.recipientBadgeCollectionList.entityForApiEntity(toDelete).deleteCollection())
						.then(() => verifyManagedEntitySet(recipientBadgeCollectionManager.recipientBadgeCollectionList, endingCollections))
				]);
			}
		)
	);

});

export function expectCollectionPost(
	mockBackend: MockBackend,
	newCollection: ApiRecipientBadgeCollection
) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Post,
		`/v1/earner/collections?json_format=plain`,
		newCollection,
		201
	);
}

export function expectCollectionPut(
	mockBackend: MockBackend,
	collection: ApiRecipientBadgeCollection
) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Put,
		`/v1/earner/collections/${collection.slug}?json_format=plain`,
		collection,
		201
	);
}

export function expectAllCollectionsRequest(mockBackend: MockBackend, collections: ApiRecipientBadgeCollection[]) {
	return expectRequestAndRespondWith(
		mockBackend,
		RequestMethod.Get,
		`/v1/earner/collections?json_format=plain`,
		collections
	);
}
