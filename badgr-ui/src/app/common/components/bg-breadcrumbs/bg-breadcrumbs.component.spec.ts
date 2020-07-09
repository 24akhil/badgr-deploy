import {async, ComponentFixture, TestBed} from '@angular/core/testing';

import {BgBreadcrumbsComponent} from './bg-breadcrumbs.component';

describe('BgBreadcrumbsComponent', () => {

  let component: BgBreadcrumbsComponent;
  let fixture: ComponentFixture<BgBreadcrumbsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ BgBreadcrumbsComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(BgBreadcrumbsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  xit('should create', () => {
    expect(component).toBeTruthy();
  });

});
