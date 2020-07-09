import {FormControl} from '@angular/forms';
import {ValidationResult} from './email.validator';

export class DateValidator {
	static validDate(control: FormControl): ValidationResult {
		const value = control.value;
		if (typeof value === "string" && value.trim().length > 0 && isNaN(new Date(value).getTime())) {
			return { 'invalidDate': true };
		} else {
			return null;
		}
	}
}
