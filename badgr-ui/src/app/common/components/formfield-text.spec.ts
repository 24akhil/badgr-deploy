// tslint:disable
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { Injectable, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { By } from '@angular/platform-browser';
// import { Observable } from 'rxjs/Observable';
// import 'rxjs/add/observable/of';
// import 'rxjs/add/observable/throw';

import {Component, Directive} from '@angular/core';
import {FormFieldText} from './formfield-text';
import {CommonDialogsService} from '../services/common-dialogs.service';
import { RouterTestingModule } from "@angular/router/testing";
import { COMMON_IMPORTS } from "../badgr-common.module";
import { COMMON_MOCKS_PROVIDERS_WITH_SUBS } from "../../mocks/mocks.module.spec";
import { BadgrButtonComponent } from "./badgr-button.component";

describe('FormFieldText', () => {
  let fixture;
  let component;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [
        FormFieldText,
				BadgrButtonComponent
      ],
			imports: [
				RouterTestingModule,
				CommonModule,
				...COMMON_IMPORTS,
			],
			providers: [
				...COMMON_MOCKS_PROVIDERS_WITH_SUBS,
			],
      schemas: [ CUSTOM_ELEMENTS_SCHEMA ]
    }).compileComponents();
    fixture = TestBed.createComponent(FormFieldText);
    component = fixture.debugElement.componentInstance;
  });

  it('should create a component', async () => {
    expect(component).toBeTruthy();
  });

  it('should run #ngOnInit()', async () => {
    const result = component.ngOnInit();
  });

  it('should run #ngAfterViewInit()', async () => {
    const result = component.ngAfterViewInit();
  });

  xit('should run #ngOnChanges()', async () => {
    // const result = component.ngOnChanges(changes);
  });

  it('should run #updateDisabled()', async () => {
    const result = component.updateDisabled();
  });

  it('should run #unlock()', async () => {
    const result = component.unlock();
  });

  xit('should run #cacheControlState()', async () => {
    const result = component.cacheControlState();
  });

  xit('should run #focus()', async () => {
    const result = component.focus();
  });

  xit('should run #select()', async () => {
    const result = component.select();
  });

  it('should run #handleKeyPress()', async () => {
    const result = component.handleKeyPress(event);
  });

  xit('should run #handleKeyUp()', async () => {
    const result = component.handleKeyUp(event);
  });

  it('should run #postProcessInput()', async () => {
    const result = component.postProcessInput();
  });

});
