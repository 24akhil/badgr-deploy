export interface ApiV2Wrapper<T> {
	result: T[] | T;
	status: ApiV2Status;
	validationErrors?: string[];
	fieldErrors?: object;
	nonFieldErrors?: string[];
	warnings?: object;
}

export interface ApiV2Status {
	success: boolean;
	description: string;
}
