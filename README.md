# Badgr Server
*Digital badge management for issuers, earners, and consumers*

Badgr-server is the Python/Django API backend for issuing [Open Badges](http://openbadges.org). In addition to a powerful Issuer API and browser-based user interface for issuing, Badgr offers integrated badge management and sharing for badge earners. Free accounts are hosted by Concentric Sky at [Badgr.com](http://info.badgr.com), but for complete control over your own issuing environment, Badgr Server is available open source as a Python/Django application.

See also [badgr-ui](https://github.com/concentricsky/badgr-ui), the Angular front end that serves as users' interface for this project.

### About the Badgr Project
Badgr was developed by [Concentric Sky](https://concentricsky.com), starting in 2015 to serve as an open source reference implementation of the Open Badges Specification. It provides functionality to issue portable, verifiable Open Badges as well as to allow users to manage badges they have been awarded by any issuer that uses this open data standard. Since 2015, Badgr has grown to be used by hundreds of educational institutions and other people and organizations worldwide. See [Project Homepage](https://badgr.org) for more details about contributing to and integrating with Badgr.

## How to get started on your local development environment.
Prerequisites:

* Install docker (see [instructions](https://docs.docker.com/install/))

### Copy local settings example file

Copy the example development settings:
  * `cp .docker/etc/settings_local.dev.py.example .docker/etc/settings_local.dev.py`
    
**NOTE**: you *may* wish to copy and edit the production config. See Running the Django Server in "Production" below for more details.
  * `cp .docker/etc/settings_local.prod.py.example .docker/etc/settings_local.prod.py`

### Customize local settings to your environment
    
Edit the `settings_local.dev.py` and/or `settings_local.prod.py` to adjust the following settings:
* Set `DEFAULT_FROM_EMAIL` to an address, for instance `"noreply@localhost"`
    * The default `EMAIL_BACKEND= 'django.core.mail.backends.console.EmailBackend'` will log email content to console, which is often adequate for development. Other options are available. See Django docs for [sending email](https://docs.djangoproject.com/en/1.11/topics/email/).
* Set `SECRET_KEY` and `UNSUBSCRIBE_SECRET_KEY` each to (different) cryptographically secure random values.
    * Generate values with: `python -c "import base64; import os; print(base64.b64encode(os.urandom(30)).decode('utf-8'))"`
* Set `AUTHCODE_SECRET_KEY` to a 32 byte url-safe base64-encoded random string. This key is used for symmetrical encryption of authentication tokens.  If not defined, services like OAuth will not work. 
    * Generate a value with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"`
  
#### Additional configuration options
Set or adjust these values in your `settings_local.dev.py` and/or `settings_local.prod.py` file to further configure the application to your specific needs.
* `HELP_EMAIL`:
  - An email address for your support staff. The default is `help@badgr.io`.
* `BADGR_APPROVED_ISSUERS_ONLY`:
  - If you choose to use set this value to `True`, that means new user accounts will not be able to define new issuers (though they can be added as staff on issuers defined by others) unless they have the Django user permission 'issuer.add_issuer'. The recommended way to grant users this privilege is to create a group that grants it in the `/staff` admin area and addthe appropriate users to that group.
* `PINGDOM_MONITORING_ID`:
  - If you use [Pingdom](https://www.pingdom.com/) to monitor site performance, including this setting will embed Pingdom tracking script into the header.
* `CELERY_ALWAYS_EAGER`:
  - Setting this value to `True` causes Celery to immediately run tasks synchronously. Celery is an asynchronous task runner built into Django and Badgr. Advanced deployments may separate celery workers from web nodes for improved performance. For development environments where Celery tasks should run synchronously, set this flag to true. Very few time-intensive tasks are part of this repository, and eager is a safe setting for most production deploys.
* `OPEN_FOR_SIGNUP`:
  - Allows you to turn off signup through the API by setting to `False` if you would like to use Badgr for only single-account use or to manually create all users in `/staff`. The default is `True` (signup API is enabled). UX is not well-supported in the `/staff` interface.
* `DEFAULT_FILE_STORAGE` and `MEDIA_URL`:
  - Django supports various backends for storing media, as applicable for your deployment strategy. See Django docs on the [file storage API](https://docs.djangoproject.com/en/1.11/ref/files/storage/)
 
### Running the Django Server in Development

For development, it is usually best to run the project with the builtin django development server. The 
development server will reload itself in the docker container whenever changes are made to the code in `apps/`.

To run the project with docker in a development mode:

* `docker-compose up`: build and get django and other components running
* `docker-compose exec api python /badgr_server/manage.py migrate` - (while running) set up database tables
* `docker-compose exec api python /badgr_server/manage.py dist` - generate docs swagger file(s)
* `docker-compose exec api python /badgr_server/manage.py collectstatic` - Put built front-end assets into the static directory (Admin panel CSS, swagger docs).
* `docker-compose exec api python /badgr_server/manage.py createsuperuser` - follow prompts to create your first admin user account

### Running the Django Server in "Production"

By default `docker-compose` will look for a `docker-compose.yml` for instructions of what to do. This file
is the development (and thus default) config for `docker-compose`.

If you'd like to run the project with a more production-like setup, you can specify the `docker-compose.prod.yml` 
file. This setup **copies** the project code in (instead of mirroring) and uses nginx with uwsgi to run django.

* `docker-compose -f docker-compose.prod.yml up -d` - build and get django and other components (production mode)

* `docker-compose -f docker-compose.prod.yml exec api python /badgr_server/manage.py migrate` - (while running) set up database tables

If you are using the production setup and you have made changes you wish to see reflected in the running container,
you will need to stop and then rebuild the production containers:

* `docker-compose -f docker-compose.prod.yml build` - (re)build the production containers


### Accessing the Django Server Running in Docker

The development server will be reachable on port `8000`:

* http://localhost:8000/ (development)

The production server will be reachable on port `8080`:

* http://localhost:8080/ (production)

There are various examples of URLs in this readme and they all feature the development port. You will
need to adjust that if you are using the production server.

### First Time Setup
* Sign in to http://localhost:8000/staff/
* Add an `EmailAddress` object for your superuser. [Edit your super user](http://localhost:8000/staff/badgeuser/badgeuser/1/change/)
* Add an initial `TermsVersion` object

#### Badgr App Configuration
* Sign in to http://localhost:8000/staff
* View the "Badgr app" records and use the staff admin forms to create a BadgrApp. BadgrApp(s) describe the configuration that badgr-server needs to know about an associated installation of badgr-ui.

If your [badgr-ui](https://github.com/concentricsky/badgr-ui) is running on http://localhost:4000, use the following values:
* CORS: ensure this setting matches the domain on which you are running badgr-ui, including the port if other than the standard HTTP or HTTPS ports. `localhost:4000`
* Signup redirect: `http://localhost:4000/signup/`
* Email confirmation redirect: `http://localhost:4000/auth/login/`
* Forgot password redirect: `http://localhost:4000/change-password/`
* UI login redirect: `http://localhost:4000/auth/login/`
* UI signup success redirect: `http://localhost:4000/signup/success/`
* UI connect success redirect: `http://localhost:4000/profile/`
* Public pages redirect: `http://localhost:4000/public/`

#### Authentication Configuration
* [Create an OAuth2 Provider Application](http://localhost:8000/staff/oauth2_provider/application/add/) for the Badgr-UI to use with
    * Client id: `public`
    * Client type: Public
    * allowed scopes: `rw:profile rw:issuer rw:backpack`
    * Authorization grant type: Resource owner password-based
    * Name: `Badgr UI`
    * Redirect uris: blank (for Resource owner password-based. You can use this to set up additional OAuth applications that use authorization code token grants as well.)

### Install and run Badgr UI {#badgr-ui}
Start in your `badgr` directory and clone badgr-ui source code: `git clone https://github.com/concentricsky/badgr-ui.git badgr-ui`

For more details view the Readme for [Badgr UI](https://github.com/concentricsky/badgr-ui).
