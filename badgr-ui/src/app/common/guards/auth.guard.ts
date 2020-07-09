import {Injectable} from '@angular/core';
import {ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot} from '@angular/router';
import {SessionService} from '../services/session.service';
import {OAuthManager} from '../services/oauth-manager.service';

@Injectable()
export class AuthGuard implements CanActivate {
	constructor(
		private sessionService: SessionService,
		private router: Router,
		private oAuthManager: OAuthManager
	) {}

	canActivate(
		// Not using but worth knowing about
		next:  ActivatedRouteSnapshot,
		state: RouterStateSnapshot
	) {
		// Ignore the auth module
		if (state.url.startsWith("/auth") && !state.url.includes("welcome")) return true;

		// Ignore the public module
		if (state.url.startsWith("/public")) return true;

		if (! this.sessionService.isLoggedIn) {
			this.router.navigate(['/auth']);
			return false;
		} else if (this.oAuthManager.isAuthorizationInProgress) {
			this.router.navigate(['/auth/oauth2/authorize']);
			return false;
		} else {
			return true;
		}
	}
}
