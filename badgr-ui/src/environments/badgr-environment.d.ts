import { BadgrConfig } from './badgr-config';

export interface BadgrEnvironment {
	production: boolean;
	config?: Partial<BadgrConfig>;
	remoteConfig?: {
		baseUrl: string;
		version: string;
	};
}
