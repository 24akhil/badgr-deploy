import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {LogoutComponent} from './components/logout/logout.component';
import {ResetPasswordSent} from './components/reset-password-sent/reset-password-sent.component';
import {RequestPasswordResetComponent} from './components/request-password-reset/request-password-reset.component';
import {LoginComponent} from './components/login/login.component';
import {BadgrCommonModule, COMMON_IMPORTS} from '../common/badgr-common.module';
import {CommonEntityManagerModule} from '../entity-manager/entity-manager.module';
import {ResetPasswordComponent} from './components/reset-password/reset-password.component';
import {OAuth2AuthorizeComponent} from './components/oauth2-authorize/oauth2-authorize.component';
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { WelcomeComponent } from './components/welcome/welcome.component';

const routes = [
	{
		path: "",
		redirectTo: "login",
		pathMatch: 'full',
	},
	{
		path: "login",
		component: LoginComponent
	},
	{
		path: "logout",
		component: LogoutComponent
	},
	{
		path: "login/:name",
		component: LoginComponent
	},
	{
		path: "login/:name/:email",
		component: LoginComponent
	},

	/* OAuth2 */
	{
		path: "oauth2/authorize",
		component: OAuth2AuthorizeComponent
	},

	/* Reset Password */
	{
		path: "request-password-reset",
		component: RequestPasswordResetComponent
	},
	{
		path: "request-password-reset/:email",
		component: RequestPasswordResetComponent
	},
	{
		path: "reset-password-sent",
		component: ResetPasswordSent
	},
	{
		path: "change-password",
		component: ResetPasswordComponent
	},
	{
		path: "change-password/:token",
		component: ResetPasswordComponent
	},
	{
		path: "welcome",
		component: WelcomeComponent
	},
	{
		path: "**",
		redirectTo: "login",
	},
];

@NgModule({
	imports: [
		...COMMON_IMPORTS,
		BadgrCommonModule,
		CommonEntityManagerModule,
		RouterModule.forChild(routes),
	],
	declarations: [
		LoginComponent,
		RequestPasswordResetComponent,
		ResetPasswordSent,
		ResetPasswordComponent,
		LogoutComponent,
		OAuth2AuthorizeComponent,
		WelcomeComponent
	],
	exports: [],
	providers: []
})
export class AuthModule {}
