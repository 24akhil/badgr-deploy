import {
	ApiBadgeClass,
	ApiBadgeClassAlignment,
	ApiBadgeClassExpiration,
	BadgeClassExpiresDuration,
	BadgeClassRef,
	BadgeClassUrl
} from './badgeclass-api.model';
import {IssuerUrl} from './issuer-api.model';
import {ManagedEntity} from '../../common/model/managed-entity';
import {ApiEntityRef} from '../../common/model/entity-ref';
import {CommonEntityManager} from '../../entity-manager/services/common-entity-manager.service';

export class BadgeClass extends ManagedEntity<ApiBadgeClass, BadgeClassRef> {

	get badgeUrl(): BadgeClassUrl { return this.apiModel.json.id; }

	get issuerUrl(): IssuerUrl { return this.apiModel.issuer; }

	get name(): string { return this.apiModel.name; }
	set name(name: string) { this.apiModel.name = name; }

	get description(): string { return this.apiModel.description; }
	set description(description: string) {
		this.apiModel.json.description = description;
		this.apiModel.description = description;
	}

	get image(): string { return this.apiModel.image; }
	set image(image: string) { this.apiModel.image = image;}

	get createdAt(): Date { return new Date(this.apiModel.created_at); }

	get createdBy(): string { return this.apiModel.created_by; }

	get recipientCount(): number { return this.apiModel.recipient_count; }

	get criteria_text(): string { return this.apiModel.criteria_text; }
	set criteria_text(criteriaText: string) {
		this.apiModel.json.criteria_text = criteriaText;
		this.apiModel.criteria_text = criteriaText;
	}

	get criteria_url(): string { return this.apiModel.criteria_url; }
	set criteria_url(criteriaUrl: string) {
		this.apiModel.json.criteriaUrl = criteriaUrl;
		this.apiModel.criteria_url = criteriaUrl;
	}

	get tags(): string[] {
		return this.apiModel.tags;
	}
	set tags(tags: string[]) {
		this.apiModel.tags = tags;
	}

	get expiresDuration(): BadgeClassExpiresDuration | undefined {
		return this.apiModel.expires ? this.apiModel.expires.duration : undefined;
	}
	set expiresDuration(duration: BadgeClassExpiresDuration | undefined) {
		if (!this.apiModel.expires) {
			this.apiModel.expires = {} as ApiBadgeClassExpiration;
		}
		this.apiModel.expires.duration = duration;
	}
	get expiresAmount(): number | undefined {
		return this.apiModel.expires ? this.apiModel.expires.amount : undefined;
	}
	set expiresAmount(amount: number | undefined) {
		if (!this.apiModel.expires) {
			this.apiModel.expires = {} as ApiBadgeClassExpiration;
		}
		this.apiModel.expires.amount = amount;
	}


	get issuerSlug(): string {
		return BadgeClass.issuerSlugFromUrl(this.issuerUrl);
	}

	get alignments() {
		return this.apiModel.alignment;
	}
	set alignments(alignments: ApiBadgeClassAlignment[]) {
		this.apiModel.alignment = alignments;
	}

	// TODO: The API should give us the issuer slug for a badge, and we should not need to parse the URL.
	static issuerSlugForApiBadge(apiBadge: ApiBadgeClass) {
		return BadgeClass.issuerSlugFromUrl(apiBadge.issuer);
	}

	private static issuerSlugFromUrl(issuerUrl: string) {
		return (issuerUrl.match(/\/public\/issuers\/([^\/]+)/) || [])[ 1 ] || null;
	}
	constructor(
		commonManager: CommonEntityManager,
		initialEntity: ApiBadgeClass = null,
		onUpdateSubscribed: () => void = undefined
	) {
		super(commonManager, onUpdateSubscribed);

		if (initialEntity != null) {
			this.applyApiModel(initialEntity);
		}
	}

	protected buildApiRef(): ApiEntityRef {
		return {
			"@id": this.badgeUrl,
			slug: this.apiModel.slug
		};
	}
	clearExpires(): void {
		this.apiModel.expires = null;
	}

	expirationDateRelative(issuedOn?: Date): Date | undefined {
		if (this.expiresAmount) {
			const ret = issuedOn || new Date();
			switch (this.expiresDuration) {
				case 'days': ret.setDate(ret.getDate() + this.expiresAmount); break;
				case 'months': ret.setMonth(ret.getMonth() + this.expiresAmount); break;
				case 'weeks': ret.setDate(ret.getDate() + this.expiresAmount * 7); break;
				case 'years': ret.setFullYear(ret.getFullYear() + this.expiresAmount); break;
				default: break;
			}
			return new Date(ret);
		}
	}

	update(): Promise<this> {
		return this.badgeManager.badgeClassApi.getBadgeForIssuerSlugAndBadgeSlug(this.issuerSlug, this.slug).then(
			apiBadge => this.applyApiModel(apiBadge)
		);
	}

	save(): Promise<this> {
		return this.badgeManager.badgeClassApi.updateBadgeClass(this.issuerSlug, this.apiModel)
			.catch(e => {
				this.revertChanges();
				throw e;
			})
			.then(apiBadge => this.applyApiModel(apiBadge));
	}
}

