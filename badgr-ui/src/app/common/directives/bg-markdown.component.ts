import {AfterViewChecked, Directive, ElementRef, Input, Renderer2} from '@angular/core';

import * as marked from 'marked';
import {DomSanitizer} from '@angular/platform-browser';

@Directive({
	selector: '[bgMarkdown]'
})
export class BgMarkdownComponent implements AfterViewChecked {
	renderedHtml?: string;

	@Input()
	set bgMarkdown(markdown: string) {
		markdown = markdown || "";
		this.renderedHtml = marked(
			markdown,
			{
				gfm: false,
				tables: true,
				breaks: false,
				pedantic: false,
				sanitize: true,
				smartLists: true,
				smartypants: false
			}
		);
	}

	constructor(
		protected elemRef: ElementRef<HTMLElement>,
		private domSanitizer: DomSanitizer,
		private renderer: Renderer2
	) {
	}

	ngAfterViewChecked(): void {
		if (this.elemRef && this.elemRef.nativeElement) {
			this.renderer.setProperty(
				this.elemRef.nativeElement,
				"innerHTML",
				this.renderedHtml
			);
		}
	}
}
