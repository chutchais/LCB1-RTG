"# LCB1-RTG" 
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ssh_rtg
lcb1rtg
git pull origin main
docker-compose up -d --build


#Create Volumn RTG
1)Create volumes named "rtg"

>docker volume create --name rtg \
--opt type=none --opt device=/opt/rtg \
--opt o=bind

2)Check volume is exist
>docker volume ls

**must see volume name "rtg"

## Technician repair entry

Open `/maintenance/jobs/` (also linked from the maintenance dashboard).
The Thai-first screens support reporting a failure, starting/completing a repair,
and adding camera/gallery photos. Existing admin and report pages remain unchanged.

Create ordinary active Django users; staff/admin access is not required.
In Django admin, assign a technician group these maintenance permissions:
`view_failure`, `add_failure`, `change_failure`, and `add_failureimage`.
Users with only `view_failure` can read jobs but cannot change them.

New reports record the reporting user, receiving time, Bangkok operation date/shift,
and available equipment readings. Users select the job type (default `BD`) when reporting;
supervisors can classify the job and enter root cause/vendor/cost information in admin.
Starting and completing a repair record the current time; use admin for historical corrections.

Photos are optional and upload individually **after** the job is saved.
The phone interface resizes photos, shows previews/progress, and lets users retry
failed uploads without re-entering the job. Without JavaScript, save the job first,
then upload one photo at a time from its detail page. Ensure `MEDIA_ROOT` is writable
and your deployment serves `MEDIA_URL`, as for existing maintenance images.
The container installs Pillow through `src\requirements.txt`; rebuild it for this update.

## Technician workflow tests

Run from the repository root with the project's Python dependencies installed.
The test settings use an isolated in-memory SQLite database and local-memory cache,
without PostgreSQL, Redis, or MQTT services:

```powershell
python src\manage.py test maintenance.tests.TechnicianWorkflowTests --settings=rtg.test_settings
python src\manage.py test maintenance.tests.TechnicianWorkflowTests.test_invalid_photo_does_not_lose_job_and_valid_retry_works --settings=rtg.test_settings
python src\manage.py check --settings=rtg.test_settings
node --check src\static\js\technician.js
```