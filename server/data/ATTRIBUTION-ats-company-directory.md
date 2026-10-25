# Attribution — ATS Company Directory

UpdateApply’s full `company_board` catalog import uses the **ATS Company Directory**
published under the `lastroundai-hiring-data` namespace.

| | |
|---|---|
| **License** | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Publisher / crawl** | LastRound / fyrosofttech (July–August 2026 snapshot) |
| **DataHub** | https://datahub.io/lastroundai-hiring-data/lastroundai-hiring-data/ats-directory |
| **CSV used** | `lastroundai-ats-company-directory-2026-08.csv` |
| **GitHub** | https://github.com/fyrosofttech/lastroundai-hiring-data |
| **Kaggle mirror** | https://www.kaggle.com/datasets/umamaheshbandaru/ats-company-directory-9935-public-job-boards |

Import command (does **not** fetch jobs):

```bash
uv run updateapply-catalog import-directory --download
```

Slugs go stale; ingest quarantines 404s as `company_board.status = unavailable`.
Absence of a company is not proof that the company left that ATS.
