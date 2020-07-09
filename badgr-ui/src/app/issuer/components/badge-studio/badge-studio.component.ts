import {Component, ElementRef, OnInit, ViewChild} from '@angular/core';
// import "font-awesome/css/font-awesome.css";
import * as FontFaceObserver from 'fontfaceobserver';
import {canvasVisualCenter} from '../../../common/util/visual-center';
import {HttpClient} from '@angular/common/http';

// The FabricJs Import does not work as expected. Instead of getting a "fabric" variable with properties for the various
// fabric classes, it contains another nested "fabric" property with those values. This seems to be the only way to get
// it to work correctly.
@Component({
	selector: 'badge-studio',
	host: {},
	template: `
		<canvas #canvas width="400" height="400"></canvas>
	`,
	styleUrls: [
		'../../../../../node_modules/font-awesome/css/font-awesome.css'
	]

})
export class BadgeStudioComponent implements OnInit {

	get canvas() {
		return (this.canvasElem.nativeElement as HTMLCanvasElement);
	}

	get context2d(): CanvasRenderingContext2D {
		return this.canvas.getContext("2d");
	}

	dataUrl: string;
	@ViewChild("canvas")
	private canvasElem: ElementRef;

	// private ready: boolean;

	private fontPromise: Promise<unknown>;

	constructor(
		protected http: HttpClient
	) {
	}

	ngOnInit() {
		this.fontPromise = new FontFaceObserver('FontAwesome').load("")
			.catch(e => console.error(e));
	}

	generateRandom(): Promise<string> {
		return this.fontPromise.then(
			() => new Promise<string>((resolve, reject) => {
				const shapeColor = shapeColors[Math.floor(Math.random() * shapeColors.length)];
				const iconColor = "#FFFFFF";

				this.context2d.clearRect(0, 0, this.canvas.width, this.canvas.height);

				// Grab a random SVG from our set
				this.http.get(
					shapeImages[Math.floor(Math.random() * shapeImages.length)],
					{
						observe: "body",
						responseType: "text"
					}
				).toPromise()
					.then(res => {
						const svgRoot = new DOMParser().parseFromString(res, "image/svg+xml").documentElement;

						// We need to attach the SVG to the window so we can compute the style of the elements for re-coloring
						document.body.appendChild(svgRoot);

						// Re-color any non-white elements
						Array.from(svgRoot.querySelectorAll("*"))
							.filter(e => "style" in e) // Filter out elements that don't have a style to change (this fixes a bug in IE)
							.forEach((e: HTMLElement) => {
							const fill = window.getComputedStyle(e)["fill"];

							if (! fill.match(/^rgb\(255,\s*255,\s*255\s*\)$/)) {
								e.style.fill = shapeColor;
							}
						});

						// And clean up the document
						svgRoot.remove();

						// Work around https://bugzilla.mozilla.org/show_bug.cgi?id=700533
						svgRoot.setAttribute("width", "" + this.canvas.width);
						svgRoot.setAttribute("height", "" + this.canvas.height);

						// Convert the SVG into a data URL that we can use to render into a canvas
						const svgDataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(svgRoot));
						const svgImage = new Image();
						svgImage.onload = () => {
							this.context2d.drawImage(
								svgImage,
								0,
								0,
								this.canvas.width,
								this.canvas.height
							);

							const iconIndex = Math.floor(Math.random() * fontAwesomeIconData.length / 2);
							const iconChar = fontAwesomeIconData[iconIndex * 2];
							const iconGeometricCenter = fontAwesomeIconData[iconIndex * 2 + 1] === "1";
							const iconSize = 150;

							// Render the icon into the canvas, either with geometric or visual centering
							if (iconGeometricCenter) {
								this.renderIcon(
									this.canvas,
									iconChar,
									iconColor,
									iconSize
								);
							} else {
								const centerSize = 100;
								const iconCanvas = document.createElement("canvas");
								iconCanvas.width  = centerSize;
								iconCanvas.height = centerSize;
								const iconContext = iconCanvas.getContext("2d");
								iconContext.fillStyle = "black";
								iconContext.fillRect(0, 0, centerSize, centerSize);

								this.renderIcon(
									iconCanvas,
									iconChar,
									iconColor,
									40
								);

								const center = canvasVisualCenter(iconCanvas);
								this.renderIcon(
									this.canvas,
									iconChar,
									iconColor,
									iconSize,
									{
										x: (.5 - center.visualLeft) * this.canvas.width + (iconCanvas.width / centerSize) / 2,
										y: (.5 - center.visualTop) * this.canvas.height + (iconCanvas.height / centerSize) / 2
									}
								);
							}

							this.dataUrl = this.canvas.toDataURL();
							resolve(this.dataUrl);
						};
						svgImage.src = svgDataUrl;
					});
			})
		);
	}

	private renderIcon(
		iconCanvas: HTMLCanvasElement,
		iconChar: string,
		iconColor: string,
		fontSize: number,
		offset: {x: number; y: number} = {x: 0, y: 0}
	): HTMLCanvasElement {
		const iconContext = iconCanvas.getContext("2d");
		iconContext.font = `${fontSize}px FontAwesome`;
		iconContext.textAlign = "center";
		iconContext.fillStyle = iconColor;
		iconContext.textBaseline = "middle";
		iconContext.fillText(
			iconChar,
			iconCanvas.width / 2 + offset.x,
			iconCanvas.height / 2 + offset.y
		);

		return iconCanvas;
	}
}

const shapeColors = [
	"#696DE9",
	"#008FFF",
	"#1EB9E9",
	"#5BD1FF",
	"#3FDE67",
	"#FF4762",
	"#FF5428",
	"#FFA600",
	"#FFD400",
	"#9FA0A4",
	"#F7402D",
	"#EC1460",
	"#9D1AB2",
	"#6733B9",
	"#3D4DB7",
	"#1093F5",
	"#00A6F7",
	"#00BBD6",
	"#009687",
	"#46B04A",
	"#8AC441",
	"#CCDD1E",
	"#231F20",
	"#FFC200",
	"#FF9800",
	"#FF5405",
	"#7A5548",
	"#9D9D9D",
	"#5F7C8B",
	"#475D68",
];

const shapeImages = [
	require("../../../../breakdown/static/badgestudio/shapes/circle.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/diamond.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/hex.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/round-bottom.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/round-top.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/square.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/triangle-bottom.svg") as string,
	require("../../../../breakdown/static/badgestudio/shapes/triangle-top.svg") as string,
];

// Created from http://fontawesome.io/cheatsheet/
// Each character is followed by a number indicating if it should be geometrically (1) or visually centered (0).
// This is used instead of a more readable data array to save program space.
const fontAwesomeIconData = "10011111111011110000001111111111111" +
	"1111110111100011111111111111001101011111011000" +
	"10001000000111111111000000000000010111010001110" +
	"1111011011101111111111001111011100111111111110" +
	"0111111110111111111111111111111100111100011111" +
	"1010111111110101111011";
