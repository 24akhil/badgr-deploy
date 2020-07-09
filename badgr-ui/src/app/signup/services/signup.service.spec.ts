import {BaseRequestOptions, Http, Response, ResponseOptions} from '@angular/http';
import {MockBackend} from '@angular/http/testing';
import {inject, TestBed} from '@angular/core/testing';
import {AppConfigService} from '../../common/app-config.service';
import {SignupModel} from '../models/signup-model.type';
import {SignupService} from './signup.service';
import {MessageService} from '../../common/services/message.service';
import {SessionService} from '../../common/services/session.service';


xdescribe('SignupService', () => {
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

			SignupService,
			SessionService,
		],
		imports: [ ]
	}));

	xit("should send signup payload",
		inject([ MockBackend, SignupService ], (backend, signupService) => {
			let connection, error, signupModel;

			backend.connections.subscribe(c => connection = c);

			signupModel = new SignupModel(
				'username@email.com', 'Firstname', 'Lastname', 'password', true, true);
			signupService.submitSignup(signupModel)
				.then(
					() => error = false,
					() => error = true
				);

			connection.mockRespond(new Response(
				new ResponseOptions({ 'status': 200 })));

			expect(error).toBe(false);
		})
	);
});
