import {AfterViewInit, Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';

import {CommonDialogsService} from '../services/common-dialogs.service';
import {CustomValidatorMessages, messagesForValidationError} from './formfield-text';
import {DomSanitizer, SafeHtml} from '@angular/platform-browser';

@Component({
	selector: 'bg-formfield-markdown',
	host: {
		'class': "forminput",
		'[class.forminput-is-error]': "isErrorState",
		'[class.forminput-locked]': "isLockedState",
	},
	template: `
	<div class="mdeditor">
		<div class="mdeditor-x-editor">
			<label [attr.for]="inputName" *ngIf="label || includeLabelAsWrapper">
				{{ label }} <span *ngIf="optional">(OPTIONAL)</span>
				<span *ngIf="formFieldAside">{{ formFieldAside }}</span>
				<button type="button" *ngIf="isLockedState" (click)="unlock()">(unlock)</button>
				<ng-content select="[label-additions]"></ng-content>
			</label>
				<textarea
				autosize
				[name]="inputName"
				[ngStyle]="{'height.px':textHeight}"
				[id]="inputName"
				[formControl]="control"
				[placeholder]="placeholder || ''"
				(change)="postProcessInput()"
				(focus)="cacheControlState()"
				(keypress)="handleKeyPress($event)"
				*ngIf="!_preview"
				#textareaInput
			></textarea>
		</div>

		<div class="markdown mdeditor-x-preview"
			     #markdownPreviewPane
			     [bgMarkdown]="control.value"
			     [style.minHeight.px]="textHeight"
			     *ngIf="_preview"
			>Markdown preview
			</div>

    <div class="mdeditor-x-tabbar">
		<div class="mdeditor-x-tabs">
			<div class="mdeditor-x-tab mdeditor-x-writebutton" [ngClass]="{'mdeditor-x-tab-is-active':!_preview}"
			(click)="markdownPreview(false);">Write
			</div>
			<div class="mdeditor-x-tab mdeditor-x-previewbutton" [ngClass]="{'mdeditor-x-tab-is-active':_preview}"
			(click)="markdownPreview(true);">Preview
			</div>
		</div>
		<div class="mdeditor-x-help">
			<div class="l-flex l-flex-1x l-flex-aligncenter">
				<button class="buttonicon buttonicon-link" type="button" (click)="openMarkdownHintsDialog()">
					<svg class="icon l-flex-shrink0" icon="icon_markdown"></svg>
				</button>
				<button (click)="openMarkdownHintsDialog()" type="button" class="u-text-link-small u-hidden-maxmobilelarge">Markdown Supported</button>
			</div>
		</div>
    </div>
</div>
`
})
export class FormFieldMarkdown implements OnChanges, AfterViewInit {

	@Input()
	set unlocked(unlocked: boolean) {
		this._unlocked = unlocked;
		this.updateDisabled();
	}

	get unlocked() { return this._unlocked; }
	@Input()
	set locked(locked: boolean) {
		this._locked = locked;
		this.updateDisabled();
	}

	get locked() { return this._locked; }

	get inputElement(): HTMLTextAreaElement {
		if (this.textareaInput && this.textareaInput.nativeElement) {
			return this.textareaInput.nativeElement;
		}
		return null;
	}

	get hasFocus(): boolean {
		return document.activeElement === this.inputElement;
	}

	get errorMessageForDisplay(): string {
		return this.hasFocus ? this.cachedErrorMessage : this.uncachedErrorMessage;
	}

	get uncachedErrorMessage(): string {
		return messagesForValidationError(
			this.label,
			this.control && this.control.errors,
			this.errorMessage
		).concat(messagesForValidationError(
			this.label,
			this.errorGroup && this.errorGroup.errors,
			this.errorGroupMessage
		))[ 0 ]; // Only display the first error
	}

	get value() {
		return this.control.value;
	}

	get controlErrorState() { return this.control.dirty && (!this.control.valid || (this.errorGroup && !this.errorGroup.valid)); }

	get isErrorState() {
		if (this.hasFocus && this.cachedErrorState !== null) {
			return this.cachedErrorState;
		} else {
			return this.controlErrorState;
		}
	}

	get isLockedState() { return this.locked && !this.unlocked; }

	get inputName() { return (this.label || this.placeholder || this.randomName).replace(/[^\w]+/g, "_").toLowerCase(); }
	@Input() control: FormControl;
	@Input() initialValue: string;
	@Input() label: string;
	@Input() includeLabelAsWrapper = false; // includes label for layout purposes even if label text wasn't passed in.
	@Input() formFieldAside: string; // Displays additional text above the field. I.E (optional)
	@Input() errorMessage: CustomValidatorMessages;
	@Input() description: string;
	@Input() placeholder: string;
	@Input() optional = false;

	@Input() errorGroup: FormGroup;
	@Input() errorGroupMessage: CustomValidatorMessages;

	@Input() unlockConfirmText = "Unlocking this field may have unintended consequences. Are you sure you want to continue?";

	@Input() autofocus = false;

	@ViewChild("textareaInput") textareaInput: ElementRef;
	@ViewChild("markdownPreviewPane") markdownPreviewPane: ElementRef;

	textHeight: number;
	_preview = false;

	private _lastRenderedMarkdown?: string;
	private _currentMarkdownHtml?: SafeHtml;

	private _unlocked = false;

	private _locked = false;

	private cachedErrorMessage = null;
	private cachedErrorState = null;
	private cachedDirtyState = null;

	private randomName = "field" + Math.random();

	constructor(
		private dialogService: CommonDialogsService,
		private domSanitizer: DomSanitizer,
	) { }

	ngAfterViewInit() {
		if (this.autofocus) {
			this.focus();
		}
	}

	ngOnChanges(changes: SimpleChanges) {
		// Unlocked by default when there is no value
		if (!this.control.value) {
			this.unlocked = true;
		}

		if ("initialValue" in changes) {
			const initialValue = changes[ "initialValue" ].currentValue;
			if ((this.value === null || this.value === undefined || this.value === '') &&
				(initialValue !== null && initialValue !== undefined && initialValue !== '')
			) {
				this.control.setValue(initialValue);
			}
		}

		this.updateDisabled();
	}

	markdownPreview(preview) {
		if (this.textareaInput) {
			this.textHeight = this.textareaInput.nativeElement.offsetHeight;
		}

		this._preview = preview;
	}

	updateDisabled() {
		if (!this.control) {
			return;
		}

		if (this.isLockedState) {
			this.control.disable();
		} else {
			this.control.enable();
		}
	}

	openMarkdownHintsDialog() {
		console.log("here we go");
		this.dialogService.markdownHintsDialog.openDialog();
	}

	unlock() {
		this.dialogService.confirmDialog.openResolveRejectDialog({
			dialogTitle: "Are you sure?",
			dialogBody: this.unlockConfirmText,
			resolveButtonLabel: "Continue",
			rejectButtonLabel: "Cancel",
		}).then(
			() => this.unlocked = true,
			() => void 0
		);
	}

	focus() {
		this.inputElement.focus();
	}

	select() {
		this.inputElement.select();
	}

	private cacheControlState() {
		this.cachedErrorMessage = this.uncachedErrorMessage;
		this.cachedDirtyState = this.control.dirty;
		this.cachedErrorState = this.controlErrorState;
	}

	private postProcessInput() {
	}

	private handleKeyPress(event: KeyboardEvent) {
		// This handles revalidating when hitting enter from within an input element. Ideally, we'd catch _all_ form submission
		// events, but since the form supresses those if things aren't valid, that doesn't really work. So we do this hack.
		if (event.keyCode === 13) {
			this.control.markAsDirty();
			this.cacheControlState();
		}
	}
}
