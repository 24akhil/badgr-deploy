import {ApiIssuer, ApiIssuerStaff, IssuerRef, IssuerStaffRef, IssuerStaffRoleSlug, IssuerUrl} from './issuer-api.model';
import {ManagedEntity} from '../../common/model/managed-entity';
import {ApiEntityRef} from '../../common/model/entity-ref';
import {CommonEntityManager} from '../../entity-manager/services/common-entity-manager.service';
import {EmbeddedEntitySet} from '../../common/model/managed-entity-set';


export class Issuer extends ManagedEntity<ApiIssuer, IssuerRef> {
	readonly staff = new EmbeddedEntitySet(
		this,
		() => this.apiModel.staff,
		apiEntry => new IssuerStaffMember(this),
		IssuerStaffMember.urlFromApiModel
	);

	protected buildApiRef(): ApiEntityRef {
		return {
			"@id": this.issuerUrl,
			slug: this.apiModel.slug,
		};
	}

	constructor(
		commonManager: CommonEntityManager,
		initialEntity: ApiIssuer = null,
		onUpdateSubscribed: () => void = undefined
	) {
		super(commonManager, onUpdateSubscribed);

		if (initialEntity != null) {
			this.applyApiModel(initialEntity);
		}
	}

	get issuerUrl(): IssuerUrl { return this.apiModel.json.id; }

	get name(): string { return this.apiModel.name; }

	get description(): string { return this.apiModel.description; }

	get image(): string { return this.apiModel.image; }

	get email(): string { return this.apiModel.json.email; }

	get websiteUrl(): string { return this.apiModel.json.url; }

	get createdAt(): Date { return new Date(this.apiModel.created_at); }

	get createdBy(): string { return this.apiModel.created_by; }

	get badgeClassCount(): number {
		const badges = this.commonManager.badgeManager.badgesList;

		return badges.loaded
			? badges.entities.filter(b => b.issuerSlug === this.slug).length
			: this.apiModel.badgeClassCount;
	}

	async update(): Promise<this> {
		this.applyApiModel(
			await this.issuerApiService.getIssuer(this.slug),
			true
		);
		return this;
	}

	async delete(): Promise<ApiIssuer> {
		return this.issuerApiService.deleteIssuer(this.slug);
	}

	private get issuerApiService() {
		return this.commonManager.issuerManager.issuerApiService;
	}

	async addStaffMember(
		role: IssuerStaffRoleSlug,
		email: string
	): Promise<this> {
		await this.issuerApiService.updateStaff(
			this.slug,
			{
				action: "add",
				email,
				role,
			}
		);

		return this.update();
	}

	get currentUserStaffMember(): IssuerStaffMember {
		if (this.profileManager.userProfile && this.profileManager.userProfile.emails.entities) {
			const emails = this.profileManager.userProfile.emails.entities;

			return this.staff.entities.find(
				staffMember => !!emails.find(
					profileEmail => profileEmail.email === staffMember.email
				)
			) || null;
		} else {
			return null;
		}
	}
}

export class IssuerStaffMember extends ManagedEntity<ApiIssuerStaff, IssuerStaffRef> {

	get roleSlug() { return this.apiModel.role; }
	get roleInfo() { return issuerRoleInfoFor(this.roleSlug); }
	get email() { return this.apiModel.user.email; }
	get telephone() { return (typeof this.apiModel.user.telephone === "string") ?this.apiModel.user.telephone :this.apiModel.user.telephone[0]; }
	get url() { return (typeof this.apiModel.user.url === "string") ?this.apiModel.user.url :this.apiModel.user.url[0]; }
	get firstName() { return this.apiModel.user.first_name; }
	get lastName() { return this.apiModel.user.last_name; }

	set roleSlug(role: IssuerStaffRoleSlug) {
		this.apiModel.role = role;
	}

	get isOwner() { return this.roleSlug === "owner"; }


	/**
	 * Returns a label to use for this member based on the name if it's available (e.g. "Luke Skywalker"), or the email
	 * if it isn't (e.g. "lskywalker@rebel.alliance")
	 *
	 * @returns {string}
	 */
	get nameLabel(): string {
		const names = [this.firstName, this.lastName].filter(n => n && n.length > 0);
		if (names.length > 0) {
			return names.join(" ");
		} else {
			return this.email;
		}
	}

	/**
	 * Returns a label to use for this member based on the name and email if available (e.g. "Luke Skywalker (lskywalker@rebel.alliance)")
	 *
	 * @returns {string}
	 */
	get fullLabel(): string {
		const names = [this.firstName, this.lastName].filter(n => n && n.length > 0);
		if (names.length > 0) {
			return names.join(" ") + `(${this.email})`;
		} else {
			return this.email;
		}
	}

	static urlFromApiModel(apiStaff: ApiIssuerStaff) {
		return apiStaff.user.email;
	}
	constructor(public issuer: Issuer) {
		super(issuer.commonManager);
	}

	protected buildApiRef(): IssuerStaffRef {
		return {
			"@id": IssuerStaffMember.urlFromApiModel(this.apiModel),
			"slug": IssuerStaffMember.urlFromApiModel(this.apiModel),
		};
	}

	async save(): Promise<IssuerStaffMember> {
		await this.issuerManager.issuerApiService.updateStaff(
			this.issuer.slug,
			{
				action: "modify",
				email: this.email,
				role: this.apiModel.role,
			}
		);

		return this.issuer.update().then(() => this);
	}

	async remove(): Promise<Issuer> {
		await this.issuerManager.issuerApiService.updateStaff(
			this.issuer.slug,
			{
				action: "remove",
				email: this.email
			}
		);

		return this.issuer.update();
	}
}

export const issuerStaffRoles = [
	{
		slug: "owner",
		label: "Owner",
		indefiniteLabel: "an owner",
		description: "Ability to add and remove staff. Full rights to create, delete, and award badges. Ability to edit issuer details."
	},
	{
		slug: "editor",
		label: "Editor",
		indefiniteLabel: "an editor",
		description: "Full rights to create, delete, and award badges. Ability to edit issuer details."
	},
	{
		slug: "staff",
		label: "Staff Member",
		indefiniteLabel: "a staff member",
		description: "Ability to issue badges created by Owners and Editors."
	},
];
export function issuerRoleInfoFor(slug: IssuerStaffRoleSlug) {
	return issuerStaffRoles.find(r => r.slug === slug);
}
